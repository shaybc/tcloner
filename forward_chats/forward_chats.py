import dotenv
import os
import logging
import time
import json
import base64
from io import BytesIO
import telethon.sync
from telethon import functions
from telethon.tl.types import Channel, Chat, ChatFull, DialogFilterDefault, InputMessagesFilterDocument, InputMessagesFilterVideo, InputMessagesFilterUrl, InputMessagesFilterVoice, InputMessagesFilterRoundVoice, InputMessagesFilterMusic
from telethon.tl.functions.channels import GetFullChannelRequest
from common.utils import anti_flood, init_logger, search_telegram, delete_channel_history


# this function loads all the environment variables from the .env file into global variables
# it does that using the dotenv library
# it also init other global variables
def init_env_vars():
    global api_id, api_hash, phone, logFilename, telegram_session_filename, source_folder, dest_channel_invite_link, delay_between_reads, message_filename
    
    # load environment variables from .env file
    dotenv.load_dotenv(".env", override=True, encoding='utf8')

    # load environment variables from .env file into variables
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE")
    logFilename = os.getenv("logFilename")
    message_filename = os.getenv("message_filename")
    telegram_session_filename = os.getenv("telegram_session_filename")
    source_folder = os.getenv("source_folder")
    dest_channel_invite_link = os.getenv("dest_channel_invite_link")
    delay_between_reads = int(os.getenv("delay_between_reads"))


# this function prints all the environment variables to the log file
# and the console (using the logging library)
# it is printed at the beginning of the script in each run
def print_env_vars():
    global api_id, api_hash, phone, logFilename, telegram_session_filename, source_folder, dest_channel_invite_link, delay_between_reads, message_filename
    
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
    logging.info(f"src_channel_invite_links: {source_folder}")
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
    global client, source_folder, dest_channel_invite_link, message_filename

    # get destination group entity
    dest_chat_entity = await client.get_entity(dest_channel_invite_link)
    
    # delete the history of the destination channel
    await delete_channel_history(client, dest_chat_entity)
    
    # open the default channel image file and read its daata as bytes array
    with open('.\\default_channel_photo.jpg', 'rb') as f:
        image_data = f.read()
        
    # Encode the image data as base64 string
    default_image_base64 = base64.b64encode(image_data).decode('utf-8')
    
    # get all the dialog filters (all custom folders and the default folder)
    request = await client(functions.messages.GetDialogFiltersRequest())
    
    # loop over all the custom folders
    for dialog_filter in request:
        # logging.info(f'\n\nFolder:\n\n {dialog_filter}\n\n-------------------')
        
        # if the current folder is the source folder
        if not isinstance(dialog_filter, DialogFilterDefault) and dialog_filter.title == source_folder:
            # logging.info("Folder: " + dialog_filter.title)
                        
            # if the file already exists, delete it
            if os.path.exists(message_filename):
                os.remove(message_filename)
            
            # Save the array open in the JSON file
            with open(message_filename, 'w', encoding='utf-8') as json_file:
                json_file.write('[\n')
            
            # loop over all the chats in the source folder
            for chat in dialog_filter.include_peers:    
                # logging.info("Chat: " + str(chat))
                
                # prevent flood alert from telegram
                anti_flood()
                
                # get the chat/channel entity object
                channel_entity = await client.get_entity(chat)
                logging.info("Chat Entity: " + str(channel_entity))
                
                if isinstance(channel_entity, Channel) or isinstance(channel_entity, Chat):
                    # Get full information about the chat/channel
                    channel_full_info: ChatFull = await client(GetFullChannelRequest(channel=channel_entity))
                    # logging.info("Full Chat Info: " + str(channel_full_info))
                    
                    # get the chat description
                    chat_description = channel_full_info.full_chat.about
                    
                    # get the number of users in the chat
                    users_count = channel_full_info.full_chat.participants_count
                    logging.info(f"{chat_link} -- {channel_entity.title}")
                else:
                    chat_description = "לא נמצא תיאור"
                    users_count = 1
                
                # get the chat link
                chat_link = 'no link available'
                if hasattr(channel_entity, 'username') and channel_entity.username is not None:
                    chat_link = f'https://t.me/{channel_entity.username}'
                elif "https://" in chat_description:
                    chat_link = chat_description
                elif channel_full_info and channel_full_info.full_chat.exported_invite:
                    invite_link = channel_full_info.full_chat.exported_invite
                    chat_link = invite_link.link
                    # logging.info(f'invite link: {invite_link}')
                else:
                    chat_link = "לא נמצא לינק, יש לחפש ידנית"
                    logging.info("----- No link available for: " + channel_entity.title)
                
                is_channel = channel_entity.broadcast # broadcast is a channel with less than 100,000 members and only admins can post
                is_supergroup = channel_entity.megagroup # supergroup is a channel with 100,000 to 200,000 members, and have topics
                is_gigagroup = channel_entity.gigagroup # gigagroups channel with more then 200,000 members
                is_private = True if channel_entity.username is None else False

                # Check if the entity is a Channel or a Chat
                if isinstance(channel_entity, Channel):
                    chat_type = "ערוץ (רק מנהלים יכולים לפרסם)"
                elif isinstance(channel_entity, Chat):
                    chat_type = "קבוצה"
                else:
                   chat_type = "משתמש"
                                
                # if is_channel:
                #     chat_type = "עד 100,000 משתמשים " + chat_type
                # elif is_supergroup:
                #     chat_type = "סופר קבוצה (עד 200,000 משתמשים + חלוקה לנושאים) - Supergroup" + chat_type
                # elif is_gigagroup:
                #     chat_type = "גיגה קבוצה (מעל 200,000 משתמשים) - Gigagroup" + chat_type
                
                if is_private:
                    chat_type = "(פרטי) " + chat_type
                else:
                    chat_type = "(ציבורי) " + chat_type
                    
                
                # Get the number of documents/files in the channel
                channel_documents = await search_telegram(client=client, channel_entity=channel_entity, filter=InputMessagesFilterDocument())
                file_count = channel_documents.count
                
                # prevent flood alert from telegram
                anti_flood()

                # Get the number of video/media in the channel
                channel_videos = await search_telegram(client=client, channel_entity=channel_entity, filter=InputMessagesFilterVideo())
                video_count = channel_videos.count
                
                # prevent flood alert from telegram
                anti_flood()

                # Get the number of video/media in the channel
                channel_voice = await search_telegram(client=client, channel_entity=channel_entity, filter=InputMessagesFilterVoice())
                voice_count = channel_voice.count
                
                # prevent flood alert from telegram
                anti_flood()

                # Get the number of video/media in the channel
                channel_audio = await search_telegram(client=client, channel_entity=channel_entity, filter=InputMessagesFilterRoundVoice())
                audio_count = channel_audio.count
                
                # prevent flood alert from telegram
                anti_flood()

                # Get the number of video/media in the channel
                channel_links = await search_telegram(client=client, channel_entity=channel_entity, filter=InputMessagesFilterUrl())
                link_count = channel_links.count
                
                # create the message description if the chat description is not empty
                message_description = f"<pre language=\"c++\">\n{chat_description}\n</pre>\n" if chat_description else ""
 
                formatted_users = "{:,}".format(users_count)
                formatter_files = "{:,}".format(file_count)
                formatted_videos = "{:,}".format(video_count)
                formatted_voice = "{:,}".format(voice_count)
                formatted_audio = "{:,}".format(audio_count)
                formatted_links = "{:,}".format(link_count)
 
                # create and format the message to send that describes the current channel details
                message_to_send = f"\n\n<b>{channel_entity.title}</b>\n\n \
✅ הערוץ פעיל (נבדק ב: {time.strftime('%d/%m/%y')}) \n \
🔢 <b>סוג הערוץ</b>: {chat_type}\n \
👤 <b>משתמשים</b>: {formatted_users}\n \
📄 <b>קבצים</b>: {formatter_files}\n \
🎬 <b>וידאו</b>: {formatted_videos}\n \
🎤 <b>הקלטות</b>: {formatted_voice}\n \
🎵 <b>אודיו</b>: {formatted_audio}\n \
🔗 <b>לינקים</b>: {formatted_links}\n\n \
💬 <b>פרטים</b>: {message_description}\n \
⬅️ <b>לינק</b>: {chat_link}\n \
."
 
                # Download the profile image into memory in a BytesIO object
                image = BytesIO()
                await client.download_profile_photo(entity=channel_entity, file=image)
                
                # check if the image is not empty
                if image.getbuffer().nbytes == 0:
                    # if the image is empty, use the default image
                    image = BytesIO(base64.b64decode(default_image_base64))
                else:
                    # if the image is not empty, use the downloaded image
                    image.seek(0)
                
                # Get the bytes data of the image
                image_data = image.getvalue()
                
                # Encode the image data as base64
                image_base64 = base64.b64encode(image_data).decode('utf-8')

                # Create a dictionary to store the message data
                message_data = {
                    "image_base64": image_base64,  # Base64-encoded image data
                    "channel_title": channel_entity.title,
                    "participants_count": users_count,
                    "file_count": file_count,
                    "video_count": video_count,
                    "voice_count": voice_count,
                    "audio_count": audio_count,
                    "link_count": link_count,
                    "status": "✅",
                    "date": time.strftime('%d/%m/%y'),
                    "chat_type": chat_type,
                    "chat_description": chat_description,
                    "chat_link": chat_link,
                }
                
                # Serialize the message data to JSON in a pretty format
                message_json = json.dumps(message_data, ensure_ascii=False, indent=4)
                
                # Save the JSON data to a file
                with open(message_filename, 'a', encoding='utf-8') as json_file:
                    json_file.write(message_json + ',\n')

                # Upload the base64-encoded image
                uploaded_photo = await client.upload_file(image, file_name='image.jpg')

                # send the message to the destination channel with the base64 image in html format 
                await client.send_message(entity=dest_chat_entity, file=uploaded_photo, message=message_to_send, silent=True, parse_mode='html')
                        
            # Save the array close in the JSON file
            with open(message_filename, 'a', encoding='utf-8') as json_file:
                json_file.write(']\n')
            
            # break the loop after finding the source folder
            break


# Call the main function
if __name__ == "__main__":
    # init the app
    initApp()
    
    # with client:
    client.loop.run_until_complete(startClient())

    client.loop.run_until_complete(main())
