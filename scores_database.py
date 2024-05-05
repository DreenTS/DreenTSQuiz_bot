import aiosqlite


DB_NAME = 'scores.db'


async def create_table():
    # Создаем соединение с базой данных (если она не существует, то она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        # Выполняем SQL-запрос к базе данных
        await db.execute('CREATE TABLE IF NOT EXISTS scores (user_id INTEGER PRIMARY KEY, fullname VARCHAR, '
                         'username VARCHAR, total_scores INTEGER, quiz_amount INTEGER)')
        # Сохраняем изменения
        await db.commit()


async def update_values(user_id, fullname, username, scores, quiz_amount):
    # Создаем соединение с базой данных (если она не существует, она будет создана)
    async with aiosqlite.connect(DB_NAME) as db:
        _scores = await get_scores(user_id)
        if _scores:
            scores += _scores[0]
            quiz_amount += _scores[1]
        # Вставляем новую запись или заменяем ее, если с данным user_id уже существует
        await db.execute(
            'INSERT OR REPLACE INTO scores (user_id, fullname, username, total_scores, quiz_amount) VALUES '
            '(?, ?, ?, ?, ?)', (user_id, fullname, username, scores, quiz_amount))
        # Сохраняем изменения
        await db.commit()


async def get_scores(user_id):
    # Подключаемся к базе данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute(f'SELECT total_scores, quiz_amount FROM scores WHERE user_id = {user_id}') as cursor:
            # Возвращаем результат
            results = await cursor.fetchone()
            return results


async def get_top_10_scores():
    async with aiosqlite.connect(DB_NAME) as db:
        # Получаем запись для заданного пользователя
        async with db.execute(f'SELECT * FROM scores ') as cursor:
            # Возвращаем результат
            users = await cursor.fetchall()
            return users
