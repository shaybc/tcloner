# tcloner

`tcloner` clones Telegram channel media messages from one channel to another using Telethon.

## Prerequisites (Windows)

- Python installed (`py` command available in CMD)
- A Telegram API ID / API HASH from https://my.telegram.org/apps
- This repository cloned locally (example path used below: `C:\GitHub\shaybc\tcloner`)

## 1) Open CMD and go to the project folder

```cmd
cd /d C:\GitHub\shaybc\tcloner
```

## 2) Create and activate a virtual environment

Create venv (one-time):

```cmd
py -m venv .venv
```

Activate it each time before running:

```cmd
.venv\Scripts\activate
```

Install dependencies (one-time per venv):

```cmd
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

## 3) Set `.env` source and destination channels

Create or edit `.env` in the project root (`C:\GitHub\shaybc\tcloner\.env`) and set at least these values:

```env
API_ID=your_api_id
API_HASH=your_api_hash
PHONE=+972XXXXXXXXX

logFilename=logs/app.log
telegram_session_filename=telegram.session

src_channel_invite_links=https://t.me/+SOURCE_LINK
dest_channel_invite_link=https://t.me/+DESTINATION_LINK

message_tracker_filename=message_tracker.pkl
require_min_size=false
delay_between_reads=2
listen_to_chats=false
```

Notes:
- `src_channel_invite_links` supports multiple links separated by commas.
- Keep `telegram_session_filename` as a file name/path you can persist.

## 4) Store/login session (first time)

Run the session creator and complete Telegram login (OTP + password if enabled):

```cmd
py create_session\create_session.py
```

This stores the session file defined by `telegram_session_filename` in `.env`.

## 5) Run the cloner

```cmd
py main.py
```

The script reads from `src_channel_invite_links` and forwards to `dest_channel_invite_link`.

## Daily run (after first-time setup)

```cmd
cd /d C:\GitHub\shaybc\tcloner
.venv\Scripts\activate
py main.py
```
