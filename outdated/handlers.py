from aiogram import types
from aiogram.dispatcher.filters import Text
from api_client import (check_user_registration, register_user, get_user_details,
                        add_device, list_rates, create_subscription, apply_referral, create_peer_and_update_subscription)
from utils import (build_main_menu_keyboard, error_message)
from bot_states import BotStates
from aiogram.dispatcher import FSMContext

async def start_command(message: types.Message):
    user = message.from_user
    try:
        success, exists = await check_user_registration(user.id)
        if not success:
            await message.answer("Unable to verify user registration. Please try again.")
            return

        if not exists:
            success, response = await register_user(user.id, user.username, user.first_name, user.last_name)
            if not success:
                await message.answer(f"Registration failed: {response}")
                return
            await message.answer(f"Welcome to our bot, {user.first_name}!", reply_markup=build_main_menu_keyboard())
        else:
            await message.answer(f"Welcome back, {user.first_name}!", reply_markup=build_main_menu_keyboard())
    except Exception as e:
        await message.answer("An error occurred. Please try again later.")
        print(f"Error in start_command: {e}")

async def main_menu(callback_query: types.CallbackQuery):
    """ Display the main menu using inline keyboard """
    await callback_query.message.edit_text(
        "Main menu:",
        reply_markup=build_main_menu_keyboard()
    )

from aiogram import types

async def handle_callback_query(callback_query: types.CallbackQuery):
    """ Process callback queries """
    await callback_query.answer()  # Always respond to callback queries to stop the loading animation on the button
    data = callback_query.data
    # Log to ensure data is received (use print as a simple logging for debugging)
    print(f"Callback data received: {data}")

    if data == "personal_cabinet":
        await callback_query.message.edit_text("Here's your personal cabinet.")
    elif data == "add_device":
        await callback_query.message.edit_text("Please enter the name of your device:")
    elif data == "technical_support":
        await callback_query.message.edit_text("Contact support: support@example.com")
    elif data == "instruction":
        await callback_query.message.edit_text("Here are the instructions for using our services.")
    elif data == "trial_sub":
        await callback_query.message.edit_text("Please enter your secret code for a trial subscription.")
    else:
        await callback_query.message.edit_text("Select an option from the menu.")


async def device_addition_callback_query(call: types.CallbackQuery):
    """ Handle adding a new device from callback query """
    # Expect call.data to be in format "add_device_{device_name}"
    _, device_name = call.data.split('_')
    user_details = get_user_details(call.from_user.id)
    if user_details:
        success, _ = add_device(user_details['id'], device_name)
        if success:
            await call.message.answer("Device added successfully!")
        else:
            await call.message.answer(error_message())
    else:
        await call.message.answer("User not found.")
    await call.answer()

async def handle_subscription_selection(callback_query: types.CallbackQuery):
    rates = list_rates(is_referral=False)  # Assume this fetches non-referral rates
    await callback_query.message.edit_text(
        "Please choose a rate:",
        reply_markup=build_rate_keyboard(rates)
    )

async def handle_rate_selection(callback_query: types.CallbackQuery, rate_id):
    # Assume payment is done here, so proceed with peer creation
    subscription_id = "your_subscription_id_from_db"  # Get this from your database after payment
    success, response = create_peer_and_update_subscription(subscription_id)
    if success:
        await callback_query.message.answer("Subscription and WireGuard configuration created successfully!")
    else:
        await callback_query.message.answer(f"Failed to finalize subscription: {response}")

async def handle_referral_entry(message: types.Message, state: FSMContext):
    # Assuming we switch to this state after the user presses an "Enter Referral ID" button
    referral_id = message.text
    telegram_id = message.from_user.id

    # Attempt to apply the referral ID using the function defined in api_client.py
    success, response = apply_referral(telegram_id, referral_id)
    
    if success:
        await message.answer("Referral ID applied successfully!")
        await state.finish()  # Clear the current state after successful application
    else:
        await message.answer(f"Failed to apply Referral ID: {response}")
        await state.finish()  # Optionally clear the state even after failure or ask for retry


async def finalize_subscription(callback_query: types.CallbackQuery, rate_id):
    user_id = callback_query.from_user.id
    success, response = create_subscription(user_id, rate_id)
    if success:
        await callback_query.message.answer("Subscription created successfully!")
    else:
        await callback_query.message.answer(f"Failed to create subscription: {response}")

def register_all(dp):
    dp.register_message_handler(start_command, commands=['start'])
    dp.register_message_handler(main_menu, commands=['menu'])
    dp.register_callback_query_handler(device_addition_callback_query, Text(startswith='add_device_'))
    dp.register_message_handler(handle_subscription_selection, commands=['choose_rate'])
    dp.register_callback_query_handler(finalize_subscription, lambda call: call.data.startswith('rate_'))
    dp.register_callback_query_handler(handle_callback_query)  # This handles all callback queries
    dp.register_message_handler(handle_referral_entry, state=BotStates.AWAITING_REFERRAL_INPUT)
    dp.register_callback_query_handler(finalize_subscription, lambda cq: cq.data.startswith('choose_rate_'))