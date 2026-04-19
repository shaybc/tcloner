import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError
from telethon.tl.types import DocumentAttributeFilename, Message

from ai_checker import EpisodeChecker
from config import Config
from downloader import download_episode
from state_manager import StateManager


LOGGER = logging.getLogger(__name__)
QUALITY_SCORES = {
    "2160p": 4,
    "4k": 4,
    "1080p": 3,
    "720p": 2,
    "480p": 1,
    "sd": 1,
    "hdtv": 1,
    "unknown": 0,
}


@dataclass
class PendingEpisode:
    quality_score: int
    message: Message
    meta: dict[str, Any]


class TelegramMonitor:
    def __init__(
        self,
        config: Config,
        state_manager: StateManager,
        checker: EpisodeChecker,
    ) -> None:
        self.config = config
        self.state_manager = state_manager
        self.checker = checker
        self.client = TelegramClient(
            config.session_file,
            config.telegram_api_id,
            config.telegram_api_hash,
        )
        self._pending_live: dict[tuple[str, str], PendingEpisode] = {}
        self._api_lock = asyncio.Lock()
        self._last_api_request_ts = 0.0

    async def start(self) -> None:
        await self._start_with_retry()
        await self._catch_up()
        await self._start_live_listener()

    async def _start_with_retry(self) -> None:
        delay = 1
        while True:
            try:
                await self._throttled_call(self.client.start, phone=self.config.telegram_phone)
                LOGGER.info("Connected to Telegram")
                return
            except FloodWaitError as exc:
                await self._handle_flood_wait(exc, "client.start")
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Telegram connection failed, retrying in %ss: %s", delay, exc)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)

    async def _catch_up(self) -> None:
        for channel in self.config.telegram_channels:
            LOGGER.info("Catch-up started for channel: %s", channel)
            winners: dict[tuple[str, str], PendingEpisode] = {}
            highest_seen_id = self.state_manager.get_last_message_id(channel)
            last_id = highest_seen_id

            while True:
                try:
                    async for message in self.client.iter_messages(channel, min_id=last_id, reverse=True):
                        highest_seen_id = max(highest_seen_id, int(message.id or 0))
                        if not self._is_video_message(message):
                            continue

                        processed = await self._classify_message(message, channel)
                        if not processed:
                            continue
                        key = (processed["series_name"], processed["episode_code"])
                        current = winners.get(key)
                        if not current or processed["quality_score"] > current.quality_score:
                            winners[key] = PendingEpisode(
                                quality_score=processed["quality_score"],
                                message=message,
                                meta=processed,
                            )
                    break
                except FloodWaitError as exc:
                    await self._handle_flood_wait(exc, f"iter_messages({channel})")

            for winner in winners.values():
                await self._download_if_needed(winner.message, winner.meta)

            if highest_seen_id > last_id:
                self.state_manager.set_last_message_id(channel, highest_seen_id)
                LOGGER.info("Updated last_message_id for %s -> %s", channel, highest_seen_id)

    async def _start_live_listener(self) -> None:
        @self.client.on(events.NewMessage(chats=self.config.telegram_channels))
        async def handler(event) -> None:
            message = event.message
            channel = str(event.chat_id)
            if not self._is_video_message(message):
                return

            processed = await self._classify_message(message, channel)
            if not processed:
                return

            key = (processed["series_name"], processed["episode_code"])
            current = self._pending_live.get(key)
            if current and processed["quality_score"] <= current.quality_score:
                LOGGER.info("Skipping lower/equal quality duplicate in live mode: %s", key)
                return

            self._pending_live[key] = PendingEpisode(
                quality_score=processed["quality_score"],
                message=message,
                meta=processed,
            )
            await self._download_if_needed(message, processed)

            self.state_manager.set_last_message_id(channel, int(message.id or 0))

        LOGGER.info("Live listener started")
        await self.client.run_until_disconnected()

    def _is_video_message(self, message: Message) -> bool:
        if getattr(message, "video", None):
            return True
        mime_type = getattr(getattr(message, "file", None), "mime_type", "") or ""
        return mime_type.startswith("video/")

    def _extract_filename(self, message: Message) -> str:
        if getattr(getattr(message, "file", None), "name", None):
            return str(message.file.name)
        document = getattr(message, "document", None)
        if not document:
            return ""
        for attribute in getattr(document, "attributes", []):
            if isinstance(attribute, DocumentAttributeFilename):
                return attribute.file_name
        return ""

    async def _classify_message(
        self,
        message: Message,
        channel: str,
    ) -> dict[str, Any] | None:
        post_text = message.message or ""
        filename = self._extract_filename(message)
        result = await self.checker.check_episode(post_text, filename, self.config.tv_series)

        if result is None:
            LOGGER.info("Skipped message %s in %s: no tracked episode match", message.id, channel)
            return None

        series_name = str(result["series_name"])
        season = int(result["season"])
        episode = int(result["episode"])
        quality = str(result.get("quality", "unknown"))
        quality_score = QUALITY_SCORES.get(quality.lower(), 0)
        episode_code = f"S{season:02d}E{episode:02d}"

        if self.state_manager.is_downloaded(series_name, episode_code):
            LOGGER.info("Skipped %s %s: already downloaded", series_name, episode_code)
            return None

        return {
            "series_name": series_name,
            "season": season,
            "episode": episode,
            "quality": quality,
            "quality_score": quality_score,
            "episode_code": episode_code,
        }

    async def _download_if_needed(self, message: Message, meta: dict[str, Any]) -> None:
        ok = await download_episode(
            self.client,
            message,
            self.config,
            meta["series_name"],
            meta["season"],
            meta["episode"],
            meta["episode_code"],
        )
        if ok:
            self.state_manager.mark_downloaded(meta["series_name"], meta["episode_code"])
            LOGGER.info(
                "Downloaded and marked state: %s %s",
                meta["series_name"],
                meta["episode_code"],
            )
        else:
            LOGGER.warning(
                "Download failed, state not updated: %s %s",
                meta["series_name"],
                meta["episode_code"],
            )

    async def _throttled_call(self, func, *args, **kwargs):
        async with self._api_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            remaining = self.config.telegram_min_request_interval - (now - self._last_api_request_ts)
            if remaining > 0:
                await asyncio.sleep(remaining)

            result = await func(*args, **kwargs)
            self._last_api_request_ts = loop.time()
            return result

    async def _handle_flood_wait(self, exc: FloodWaitError, context: str) -> None:
        sleep_seconds = int(getattr(exc, "seconds", 0)) + 1
        capped_sleep = min(sleep_seconds, self.config.telegram_flood_max_sleep_seconds)
        LOGGER.warning(
            "Telegram flood-wait in %s. waiting %ss (requested=%ss, cap=%ss)",
            context,
            capped_sleep,
            sleep_seconds,
            self.config.telegram_flood_max_sleep_seconds,
        )
        await asyncio.sleep(capped_sleep)

    async def stop(self) -> None:
        self.state_manager.save()
        if self.client.is_connected():
            await self.client.disconnect()
        LOGGER.info("Monitor stopped and state saved")
