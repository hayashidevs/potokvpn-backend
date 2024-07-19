from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def build_main_menu_keyboard():
    """Build the main menu inline keyboard."""
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton("Personal Cabinet", callback_data='personal_cabinet'),
        InlineKeyboardButton("Add Device", callback_data='add_device'),
        InlineKeyboardButton("Technical Support", callback_data='technical_support'),
        InlineKeyboardButton("Instruction", callback_data='instruction'),
        InlineKeyboardButton("Secret Code for Trial Sub", callback_data='trial_sub')
    ]
    keyboard.add(*buttons)
    return keyboard

def create_inline_keyboard(items, prefix=''):
    """ Generate an inline keyboard from a list of items with optional prefix """
    keyboard = InlineKeyboardMarkup()
    for item in items:
        button_text = f"{item['name']} - {item.get('detail', '')}"
        callback_data = f"{prefix}{item['id']}"
        keyboard.add(InlineKeyboardButton(button_text, callback_data=callback_data))
    return keyboard

def build_rate_keyboard(rates):
    """Generate an inline keyboard from a list of rate items."""
    keyboard = InlineKeyboardMarkup()
    for rate in rates:
        button_text = f"{rate['name']}"
        callback_data = f"choose_rate_{rate['id']}"  # Corrected f-string usage
        button = InlineKeyboardButton(button_text, callback_data=callback_data)
        keyboard.add(button)
    return keyboard

def error_message():
    """ Return a standard error message """
    return "An error occurred. Please try again later."