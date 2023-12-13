import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import aiohttp
from codecs import encode
import mimetypes
import tempfile
import logging


from google_handlers import google_api_auth, async_upload_file_to_drive, async_create_sheet_entry


# Configure logging
logging.basicConfig(level=logging.WARNING)

# Environment variables
_ = load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_API")
AI_OR_NOT = os.getenv("AI_OR_NOT")
GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
SPREAD_SHEET_ID = os.getenv('SPREAD_SHEET_ID')

# Configure Discord bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    """
    Event handler for when the bot is ready and operational.

    This function is called when the bot has successfully connected
    to Discord and is ready to start receiving events. It logs the
    bot's name to indicate a successful start.
    """
    logging.info(f'Logged in as {bot.user.name}')


@bot.event
async def on_message(message: discord.Message):
    """
    Event handler for new messages.

    This function is triggered whenever a message is sent in a channel
    that the bot has access to. It checks if the message contains image
    attachments and processes them accordingly.

    Parameters:
    message (discord.Message): The message object containing details of the received message.
    """
    if message.author == bot.user or message.author.bot:
        return

    if message.attachments:
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(image_ext) for image_ext in ['.png', '.jpg', '.jpeg', '.gif']):
                await analyze_image(attachment, message)

    await bot.process_commands(message)


async def analyze_image(attachment: discord.Attachment, message: discord.Message):
    """
    Analyze and process an image attachment from a Discord message.

    Downloads the image from the attachment URL, analyzes it using the
    AI-or-Not API, uploads the image to Google Drive, and logs the analysis
    result along with the user details and timestamp to a Google Sheet.

    Parameters:
    attachment (discord.Attachment): The attachment object containing the image.
    message (discord.Message): The message object from which the attachment was received.
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()

                    boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
                    headers = {
                        'Authorization': f'Bearer {AI_OR_NOT}',
                        'Content-Type': f'multipart/form-data; boundary={boundary}'
                    }
                    data = [
                        encode('--' + boundary),
                        encode(
                            'Content-Disposition: form-data; name="object"; filename="{}"'.format(attachment.filename)),
                        encode('Content-Type: {}'.format(mimetypes.guess_type(
                            attachment.filename)[0] or 'application/octet-stream')),
                        encode(''),
                        image_data,
                        encode('--' + boundary + '--'),
                        encode('')
                    ]
                    body = b'\r\n'.join(data)

                    async with session.post("https://api.aiornot.com/v1/reports/image", data=body, headers=headers) as post_resp:
                        if post_resp.status == 200:
                            analysis_result = await post_resp.json()
                            verdict = analysis_result['report']['verdict']
                            await message.channel.send(f"The image was analyzed and determined to be: {verdict.upper()}")

                            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                                temp_file.write(image_data)
                                temp_file_path = temp_file.name

                            creds = google_api_auth()
                            await async_upload_file_to_drive(creds, temp_file_path, attachment.filename, GOOGLE_DRIVE_FOLDER_ID)
                            os.remove(temp_file_path)
                            formatted_timestamp = message.created_at.strftime(
                                "%Y-%m-%d %H:%M:%S")
                            values = [
                                [message.author.name, attachment.url, verdict, formatted_timestamp]]

                            await async_create_sheet_entry(creds, SPREAD_SHEET_ID, 'Sheet1!A1', values)
    except Exception as e:
        logging.error(f"Error in analyze_image: {e}")

bot.run(DISCORD_TOKEN)
