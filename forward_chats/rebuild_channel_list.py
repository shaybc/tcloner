import dotenv
import os
import logging
import json
import base64
from io import BytesIO
import telethon.sync

from common.utils import anti_flood
from common.utils import delete_channel_history
from common.utils import init_logger

# this function loads all the environment variables from the .env file into global variables
# it does that using the dotenv library
# it also init other global variables
def init_env_vars():
    global api_id, api_hash, phone, logFilename, telegram_session_filename, dest_channel_invite_link, delay_between_reads, message_filename
    
    # load environment variables from .env file
    dotenv.load_dotenv(".env", override=True)

    # load environment variables from .env file into variables
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE")
    logFilename = os.getenv("logFilename")
    message_filename = os.getenv("message_filename")
    telegram_session_filename = os.getenv("telegram_session_filename")
    dest_channel_invite_link = os.getenv("dest_channel_invite_link")
    delay_between_reads = int(os.getenv("delay_between_reads"))


# this function prints all the environment variables to the log file
# and the console (using the logging library)
# it is printed at the beginning of the script in each run
def print_env_vars():
    global api_id, api_hash, phone, logFilename, telegram_session_filename, dest_channel_invite_link, delay_between_reads, message_filename
    
    # log all the loaded environment variables
    logging.info("Starting 'Channel Cloner' - Telegram channel backup content from one channel to another by forwarding messages")
    logging.info(" ")
    logging.info("#############################################################")
    logging.info("#             Loaded Environment Variables:                 #")
    logging.info("#############################################################")
    logging.info(f"API_ID: {api_id}")
    logging.info(f"API_HASH: {api_hash}")
    logging.info(f"PHONE: {phone}")
    logging.info(f"logFilename: {logFilename}")
    logging.info(f"message_filename: {message_filename}")
    logging.info(f"telegram_session_filename: {telegram_session_filename}")
    logging.info(f"dest_channel_invite_link: {dest_channel_invite_link}")
    logging.info(f"delay_between_reads: {delay_between_reads}")
    logging.info("#############################################################")
    logging.info(" ")


# this function init the app
# it calls all the init functions
# and init the telegram client
def initApp():
    global client, telegram_session_filename, api_id, api_hash, logFilename
    
    # init the environment variables
    init_env_vars()

    # init the logger
    init_logger(logFilename)

    # print the environment variables to the log file and the console
    print_env_vars()

    # init the telegram client
    logging.info("Creating Telegram Client...")
    client = telethon.sync.TelegramClient(session=telegram_session_filename, api_id=api_id, api_hash=api_hash) # create a Telegram client
    logging.info("Done - Creating Telegram Client !")


# this function starts the telegram client and connects to telegram
async def startClient():
    global client
    
    # Connect to Telegram via the client
    logging.info("Starting Telegram Client ...")
    await client.start()
    logging.info("Done - Telegram Client Started !")


# this function is the main function of the script
# it implements the main logic of finding the channels that stored in the source telegram custom folder
# and fetch each channel's link and description and forward it to the destination channel as a text message
async def main():
    global client, dest_channel_invite_link, message_filename

    # get destination group entity
    dest_chat_entity = await client.get_entity(dest_channel_invite_link)
        
    # if the file already exists, delete it
    if not os.path.exists(message_filename):
        logging.error(f"File {message_filename} does not exist")
        return
    
    # Read the channels array json from the JSON file
    with open(message_filename, 'r', encoding='utf-8') as json_file:
        messages_json = json_file.read()
    
    # parse the json string to a json object
    messages_json = json.loads(messages_json)
    
    # delete the history of the destination channel
    await delete_channel_history(client, dest_chat_entity)

    # loop over all the json array entries and construct a message for each entry and send it to the destination channel
    for message in messages_json:
        # get the image base64 from the message
        image_base64 = message["image_base64"]
        
        # get the channel title from the message
        channel_title = message["channel_title"]
        
        # get the participants count from the message
        participants_count = message["participants_count"]
        formatted_users = "{:,}".format(participants_count)
        
        # get the file count from the message
        file_count = message["file_count"]
        formatter_files = "{:,}".format(file_count)
        
        # get the video count from the message
        video_count = message["video_count"]
        formatted_videos = "{:,}".format(video_count)
        
        # get the voice count from the message
        voice_count = message["voice_count"]
        formatted_voice = "{:,}".format(voice_count)
        
        # get the audio count from the message
        audio_count = message["audio_count"]
        formatted_audio = "{:,}".format(audio_count)
        
        # get the link count from the message
        link_count = message["link_count"]
        formatted_links = "{:,}".format(link_count)
        
        # get the status from the message
        status = message["status"]
        
        # get the date from the message
        date = message["date"]
        
        # get the chat type from the message
        chat_type = message["chat_type"]
        
        # get the chat description from the message
        chat_description = message["chat_description"]
        
        # get the chat link from the message
        chat_link = message["chat_link"]
        
        # create the message description if the chat description is not empty
        message_description = f"<pre language=\"c++\">\n{chat_description}\n</pre>\n" if chat_description else ""
        
        # create and format the message to send that describes the current channel details
        message_to_send = f"\n\n<b>{channel_title}</b>\n\n \
{status} הערוץ פעיל (נבדק ב: {date}) \n \
📣 <b>סוג ערוץ</b>: {chat_type}\n \
👤 <b>משתמשים</b>: {formatted_users}\n \
📄 <b>קבצים</b>: {formatter_files}\n \
🎬 <b>וידאו</b>: {formatted_videos}\n \
🎤 <b>הקלטות</b>: {formatted_voice}\n \
🎵 <b>אודיו</b>: {formatted_audio}\n \
🔗 <b>לינקים</b>: {formatted_links}\n\n \
💬 <b>פרטים</b>: {message_description}\n \
⬅️ <b>לינק</b>: {chat_link}\n \
."

        # Decode the base64 image data
        image_data = base64.b64decode(image_base64)
        
        # Create a BytesIO object from the decoded image data
        image = BytesIO(image_data)
        
        # Upload the base64-encoded image
        anti_flood()
        uploaded_photo = await client.upload_file(image, file_name='image.jpg')

        # send the message to the destination channel with the base64 image in html format 
        await client.send_message(entity=dest_chat_entity, file=uploaded_photo, message=message_to_send, silent=True, parse_mode='html')


# Call the main function
if __name__ == "__main__":
    # init the app
    initApp()
    
    # with client:
    client.loop.run_until_complete(startClient())

    client.loop.run_until_complete(main())
