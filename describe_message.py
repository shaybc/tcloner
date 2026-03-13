import dotenv
import os
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, MessageMediaGeo, GeoPoint, DocumentAttributeAudio, DocumentAttributeVideo, DocumentAttributeFilename, DocumentAttributeAnimated
import telethon.sync


# change the link to the message you want to read
# message_link = "https://t.me/c/2053120345/32556" # message with a tag, image, text
# message_link = "https://t.me/c/2053120345/32558" # message with image, text
# message_link = "https://t.me/c/2053120345/32557" # message with a video file
message_link = "https://t.me/c/2053120345/32559" # message with a playable video
# message_link = "https://t.me/c/2053120345/32513" # playable video, text, link

# message_link = "https://t.me/c/2053120345/32633" # test


# load environment variables from .env file
dotenv.load_dotenv(dotenv.find_dotenv())

# init the telegram client
print("Connecting to Telegram...")
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
telegram_session_filename = os.getenv("telegram_session_filename")

print(f"API_ID: {api_id}")
print(f"API_HASH: {api_hash}")
print(f"telegram_session_filename: {telegram_session_filename}")

client = telethon.sync.TelegramClient(session=telegram_session_filename, api_id=api_id, api_hash=api_hash) # create a Telegram client
print("Done - Connected to Telegram !")


async def main():
    global client, message_link
    
    # Connect to Telegram via the client
    print("Starting Telegram Client ...")
    await client.start()
    print("Done - Telegram Client Started !")

    # Manually parse the message link to extract channel or chat ID and message ID
    parts = message_link.split('/')
    chat_type = parts[-3]  # Extract the channel, group or user type
    entity = parts[-2]  # Extract the channel or chat ID
    message_id = int(parts[-1])  # Extract the message ID
    print(f"Entity: {entity}, Message ID: {message_id}")

    # Convert the entity to the appropriate type (channel, chat, or user)
    if chat_type.startswith('c'):
        entity = PeerChannel(int(entity))
    elif chat_type.startswith('g'):
        entity = PeerChat(int(entity))
    elif chat_type.startswith('u'):
        entity = PeerUser(int(entity))
    else:
        raise ValueError("Invalid entity type")

    # Get the message using the entity and message ID
    message = await client.get_messages(entity, ids=message_id)
    print(f"Read message id: {message_id} from {message_link}")
    
    try:
        # check if the message has a tag
        if message.entities:
            print(f"Message has a messageEntity")
            # can be one of: Hashtag, Mention, Email, Bold, Italic, Code, Pre, MentionName, Cashtag, Phone, Strike, Underline, BotCommand, Blockquote, BankCard, TextUrl, Url
            for entity in message.entities:
                start = entity.offset
                end = start + entity.length
                messageEntity = message.text[start:end]
                print(f"    Entity: {messageEntity}")
        
        # check if the message has a text
        if message.text:
            print(f"Message has a text")
        
        # check if the message has a video
        if message.video:
            print(f"Message has a video")
            if message.video.attributes:
                for attribute in message.video.attributes:
                    if isinstance(attribute, DocumentAttributeFilename):
                        print(f"    FileName: {attribute.file_name}")
                    if isinstance(attribute, DocumentAttributeVideo):
                        print(f"    Video Resolution: {attribute.w}x{attribute.h}")
                        print(f"    Duration: {attribute.duration} seconds")
            
        # check if the message has a contact
        if message.contact:
            print(f"Message has a contact")
            
        # check if the message has a link
        if message.web_preview:
            print(f"Message has a link")
            
        # check if the message has a game
        if message.game:
            print(f"Message has a game")
            
        # check if the message has a invoice
        if message.invoice:
            print(f"Message has a invoice")
            
        # check if the message has a venue
        if message.venue:
            print(f"Message has a venue")
        
        # check if the message has a media
        if message.media:
            print(f"Message has a media")
            
        # check if the message has a location
        if message.media and isinstance(message.media, MessageMediaGeo):
            print(f"Message has a location")
        
        # check if the message has a file
        if message.file:
            print(f"Message has a file")
        
        # check if the message has a photo
        if message.photo:
            print(f"Message has a photo")
            
        # check if the message has a document
        if message.document:
            print(f"Message has a document")
            print(f"    File Size: {message.document.size} bytes")
            print(f"    File Type: {message.document.mime_type}")
            # Check for specific attributes based on the file type
            for attribute in message.document.attributes:
                if isinstance(attribute, DocumentAttributeFilename):
                    print(f"    File Name: {attribute.file_name}")
                if isinstance(attribute, DocumentAttributeAnimated):
                    print("This is an animated (GIF) video.")
                
        # check if the message has a voice
        if message.voice:
            print(f"Message has a voice")
        
        # check if the message has a audio
        if message.audio:
            print(f"Message has a audio")
            if message.audio.attributes:
                for attribute in message.audio.attributes:
                    if isinstance(attribute, DocumentAttributeFilename):
                        print(f"    FileName: {attribute.file_name}")
                    if isinstance(attribute, DocumentAttributeAudio):
                        print(f"    Duration: {attribute.duration} seconds")
            
        # check if the message has a sticker
        if message.sticker:
            print(f"Message has a sticker")
            if message.sticker and message.sticker.attributes:
                for attribute in message.sticker.attributes:
                    if isinstance(attribute, DocumentAttributeFilename):
                        print(f"    Sticker: {attribute.file_name}")
            
        # check if the message has a gif
        if message.gif:
            print(f"Message has a gif")
            
        # check if the message has a video note
        if message.video_note:
            print(f"Message has a video note")
            
        # check if the message has a poll
        if message.poll:
            print(f"Message has a poll")
        
        # check if the message has a button
        if message.buttons:
            print(f"Message has a button")
            
        # check if the message has a reply
        if message.reply:
            print(f"Message has a reply")
            
    except Exception as e:
        print(f"Failed reading message info due to: {e}")
        
    # Disconnect the client
    await client.disconnect()


# Call the main function
if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
