from quart import Quart, request, jsonify
import asyncio
import aiohttp
import os
from datetime import datetime
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from aiofiles import open as aio_open  # For async file handling
from io import BytesIO  # Import BytesIO for in-memory file handling
import config
import api_client

# Initialize Quart app (asynchronous alternative to Flask)
app = Quart(__name__)

# Configure Python Telegram Bot
PTB_TOKEN = config.TELEGRAM_TOKEN
ptb_bot = Bot(token=PTB_TOKEN)

# Shared session management for aiohttp
shared_session = None

# Initialize shared aiohttp session
async def setup_shared_session():
    global shared_session
    if shared_session is None:
        shared_session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=50))

# Close shared aiohttp session
async def close_shared_session():
    global shared_session
    if shared_session:
        await shared_session.close()
        shared_session = None

@app.before_serving
async def before_serving():
    # Setup shared session before starting to serve
    await setup_shared_session()

@app.after_serving
async def after_serving():
    # Close shared session after serving
    await close_shared_session()

@app.route('/initiate_payment', methods=['POST'])
async def initiate_payment():
    data = await request.get_json()
    client_id = data.get('client_id')
    rate_id = data.get('rate_id')
    telegram_id = data.get('telegram_id')
    type_payment = data.get('type_payment')
    subs_id = data.get('subs_id')
    ref_client = data.get('ref_client')

    # Validate required parameters
    if not all([client_id, rate_id, telegram_id, type_payment]):
        return jsonify({'status': 'error', 'message': 'Missing required parameters'}), 400

    if type_payment == "new_device":
        # Generate the payment URL
        payment_url = (
            f"{config.WEBSITE}/telegram/create-payment/{client_id}/{rate_id}/?ref_client={ref_client}"
            if ref_client else f"{config.WEBSITE}/telegram/create-payment/{client_id}/{rate_id}/"
        )
    elif type_payment == "renewal":
        if not subs_id:
            return jsonify({'status': 'error', 'message': 'Missing subs_id for renewal'}), 400
        payment_url = f"{config.WEBSITE}/telegram/create-payment/{client_id}/{rate_id}/?type_payment=renewal&subs_id={subs_id}"
    else:
        return jsonify({'status': 'error', 'message': 'Invalid type_payment value'}), 400

    try:
        async with shared_session.get(payment_url) as response:
            if response.status == 200:
                payment_link = str(response.url)
                return jsonify({'status': 'success', 'payment_link': payment_link})
            else:
                error_message = await response.text()
                return jsonify({'status': 'error', 'message': f'Failed to create payment: {error_message}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Exception during payment initiation: {str(e)}'}), 500

@app.route('/payment_completed', methods=['POST'])
async def payment_completed():
    data = await request.get_json()
    client_id = data.get('client_id')
    rate_id = data.get('rate_id')
    download_link = data.get('download_link')
    datestart = data.get('datestart') or datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    ref_client = data.get("ref_client")

    # Validate required fields
    if not client_id or not rate_id or not download_link:
        return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400

    try:
        datestart_obj = datetime.strptime(datestart, "%Y-%m-%dT%H:%M:%SZ")
        formatted_datestart = datestart_obj.strftime('%d-%b-%Y')
    except ValueError as e:
        return jsonify({'status': 'error', 'message': f'Invalid date format for datestart: {e}'}), 400

    # Async retrieval of Telegram ID based on client ID
    try:
        telegram_id = await api_client.get_telegram_id_for_client_id(client_id)
        if not telegram_id:
            raise ValueError("Telegram ID not found for client_id")
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to retrieve Telegram ID: {e}'}), 500

    config_filename = f"{client_id[:8]}_{rate_id[:8]}_{formatted_datestart}.conf"
    config_dir = os.path.join(os.path.dirname(__file__), 'configs')
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, config_filename)

    # Download and save the config file
    download_url = f"{config.WEBSITE}/{download_link}"
    try:
        async with shared_session.get(download_url) as response:
            if response.status == 200:
                async with aio_open(config_path, 'wb') as config_file:
                    await config_file.write(await response.read())
            else:
                return jsonify({'status': 'error', 'message': f'Failed to download config file. Status: {response.status}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to download config file: {e}'}), 500

    # Load and send the config file to the user via Telegram
    try:
        async with aio_open(config_path, 'rb') as config_file:
            file_data = await config_file.read()
        file_like_object = BytesIO(file_data)

        await ptb_bot.send_document(
            chat_id=telegram_id,
            document=file_like_object,
            filename=config_filename,
            caption=(
                "🎉 Команда проекта Поток благодарит Вас за оформленную подписку.\n"
                "Чтобы воспользоваться файлом, добавьте его в приложение по "
                "<a href='https://teletype.in/@potok_you/guide'>инструкции</a>."
            ),
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to send Telegram document: {e}'}), 500

    # Trigger referral bonus if a referral client is present
    if ref_client:
        try:
            bonus_days = await api_client.get_bonus_days_from_rateid(rate_id)
            if bonus_days is not None:
                client_subscriptions = await api_client.get_subscriptions_by_client_id(ref_client)
                subscription_massiv = [
                    [{'text': subscription['name'] or "Unnamed Subscription", 'callback_data': f"add_subs_{subscription['id']}///{bonus_days}"}]
                    for subscription in client_subscriptions
                ]

                telegram_id_referrer = await api_client.get_telegram_id_for_client_id(ref_client)
                payload = {
                    'chat_id': telegram_id_referrer,
                    'text': (
                        'Ваш друг воспользовался Вашим реферальным кодом.\n'
                        f'Вы можете получить бонусные {bonus_days} дней!\n'
                        'Пожалуйста, выберите подписку, на которую мы добавим Вам бонусные дни доступа.'
                    ),
                    'reply_markup': {'inline_keyboard': subscription_massiv}
                }

                async with shared_session.post(f"https://api.telegram.org/bot{PTB_TOKEN}/sendMessage", json=payload) as ref_response:
                    if ref_response.status != 200:
                        error_message = await ref_response.text()
                        return jsonify({'status': 'error', 'message': f'Failed to send referral callback: {error_message}'}), 500
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Exception during referral callback message: {e}'}), 500

    return jsonify({'status': 'success', 'message': 'File downloaded and sent to user, referral handled if applicable'}), 200

@app.route('/send_renewal_confirmation', methods=['POST'])
async def send_renewal_confirmation():
    data = await request.get_json()
    client_id = data.get('client_id')

    if not client_id:
        return jsonify({'status': 'error', 'message': 'Missing client_id parameter'}), 400

    try:
        telegram_id = await api_client.get_telegram_id_for_client_id(client_id)
        if not telegram_id:
            return jsonify({'status': 'error', 'message': 'Telegram ID not found for the given client ID'}), 400

        await ptb_bot.send_message(
            chat_id=telegram_id,
            text="✅ Ваша подписка успешно продлена\n\n[Будь в Потоке]",
            parse_mode=ParseMode.HTML
        )
        return jsonify({'status': 'success', 'message': 'Renewal confirmation sent successfully'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Exception occurred while sending Telegram message: {e}'}), 500

# Run Quart app on a different port to avoid conflicts
if __name__ == '__main__':
    app.run(port=9090)
