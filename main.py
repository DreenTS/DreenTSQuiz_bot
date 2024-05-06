import asyncio
import logging
import os
from datetime import datetime
from pytz import timezone
from time import mktime
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
import quiz_database
import scores_database
from quiz_data import QUESTIONS, OPTIONS, CORRECT_OPTION_INDEXES

# Диспетчер
DP = Dispatcher()
BOT_START_TIME = mktime(datetime.now(timezone('UTC')).timetuple())


class TimeCheckMiddleware(BaseMiddleware):

    async def __call__(self, handler, event, data):
        msg_time = mktime(event.date.astimezone(timezone('UTC')).timetuple())
        if msg_time >= BOT_START_TIME:
            return await handler(event, data)


# Устанавливаем middleware
DP.message.middleware(TimeCheckMiddleware())


# Хэндлер на команду /start
@DP.message(Command("start"))
async def cmd_start(message: types.Message):
    # Создаем сборщика клавиатур типа Reply
    builder = ReplyKeyboardBuilder()
    # Добавляем кнопки в сборщик
    buttons = [types.KeyboardButton(text="О боте"),
               types.KeyboardButton(text="Начать новую игру"),
               types.KeyboardButton(text="Продолжить проходить квиз"),
               types.KeyboardButton(text="Узнать мои баллы"),
               types.KeyboardButton(text="ТОП-10 пользователей")]
    builder.add(*buttons)
    builder.adjust(3)
    # Прикрепляем кнопки к сообщению
    image = types.FSInputFile('images/logo.png')
    await message.answer_photo(
        image,
        caption="Добро пожаловать! Можем начать новую игру  или продолжить проходить незаконченный квиз. Что выберете?",
        reply_markup=builder.as_markup(resize_keyboard=True)
    )


# Хэндлер на команду /info
@DP.message(F.text == "О боте")
@DP.message(Command("info"))
async def cmd_info(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(text='Привет! Это бот для прохождения квизов.\n'
                              'Вы можете ввести следующие команды:\n'
                              '   ***/info*** - выводит данное сообщение\n'
                              '   ***/new_quiz*** - начать новый квиз\n'
                              '   ***/continue*** - продолжить прохождение квиза\n'
                              '   ***/my_scores*** - узнать кол-во заработанных баллов\n'
                              '   ***/top_10*** - вывести ТОП-10 пользователей по прохождению квизов',
                         parse_mode='Markdown'
                         )


# Хэндлер на команду /new_quiz
@DP.message(F.text == "Начать новую игру")
@DP.message(Command("new_quiz"))
async def cmd_new_quiz(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(f"Давайте начнем квиз! "
                         f"За каждый правильный ответ в пройденном квизе Вы будете получать 1 балл!")
    # Запускаем новый квиз
    await new_quiz(message)


# Хэндлер на команду /continue
@DP.message(F.text == "Продолжить проходить квиз")
@DP.message(Command("continue"))
async def cmd_continue(message: types.Message):
    # Отправляем новое сообщение без кнопок
    await message.answer(f"Так, на чем же мы остановились...")
    await asyncio.sleep(1)
    # Запускаем новый квиз
    await continue_quiz(message)


# Хэндлер на команду /my_scores
@DP.message(F.text == "Узнать мои баллы")
@DP.message(Command("my_scores"))
async def cmd_my_scores(message: types.Message):
    # Отправляем новое сообщение без кнопок
    scores = await scores_database.get_scores(message.from_user.id)
    if scores and scores[1] > 0:
        await message.answer(text=f"Ваша статистика:\n"
                                  f"\n    ***Кол-во пройденных квизов:*** {scores[1]}"
                                  f"\n    ***Кол-во набранных баллов:*** {scores[0]}",
                             parse_mode='Markdown')
    else:
        await message.answer("Вы не прошли ни одного квиза :(")


# Хэндлер на команду /top_10
@DP.message(F.text == "ТОП-10 пользователей")
@DP.message(Command("top_10"))
async def cmd_top_10(message: types.Message):
    # Отправляем новое сообщение без кнопок
    users = await scores_database.get_top_10_scores()
    users = sorted(users, reverse=True, key=lambda x: x[3])
    result = ''
    for i, user in enumerate(users[:10]):
        if user[4] > 0:
            result += (f'\n{i + 1}) {user[1]}{" (@" + user[2] + ")" if user[2] else ""}:'
                       f'\n    ***кол-во баллов:*** {user[3]}'
                       f'\n    ***пройдено квизов:*** {user[4]}\n')

    result = result.replace('_', '\\_')

    if result:
        result = '***ТОП-10 пользователей по кол-ву баллов, набранных при прохождении квизов:***\n' + result
    else:
        result += 'Ни один пользователь ещё не проходил квизы :('

    await message.answer(text=result, parse_mode='Markdown')


async def new_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    user_tag = message.from_user.username
    # устанавливаем значение текущего индекса вопроса и id сообщения в -1
    await quiz_database.update(user_id, -1, -1)
    await scores_database.update_values(user_id, user_name, user_tag, 0, 0)
    # запрашиваем новый вопрос для квиза
    await get_question(message, user_id, -1)


async def continue_quiz(message):
    # получаем id пользователя, отправившего сообщение
    user_id = message.from_user.id
    current_user_data = await quiz_database.get_from_user(user_id)
    if current_user_data is not None and current_user_data[0] != -1:
        # запрашиваем новый вопрос для квиза
        await get_question(message, user_id, current_user_data[0] - 1)
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
    await quiz_database.update(user_id, curr_q_index, msg.message_id)


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
    user = callback.from_user
    user_msg_id = (await quiz_database.get_from_user(user.id))[1]

    if curr_msg_id == user_msg_id:
        # редактируем текущее сообщение с целью убрать кнопки (reply_markup=None)
        await callback.bot.edit_message_reply_markup(
            chat_id=user.id,
            message_id=callback.message.message_id,
            reply_markup=None
        )

        # Получение индекса текущего вопроса для данного пользователя
        current_question_index = (await quiz_database.get_from_user(user.id))[0]

        # Получение индекса текущего ответа пользователя
        current_option_index = int(callback.data.split('-')[0])

        # Отправляем в чат сообщение, что ответ верный
        if current_option_index == CORRECT_OPTION_INDEXES[current_question_index]:
            result = '***Верно! +1 балл!***'
            await scores_database.update_values(user.id, user.full_name, user.username, 1, 0)
        else:
            right_answer = OPTIONS[current_question_index][CORRECT_OPTION_INDEXES[current_question_index]]
            result = f'Неверно! Правильный ответ:\n***{right_answer}***'

        await callback.message.answer(
            text=f"Ваш ответ:\n***{OPTIONS[current_question_index][current_option_index]}***\n\n{result}",
            parse_mode='Markdown'
        )

        await asyncio.sleep(1)

        # Проверяем достигнут ли конец квиза
        if current_question_index < len(QUESTIONS) - 1:
            # Следующий вопрос
            await get_question(callback.message, user.id, current_question_index)
        else:
            await quiz_database.update(user.id, -1, -1)
            # Уведомление об окончании квиза
            await callback.message.answer(text="Это был последний вопрос. Квиз завершен!")
            await scores_database.update_values(user.id, user.full_name, user.username, 0, 1)


async def create_tables():
    await quiz_database.create_table()
    await scores_database.create_table()


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
        types.BotCommand(command="/info", description="Bot info"),
        types.BotCommand(command="/new_quiz", description="Start new quiz"),
        types.BotCommand(command="/continue", description="Continue quiz"),
        types.BotCommand(command="/my_scores", description="Show your total scores"),
        types.BotCommand(command="/top_10", description="Show TOP-10 users")
    ]
    await bot.set_my_commands(bot_commands)

    await create_tables()
    await DP.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
