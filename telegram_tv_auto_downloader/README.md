# Telegram TV Series Auto-Downloader

Async Python app that monitors Telegram channels for TV episode posts, classifies candidate videos with AI, downloads matched episodes, and stores them in a season/series folder hierarchy.

## Features

- Catch-up mode for messages newer than each channel's saved `last_message_id`
- Live mode listener for newly posted Telegram messages
- AI-based episode extraction using Gemini API (default model: gemini-2.5-flash-lite)
- Highest-quality winner selection per episode (`4K/2160p > 1080p > 720p > 480p > unknown`)
- Atomic state persistence to `state.json`
- Download logging with progress percentage
- Windows-safe series folder/file naming

## Requirements

- Python 3.10+
- Telegram API credentials from [my.telegram.org/apps](https://my.telegram.org/apps)
- Access to at least one monitored Telegram channel
- Gemini API key (free API key supported)

Install dependencies:

```bash
pip install -r requirements.txt
```

## 1) Create `.env`

Create `.env` in this folder:

```env
# Telegram credentials
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890

# Channels to monitor (comma-separated list of channel usernames or IDs or invite links)
TELEGRAM_CHANNELS=@channel1,@channel2,-1001234567890

# AI API configuration
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash-lite
# Backward compatible aliases also supported:
# AI_API_KEY=your_gemini_api_key
# AI_MODEL=gemini-2.5-flash-lite

# TV Series to track (JSON format)
TV_SERIES=[
  {"name": "The Neighborhood", "seasons": [8]},
  {"name": "Yellowstone", "seasons": [5, 6]}
]

# Storage
TV_ROOT_FOLDER=Z:\\tv
TEMP_FOLDER=C:\\temp\\tv_downloads

# Polling interval in seconds (catch-up interval metadata)
POLL_INTERVAL=300

# Telegram anti-flood tuning (optional)
TELEGRAM_MIN_REQUEST_INTERVAL=0.5
TELEGRAM_FLOOD_MAX_SLEEP_SECONDS=900

# Optional
DEBUG=false
STATE_FILE=state.json
LOG_FILE=app.log
TELEGRAM_SESSION_FILE=telegram_session
```

## 2) Run

```bash
python main.py
```

On first run Telethon will prompt for OTP / 2FA as needed and create `telegram_session*` files.

## State format

`state.json` structure:

```json
{
  "last_message_ids": {
    "@channel1": 12345
  },
  "downloaded_episodes": {
    "The Neighborhood": ["S08E12"]
  }
}
```

## Notes

- Download failures do not mark episodes as downloaded.
- File-system failures are logged as `CRITICAL`.
- Press `Ctrl+C` to stop gracefully; state is saved before exit.
- Anti-flood: the monitor handles Telegram `FloodWait` by sleeping and retrying, and applies a minimum gap between sensitive API calls.
