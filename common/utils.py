import time
import os
import sys
import logging
import telethon.sync
from telethon.tl.functions.messages import SearchRequest


delay_between_reads = 2


# this function is used to avoid flooding telegram with too many requests
def anti_flood():
    global delay_between_reads
    # Wait for $delay_between_reads seconds before forwarding the next message to avoid flooding telegram with too many requests
    time.sleep(delay_between_reads)


async def delete_channel_history(client, channel_entity):    
    try:
        first_message_id = 1
        last_message_id = 1
        
        # get the channel first non service message id
        async for message in client.iter_messages(channel_entity, reverse=True):
            if not isinstance (message, telethon.tl.types.MessageService):
                first_message_id = message.id
                break
            anti_flood()
        
        # get the channel last message id
        async for message in client.iter_messages(channel_entity, limit=1):
            last_message_id = message.id
        
        # create a list of all the messages ids in the channel to delete
        messages_ids = [i for i in range(first_message_id, last_message_id + 1)]
        
        # delete all the messages in the channel
        await client.delete_messages(channel_entity, messages_ids)
    except Exception as e:
        print(f"Error: {e}")


# this function init the logger
# it configures the logger to log to a file and to the console
# it also configures the log line format using a time stamp, log level and the log message prefix
def init_logger(logFilename):
    
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
        

async def search_telegram(client, channel_entity, query_string='', filter=None, min_date=None, max_date=None, offset_id=0, add_offset=0, limit=0, max_id=0, min_id=0, hash=0):
    result = await client(SearchRequest(
        channel_entity,               #   peer
        query_string,                 #   query string
        filter,                       #   filter
        min_date,                     #   min_date
        max_date,                     #   max_date
        offset_id,                    #   offset_id
        add_offset,                   #   add_offset
        limit,                        #   limit
        max_id,                       #   max_id
        min_id,                       #   min_id
        hash                          #   hash
        ))
     
    return result
