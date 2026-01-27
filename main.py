import random
import config
import TeleBot
import psycopg2
from psycopg2 import Error
from telebot import types, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

TOKEN = config.TOKEN
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage)

def get_db_connection():
    try:
        connection = psycopg2.connect(**config.DB_CONFIG)
        return connection
    except Error:
        print("Ошибка подключения к базе данных!")
        return None


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    rus_word = State()
    other_words = State()

def register_user(user_id, username):
    connection = get_db_connection()
    if not connection:
        return
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO tg_users (tg_user_id, user_name) VALUES (%s, %s) ON CONFLICT (tg_user_id) DO NOTHING",
            (user_id, username)
        )
        connection.commit()
    finally:
        cursor.close()
        connection.close()

def get_user_id(tg_user_id):
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT id FROM tg_users WHERE tg_user_id = %s", (tg_user_id,))
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            return result[0] if result else None
        except Error:
            print(f"Ошибка при получении пользователя!")
            return None
    return None


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

    markup = types.ReplyKeyboardMarkup(row_width=2)
    rus_word = 'мир'
    target_word = 'Peace'
    other_words = ['Green', 'White', 'Hello', 'Car']
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


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        target_word = data['target_word']
    if message.text == target_word:
        bot.send_message(message.chat.id, 'Все правильно')
    else:
        bot.send_message(message.chat.id, 'Ошибка')


if __name__ == '__main__':
    print('Бот запущен...')
    print('Для завершения нажмите Ctrl+Z')
    bot.polling()