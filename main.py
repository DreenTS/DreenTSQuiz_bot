import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database import create_table, update_database, get_from_user
from quiz_data import QUESTIONS, OPTIONS, CORRECT_OPTION_INDEXES


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


# Хэндлер на команды /new_quiz
@DP.message(F.text == "Начать новую игру")
@DP.message(Command("new_quiz"))
async def cmd_new_quiz(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(f"Давайте начнем квиз!")
    # Запускаем новый квиз
    await new_quiz(message)


# Хэндлер на команды /continue
@DP.message(F.text == "Продолжить проходить квиз")
@DP.message(Command("continue"))
async def cmd_continue(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(f"Так, на чем же мы остановились...")
    # Запускаем новый квиз
    await continue_quiz(message)


async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id

    # сбрасываем значение текущего индекса вопроса квиза в 0
    current_question_index = 0
    await update_database(user_id, current_question_index)

    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id)


async def continue_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    current_question_index = await get_from_user(user_id)
    if current_question_index is not None:
        # запрашиваем новый вопрос для квиза
        await get_question(message, user_id)
    else:
        await message.answer(text='У Вас нет незавершенных квизов!')


async def get_question(message, user_id):
    # Запрашиваем из базы текущий индекс для вопроса
    current_question_index = await get_from_user(user_id)
    # Получаем список вариантов ответа для текущего вопроса
    opts = OPTIONS[current_question_index]

    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа (не индекс!)
    kb = generate_options_keyboard(opts)
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    await message.answer(text=f"***Вопрос №{current_question_index + 1}:***\n\n{QUESTIONS[current_question_index]}",
                         reply_markup=kb, parse_mode='Markdown')


def generate_options_keyboard(answer_options):
    # Создаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()

    # В цикле создаем Inline кнопки, а точнее Callback-кнопки
    for index, option in enumerate(answer_options):
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=option,
            # Присваиваем данные для колбэк запроса.
            callback_data=f"{index}-quiz_answer")
        )

    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()


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


if __name__ == '__main__':
    asyncio.run(main())
