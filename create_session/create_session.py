
import logging
import os
import sys
import dotenv
import telethon.sync


# this app uses python client for Telegram API called Telethon
# https://docs.telethon.dev/en/latest/


###############   CREATE TELEGRAM APP_ID AND APP_HASH   ################
# open: https://core.telegram.org/api/obtaining_api_id
# perform login with your phone number
# then goto: https://my.telegram.org/apps (API development tools)
# fill in app name (don't use test or sinple name or you will get an error)
# fill in short app name (the same as app name)
# fill the rest of the fields (some dummy https url, description, etc)
# get the API_ID and API_HASH from the resulting page


###############   CREATE TELEGRAM SESSION FILE   ################
# fill the APP_ID and APP_HASH in the .env file
# fill the PHONE number in the .env file
# make sure the telegram_session_filename in the .env file is set to a unique name for each session file
# run py .\create_session.py
# enter your phone number (with country code)
# enter the OTP code you received in the telegram app
# enter your password
# a message will be sent to your telegram account to create a new login session
# if successful, the session will be saved to a file named to whatever you set in the .env file under `telegram_session_filename`
# the saved session file can be copied and used in your python application (without the need to login again)


###############   CREATE TELEGRAM BOT (not required)   ################
# open telegram dewsktop client
# go to BotFather at: https://t.me/BotFather
# create a new bot by sending the command: /newbot
# write the app name (for example: MyTestApp)
# write the app username that must end with 'bot' (for example: MyTestApp_bot)
# you will receive a token that looks like this: 1234567890:ABCdefGhIjKlMnOpQrStUvWxYz
# copy the first part of the token (before the colon) - this is your API_ID
# copy the second part of the token (after the colon) - this is your API_HASH




# load environment variables from .env file
dotenv.load_dotenv(".env", override=True, encoding='utf-8')

# load environment variables from .env file into variables
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")
logFilename = os.getenv("logFilename")
telegram_session_filename = os.getenv("telegram_session_filename")

# print all the loaded environment variables
print(f"API_ID: {api_id}")
print(f"API_HASH: {api_hash}")
print(f"PHONE: {phone}")
print(f"logFilename: {logFilename}")
print(f"telegram_session_filename: {telegram_session_filename}")

# init the telegram client
client = telethon.sync.TelegramClient(session=telegram_session_filename, api_id=api_id, api_hash=api_hash) # create a Telegram client

async def main():
    global client, logFilename
    
    # make sure the folder to logFilename file exist
    os.makedirs(os.path.dirname(logFilename), exist_ok=True)
    
    # configure logging, both to a file and to the console
    logging.basicConfig(filename=logFilename, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    
    # Connect to Telegram via the client
    logging.info("Connecting to Telegram...")
    await client.start(phone=phone)
    logging.info("Done - Connected to Telegram Client !")
    logging.info("Session file saved as: " + telegram_session_filename)


# Call the main function
if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
