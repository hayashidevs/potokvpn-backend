import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, \
    PreCheckoutQuery, LabeledPrice
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import BadRequest
import requests
import datetime
from datetime import timedelta
import time
import re
import api_client
import config
from api_client import *
import uuid
import yaml
from utils import setup_logging, log

key = config.Promik
API_TOKEN = config.TELEGRAM_TOKEN
YOOTOKEN = config.PAYMENTS_TOKEN

urls = {'iphone': 'https://apps.apple.com/mx/app/amneziawg/id6478942365?l=en-GB', 'android': 'https://play.google.com/store/apps/details?id=org.amnezia.vpn', 'macos': 'https://github.com/hayashidevs/potokvpn-client/releases/latest/download/PotokVPN.dmg', 'windows': 'https://github.com/hayashidevs/potokvpn-client/releases/latest/download/PotokVPN_x64.exe', 'linux': 'https://github.com/hayashidevs/potokvpn-client/releases/latest/download/PotokVPN_Linux_Installer.tar'}

tgIDs = []

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# States
class FormStates(StatesGroup):
    PROMOCODE = State()
    DEVICE_SELECTION = State()


class FormStatesTestSubs(StatesGroup):
    PROMO = State()
    NAME_SUBS = State()


class Oform(StatesGroup):
    NameDevice = State()
    Promo = State()
    Tariff = State()


class UpdateSubs(StatesGroup):
    SelectSubscription = State()


class Add_days_for_sub(StatesGroup):
    Tariff = State()


# Обработчик команды /start
@dp.message_handler(Command("start"), state='*')
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    check_register = await api_client.check_and_register_with_username(
            message.from_user.id, 
            message.from_user.username, 
            message.from_user.first_name,
            message.from_user.last_name
    )

    if check_register is False:
        status = await api_client.check_user_registration(message.from_user.id)
        if status[1] is False:
            await api_client.register_user(
                message.from_user.id, 
                message.from_user.username, 
                message.from_user.first_name,
                message.from_user.last_name
            )
            await message.answer(
                f"{message.from_user.first_name}\nДобро пожаловать в [ поток 𝗩𝗣𝗡 ]\n🌐 Ваш надежный VPN сервис\n🌅 Следи за новостями в группе и будь в потоке @potok_you", reply_markup=types.ReplyKeyboardRemove())
        else:
            await message.answer(
                f"{message.from_user.first_name}\nС возвращением в [ поток 𝗩𝗣𝗡 ]\n🌐 Ваш надежный VPN сервис\n🌅 Следи за новостями в группе и будь в потоке @potok_you", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer(
                f"{message.from_user.first_name}\nДобро пожаловать в [ поток 𝗩𝗣𝗡 ]\n🌐 Ваш надежный VPN сервис\n🌅 Следи за новостями в группе и будь в потоке @potok_you", reply_markup=types.ReplyKeyboardRemove())

    await main_menu(message)



@dp.pre_checkout_query_handler(state='*')
async def checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT, state='*')
async def got_payment(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'referral_client_id' in data:
            referral_client_id = data['referral_client_id']
            referral_client_telegram_id = data['referral_client_telegram_id']

        if message.successful_payment.invoice_payload == 'product_id_prod':
            subs_id = data['subs_id']
            tarname = data['tariffname']
            days = await get_days_from_ratename(tarname)
            await update_dateend_referral(subs_id, days)
            await message.answer("Подписка продлена!", reply_markup=types.ReplyKeyboardRemove())
            await state.finish()
            await main_menu(message)
        else:
            inline_keyboard = InlineKeyboardMarkup()
            inline_keyboard.add(InlineKeyboardButton("Назад в главное меню", callback_data='back_to_main_menu'))

            date_start = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            response = await api_client.add_device(message.from_user.id, data['tariffname'], None, date_start)
            uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
            uuid_match = re.search(uuid_pattern, response)
            if uuid_match:
                subscription_id = uuid_match.group(0)
                data['subs_id'] = subscription_id
                config_name = subscription_id[:8]  # Extract first 8 digits for config_name
                update_payload = {'config_name': config_name}
                await api_client.update_subscription_is_used(subscription_id, update_payload)
            else:
                print("UUID not found in response.")
                await message.answer("Ошибка: не удалось найти UUID в ответе.")
                log(subscription_id, data, config_name, update_payload, "Ошибка: не удалось найти UUID в ответе.", response, uuid_match )
                return

            try:
                if data['is_referral'] == True:
                    chatid = data.get('chatid')
                    update_result = await update_usedref(message.from_user.id)
                    bonus_days = await get_bonus_days_from_ratename(data['tariffname'])
                    if bonus_days is None:
                        await message.answer("Ошибка: не удалось получить бонусные дни для тарифа.")
                        return
                    print(f"Bonus days for rate '{data['tariffname']}': {bonus_days}")

                    client_subscriptions = await get_subscriptions_by_client_id(referral_client_id)
                    if isinstance(client_subscriptions, str):
                        await message.answer(client_subscriptions, reply_markup=inline_keyboard)
                        return

                    await state.update_data(subscriptions=client_subscriptions)

                    reply_keyboard_for_referral = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    for subscription in client_subscriptions:
                        reply_keyboard_for_referral.add(
                            InlineKeyboardButton(subscription['name'] if subscription['name'] else "Unnamed Subscription",
                                                callback_data=f'add_subs_{subscription["id"]}///{bonus_days}'))

                    await bot.send_message(
                        referral_client_telegram_id,
                        f'🔤 Ваш друг воспользовался Вашим реферальным кодом\n📲 Выберите подписку, на которое мы добавим Вам {bonus_days} дней доступа',
                        reply_markup=reply_keyboard_for_referral
                    )

                    print(f"Updating referred_by for client: {message.from_user.id}, referred_by: {referral_client_id}")
                    result = await add_referred_by(message.from_user.id, referral_client_id)
                    print(f"Referral update result: {result}")

                    if not result:
                        await message.answer('Ошибка при обновлении реферального кода.')
                        log(result, referral_client_telegram_id, client_subscriptions, "Ошибка при обновлении реферального кода." )
                        return

            except Exception as e:
                print(f'Реферальный код не был указан, но подписка успешно добавлена: {e}')
                log( f"Реферальный код не был указан, но подписка успешно добавлена: {e}" )

            product_id = message.successful_payment.invoice_payload

            subscription_id = data['subs_id']
            config_name = subscription_id[:8]
            count_subs = await get_subscription_count_by_telegram_id(message.from_user.id)
            print(count_subs)
            device_name = f'{message.from_user.first_name}_{count_subs + 1}'
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("Iphone", url=urls['iphone']),
                InlineKeyboardButton("Android", url=urls['android']),
                InlineKeyboardButton("MacOS", url=urls['macos']),
                InlineKeyboardButton("Windows", url=urls['windows']),
            )
            await message.reply(f'🔐 Ваша подписка успешно добавлена!', reply_markup=types.ReplyKeyboardRemove())
            await message.reply(f'⤵️ Чтобы активировать [поток VPN], установите приложение WireGuard под Ваше устройство', reply_markup=keyboard)
            try:
                response = requests.post(f'{config.WGAPI_URL}/wireguard/add_user/', json={'subscription_id': subscription_id})
                response_data = response.json()

                print(f'Wireguard API response: {response_data}')
                log(f'Wireguard API response: {response_data}')

                if response.status_code != 200 or 'config_content' not in response_data:
                    await message.answer("Ошибка: не удалось добавить пользователя Wireguard.")
                    log(f"Ошибка: не удалось добавить пользователя Wireguard.", response.status_code, 'config_content', response_data )
                    return

                config_file_text = response_data.get('config_content', '').replace(",::/128", "")

                if not config_file_text:
                    await message.answer("Ошибка: не удалось получить текст конфигурации.")
                    log("Ошибка: не удалось получить текст конфигурации:", config_file_text)
                    return

                config_file_path = f'configs/{subscription_id[:8]}.conf'
                with open(config_file_path, 'w+') as config_file:
                    config_file.write(config_file_text)

                await bot.send_document(message.chat.id, open(config_file_path, 'rb'))
                os.remove(config_file_path)

                update_data = {
                    'subscription_id': subscription_id,
                    'config_name': config_name
                }

                response = requests.post(f'{config.DJANGO_API_URL}/api/update_subscription/', data=update_data)
                print(response)
            except Exception as e:
                print(f'Error during Wireguard API request: {str(e)}')
                log(f'Error during Wireguard API request: {str(e)}')
                await message.answer("Ошибка при запросе к API Wireguard.")

            await update_name_subs(subscription_id, device_name)
            await state.finish()
            await main_menu(message)
            



@dp.callback_query_handler(lambda c: c.data and c.data.startswith('add_subs_'))
async def process_add_subs(call: types.CallbackQuery, state: FSMContext):
    try:
        # Parse the subscription ID and bonus days from the callback data
        data = call.data.split('///')
        subs_id = data[0].replace('add_subs_', '')
        bonus_days = int(data[1])

        # Update the subscription end date with the bonus days
        result = await update_dateend_referral(subs_id, bonus_days)
        if 'successfully' in result:
            await call.message.answer(f'Подписка успешно продлена на {bonus_days} дней!')
        else:
            await call.message.answer(f'Ошибка продления подписки: {result}')
            log(f'Ошибка продления подписки: {result}')

        await state.finish()
    except Exception as e:
        print(f"Exception in process_add_subs: {e}")
        log(f"Exception in process_add_subs: {e}")
        await call.message.answer("Произошла ошибка при продлении подписки. Пожалуйста, попробуйте еще раз.")
        await state.finish()


# Input Ref Code
@dp.callback_query_handler(text='inputrefcode', state='*')
async def add_device(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Назад в главное меню", callback_data='back_to_main_menu'))
    await call.message.edit_text("⌨️ Введите реферальный код Вашего друга и получите скидку до -30% на первую покупку", reply_markup=keyboard)
    await Oform.Promo.set()




async def main_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Обратиться в тех.поддержку", callback_data='support'),
        InlineKeyboardButton("Инструкция", callback_data='instructions'),
        InlineKeyboardButton("Личный Кабинет", callback_data='account'),
        InlineKeyboardButton("Оформить подписку", callback_data='add_device')
    )
    
    used_test, _ = await is_test_subscription_used(message.from_user.id)
    if not used_test:
        keyboard.add(InlineKeyboardButton("Активировать подарок 🎁", callback_data='test_subscription'))
    
    await message.answer("🗂️ Выберите пункт меню:", reply_markup=keyboard)

async def main_menu_call(call: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Обратиться в тех.поддержку", callback_data='support'),
        InlineKeyboardButton("Инструкция", callback_data='instructions'),
        InlineKeyboardButton("Личный Кабинет", callback_data='account'),
        InlineKeyboardButton("Оформить подписку", callback_data='add_device'),
    )

    used_test, _ = await is_test_subscription_used(call.from_user.id)
    if not used_test:
        keyboard.add(InlineKeyboardButton("Активировать подарок 🎁", callback_data='test_subscription'))

    await bot.send_message(call.from_user.id, "🗂️ Выберите пункт меню:", reply_markup=keyboard)


@dp.callback_query_handler(text='instructions', state='*')
async def test_subscription(call: types.CallbackQuery, state: FSMContext):
    inline_button = types.InlineKeyboardButton(text="Инструкция", url="https://teletype.in/@potok_you/guide")
    inline_button2 = types.InlineKeyboardButton(text="Назад", callback_data='back_to_main_menu')

    # Создаем клавиатуру и добавляем кнопку
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(inline_button)
    keyboard.add(inline_button2)

    await call.message.answer(text="📑 Перейдите по ссылке, чтобы ознакомиться с инструкцией сервиса", reply_markup=keyboard)


@dp.callback_query_handler(text='add_device')
async def add_device(call: types.CallbackQuery):
    refby = await get_user_details(call.from_user.id)
    print(f'REFFERAL BY: {refby}')
    if refby is None:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Да", callback_data='inputrefcode'),
            InlineKeyboardButton("Нет", callback_data='skiprefcode'),
            InlineKeyboardButton("Назад", callback_data='back_to_main_menu')
        )
        await call.message.edit_text(
                    f"🎟️ У вас есть реферальный код?",
                    reply_markup=keyboard)
    else:
        rates = await api_client.list_rates()

        filtered_rates = [rate for rate in rates if 'price' in rate and rate['price']]
        filtered_rates.sort(key=lambda rate: rate['price'])

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for rate in filtered_rates:
            keyboard.add(KeyboardButton(f"{rate['name']} - {rate['price']} руб."))

        await call.message.answer("⬇️ Выберите тариф из списка для новой подписки", reply_markup=keyboard)
        await Oform.Tariff.set()
    


# Обработчик кнопки "Назад"
@dp.callback_query_handler(text='back_to_main_menu', state='*')
async def back_to_main_menu(call: types.CallbackQuery, state: FSMContext):
    await state.finish()  # Сбрасываем состояние
    await bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    await main_menu(call.message)



@dp.callback_query_handler(text='test_subscription', state='*')
async def test_subscription(call: types.CallbackQuery, state: FSMContext):
    # Check if the user has already used the referral
    used_test, client_details = await is_test_subscription_used(call.from_user.id)
    
    if used_test:
        await call.message.answer("Вы уже использовали подарок.")
        await main_menu_call(call)
        return
    
    await call.message.answer("🎁 Введите кодовое слово и активируйте подарочный сертификат")
    await call.message.delete_reply_markup()  # Удаляем клавиатуру
    # Устанавливаем состояние 'test_subscription'
    await FormStatesTestSubs.PROMO.set()


@dp.message_handler(Command("add_device"), state='*')
async def add_device(message: types.Message, state: FSMContext):
    try:
        await state.finish()
    except:
        pass
    refby = await get_user_details(message.from_user.id)
    if refby is None:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("Да", callback_data='inputrefcode'),
            InlineKeyboardButton("Нет", callback_data='skiprefcode'),
            InlineKeyboardButton("Назад", callback_data='back_to_main_menu')
        )
        await message.reply(
                    f"🎟️ У вас есть реферальный код?",
                    reply_markup=keyboard)
    else:
        rates = await api_client.list_rates()

        filtered_rates = [rate for rate in rates if 'price' in rate and rate['price']]
        filtered_rates.sort(key=lambda rate: rate['price'])

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for rate in filtered_rates:
            keyboard.add(KeyboardButton(f"{rate['name']} - {rate['price']} руб."))

        await message.answer("⬇️ Выберите тариф из списка для новой подписки", reply_markup=keyboard)
        await Oform.Tariff.set()


@dp.message_handler(Command("invite"), state='*')
async def get_ref_code(message: types.Message, state: FSMContext):
    try:
        await state.finish()
    except:
        pass
    unical_ref_code = await get_referral_id_by_telegram_id(message.from_user.id)
    if unical_ref_code is None:
        unical_ref_code = await get_client_id_from_telegram_id(message.from_user.id)
        if not unical_ref_code:
            log("Account not found", unical_ref_code)
            await message.reply("Не удалось найти ваш аккаунт.")
            return
    
    inline_keyboard = InlineKeyboardMarkup()
    inline_keyboard.add(InlineKeyboardButton("Назад в личный кабинет", callback_data='account'))
    await bot.send_message(message.from_user.id, f"🎟️ Ваш реферальный код: <pre>{unical_ref_code}</pre>\nС его помощью Вы можете пригласить неограниченное количество друзей и получить до 30 дней бесплатного доступа за каждого пользователя\n⤵️ Скопируйте код и отправьте другу", reply_markup=inline_keyboard, parse_mode="HTML")



@dp.callback_query_handler(text='get_ref_code')
async def get_ref_code(call: types.CallbackQuery):
    unical_ref_code = await get_referral_id_by_telegram_id(call.from_user.id)
    if unical_ref_code is None:
        unical_ref_code = await get_client_id_from_telegram_id(call.from_user.id)
        if not unical_ref_code:
            log("Account not found", unical_ref_code)
            await call.message.reply("Не удалось найти ваш аккаунт.")
            return
    
    inline_keyboard = InlineKeyboardMarkup()
    inline_keyboard.add(InlineKeyboardButton("Назад в личный кабинет", callback_data='account'))
    await bot.send_message(call.from_user.id, f"🎟️ Ваш реферальный код: <pre>{unical_ref_code}</pre>\nС его помощью Вы можете пригласить неограниченное количество друзей и получить до 30 дней бесплатного доступа за каждого пользователя\n⤵️ Скопируйте код и отправьте другу", reply_markup=inline_keyboard, parse_mode="HTML")
    

@dp.message_handler(Command("account"), state='*')
async def my_devices(message: types.Message, state: FSMContext):
    try:
        await state.finish()
    except:
        pass
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Назад", callback_data='back_to_main_menu'),
        InlineKeyboardButton("Изменить тарифный план", callback_data='change_plan'),
        InlineKeyboardButton("Оформить подписку", callback_data='add_device'),
        InlineKeyboardButton('Скачать файл конфигурации', callback_data='get_config'),
        InlineKeyboardButton('Пригласить друга', callback_data='get_ref_code')
    )

    client_id = await get_client_id_from_telegram_id(message.from_user.id)
    if not client_id:
        log("Account not found ", client_id)
        await message.reply("Не удалось найти ваш аккаунт.", reply_markup=keyboard)
        return

    subscriptions = await get_subscriptions_by_client_id(client_id)
    print(subscriptions)

    if isinstance(subscriptions, str):
        # Handle the case when an error message is returned
        await message.reply(subscriptions, reply_markup=keyboard)
        return

    texttoper = f"Мои подписки:\n"
    for subscription in subscriptions:
        if subscription['clientid'] == client_id:
            date_string = subscription['datestart']
            date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
            readable_date = date_object.strftime("%d %B %Y, %H:%M:%S")
            date_string2 = subscription['dateend']
            date_object2 = datetime.strptime(date_string2, "%Y-%m-%dT%H:%M:%SZ")
            readable_date2 = date_object2.strftime("%d %B %Y, %H:%M:%S")
            texttoper += f"<pre>Подписка: {subscription['name']}\nНачало: {readable_date}\nКонец: {readable_date2}\n\n"

        texttoper += '</pre>'

    await message.reply(texttoper, reply_markup=keyboard, parse_mode='HTML')

@dp.callback_query_handler(text='account')
async def my_devices(call: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
    except:
        pass
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("Назад", callback_data='back_to_main_menu'),
        InlineKeyboardButton("Изменить тарифный план", callback_data='change_plan'),
        InlineKeyboardButton("Оформить подписку", callback_data='add_device'),
        InlineKeyboardButton('Скачать файл конфигурации', callback_data='get_config'),
        InlineKeyboardButton('Пригласить друга', callback_data='get_ref_code')
    )

    client_id = await get_client_id_from_telegram_id(call.from_user.id)
    if not client_id:
        log("Account not found ", client_id)
        await call.message.edit_text("Не удалось найти ваш аккаунт.", reply_markup=keyboard)
        return

    subscriptions = await get_subscriptions_by_client_id(client_id)
    print(subscriptions)

    if isinstance(subscriptions, str):
        # Handle the case when an error message is returned
        await call.message.edit_text(subscriptions, reply_markup=keyboard)
        return

    texttoper = f"Мои подписки:\n"
    for subscription in subscriptions:
        if subscription['clientid'] == client_id:
            date_string = subscription['datestart']
            date_object = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")
            readable_date = date_object.strftime("%d %B %Y, %H:%M:%S")
            date_string2 = subscription['dateend']
            date_object2 = datetime.strptime(date_string2, "%Y-%m-%dT%H:%M:%SZ")
            readable_date2 = date_object2.strftime("%d %B %Y, %H:%M:%S")
            texttoper += f"<pre>Подписка: {subscription['name']}\nНачало: {readable_date}\nКонец: {readable_date2}\n\n"

        texttoper += '</pre>'

    await call.message.edit_text(texttoper, reply_markup=keyboard, parse_mode='HTML')


@dp.callback_query_handler(text='change_plan')
async def change_plan(call: types.CallbackQuery):
    client_id = await get_client_id_from_telegram_id(call.from_user.id)
    subs_user = await get_subscriptions_by_client_id(client_id)
    print(subs_user)
    reply_keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for subs in subs_user:
        datestart = subs['datestart']
        dateend = subs['dateend']
        days = (datetime.strptime(dateend, "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(datestart, "%Y-%m-%dT%H:%M:%SZ")).days

        if days >= 31:
            reply_keyboard.add(
                InlineKeyboardButton(f"{subs['name']} - {days // 30} мес." if subs['name'] else "Unnamed Rate",
                                    callback_data=f'add_days_for_{subs["id"]}')
            )
        else:
            reply_keyboard.add(
                InlineKeyboardButton(f"{subs['name']} - {days} дней" if subs['name'] else "Unnamed Rate",
                                    callback_data=f'add_days_for_{subs["id"]}')
            )
    await bot.send_message(call.from_user.id, "🔀 Выберите подписку для которой хотите изменить тарифный план\n✔️ Текущие дни сохраняются с добавлением новых", reply_markup=reply_keyboard)


@dp.callback_query_handler(text='get_config')
async def get_config(call: types.CallbackQuery):
    client_id = await get_client_id_from_telegram_id(call.from_user.id)
    subs_user = await get_subscriptions_by_client_id(client_id)
    print(subs_user)
    reply_keyboard = InlineKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for subs in subs_user:
        if not subs['is_used']:
            datestart = subs['datestart']
            dateend = subs['dateend']
            days = (datetime.strptime(dateend, "%Y-%m-%dT%H:%M:%SZ") - datetime.strptime(datestart, "%Y-%m-%dT%H:%M:%SZ")).days
            if days >= 31:
                reply_keyboard.add(
                    InlineKeyboardButton(f"{subs['name']} - {days // 30} мес." if subs['name'] else "Unnamed Rate",
                                        callback_data=f'g_conf_{subs["id"]}')
                )
            else:
                reply_keyboard.add(
                    InlineKeyboardButton(f"{subs['name']} - {days} дней" if subs['name'] else "Unnamed Rate",
                                        callback_data=f'g_conf_{subs["id"]}')
                )
    await bot.send_message(call.from_user.id, "📱 Выберите подписку, для которой необходимо получить потерянный/удаленный файл", reply_markup=reply_keyboard)



@dp.callback_query_handler(text='skiprefcode', state="*")
async def skip_code(call: types.CallbackQuery, state: FSMContext):
    rates = await api_client.list_rates()

    filtered_rates = [rate for rate in rates if 'price' in rate and rate['price']]
    filtered_rates.sort(key=lambda rate: rate['price'])

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for rate in filtered_rates:
        keyboard.add(KeyboardButton(f"{rate['name']} - {rate['price']} руб."))

    await call.message.answer("⬇️ Выберите тариф из списка для новой подписки", reply_markup=keyboard)
    await Oform.Tariff.set()


@dp.message_handler(state=Oform.Promo)
async def process_promo_code(message: types.Message, state: FSMContext):
    try:
        inline_keyboard = InlineKeyboardMarkup()
        inline_keyboard.add(InlineKeyboardButton("Назад в главное меню", callback_data='back_to_main_menu'))

        client_input = message.text
        client_id = await get_client_id_from_telegram_id(message.from_user.id)

        # Get own client details to check own referral_id
        own_client_details = await someone_used_referral(client_id)
        if own_client_details.get('referral_id') == client_input:
            await message.answer("🚫 Вы не можете использовать собственный реферальный код", reply_markup=inline_keyboard)
            await Oform.Promo.set()
            return

        # Find the client by referral_id or id
        if len(client_input) == 36 and '-' in client_input:
            client = await someone_used_referral(client_input)
        else:
            client = await find_client_by_referral_id(client_input)
            if client == None:
                log("Client Referral code did not found: ", client)
                await message.answer("��� Не удалось найти клиента с указанным реферальным кодом", reply_markup=inline_keyboard)
                await Oform.Promo.set()
                return

        if isinstance(client, str):
            await message.answer(client, reply_markup=inline_keyboard)
            await Oform.Promo.set()
            return

        async with state.proxy() as data:
            data['referral_client_id'] = client['id']  # Save referral client ID to state
            data['referral_client_telegram_id'] = client['telegramid']  # Save telegram id to state
            data['is_referral'] = True  # Mark as referral for future state transitions

        async with state.proxy() as data:
            is_referral = data.get('is_referral', False)
            rates = await api_client.list_rates_isreferral() if is_referral else await api_client.list_rates()

        filtered_rates = [rate for rate in rates if 'price' in rate and rate['price']]
        filtered_rates.sort(key=lambda rate: rate['price'])

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for rate in filtered_rates:
            keyboard.add(KeyboardButton(f"{rate['name']} - {rate['price']} руб."))

        await message.answer("⬇️ Выберите тариф из списка для новой подписки", reply_markup=keyboard)
        await Oform.Tariff.set()

    except BadRequest as e:
        print(f"BadRequest Exception: {e}")
        log(f"BadRequest Exception: {e}")
    except Exception as e:
        log(f"Exception: {e}")
        print(f"Exception: {e}")



@dp.message_handler(state=UpdateSubs.SelectSubscription)
async def process_subscription_selection(message: types.Message, state: FSMContext):
    try:
        selected_subscription_name = message.text
        print(f"User selected subscription name: {selected_subscription_name}")

        data = await state.get_data()
        subscriptions = data.get('subscriptions', [])
        print(f"Available subscriptions from state: {subscriptions}")

        selected_subscription = next(
            (subscription for subscription in subscriptions if subscription['name'] == selected_subscription_name),
            None
        )

        if not selected_subscription:
            log("Selected subscription not found: ", selected_subscription)
            await message.answer("Выбранная подписка не найдена. Пожалуйста, выберите еще раз.")
            return

        print(f"Selected subscription details: {selected_subscription}")

        # Update the subscription end date
        update_result = await update_dateend_referral(selected_subscription['id'])
        await message.answer(update_result)

        # Optionally reset state or set to a new state
        await state.finish()
    except Exception as e:
        print(f"Exception in process_subscription_selection: {e}")
        log(f"Exception in process_subscription_selection: {e}")
        await message.answer("Произошла ошибка. Пожалуйста, попробуйте еще раз.")


@dp.callback_query_handler(text='support', state='*')
async def test_subscription(call: types.CallbackQuery, state: FSMContext):
    state.finish()
    inline_button = types.InlineKeyboardButton(text="Обратиться в поддержку", url="https://t.me/potok_support")
    inline_button2 = types.InlineKeyboardButton(text="Назад", callback_data='back_to_main_menu')

    # Создаем клавиатуру и добавляем кнопку
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(inline_button)
    keyboard.add(inline_button2)

    await call.message.answer(text="ℹ️ Перейдите по ссылке, чтобы связаться с технической поддержкой", reply_markup=keyboard)


@dp.message_handler(Command("support"), state='*')
async def test_subscription(message: types.Message, state: FSMContext):
    state.finish()
    inline_button = types.InlineKeyboardButton(text="Обратиться в поддержку", url="https://t.me/potok_support")
    inline_button2 = types.InlineKeyboardButton(text="Назад", callback_data='back_to_main_menu')

    # Создаем клавиатуру и добавляем кнопку
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(inline_button)
    keyboard.add(inline_button2)

    await message.answer(text="ℹ️ Перейдите по ссылке, чтобы связаться с технической поддержкой", reply_markup=keyboard)



@dp.message_handler(state=FormStates.PROMOCODE)
async def process_promo_code(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['promo_code'] = message.text
    # Здесь можно выполнить проверку промокода и продолжить логику
    await message.answer("Спасибо! Ваш запрос обрабатывается.")
    await state.finish()  # Сбрасываем состояние


@dp.callback_query_handler(state='*')
async def get_config_by_name(call: types.CallbackQuery, state: FSMContext):
    if 'g_conf_' in call.data:
        subs_id = call.data.replace('g_conf_', '')
        config_file_text = requests.post(f'{config.WGAPI_URL}/wireguard/get_config/', json={'subscription_id': subs_id}).json()['config_content']
        config_file_text = config_file_text.replace(",::/128", "")
        file_path = f'configs/{subs_id[:8]}.conf'
        with open(file_path, 'w+') as config_file:
            config_file.write(config_file_text)
        file = types.InputFile(file_path, filename=f"{subs_id[:8]}.conf")
        await bot.send_document(call.from_user.id, file)
        await main_menu_call(call)
    elif 'add_subs_' in call.data:
        subs_id = call.data.replace('add_subs_', '').split('///')[0]
        bonus_days = call.data.replace('add_subs_', '').split('///')[1]
        await bot.send_message(call.from_user.id, f'Вашей подписке был продлён срок на {bonus_days} дней!')
        await api_client.update_dateend_referral(subs_id, int(bonus_days))
    elif 'add_days_for_' in call.data:
        subs_id = call.data.replace('add_days_for_', '')
        rates = await api_client.list_rates()

        filtered_rates = [rate for rate in rates if 'price' in rate and rate['price']]
        filtered_rates.sort(key=lambda rate: rate['price'])

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for rate in filtered_rates:
            keyboard.add(KeyboardButton(f"{rate['name']} - {rate['price']} руб."))
        await bot.send_message(call.from_user.id, '⬇️ Выберите тариф из списка для продления текущей подписки', reply_markup=keyboard)
        await Add_days_for_sub.Tariff.set()
        async with state.proxy() as data:
            data['subs_id'] = subs_id


@dp.message_handler(state=Add_days_for_sub.Tariff)
async def process_device_type(message: types.Message, state: FSMContext):
    tariffname_price = message.text.split(' - ')
    tariffname = tariffname_price[0]
    tariffprice = re.sub(r'\D', '', tariffname_price[1])  # Remove non-numeric characters
    
    async with state.proxy() as data:
        data['tariffname'] = tariffname

    prices = [
        LabeledPrice(label=tariffname, amount=int(tariffprice) * 100)  # Convert to minor units, e.g., kopeks
    ]
    await bot.send_invoice(
        chat_id=message.chat.id,
        title='Оплата товара',
        description='Продление подписки',
        provider_token=YOOTOKEN,
        currency='RUB',
        prices=prices,
        start_parameter='pay',
        payload='product_id_prod'
    )

@dp.message_handler(state=FormStatesTestSubs.PROMO)
async def process_device_type(message: types.Message, state: FSMContext):
    promo = message.text
    # Check if the entered promo code is the predefined key
    if promo == key:
        # Update the test subscription field for the user
        # await update_test_subscription_used(message.from_user.id)
        
        # Attempt to add a new test subscription for the user
        response = await api_client.add_device(
            message.from_user.id, 'test rate', 'Тестовая подписка', 
            datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        )
        
        # If the response is not a string, something went wrong
        if not isinstance(response, str):
            await message.answer('Ошибка при создании подписки. Попробуйте снова позже.')
            await state.finish()
            return
        
        # Proceed with creating the UUID and configuring the subscription
        subscription_id = response
        try:
            uuid_obj = uuid.UUID(subscription_id)
        except ValueError:
            await message.answer('Ошибка: неверный формат UUID.')
            await state.finish()
            return
        
        # Prepare the WireGuard API payload with the subscription ID
        wg_payload = {'subscription_id': str(uuid_obj)}
        print(f"Request to WireGuard API: {wg_payload}")
        
        # Send request to WireGuard API
        wg_response = requests.post(f'{config.WGAPI_URL}/wireguard/add_user/', json=wg_payload)
        print(f"Response from WireGuard API: {wg_response.status_code} - {wg_response.text}")
        
        # Handle any issues in the WireGuard response
        if wg_response.status_code != 200:
            await message.answer('Ошибка при обращении к API WireGuard. Попробуйте снова позже.')
            await state.finish()
            return
        
        # Extract configuration content from response and write to a file
        wg_response_data = wg_response.json()
        config_file_text = wg_response_data.get('config_content', '').replace(",::/128", "")
        
        if not config_file_text:
            await message.answer('Ошибка: не удалось получить конфигурацию WireGuard.')
            await state.finish()
            return

        # Save configuration to a file and send to the user
        config_file_path = f'configs/{subscription_id[:8]}.conf'
        with open(config_file_path, 'w') as config_file:
            config_file.write(config_file_text)
        
        await bot.send_document(message.chat.id, open(config_file_path, 'rb'))
        os.remove(config_file_path)
        
        # Notify user of successful test subscription creation
        await message.answer(
        f"Поздравляем!\n"
        "Вы активировали подарочную подписку, чтобы подключить Potok VPN добавьте файл в приложение\n\n"
        '<a href="https://teletype.in/@potok_you/guide">Инструкция</a>',
        parse_mode=ParseMode.HTML
    )

        
        await state.finish()
        await main_menu(message)
    
    # Check if the promo code exists and is valid
    elif await get_uniqe_codes_and_update(promo):
        # Update the test subscription field for the user
        # await update_test_subscription_used(message.from_user.id)
        
        # Attempt to add a new promotional subscription
        response = await api_client.add_device(
            message.from_user.id, 'free_sub', 'Подарочная подписка', 
            datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        )
        
        # Handle response to ensure subscription creation was successful
        if not isinstance(response, str):
            await message.answer('Ошибка при создании подписки. Попробуйте снова позже.')
            await state.finish()
            return
        
        subscription_id = response
        
        # Verify the format of the subscription ID
        try:
            uuid_obj = uuid.UUID(subscription_id)
        except ValueError:
            await message.answer('Ошибка: неверный формат UUID.')
            await state.finish()
            return
        
        # Send subscription ID to WireGuard API
        wg_payload = {'subscription_id': str(uuid_obj)}
        wg_response = requests.post(f'{config.WGAPI_URL}/wireguard/add_user/', json=wg_payload)
        
        if wg_response.status_code != 200:
            await message.answer('Ошибка при обращении к API WireGuard. Попробуйте снова позже.')
            await state.finish()
            return
        
        # Get and clean up configuration text
        wg_response_data = wg_response.json()
        config_file_text = wg_response_data.get('config_content', '').replace(",::/128", "")
        
        if not config_file_text:
            await message.answer('Ошибка: не удалось получить конфигурацию WireGuard.')
            await state.finish()
            return
        
        # Save and send configuration file to user
        config_file_path = f'configs/{subscription_id[:8]}.conf'
        with open(config_file_path, 'w') as config_file:
            config_file.write(config_file_text)
        
        await bot.send_document(message.chat.id, open(config_file_path, 'rb'))
        os.remove(config_file_path)
        
        await message.answer(
        f"Поздравляем!\n"
        "Вы активировали подарочную подписку, чтобы подключить Potok VPN добавьте файл в приложение\n\n"
        '<a href="https://teletype.in/@potok_you/certificates">Инструкция</a>',
        parse_mode=ParseMode.HTML
    )

        
        await state.finish()
        await main_menu(message)
    
    # If the promo code is invalid, show error message
    else:
        await message.answer('🚫 Неверное кодовое слово либо истек срок его использования')
        await main_menu(message)


@dp.message_handler(state=Oform.Tariff)
async def process_tariff(message: types.Message, state: FSMContext):
    try:
        # Получение имени и цены тарифа из сообщения
        tariffname_price = message.text.split(' - ')
        tariffname = tariffname_price[0]
        tariffprice = re.sub(r'\D', '', tariffname_price[1])  # Убираем все символы кроме цифр

        # Сохранение информации о тарифе в состояние FSM
        async with state.proxy() as data:
            data['tariffname'] = tariffname

        # Получение идентификаторов клиента и тарифа
        telegram_id = message.chat.id
        client_id = await get_client_id_from_telegram_id(telegram_id)
        rate_id = await get_rate_id_from_ratename(tariffname)

        # Отправка запроса на Flask-сервер для создания оплаты
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:5000/initiate_payment",
                json={
                    "client_id": client_id,
                    "rate_id": rate_id,
                    "telegram_id": telegram_id
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    payment_link = data.get("payment_link")
                    if payment_link:
                        keyboard_payment = InlineKeyboardMarkup().add(InlineKeyboardButton(text="Оплатить", url=payment_link))
                        # Отправка ссылки на оплату в Telegram
                        await message.reply(
                            f"✅ Пожалуйста, завершите оплату по следующей ссылке\n"
                            "💬 После завершения оплаты конфигурация будет отправлена в этот чат.", reply_markup=keyboard_payment
                        )
                    else:
                        await message.reply("❌ Не удалось создать оплату. Попробуйте позже.")
                else:
                    error_message = await response.text()
                    await message.reply(f"❌ Ошибка создания оплаты: {error_message}")
    except Exception as e:
        await message.reply(f"Произошла ошибка: {str(e)}")



async def print_state(state: FSMContext):
    async with state.proxy() as data:
        print("Current state data:", data)

async def midnight_task():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{config.DJANGO_API_URL}/api/subscriptions/") as response:
            if response.status != 200:
                log(f"Failed to get subscriptions with status {response.status}: {await response.text()}")
                print(f"Failed to get subscriptions: {response.status}")
                return f"Failed to get subscriptions with status {response.status}: {await response.text()}"

            subscriptions = await response.json()

        for i in subscriptions:
            now = datetime.utcnow()  # Use UTC time for consistent comparisons
            end_datetime = datetime.strptime(i['dateend'], "%Y-%m-%dT%H:%M:%SZ")
            time_difference = end_datetime - now
            sub_name = i['name']

            if time_difference.days == 2:
                telegram_id = await get_telegram_id_for_client_id(i['clientid'])
                print(f"Sending message to Telegram ID: {telegram_id}")
                
                inline = InlineKeyboardMarkup().add(InlineKeyboardButton(text="⏩️ Продлить подписку", callback_data='change_plan'))
                
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=f"🔚 Срок действия Вашей подписки <b>{sub_name}</b> истекает через 2 дня\n⏩️ Продлить действие подписки можно в личном кабинете, либо по кнопке [⏩️ Продлить подписку] в сообщении\n🎟️ Пригласи друга и получи до 30 дней бесплатного доступа",
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline
                    )
                    print("Message sent successfully.")
                except Exception as e:
                    log(f"Failed to send message: {e}")
                    print(f"Failed to send message: {e}")

            elif time_difference.days == 1:
                telegram_id = await get_telegram_id_for_client_id(i['clientid'])
                print(f"Sending message to Telegram ID: {telegram_id}")
                
                inline = InlineKeyboardMarkup().add(InlineKeyboardButton(text="⏩️ Продлить подписку", callback_data='change_plan'))
                
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=f"🔚 Срок действия Вашей подписки <b>{sub_name}</b> истекает через 1 день\n⏩️ Продлить действие подписки можно в личном кабинете, либо по кнопке [⏩️ Продлить подписку] в сообщении\n🎟️ Пригласи друга и получи до 30 дней бесплатного доступа",
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline
                    )
                    print("Message sent successfully.")
                except Exception as e:
                    log(f"Failed to send message: {e}")
                    print(f"Failed to send message: {e}")
            elif time_difference.days == 0:
                telegram_id = await get_telegram_id_for_client_id(i['clientid'])
                print(f"Sending message to Telegram ID: {telegram_id}")
                
                inline = InlineKeyboardMarkup().add(InlineKeyboardButton(text="⏩️ Добавить подписку", callback_data='add_device'))
                
                try:
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=f"🔚 Срок действия Вашей подписки <b>{sub_name}</b> истёк\n⏩️ Оформить подписку можно в личном кабинете, либо по кнопке [⏩️ Добавить подписку] в сообщении\n🎟️ Пригласи друга и получи до 30 дней бесплатного доступа",
                        parse_mode=ParseMode.HTML,
                        reply_markup=inline
                    )
                    print("Message sent successfully.")
                except Exception as e:
                    (f"Failed to send message: {e}")
                    print(f"Failed to send message: {e}")






async def check_time():
    while True:
        now = datetime.now().time()
        if now.hour == 20 and now.minute == 0:
            await midnight_task()
        await asyncio.sleep(60)  # Проверять время каждую минуту


if __name__ == '__main__':
    import asyncio
    # Initialize logging with the log file from config.yaml
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    loop.create_task(check_time())
    loop.run_forever()
