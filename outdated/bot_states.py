from aiogram.dispatcher.filters.state import State, StatesGroup

class BotStates(StatesGroup):
    AWAITING_REFERRAL_INPUT = State()  # State for when the bot is waiting for the user to input a referral ID.
