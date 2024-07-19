from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
import handlers
import config
import logging

# Initialize bot and dispatcher
bot = Bot(token=config.TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot)

def register_handlers(dp):
    """ Register all handlers from the handlers module """
    handlers.register_all(dp)

def main():
    register_handlers(dp)
    executor.start_polling(dp, skip_updates=False)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    main()
