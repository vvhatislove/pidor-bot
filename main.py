import telebot
import os
from telebot.types import MessageEntity
from telebot.util import user_link
from postgreSQL import postgreSQL
import const
import config
import random
import time

def errorMessage(msg, bot):
    bot.send_message(msg.chat.id, "В моем Пидор механизме какой-то сбой⌛. Попробуй еще раз♻")
def wrongChatMessage(msg, bot):
    bot.send_message(msg.chat.id, "Ты долбаеб👺, в группу меня кинь и там прописывай эту команду☝")

def telegramBot(TOKEN):
    DATABASE = config.DATABASE
    USER = config.USER
    PASSWORD = config.PASSWORD
    HOST = config.HOST
    PORT = config.PORT
    adminId = config.adminId
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
    @bot.message_handler(commands=['achievements'])
    def achievementsMessage(message):
        try:
            if message.chat.type == 'private':
                return wrongChatMessage(message, bot)
            else:
                user = psql.userExists(message.from_user.id, message.chat.id)
                if user:
                    pidorCount = user[5]
                    achvMessage = f"🏆Достижения {message.from_user.username if message.from_user.username else message.from_user.first_name} в чате \"{message.chat.title}\":\n\n"
                    if pidorCount >= 1:
                        achvMessage += "✅\"Твоя первая анальная пробка\"🍍\n✍️Стать пидором 1 раз\n\n"
                    else:
                        achvMessage += f"❌\"Твоя первая анальная пробка\"🍍\n✍️Стать пидором 1 раз\n🤖Еще {1 - pidorCount} раз(а)\n\n"
                    if pidorCount >= 3:
                        achvMessage += "✅\"Добро пожаловать в Анал-Лэнд\"🍩\n✍️Стать пидором 3 раза\n\n"
                    else:
                        achvMessage += f"❌\"Добро пожаловать в Анал-Лэнд\"🍩\n✍️Стать пидором 3 раза\n🤖Еще {3 - pidorCount} раз(а)\n\n"
                    if pidorCount >= 10:
                        achvMessage += "✅\"Открой в себе Gachi-чакру\"🧘🏿\n✍️Стать пидором 10 раз\n\n"
                    else:
                        achvMessage += f"❌\"Открой в себе Gachi-чакру\"🧘🏿\n✍️Стать пидором 10 раз\n🤖Еще {10 - pidorCount} раз(а)\n\n"
                    if pidorCount >= 100:
                        achvMessage += "✅\"Путь к гейскому мастерству тернист и опасен\"🔥\n✍️Стать пидором 100\n\n"
                    else:
                        achvMessage += f"❌\"Путь к гейскому мастерству тернист и опасен\"🔥\n✍️Стать пидором 100 раз\n🤖Еще {100 - pidorCount} раз(а)\n\n"
                    if pidorCount >= 300:
                        achvMessage += "✅\"Отсос у тракториста\"🚜\n✍️Стать пидором 300 раз\n\n"
                    else:
                        achvMessage += f"❌\"Отсос у тракториста\"🚜\n✍️Стать пидором 300 раз\n🤖Еще {300 - pidorCount} раз(а)\n\n"
                    if pidorCount >= 1000:
                        achvMessage += "✅\"Король пидорской горы\"⛰\n✍️Стать пидором 1000 раз\n\n"
                    else:
                        achvMessage += f"❌\"Король пидорской горы\"⛰\n✍️Стать пидором 1000 раз\n🤖Еще {1000 - pidorCount} раз(а)\n\n"
                    bot.send_message(message.chat.id, achvMessage)

                else:
                    bot.send_message(message.chat.id, "К сожалению ты не зарегистрирован на участие😔 Зарегистрируйся с помощью команды 👉/reg@pidorochek_bot")
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    @bot.message_handler(commands=['pidor'])
    def pidorMessage(message):
        try:
            cd = psql.getCooldown(message.chat.id)
            if cd:
                cooldownTime = 86400
                timeCd = message.date - cd[2]
                if (timeCd) >= cooldownTime:
                    psql.deleteCooldown(cd[0])
                else:
                    tempTime = round((cooldownTime - timeCd)/3600)
                    if tempTime == 0:
                        tempTime = round((cooldownTime - timeCd)/60)
                        return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 осталось {tempTime} минут(ы)⏳")
                    elif tempTime == 21 or tempTime == 1:
                        return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 остался {tempTime} час⏳")
                    elif tempTime == 2 or tempTime == 3 or tempTime == 4 or tempTime == 22 or tempTime == 23:
                        return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 осталось {tempTime} часa⏳")
                    else:
                        return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 осталось {tempTime} часов⏳")
            if message.chat.type == 'private':
                return wrongChatMessage(message, bot)
            else:
                psql.addCooldown(message.chat.id, message.date)
                users = psql.getRegUsers(message.chat.id)
                if bool(len(users)):
                    pidorIndex = random.randrange(len(users))
                    pidor = users[pidorIndex][4] if users[pidorIndex][4] else users[pidorIndex][3]
                    winPhraseIndex = random.randrange(len(const.winPidorPhrase))
                    firstPhraseIndex = random.randrange(len(const.pidorText))
                    secondPhraseIndex = None
                    while True:
                        secondPhraseIndex = random.randrange(len(const.pidorText))
                        if firstPhraseIndex == secondPhraseIndex:
                            continue
                        else:
                            break
                    time.sleep(0.5)
                    bot.send_message(message.chat.id, f"{const.pidorText[firstPhraseIndex]}")
                    time.sleep(1.5)
                    bot.send_message(message.chat.id, f"{const.pidorText[secondPhraseIndex]}")
                    time.sleep(1.5)
                    bot.send_message(message.chat.id, f"{const.winPidorPhrase[winPhraseIndex]}@{pidor}")
                    pidorCount = users[pidorIndex][5] + 1
                    # psql.addCooldown(message.chat.id, message.date)
                    psql.setPidorCount(message.chat.id, users[pidorIndex][1], pidorCount)
                    if pidorCount == 1:
                        bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidorIndex][4] if users[pidorIndex][4] else users[pidorIndex][3]}\nTы открыл(a) достижение!!!\n\n✅\"Твоя первая анальная пробка\"🍍\n✍️Стать пидором 1 раза\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                    if pidorCount == 3:
                        bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidorIndex][4] if users[pidorIndex][4] else users[pidorIndex][3]}\nTы открыл(a) достижение!!!\n\n✅\"Добро пожаловать в Анал-Лэнд\"🍩\n✍️Стать пидором 3 раза\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                    if pidorCount == 10:
                        bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidorIndex][4] if users[pidorIndex][4] else users[pidorIndex][3]}\nTы открыл(a) достижение!!!\n\n✅\"Открой в себе Gachi-чакру\"🧘🏿\n✍️Стать пидором 10 раз\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                    if pidorCount == 100:
                        bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidorIndex][4] if users[pidorIndex][4] else users[pidorIndex][3]}\nTы открыл(a) достижение!!!\n\n✅\"Путь к гейскому мастерству тернист и опасен\"🔥\n✍️Стать пидором 100\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                    if pidorCount == 300:
                        bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidorIndex][4] if users[pidorIndex][4] else users[pidorIndex][3]}\nTы открыл(a) достижение!!!\n\n✅\"Отсос у тракториста\"🚜\n✍️Стать пидором 300 раз\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                    if pidorCount == 1000:
                        bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidorIndex][4] if users[pidorIndex][4] else users[pidorIndex][3]}\nTы открыл(a) достижение!!!\n\n✅\"Король пидорской горы\"⛰\n✍️Стать пидором 1000 раз\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                else:
                    bot.send_message(message.chat.id, "К сожалению никто не зарегистрирован на участие😔 Зарегистрируйтесь с помощью команды 👉/reg@pidorochek_bot")
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    @bot.message_handler(commands=['stats'])
    def statsMessage(message):
        try:
            if message.chat.type == 'private':
                return wrongChatMessage(message, bot)
            else:
                users = psql.getRegUsers(message.chat.id)
                if bool(len(users)):
                    statsMessage = f"Статистика пидорасов чата \"{message.chat.title}\"👇\n"
                    users.sort(key=lambda x:x[5],reverse=True)
                    i = 0
                    for user in users:
                        if i == 0:
                            statsMessage += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)🥇\n"
                        elif i == 1:
                            statsMessage += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)🥈\n"
                        elif i == 2:
                            statsMessage += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)🥉\n"
                        else:
                            statsMessage += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)💩\n"
                        i += 1
                    bot.send_message(message.chat.id, statsMessage)
                else:
                    bot.send_message(message.chat.id, "Никто не зарегистрирован😭, пидорасов нет🙄\nЧтобы зарегистрироваться напишите 👉/reg@pidorochek_bot🙏")
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    @bot.message_handler(commands=['updatedata'])
    def updatedataMessage(message):
        try:
            if message.chat.type == 'private':
                return wrongChatMessage(message, bot)
            else:
                psql.updateData(message.from_user.id, str(message.from_user.username), str(message.from_user.first_name));
                bot.reply_to(message, f"Твои данные перезаписаны в ПидорБазу!📃\n👉Имя: {message.from_user.first_name}\n👉Никнейм: {message.from_user.username}")
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    # @bot.message_handler(commands=['dev'])
    # def dev(message):
    #     test = psql.userExists(266460350, -1001414157209)
    #     print(test[4].rstrip() if not(test[4].rstrip() == 'None') else test[3].rstrip())
        
    @bot.message_handler(content_types=['text'])
    def triggerMessage(message):
        try:
            if not (message.chat.id == message.from_user.id):
                for trigger in const.triggers:
                    if trigger in message.text.lower():
                        tempIndex = random.randrange(len(const.answerTriggers))
                        bot.reply_to(message, const.answerTriggers[tempIndex])
                        break
        except Exception as e:
            print(e)
            errorMessage(message, bot)
    bot.infinity_polling()

if __name__ == '__main__':
    TOKEN = config.TOKEN
    telegramBot(TOKEN)