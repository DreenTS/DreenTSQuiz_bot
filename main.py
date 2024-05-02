import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from database import create_table

# Диспетчер
DP = Dispatcher()


# Хэндлер на команду /start
@DP.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем кнопки в сборщик
    buttons = [types.KeyboardButton(text="Начать новую игру"), types.KeyboardButton(text="Продолжить проходить квиз")]
    builder.add(*buttons)
    # Прикрепляем кнопки к сообщению
    await message.answer(
        "Добро пожаловать! Можем начать новую игру  или продолжить проходить незаконченный квиз. Что выберете?",
        reply_markup=builder.as_markup(resize_keyboard=True))


# Запуск процесса поллинга новых апдейтов
async def main():
    # Включаем логирование, чтобы не пропустить важные сообщения
    logging.basicConfig(level=logging.INFO)

    # Указываем токен бота
    api_token = os.environ.get('BOT_TOKEN')

    # Создаем объект бота
    bot = Bot(token=api_token)

    bot_commands = [
        types.BotCommand(command="/start", description="Start bot"),
        types.BotCommand(command="/quiz", description="Start new quiz"),
        types.BotCommand(command="/continue", description="Continue quiz")
    ]
    await bot.set_my_commands(bot_commands)

    await create_table()
    await DP.start_polling(bot)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    asyncio.run(main())
