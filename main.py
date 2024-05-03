import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
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
    await asyncio.sleep(1)
    # Запускаем новый квиз
    await continue_quiz(message)


async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    # устанавливаем значение текущего индекса вопроса и id сообщения в -1
    await update_database(user_id, -1, -1)
    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id, -1)


async def continue_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    current_question_index = (await get_from_user(user_id))[0]
    if current_question_index is not None and current_question_index != -1:
        # запрашиваем новый вопрос для квиза
        await get_question(message, user_id, current_question_index - 1)
    else:
        await message.answer(text='У Вас нет незавершенных квизов!')


async def get_question(message, user_id, curr_q_index):
    curr_q_index += 1
    # Получаем список вариантов ответа для текущего вопроса
    opts = OPTIONS[curr_q_index]
    # Функция генерации кнопок для текущего вопроса квиза
    # В качестве аргументов передаем варианты ответов и значение правильного ответа (не индекс!)
    kb = generate_options_keyboard(opts)
    # Отправляем в чат сообщение с вопросом, прикрепляем сгенерированные кнопки
    msg = await message.answer(
        text=f"***Вопрос №{curr_q_index + 1}:***\n\n{QUESTIONS[curr_q_index]}",
        reply_markup=kb, parse_mode='Markdown')
    # Обновление номера текущего вопроса и id сообщения в базе данных
    await update_database(user_id, curr_q_index, msg.message_id)


def generate_options_keyboard(answer_options):
    # Создаем сборщика клавиатур типа Inline
    builder = InlineKeyboardBuilder()

    # В цикле создаем Inline кнопки, а точнее Callback-кнопки
    for index, option in enumerate(answer_options):
        builder.add(types.InlineKeyboardButton(
            # Текст на кнопках соответствует вариантам ответов
            text=option,
            # Присваиваем данные для колбэк запроса.
            callback_data=f"{index}-quiz_option")
        )

    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()


@DP.callback_query(F.data.split('-')[1] == "quiz_option")
async def got_quiz_option(callback: types.CallbackQuery):
    curr_msg_id = callback.message.message_id
    user_msg_id = (await get_from_user(callback.from_user.id))[1]

    if curr_msg_id == user_msg_id:
        # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.from_user.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )

        # Получение индекса текущего вопроса для данного пользователя
        current_question_index = (await get_from_user(callback.from_user.id))[0]

        # Получение индекса текущего ответа пользователя
        current_option_index = int(callback.data.split('-')[0])

        # Отправляем в чат сообщение, что ответ верный
        if current_option_index == CORRECT_OPTION_INDEXES[current_question_index]:
            result = 'Верно!'
        else:
            right_answer = OPTIONS[current_question_index][CORRECT_OPTION_INDEXES[current_question_index]]
            result = f'Неверно! Правильный ответ:\n***{right_answer}***'

        await callback.message.answer(
            text=f"Ваш ответ:\n***{OPTIONS[current_question_index][current_option_index]}***\n\n{result}",
            parse_mode='Markdown'
        )

        # Проверяем достигнут ли конец квиза
        if current_question_index < len(QUESTIONS):
            # Следующий вопрос
            await get_question(callback.message, callback.from_user.id, current_question_index)
        else:
            await update_database(callback.from_user.id, -1, -1)
            # Уведомление об окончании квиза
            await callback.message.answer(text="Это был последний вопрос. Квиз завершен!")


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
        types.BotCommand(command="/new_quiz", description="Start new quiz"),
        types.BotCommand(command="/continue", description="Continue quiz")
    ]
    await bot.set_my_commands(bot_commands)

    await create_table()
    await DP.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
