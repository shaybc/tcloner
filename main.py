import logging
import os
import sys
import time
import dotenv
import pickle
import threading
import telethon.sync
from telethon import utils
from telethon import events

# this script forwards all messages from one telegram channel to another telegram channel
# it basically "backs up" a telegram channel to another telegram channel
# this way you can copy other channels content to your own channel (private or public)
# it iterates over all the messages in the source channel, and forwards them to the destination channel
# it keeps track of the last message ID it read from the source channel,
# so that it can continue from where it left off in case of an error or a CTRL+C was pressed by the user
# it also takes care of not forwarding messages that cannot be forwarded (such as channel name changed, message pinned, etc...)
# and make sure not to flood telegram with too many requests, by waiting for a few seconds between each message forwarding
# and listening to telegram errors and reacting to them accordingly so your account won't get banned (due to these errors)


# this variable holds the lock object used to lock the message forwarding process, so that only one message will be forwarded at a time
message_forward_lock = threading.Lock()

# this variable flags weather to listen to new messages in the source channels (after finishing reading all the new messages from the source channels)
listen_to_chats = False

# this variable holds the channel ids to listen to
listen_to_chat_ids = []

# this variable holds the total source channels we need to iterate over
all_channels_len = 0

# this variable holds the current channel we are iterating over
current_channel_index = 0

# this function loads all the environment variables from the .env file into global variables
# it does that using the dotenv library
# it also init other global variables
def init_env_vars():
    global api_id, api_hash, phone, logFilename, telegram_session_filename, src_channel_invite_links, dest_channel_invite_link, message_tracker_filename, require_min_size, delay_between_reads, listen_to_chats, total_messages_read_so_far, last_message_id
    
    # load environment variables from .env file
    dotenv.load_dotenv(".env", override=True, encoding='utf-8')

    # load environment variables from .env file into variables
    api_id = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")
    phone = os.getenv("PHONE")
    logFilename = os.getenv("logFilename")
    telegram_session_filename = os.getenv("telegram_session_filename")
    src_channel_invite_links = os.getenv("src_channel_invite_links")
    dest_channel_invite_link = os.getenv("dest_channel_invite_link")
    message_tracker_filename = os.getenv("message_tracker_filename")
    require_min_size = os.getenv("require_min_size").lower() == "true"
    delay_between_reads = int(os.getenv("delay_between_reads"))
    listen_to_chats = os.getenv("listen_to_chats").lower() == "true"

    # init total messages read so far and the last message ID variables
    total_messages_read_so_far = 0
    last_message_id = 0


# this function prints all the environment variables to the log file
# and the console (using the logging library)
# it is printed at the beginning of the script in each run
def print_env_vars():
    global api_id, api_hash, phone, logFilename, telegram_session_filename, src_channel_invite_links, dest_channel_invite_link, message_tracker_filename, require_min_size, delay_between_reads, listen_to_chats
    
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
    logging.info(f"telegram_session_filename: {telegram_session_filename}")
    logging.info(f"src_channel_invite_links: {src_channel_invite_links}")
    logging.info(f"dest_channel_invite_link: {dest_channel_invite_link}")
    logging.info(f"message_tracker_filename: {message_tracker_filename}")
    logging.info(f"require_min_size: {require_min_size}")
    logging.info(f"delay_between_reads: {delay_between_reads}")
    logging.info(f"listen_to_chats: {listen_to_chats}")
    logging.info("#############################################################")
    logging.info(" ")


# this function init the logger
# it configures the logger to log to a file and to the console
# it also configures the log line format using a time stamp, log level and the log message prefix
def init_logger():
    global logFilename
    
    # make sure the folder to logFilename file exist
    os.makedirs(os.path.dirname(logFilename), exist_ok=True)
    
    # configure the log line format using a time stamp, log level and the log message prefix
    log_line_prefix = '%(asctime)s - %(levelname)s - %(message)s'
    
    # configure a basic logger to log to the console
    logging.basicConfig(level=logging.INFO, format=log_line_prefix, stream=sys.stdout)
    
    # create a logger that logs to a file using the FileHandler and set its format to the same format as the console logger
    file_logger = logging.FileHandler(logFilename, encoding="utf-8")
    file_logger.setFormatter(logging.Formatter(log_line_prefix))
    
    # add the file logger to the logger object so each log message will be logged to the file and to the console
    logging.getLogger().addHandler(file_logger)


# this function init the app
# it calls all the init functions
# and init the telegram client
def initApp():
    global client, telegram_session_filename, api_id, api_hash
    
    # init the environment variables
    init_env_vars()

    # init the logger
    init_logger()

    # print the environment variables to the log file and the console
    print_env_vars()

    # init the telegram client
    logging.info("Creating Telegram Client...")
    client = telethon.sync.TelegramClient(session=telegram_session_filename, api_id=api_id, api_hash=api_hash) # create a Telegram client
    logging.info("Done - Creating Telegram Client !")


# this function loads the last read message ID and total messages read so far from the tracker file
# it does that using the pickle library, the saved data is used to continue a run from where we left
# off in case of an error ocurred or a CTRL+C was pressed by the user
def load_messages_from_tracker(channel_id):
    global last_message_id, total_messages_read_so_far, message_tracker_filename
    
    try:
        with open(f".\\trackers\\{message_tracker_filename}_{channel_id}.pkl", 'rb') as file:
            total_messages_read_so_far, last_message_id = pickle.load(file)
    except (FileNotFoundError, EOFError):
        logging.info("no message tracker file found, starting from scratch...")
        total_messages_read_so_far = 0
        last_message_id = 0
    except Exception as e:
        logging.error(f"error: {e}")
        logging.error(f"failed to load the message tracker for channel: {channel_id}, due to: {e}")
        raise e # re-raise the exception so that the program will skip the current channel and continue with the next one

    # log the last read message ID and total messages read so far
    logging.info(f"last_message_id: {last_message_id}")
    logging.info(f"total_messages_read_so_far: {total_messages_read_so_far}")
        
        
# this function saves the last read message ID and total messages read so far to the tracker file
# it does that using the pickle library, the saved data is used to continue a run from where we left
# off in case of an error ocurred or a CTRL+C was pressed by the user
def save_messages_to_tracker_internal(channel_id, total_messages_read_so_far, last_message_id):
    global message_tracker_filename
    
    with open(f".\\trackers\\{message_tracker_filename}_{channel_id}.pkl", 'wb') as file:
        pickle.dump((total_messages_read_so_far, last_message_id), file)


def save_messages_to_tracker(channel_id):
    global last_message_id, total_messages_read_so_far
    
    save_messages_to_tracker_internal(channel_id, total_messages_read_so_far, last_message_id)


# this function forwards a message to the destination channel
# it also updates the last read message ID and total messages read so far
# and saves them to the tracker file
async def forward_message_to_destination_channel(message, total_messages):
    global message_forward_lock, client, dest_channel_entity, total_messages_read_so_far, last_message_id, total_messages_to_go, src_channel_entity, require_min_size, delay_between_reads, current_channel_index, all_channels_len
    
    with message_forward_lock:
        # update the total messages read so far, the last message ID, calculate the total remaining messages to go through
        total_messages_read_so_far += 1
        last_message_id = message.id
        total_messages_to_go = total_messages - total_messages_read_so_far
        # get the real chat ID and peer type (channel, group, etc...) from the source message object
        src_real_chat_id, src_peer_type = utils.resolve_id(message.chat_id)
        # create the message link
        post_link = f"https://t.me/c/{src_real_chat_id}/{message.id}"
        logging.info(f"[CHN {current_channel_index}/{all_channels_len}] readMessage(msgID: {message.id}, readSoFar: {total_messages_read_so_far}, totalMsg: {total_messages}, remains: {total_messages_to_go})  {post_link}")
        
        # # check if the message was deleted, if so - skip it
        # if message.deleted:
        #     logging.info(f"skipping message (message was deleted), msgID: {message.id}")
        #     return
        
        try:
            # if this message is not a video or a file - skip it
            if message.media and message.file and message.document:
                # make sure the video is larger then 10 megabytes
                # if require_min_size and message.document.size < 30 * 1024 * 1024:
                #     logging.info(f"skipping message (video is less then 10 megabytes), msgID: {message.id}")
                #     return
                        
                # forwards the message to the destination channel
                # forwarded_message = await client.forward_messages(dest_channel_entity, message, silent=True)
                forwarded_message = await client.send_message(entity=dest_channel_entity, message=message, silent=True)
                # get the real chat ID and peer type (channel, group, etc...) from the destination message object
                dest_real_chat_id, src_peer_type = utils.resolve_id(forwarded_message.chat_id)
                # create the forwarded message link
                forwarded_post_link = f"https://t.me/c/{dest_real_chat_id}/{forwarded_message.id}"
                logging.info(f"[CHN {current_channel_index}/{all_channels_len}] frwdMessage(msgID: {forwarded_message.id}, readSoFar: {total_messages_read_so_far}, totalMsg: {total_messages}), remains: {total_messages_to_go})  {forwarded_post_link}")
            else:
                logging.info(f"skipping message (not a video or a file), msgID: {message.id}")
        except Exception as e:
            logging.error(f"failed to forward message, msgID: {message.id} due to: {e}")
            if "You can't forward messages from a protected chat (caused by SendMediaRequest)" in str(e):
                logging.warning(f"warning: {e}")
                logging.warning(f"skipping message (You can't forward messages from a protected chat), msgID: {message.id}")
            else:
                raise e
        finally:
            # save the last read message ID and total messages read so far to the tracker file
            save_messages_to_tracker(src_real_chat_id)
                
        # Wait for $delay_between_reads seconds before forwarding the next message to avoid flooding telegram with too many requests
        time.sleep(delay_between_reads)





#####################################################
#                Main Script Code                   #
#####################################################

async def itterate_messages(src_channel_invite_link):
    global client, logFilename, dest_channel_invite_link, last_message_id, total_messages_read_so_far, src_channel_entity, dest_channel_entity, listen_to_chat_ids
    
    # get the channel entity using the invite link
    try:
        logging.info(f"Processing channel: {src_channel_invite_link}...")
        
        try:
            # Getting the entity by chat ID
            src_channel_entity = await client.get_entity(int(src_channel_invite_link))
        except ValueError:
            # Getting the entity by invite link
            src_channel_entity = await client.get_entity(src_channel_invite_link)
            
        logging.info(f"Reading messages from channel: [{src_channel_entity.id}] {src_channel_entity.title}...")
    except Exception as e:
        logging.error(f"Failed to get source channel entity for invite link: {src_channel_invite_link}, due to: {e}")
        return
    
    # if channel id is not in the listen_to_chat_ids list, then add it
    if src_channel_entity.id not in listen_to_chat_ids:
        listen_to_chat_ids.append(src_channel_entity.id)
    
    dest_channel_entity = await client.get_entity(dest_channel_invite_link)
    logging.info(f"Will forward messages to channel: [{dest_channel_entity.id}]  {dest_channel_entity.title}...")
    
    # load last read message ID and total messages read so far from the tracker file
    load_messages_from_tracker(src_channel_entity.id)
    
    keep_reading = True
    number_of_consequtive_errors = 0
    
    while keep_reading:
        # if we get 3 consequtive errors, then exit the program
        if number_of_consequtive_errors >= 3:
            logging.info("failed to forward message 3 times in a row (due to consecutive errors or due to not receiving more messages from channel), exiting...")
            return            
                        
        try:
            # consider unreceived message as error, increment the number of consequtive errors
            number_of_consequtive_errors+=1
            
            # check how many total messages are there in the channel
            total_messages = await client.get_messages(src_channel_entity, limit=1)
            # get the latest message ID in the channel
            latest_message_id = total_messages[0].id
            logging.info(f"total messages in channel: {total_messages.total}, latest message ID: {latest_message_id}")
            
            # if we reached the end of the channel (no more messages to read), then exit the iteration loop
            if total_messages_read_so_far >= total_messages.total or last_message_id == latest_message_id:
                logging.info("reached the end of the channel (no more messages to read), stopping message iteration...")
                keep_reading = False
                break
            
            # iterate over all the messages in the channel, starting from the last read message ID saved in the tracker file
            # note: we iterate in reverse order, so that we can continue from the last read message ID in case of an error
            # or in case we reach the end of the channel and new messages are added to the channel since the last time we read messages from it
            # if all messages were read, or if more than 3 consequtive errors occurred - exit the program
            async for message in client.iter_messages(src_channel_entity, min_id=last_message_id, reverse=True):
                await forward_message_to_destination_channel(message, total_messages.total)
                
                # reset the number of consequtive errors since we were able to forward the message and no error occurred
                number_of_consequtive_errors = 0
            
        except Exception as e:
            
            if "Cannot forward messages of type" in str(e):
                logging.warning(f"warning: {e}")
                logging.warning("failed to forward message, will continue with the next message...")
                # since this is not considered a failure, reset the number of consequtive errors (as if it was a success)
                # (although we didn't forward the message, we are able to continue with the next message)
                number_of_consequtive_errors=0
                continue
            
            # if error contains the text "A wait of xxx seconds is required" where xxx is a number of seconds to wait before continuing, then wait for that number of seconds
            elif "A wait of" in str(e):
                wait_seconds = int(str(e).split("A wait of")[1].split("seconds is required")[0])
                logging.warning(f"need to wait for {wait_seconds} seconds before continuing...")
                time.sleep(wait_seconds + 2) # Wait for $wait_seconds + 2 seconds just to be sure
            
            # on any other error, log the error and wait for 5 seconds before trying again
            else:
                logging.error(f"error: {e}")
                logging.error("failed to forward message, will try again in 5 seconds...")
                time.sleep(5)  # Wait for 5 seconds
            
            
            # since error occurred, increment the number of consequtive errors
            number_of_consequtive_errors+=1
                
            # load last read message ID and total messages read so far from the tracker file
            # in order to ignore last message counter increment since we failed to forward the message
            # (unless it was a "Cannot forward messages of type" error)
            load_messages_from_tracker(src_channel_entity.id)


async def listenToAllChannels():
    # if we reached here, then we finished reading all the messages in the channel
    # start listening to new messages in the source channel and forward them to the destination channel
    logging.info("Done - Finished reading all the messages in the channel, starting to listen to new messages...")
    @client.on(events.NewMessage())
    async def handler(event):
        # get the real source chat ID and peer type (channel, group, etc...) from the event message object
        src_real_chat_id, src_peer_type = utils.resolve_id(event.chat_id)
        
        # if the channel id of the message is not in the src_channel_invite_links list, then ignore it
        if src_real_chat_id not in listen_to_chat_ids:
            # print(f"ignoring message from channel: {src_real_chat_id}, it is not in: {listen_to_chat_ids}")
            return False

        # print(event.raw_text)
        try:
            await forward_message_to_destination_channel(event.message, 1)
        
        except Exception as e:
            
            if "Cannot forward messages of type" in str(e):
                logging.warning(f"warning: {e}")
                logging.warning("failed to forward message, will continue listenning ...")
            
            # if error contains the text "A wait of xxx seconds is required" where xxx is a number of seconds to wait before continuing, then wait for that number of seconds
            elif "A wait of" in str(e):
                wait_seconds = int(str(e).split("A wait of")[1].split("seconds is required")[0])
                logging.warning(f"need to wait for {wait_seconds} seconds before continuing...")
                time.sleep(wait_seconds + 2) # Wait for $wait_seconds + 2 seconds just to be sure
            
            # on any other error, log the error and wait for 5 seconds before trying again
            else:
                logging.error(f"error: {e}")
                logging.error("failed to forward message, will try again in 5 seconds...")
                time.sleep(5)  # Wait for 5 seconds

        return True
    
    await client.run_until_disconnected()


async def startClient():
    global client
    
    # Connect to Telegram via the client
    logging.info("Starting Telegram Client ...")
    await client.start()
    logging.info("Done - Telegram Client Started !")


async def exportChannelsAndGroupsLinks():
    global client
    
    # delete file if exists
    if os.path.exists("chats.txt"):
        os.remove("chats.txt")
    
    # get all the chats (channels, groups, etc...) that the user is a member of
    async for dialog in client.iter_dialogs():
        print(f"Chat ID: {dialog.entity.id}")
        
        # get the real chat ID and peer type (channel, group, etc...) from the dialog object
        real_chat_id, peer_type = utils.resolve_id(dialog.entity.id)
        
        # get the chat title
        try:
            chat_title = dialog.entity.title
        except Exception as e:
            chat_title = ""
            logging.error(f"Failed to get chat title for chat: {real_chat_id}, due to: {e}")
        
        # get the invite link of the chat
        try:
            invite_link = await client(telethon.tl.functions.messages.ExportChatInviteRequest(
                real_chat_id
            )) | ""
        except Exception as e:
            invite_link = ""
            logging.error(f"Failed to get invite link for chat: {real_chat_id}, due to: {e}")
            
        print(f"Chat ID: {real_chat_id}, Chat Title: {chat_title} Invite Link: {invite_link}\n")
        # write the real chat ID and peer type (channel, group, etc...) and chat title and invite link to a file
        with open(file="chats.txt", mode="a", encoding="UTF8") as file:
            file.write(f"Chat ID: {real_chat_id}, Chat Title: {chat_title} Invite Link: {invite_link}\n")

        # test it
        got_entity = await client.get_entity(real_chat_id)
        print(f"### Test Chat ID: {got_entity.id}")
            
            
# Call the main function
if __name__ == "__main__":
    # init the app
    initApp()
    
    # # readMessage(msgID: 248167, readSoFar: 185018, totalMsg: 298007, remains: 112989)  https://t.me/c/1199599228/248167
    # save_messages_to_tracker_internal(1199599228, 185018, 248167)
    # exit()

    # with client:
    client.loop.run_until_complete(startClient())
    
    # export all the channels and groups invite links to a file
#####    client.loop.run_until_complete(exportChannelsAndGroupsLinks())
    
    # loop through all the source channel invite links, and call forwardUnreadMessages() for each one
    all_channels = src_channel_invite_links.split(",")
    all_channels_len = len(all_channels)
    for src_channel_invite_link in all_channels:
        try:
            current_channel_index = all_channels.index(src_channel_invite_link) + 1
            # call forwardUnreadMessages() for the source channel invite link
            client.loop.run_until_complete(itterate_messages(src_channel_invite_link))
            time.sleep(2)  # Wait for 2 seconds
        except Exception as err:
            if "A wait of" in str(err):
                wait_seconds = int(str(err).split("A wait of")[1].split("seconds is required")[0])
                logging.warning(f"need to wait for {wait_seconds} seconds before continuing...")
                time.sleep(wait_seconds + 2) # Wait for $wait_seconds + 2 seconds just to be sure
            
            # on any other error, log the error and wait for 5 seconds before trying again
            else:
                logging.error(f"Failed to forward messages from channel: {src_channel_invite_link}, due to: {err}")
    
    if(listen_to_chats):
        logging.info(f"listening to channels for new incoming messages...")
        client.loop.run_until_complete(listenToAllChannels())
    
