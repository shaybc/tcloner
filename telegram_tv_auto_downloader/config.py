import json
import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv


@dataclass(slots=True)
class Config:
    telegram_api_id: int
    telegram_api_hash: str
    telegram_phone: str
    telegram_channels: list[str]
    ai_api_key: str
    ai_model: str
    tv_series: list[dict[str, Any]]
    tv_root_folder: str
    temp_folder: str
    poll_interval: int
    telegram_min_request_interval: float = 0.5
    telegram_flood_max_sleep_seconds: int = 900
    debug: bool = False
    state_file: str = "state.json"
    log_file: str = "app.log"
    session_file: str = "telegram_session"


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


def _parse_series(raw: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"TV_SERIES must be valid JSON: {exc}") from exc

    if not isinstance(parsed, list) or not parsed:
        raise ConfigError("TV_SERIES must be a non-empty JSON array")

    validated: list[dict[str, Any]] = []
    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ConfigError(f"TV_SERIES[{idx}] must be an object")
        name = str(item.get("name", "")).strip()
        seasons = item.get("seasons")
        if not name:
            raise ConfigError(f"TV_SERIES[{idx}] is missing 'name'")
        if not isinstance(seasons, list) or not seasons:
            raise ConfigError(f"TV_SERIES[{idx}] must include non-empty 'seasons' list")

        season_values: list[int] = []
        for season in seasons:
            if not isinstance(season, int):
                raise ConfigError(f"TV_SERIES[{idx}].seasons entries must be integers")
            season_values.append(season)

        validated.append({"name": name, "seasons": season_values})
    return validated


def _required(key: str) -> str:
    value = os.getenv(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required environment variable: {key}")
    return value


def load_config() -> Config:
    load_dotenv()

    telegram_channels = [
        channel.strip()
        for channel in _required("TELEGRAM_CHANNELS").split(",")
        if channel.strip()
    ]
    if not telegram_channels:
        raise ConfigError("TELEGRAM_CHANNELS must include at least one channel")

    poll_interval_raw = os.getenv("POLL_INTERVAL", "300").strip()
    try:
        poll_interval = int(poll_interval_raw)
    except ValueError as exc:
        raise ConfigError("POLL_INTERVAL must be an integer") from exc

    try:
        api_id = int(_required("TELEGRAM_API_ID"))
    except ValueError as exc:
        raise ConfigError("TELEGRAM_API_ID must be an integer") from exc

    min_request_interval_raw = os.getenv("TELEGRAM_MIN_REQUEST_INTERVAL", "0.5").strip()
    try:
        min_request_interval = float(min_request_interval_raw)
    except ValueError as exc:
        raise ConfigError("TELEGRAM_MIN_REQUEST_INTERVAL must be a float") from exc
    if min_request_interval < 0:
        raise ConfigError("TELEGRAM_MIN_REQUEST_INTERVAL must be >= 0")

    max_flood_sleep_raw = os.getenv("TELEGRAM_FLOOD_MAX_SLEEP_SECONDS", "900").strip()
    try:
        max_flood_sleep = int(max_flood_sleep_raw)
    except ValueError as exc:
        raise ConfigError("TELEGRAM_FLOOD_MAX_SLEEP_SECONDS must be an integer") from exc
    if max_flood_sleep < 1:
        raise ConfigError("TELEGRAM_FLOOD_MAX_SLEEP_SECONDS must be >= 1")

    tv_series = _parse_series(_required("TV_SERIES"))
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or _required("AI_API_KEY")
    ai_model = os.getenv("GEMINI_MODEL", "").strip() or os.getenv("AI_MODEL", "").strip() or "gemini-2.5-flash-lite"

    return Config(
        telegram_api_id=api_id,
        telegram_api_hash=_required("TELEGRAM_API_HASH"),
        telegram_phone=_required("TELEGRAM_PHONE"),
        telegram_channels=telegram_channels,
        ai_api_key=api_key,
        ai_model=ai_model,
        tv_series=tv_series,
        tv_root_folder=_required("TV_ROOT_FOLDER"),
        temp_folder=_required("TEMP_FOLDER"),
        poll_interval=poll_interval,
        telegram_min_request_interval=min_request_interval,
        telegram_flood_max_sleep_seconds=max_flood_sleep,
        debug=os.getenv("DEBUG", "false").lower() == "true",
        state_file=os.getenv("STATE_FILE", "state.json"),
        log_file=os.getenv("LOG_FILE", "app.log"),
        session_file=os.getenv("TELEGRAM_SESSION_FILE", "telegram_session"),
    )
