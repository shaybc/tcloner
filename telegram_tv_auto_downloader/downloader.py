import asyncio
import logging
import os
import shutil
from pathlib import Path

from telethon.errors import FloodWaitError

from config import Config


LOGGER = logging.getLogger(__name__)
INVALID_WINDOWS_CHARS = '\\/:*?"<>|'


def sanitize_series_name(name: str) -> str:
    return "".join("_" if ch in INVALID_WINDOWS_CHARS else ch for ch in name).strip()


def _extract_extension(filename: str | None, mime_type: str | None) -> str:
    if filename:
        suffix = Path(filename).suffix
        if suffix:
            return suffix.lower()
    if mime_type and "/" in mime_type:
        guessed = mime_type.split("/")[-1].lower()
        if guessed == "x-matroska":
            return ".mkv"
        return f".{guessed}"
    return ".mp4"


async def download_episode(
    client,
    message,
    config: Config,
    series_name: str,
    season: int,
    episode: int,
    episode_code: str,
) -> bool:
    safe_series = sanitize_series_name(series_name)
    original_filename = getattr(getattr(message, "file", None), "name", None)
    mime_type = getattr(getattr(message, "file", None), "mime_type", None)
    extension = _extract_extension(original_filename, mime_type)

    os.makedirs(config.temp_folder, exist_ok=True)

    final_filename = f"{safe_series} {episode_code}{extension}"
    season_folder = f"{safe_series} S{season:02d}"
    destination_dir = os.path.join(config.tv_root_folder, safe_series, season_folder)
    destination_path = os.path.join(destination_dir, final_filename)

    temp_target = os.path.join(config.temp_folder, final_filename)

    def on_progress(downloaded: int, total: int) -> None:
        percent = (downloaded / total * 100) if total else 0
        LOGGER.info(
            "Downloading %s: %.2f%% (%s/%s bytes)",
            final_filename,
            percent,
            downloaded,
            total,
        )

    try:
        LOGGER.info("Starting download for %s", final_filename)
        downloaded_path = None
        for attempt in range(1, 4):
            try:
                downloaded_path = await client.download_media(
                    message,
                    file=temp_target,
                    progress_callback=on_progress,
                )
                break
            except FloodWaitError as exc:
                sleep_seconds = min(
                    int(getattr(exc, "seconds", 0)) + 1,
                    config.telegram_flood_max_sleep_seconds,
                )
                LOGGER.warning(
                    "Flood-wait while downloading %s (attempt=%s). Sleeping %ss",
                    final_filename,
                    attempt,
                    sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)

        if not downloaded_path:
            LOGGER.error("Download returned empty path for %s", final_filename)
            return False

        os.makedirs(destination_dir, exist_ok=True)
        shutil.move(downloaded_path, destination_path)
        LOGGER.info("Download complete: %s", destination_path)
        return True
    except OSError as exc:
        LOGGER.critical("Filesystem error while downloading %s: %s", final_filename, exc)
        return False
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Download failed for %s: %s", final_filename, exc)
        return False
