import telebot
import os
from telebot.types import MessageEntity
from telebot.util import user_link 
import psycopg2
from postgreSQL import postgreSQL
from dotenv import load_dotenv


def telegramBot(TOKEN):
    DATABASE = os.getenv("DATABASE")
    USER = os.getenv("USER")
    PASSWORD = os.getenv("PASSWORD")
    HOST = os.getenv("HOST")
    PORT = os.getenv("PORT")

    psql = postgreSQL(DATABASE, USER,PASSWORD, HOST, PORT)

    bot = telebot.TeleBot(TOKEN)

    @bot.message_handler(commands=['start'])
    def startMessage(message):
        userId = int(message.from_user.id)
        chatId = int(message.chat.id)
        firstName = str(message.from_user.first_name)
        username = str(message.from_user.username)
        date = int(message.date)

        psql.devTestAddUserInBD(userId, chatId, firstName, username, 2, date)

        bot.send_message(message.chat.id, f"{message.from_user.first_name}")
    @bot.message_handler(commands=['help'])
    def helpMessage(message):
        bot.send_message(message.chat.id, "Привет")


    bot.infinity_polling()

if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    telegramBot(TOKEN)