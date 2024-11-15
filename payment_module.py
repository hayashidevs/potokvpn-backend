from flask import Flask, request, jsonify
import asyncio
import aiohttp
import os
from datetime import datetime
from telegram import Bot
from telegram.constants import ParseMode
from aiofiles import open as aio_open  # For async file handling
from io import BytesIO  # Import BytesIO for in-memory file handling
import config
import api_client

# Initialize Flask app
app = Flask(__name__)

# Configure Python Telegram Bot
PTB_TOKEN = config.TELEGRAM_TOKEN
ptb_bot = Bot(token=PTB_TOKEN)

# Endpoint to initiate payment
@app.route('/initiate_payment', methods=['POST'])
async def initiate_payment():
    data = request.json
    client_id = data.get('client_id')
    rate_id = data.get('rate_id')
    telegram_id = data.get('telegram_id')

    if not all([client_id, rate_id, telegram_id]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400

    # Create payment via web app
    payment_url = f"{config.WEBSITE}/telegram/create-payment/{client_id}/{rate_id}/"
    async with aiohttp.ClientSession() as session:
        async with session.get(payment_url) as response:
            if response.status == 200:
                payment_link = str(response.url)
                return jsonify({'status': 'success', 'payment_link': payment_link})
            else:
                return jsonify({'status': 'error', 'message': 'Failed to create payment'}), 500

# Endpoint to handle post-payment actions
@app.route('/payment_completed', methods=['POST'])
async def payment_completed():
    data = request.json
    client_id = data.get('client_id')
    rate_id = data.get('rate_id')
    download_link = data.get('download_link')
    datestart = data.get('datestart')  # Ensure datestart is passed in the request

    # Check if all required fields are present
    if not all([client_id, rate_id, download_link]):
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    # Async retrieval of Telegram ID based on client ID
    telegram_id = await api_client.get_telegram_id_for_client_id(client_id)

    # Parse and format datestart if provided
    if datestart:
        try:
            datestart_obj = datetime.strptime(datestart, "%Y-%m-%dT%H:%M:%SZ")
            formatted_datestart = datestart_obj.strftime('%d-%b-%Y')  # Format as DD-MMM-YYYY
        except ValueError:
            return jsonify({'status': 'error', 'message': 'Invalid date format for datestart'}), 400
    else:
        formatted_datestart = "unknown_date"  # Default if datestart is missing

    # Generate a meaningful file name
    config_filename = f"{client_id[:8]}_{rate_id[:8]}_{formatted_datestart}.conf"

    # Set up the directory and file path
    config_dir = os.path.join(os.path.dirname(__file__), 'configs')
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, config_filename)

    # Asynchronously download the config file
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.WEBSITE}/{download_link}") as response:
            if response.status == 200:
                # Save the downloaded config file asynchronously
                async with aio_open(config_path, 'wb') as config_file:
                    await config_file.write(await response.read())

                # Read the file contents into memory for sending
                async with aio_open(config_path, 'rb') as config_file:
                    file_data = await config_file.read()  # Read the content of the file

                # Use BytesIO to create an in-memory file-like object
                file_like_object = BytesIO(file_data)

                # Notify user and send the file via Telegram using python-telegram-bot
                await ptb_bot.send_document(
                    chat_id=telegram_id,
                    document=file_like_object,
                    caption=(
                        "🎉 Команда проекта Поток благодарит Вас за оформленную подписку.\n"
                        "Чтобы воспользоваться файлом, добавьте его в приложение по "
                        "<a href='https://teletype.in/@potok_you/guide'>инструкции</a>."
                    ),
                    parse_mode=ParseMode.HTML
                )

                return jsonify({'status': 'success', 'message': 'File downloaded and sent to user'})
            else:
                return jsonify({'status': 'error', 'message': 'Failed to download the config file'}), 500

# Run Flask app on a different port to avoid conflicts
if __name__ == '__main__':
    app.run(port=9090)
