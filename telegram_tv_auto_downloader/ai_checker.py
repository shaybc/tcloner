import asyncio
import json
import logging
from typing import Any
from urllib import error, parse, request

from config import Config


LOGGER = logging.getLogger(__name__)


class EpisodeChecker:
    def __init__(self, config: Config) -> None:
        self.config = config

    async def check_episode(
        self,
        post_text: str,
        filename: str,
        tv_series_list: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        prompt = self._build_prompt(post_text, filename, tv_series_list)

        for attempt in range(1, 4):
            try:
                response_text = await self._call_gemini(prompt)
                LOGGER.info(
                    "AI response received (attempt=%s, model=%s): %s",
                    attempt,
                    self.config.ai_model,
                    response_text,
                )
                return self._parse_response(response_text)
            except Exception as exc:  # noqa: BLE001
                if attempt == 3:
                    LOGGER.warning("AI call failed after retries: %s", exc)
                    return None
                wait_seconds = 2 ** (attempt - 1)
                LOGGER.warning(
                    "AI call failed (attempt=%s), retrying in %ss: %s",
                    attempt,
                    wait_seconds,
                    exc,
                )
                await asyncio.sleep(wait_seconds)

        return None

    def _build_prompt(
        self,
        post_text: str,
        filename: str,
        tv_series_list: list[dict[str, Any]],
    ) -> str:
        return (
            "You are an episode extractor.\n"
            "Return ONLY valid JSON object or null.\n"
            "If this post does not match tracked series/seasons, return null.\n"
            "Use keys: series_name, season, episode, quality.\n"
            "Quality must be one of: 2160p, 4K, 1080p, 720p, 480p, SD, HDTV, unknown.\n"
            "Choose the best quality indicator if multiple exist.\n\n"
            f"Tracked series list:\n{json.dumps(tv_series_list, ensure_ascii=False)}\n\n"
            f"Post text:\n{post_text or ''}\n\n"
            f"Filename:\n{filename or ''}\n"
        )

    async def _call_gemini(self, prompt: str) -> str:
        LOGGER.info("AI request (model=%s): %s", self.config.ai_model, prompt)
        return await asyncio.to_thread(self._call_gemini_sync, prompt)

    def _call_gemini_sync(self, prompt: str) -> str:
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{parse.quote(self.config.ai_model)}:generateContent"
            f"?key={parse.quote(self.config.ai_api_key)}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 256,
                "responseMimeType": "application/json",
            },
        }

        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Gemini HTTP {exc.code}: {body}") from exc

        response_json = json.loads(raw)
        candidates = response_json.get("candidates") or []
        if not candidates:
            return "null"

        content = candidates[0].get("content", {})
        parts = content.get("parts") or []
        if not parts:
            return "null"

        first_text = parts[0].get("text", "").strip()
        return first_text or "null"

    def _parse_response(self, response_text: str) -> dict[str, Any] | None:
        if not response_text:
            return None

        cleaned = response_text.strip()
        if cleaned.lower() == "null":
            return None

        if "```" in cleaned:
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()

        parsed = json.loads(cleaned)
        if parsed is None:
            return None
        if not isinstance(parsed, dict):
            raise ValueError("AI response must be a JSON object or null")

        required_keys = {"series_name", "season", "episode", "quality"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError("AI response missing required keys")

        return parsed
