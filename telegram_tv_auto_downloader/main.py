import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler

from ai_checker import EpisodeChecker
from config import ConfigError, load_config
from state_manager import StateManager
from telegram_monitor import TelegramMonitor


def setup_logging(debug: bool, log_file: str) -> None:
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    level = logging.DEBUG if debug else logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


async def run() -> None:
    config = load_config()
    setup_logging(config.debug, config.log_file)

    logger = logging.getLogger(__name__)
    logger.info("Starting Telegram TV series auto-downloader")

    state_manager = StateManager(config.state_file)
    checker = EpisodeChecker(config)
    monitor = TelegramMonitor(config, state_manager, checker)

    try:
        await monitor.start()
    finally:
        await monitor.stop()


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        raise SystemExit(1) from exc
    except KeyboardInterrupt:
        print("Shutdown requested. State saved.")
