import telebot
import os
from telebot.types import MessageEntity
from telebot.util import user_link 
import psycopg2
from postgreSQL import postgreSQL
from dotenv import load_dotenv
import const

def errorMessage(msg, bot):
    bot.send_message(msg.chat.id, "В моем Пидор механизме какой-то сбой⌛. Попробуй еще раз♻")
def wrongChatMessage(msg, bot):
    bot.send_message(msg.chat.id, "Ты долбаеб👺, в группу меня кинь и там прописывай эту команду☝")

def telegramBot(TOKEN):
    DATABASE = os.getenv("DATABASE")
    USER = os.getenv("USER")
    PASSWORD = os.getenv("PASSWORD")
    HOST = os.getenv("HOST")
    PORT = os.getenv("PORT")
    adminId = int(os.getenv("adminId"))
    psql = postgreSQL(DATABASE, USER,PASSWORD, HOST, PORT)

    bot = telebot.TeleBot(TOKEN)

    @bot.message_handler(commands=['start'])
    def startMessage(message):
        try: 
            if message.chat.type == 'private':
                bot.send_message(message.chat.id, f"Приветствую {message.from_user.first_name if message.from_user.first_name else message.from_user.username}👋. Я Пидор Бот🌈, чтобы воспользоваться мною, добавь меня в чат к своим друзьям или коллегам💪, и пропиши там 👉/start@pidorochek_bot")
            else:
                bot.send_message(message.chat.id, f"Приветствую обитателей чата {message.chat.title}👋.\n Я Пидор Бот🌈, вот вам краткая инструкция как мною пользоватся🔧\nВсе участники должны написать 👉/reg@pidorochek_bot\n(Чтобы посмотреть список зарегистрированых участников📜 напишите 👉/showreg@pidorochek_bot)\nПосле того как все кто хотели зарегистрировались, прописываете 👉/pidor@pidorochek_bot\nЕсли вы хотите посмотреть другие доступные команды📋 напишите 👉/help@pidorochek_bot\n Да начнется ебля в сраку👉👌")
        except Exception as e:
            print(e)
            errorMessage(message, bot)
        # userId = int(message.from_user.id)
        # chatId = int(message.chat.id)
        # firstName = str(message.from_user.first_name)
        # username = str(message.from_user.username)
        # date = int(message.date)

        # psql.devTestAddUserInBD(userId, chatId, firstName, username, 2, date)

        # bot.send_message(message.chat.id, f"{message.from_user.first_name}")
    @bot.message_handler(commands=['help'])
    def helpMessage(message):
        try:
            if message.from_user.id == adminId and message.chat.id == adminId:
                bot.send_message(message.chat.id, f"Команды для простых смертных:\n{const.privateCommands}\nМои команды:\n")
            elif message.chat.id == message.from_user.id:
                bot.send_message(message.chat.id, const.privateCommands)
            else:
                bot.send_message(message.chat.id, const.commands)
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    @bot.message_handler(commands=['reg'])
    def regMessage(message):
        try:
            if message.chat.type == 'private':
                return wrongChatMessage(message, bot)
            else:
                users = psql.userExists(message.from_user.id,message.chat.id)
                if users:
                    bot.send_message(message.chat.id, "Вы уже зарегистрировались🤡")
                else:
                    userId = int(message.from_user.id)
                    chatId = int(message.chat.id)
                    firstName = str(message.from_user.first_name)
                    username = str(message.from_user.username)
                    date = int(message.date)
                    psql.addUser(userId,chatId,firstName,username,date);
                    bot.send_message(message.chat.id, "Вы успешно зарегистрировались🌈")
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    @bot.message_handler(commands=['unreg'])
    def unregMessage(message):
        try:
            if message.chat.type == 'private':
                return wrongChatMessage(message, bot)
            else:
                users = psql.userExists(message.from_user.id, message.chat.id)
                if users:
                    psql.deleteUser(users[0])
                    bot.send_message(message.chat.id, "Вы отменили регистрацию на участие🙅‍♂️ и проебали всю статистику\nА что поделать, такова жизнь🤷‍♂️")
                else:
                    bot.send_message(message.chat.id, "Вы и так не зарегистрированы, нечего отменять🤡")

                
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    @bot.message_handler(commands=['showreg'])
    def showregMessage(message):
        try:
            if message.chat.type == 'private':
                return wrongChatMessage(message, bot)
            else:
                users = psql.getRegUsers(message.chat.id)
                if bool(len(users)):
                    infoMessage = "📋Зарегистрированые участники:\n"
                    i = 1
                    for user in users:
                        infoMessage += f"{i}.👉 {user[3] if user [3] else user[4]}"
                        i += 1
                    bot.send_message(message.chat.id, infoMessage)
                else:
                    bot.send_message(message.chat.id, "Нет зарегистрированых пользователей🙇‍♂️, чтобы зарегистрироваться напишите 👉/reg@pidorochek_bot")

                   
        except Exception as e:
            print(e)
            errorMessage(message, bot)

    bot.infinity_polling()

if __name__ == '__main__':
    load_dotenv()
    TOKEN = os.getenv("TOKEN")
    telegramBot(TOKEN)