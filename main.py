import random
import config
import TeleBot
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

TOKEN = config.TOKEN
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TOKEN, state_storage=state_storage)

known_users = []
userStep = {}
buttons = []


class Command:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    rus_word = State()
    other_words = State()


@bot.message_handler(commands=['cards', 'start'])
def start_bot(message):
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

    bot.send_message(message.chat.id, f'угадай слово {rus_word}',
                     reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['rus_word'] = rus_word
        data['other_words'] = other_words


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