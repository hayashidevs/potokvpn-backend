from flask import Flask, request, jsonify
import requests
import os
from telegram import Bot
import config
import api_client

# Initialize Flask app
app = Flask(__name__)

# Configure Python Telegram Bot
PTB_TOKEN = config.TELEGRAM_TOKEN
ptb_bot = Bot(token=PTB_TOKEN)

# Endpoint to initiate payment
@app.route('/initiate_payment', methods=['POST'])
def initiate_payment():
    data = request.json
    client_id = data.get('client_id')
    rate_id = data.get('rate_id')
    telegram_id = data.get('telegram_id')

    if not all([client_id, rate_id, telegram_id]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400

    # Create payment via web app
    payment_url = f"{config.WEBSITE}/telegram/create-payment/{client_id}/{rate_id}/"
    response = requests.get(payment_url)

    if response.status_code == 200:
        payment_link = response.url
        return jsonify({'status': 'success', 'payment_link': payment_link})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to create payment'}), 500

# Endpoint to handle post-payment actions
@app.route('/payment_completed', methods=['POST'])
def payment_completed():
    data = request.json
    client_id = data.get('client_id')
    rate_id = data.get('rate_id')
    download_link = data.get('download_link')
    telegram_id = api_client.get_telegram_id_for_client_id(client_id)

    # Download the config file
    config_response = requests.get(f"{config.WEBSITE}/{download_link}")
    if config_response.status_code == 200:
        config_filename = download_link.split('/')[-2]
        config_dir = os.path.join(os.path.dirname(__file__), 'configs')
        os.makedirs(config_dir, exist_ok=True)
        
        config_path = os.path.join(config_dir, config_filename)

        # Save the downloaded config
        with open(config_path, 'wb') as config_file:
            config_file.write(config_response.content)

        # Notify user and send the file via Telegram
        ptb_bot.send_document(chat_id=telegram_id, document=open(config_path, 'rb'), filename=config_filename)
        return jsonify({'status': 'success', 'message': 'File downloaded and sent to user'})

    else:
        return jsonify({'status': 'error', 'message': 'Failed to download the config file'}), 500

# Run Flask app on a different port to avoid conflicts
if __name__ == '__main__':
    app.run(port=5000)
