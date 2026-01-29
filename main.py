import random
import config
import telebot
import psycopg2
from telebot import types
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

TOKEN = config.TOKEN
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage)

def get_db_connection():
    return psycopg2.connect(**config.DB_CONFIG)

class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'

class MyStates(StatesGroup):
    target_word = State()
    rus_word = State()
    other_words = State()
    add_english = State()
    add_russian = State()
    delete_word = State()

def register_user(user_id, username):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO tg_users (tg_user_id, user_name) VALUES (%s, %s) ON CONFLICT (tg_user_id) DO NOTHING",
        (user_id, username)
    )
    connection.commit()
    cursor.close()
    connection.close()

def get_user_id(tg_user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT id FROM tg_users WHERE tg_user_id = %s", (tg_user_id,))
    result = cursor.fetchone()
    cursor.close()
    connection.close()
    return result[0]

def get_random_word_from_db(exclude_words=None):
    connection = get_db_connection()
    cursor = connection.cursor()

    if exclude_words:
        placeholders = ','.join(['%s'] * len(exclude_words))
        query = f"SELECT english, russian FROM words WHERE english NOT IN ({placeholders}) ORDER BY RANDOM() LIMIT 1"
        cursor.execute(query, exclude_words)
    else:
        cursor.execute("SELECT english, russian FROM words ORDER BY RANDOM() LIMIT 1")

    result = cursor.fetchone()
    cursor.close()
    connection.close()

    return {'english': result[0], 'russian': result[1]}

def get_other_words_from_db(target_word, count=3):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT english FROM words WHERE english != %s ORDER BY RANDOM() LIMIT %s",
        (target_word, count)
    )
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    return [result[0] for result in results]

def get_user_words_from_db(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT eng_word, rus_word FROM user_words WHERE user_id = %s",
        (user_id,)
    )
    results = cursor.fetchall()
    cursor.close()
    connection.close()
    return [{'english': result[0], 'russian': result[1]} for result in results]

def add_user_word_to_db(user_id, english, russian):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "INSERT INTO user_words (user_id, eng_word, rus_word) VALUES (%s, %s, %s)",
        (user_id, english, russian)
    )
    connection.commit()
    cursor.close()
    connection.close()
    return True

def delete_user_word_from_db(user_id, english):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute(
        "DELETE FROM user_words WHERE user_id = %s AND eng_word = %s",
        (user_id, english)
    )
    connection.commit()
    deleted_count = cursor.rowcount
    cursor.close()
    connection.close()
    return True

def get_next_word(user_id):
    user_words = get_user_words_from_db(user_id)
    word = get_random_word_from_db([])
    other_words = get_other_words_from_db(word['english'])
    return word, other_words

@bot.message_handler(commands=['start'])
def start_command(message):
    register_user(message.from_user.id, message.from_user.username)

    welcome_text = """
    Привет! Я -  бот для изучения английских слов!

    Доступные команды:
    /start - Начать работу с ботом
    /cards - Начать изучение слов

    Что умеет этот бот:
    • Показывает русское слово и 4 варианта перевода на английский
    • Позволяет добавлять свои слова для изучения
    • Удаляет слова из вашего личного словаря

    Нажмите /cards, чтобы начать изучение!
    """

    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=['cards'])
def start_bot(message):
    register_user(message.from_user.id, message.from_user.username)
    user_id = get_user_id(message.from_user.id)
    word_data, other_words = get_next_word(user_id)

    markup = types.ReplyKeyboardMarkup(row_width=2)
    target_word = word_data['english']
    rus_word = word_data['russian']
    target_word_btn = types.KeyboardButton(target_word)
    other_words_btn = [types.KeyboardButton(word) for word in other_words]

    buttons = [target_word_btn] + other_words_btn
    random.shuffle(buttons)

    next_btn = types.KeyboardButton(Command.NEXT)
    add_word_btn = types.KeyboardButton(Command.ADD_WORD)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, add_word_btn, delete_word_btn])

    markup.add(*buttons)

    bot.send_message(message.chat.id, f'Выбери правильный перевод для слова: <b>{rus_word}</b>',
                     parse_mode='HTML', reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['rus_word'] = rus_word
        data['other_words'] = other_words
        data['user_id'] = user_id

@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_word(message):
    start_bot(message)

@bot.message_handler(func=lambda message: message.text == Command.ADD_WORD)
def add_word_command(message):
    bot.send_message(message.chat.id, "Напишите слово на английском языке:")
    bot.set_state(message.from_user.id, MyStates.add_english, message.chat.id)


@bot.message_handler(state=MyStates.add_english)
def add_english_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['new_english'] = message.text.strip().lower()

    bot.send_message(message.chat.id, "Теперь напишите его перевод на русский:")
    bot.set_state(message.from_user.id, MyStates.add_russian, message.chat.id)


@bot.message_handler(state=MyStates.add_russian)
def add_russian_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        english_word = data['new_english']
        russian_word = message.text.strip().lower()
        user_id = data.get('user_id', get_user_id(message.from_user.id))

    if user_id and add_user_word_to_db(user_id, english_word, russian_word):
        bot.send_message(message.chat.id, f"Слово '{english_word}' - '{russian_word}' успешно добавлено в ваш словарь!")
    else:
        bot.send_message(message.chat.id, "Не удалось добавить слово. Попробуйте еще раз.")

    bot.delete_state(message.from_user.id, message.chat.id)
    start_bot(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word_command(message):
    user_id = get_user_id(message.from_user.id)
    if user_id:
        user_words = get_user_words_from_db(user_id)
        if user_words:
            markup = types.ReplyKeyboardMarkup(row_width=2)
            for word in user_words[:10]:
                markup.add(types.KeyboardButton(word['english']))
            markup.add(types.KeyboardButton("Отмена"))

            bot.send_message(message.chat.id, "Выберите слово для удаления:", reply_markup=markup)
            bot.set_state(message.from_user.id, MyStates.delete_word, message.chat.id)
        else:
            bot.send_message(message.chat.id, "У вас нет добавленных слов для удаления.")
    else:
        bot.send_message(message.chat.id, "Ошибка при получении данных пользователя.")


@bot.message_handler(state=MyStates.delete_word)
def delete_word_process(message):
    if message.text == "Отмена":
        bot.delete_state(message.from_user.id, message.chat.id)
        start_bot(message)
        return

    user_id = get_user_id(message.from_user.id)
    if user_id and delete_user_word_from_db(user_id, message.text):
        bot.send_message(message.chat.id, f"Слово '{message.text}' успешно удалено из вашего словаря!")
    else:
        bot.send_message(message.chat.id, f"Не удалось удалить слово '{message.text}' или оно не найдено.")

    bot.delete_state(message.from_user.id, message.chat.id)
    start_bot(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if 'target_word' in data:
            target_word = data['target_word']
            if message.text == target_word:
                bot.send_message(message.chat.id, 'Все правильно! Чтобы продолжить, нажмите кнопку "Дальше".')
            else:
                bot.send_message(message.chat.id, 'Неправильно! Попробуйте еще раз!')

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    bot.send_message(message.chat.id, "Используйте кнопки на клавиатуре или команды /start, /cards")


if __name__ == '__main__':
    print('Бот запущен...')
    print('Для завершения нажмите Ctrl+Z')
    bot.add_custom_filter(telebot.custom_filters.StateFilter(bot))
    bot.polling()