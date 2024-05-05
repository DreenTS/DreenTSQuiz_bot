import aiosqlite
from quiz_data import QUESTIONS

DB_NAME = 'quiz_bot.db'


async def create_table():
    # Создаем соединение с базой данных (если она не существует, то она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Выполняем SQL-запрос к базе данных
        await db.execute('CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER, '
                         'question_msg_id INTEGER)')
        # Сохраняем изменения
        await db.commit()


async def update(user_id, index, msg_id):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        if index >= len(QUESTIONS):
            index = -1
            msg_id = -1
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute(
            'INSERT OR REPLACE INTO quiz_state (user_id, question_index, question_msg_id) VALUES (?, ?, ?)',
            (user_id, index, msg_id))
        # Сохраняем изменения
        await db.commit()


async def get_from_user(user_id):
    # Подключаемся к базе данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute(
                f'SELECT question_index, question_msg_id FROM quiz_state WHERE user_id = {user_id}') as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            return results
