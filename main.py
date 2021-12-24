import telebot
from postgreSQL import PostgreSQL
import const
import random
import time
import os

DATABASE = os.environ.get('DATABASE')
USER = os.environ.get('USERNAMEDB')
PASSWORD = os.environ.get('PASSWORD')
HOST = os.environ.get('HOST')
PORT = 5432
adminId = int(os.environ.get('adminId'))

def error_message(msg, bot):
    bot.send_message(msg.chat.id, "В моем Пидор механизме какой-то сбой⌛. Попробуй еще раз♻")
def wrong_chat_message(msg, bot):
    bot.send_message(msg.chat.id, "Ты долбаеб👺, в группу меня кинь и там прописывай эту команду☝")

def telegram_bot(token):

    bot = telebot.TeleBot(token)

    @bot.message_handler(commands=['start'])
    def start_message(message):
        try: 
            if message.chat.type == 'private':
                bot.send_message(message.chat.id, f"Приветствую {message.from_user.first_name if message.from_user.first_name else message.from_user.username}👋. Я Пидор Бот🌈, чтобы воспользоваться мною, добавь меня в чат к своим друзьям или коллегам💪, и пропиши там 👉/start@pidorochek_bot")
            else:
                bot.send_message(message.chat.id, f"Приветствую обитателей чата {message.chat.title}👋.\n Я Пидор Бот🌈, вот вам краткая инструкция как мною пользоватся🔧\nВсе участники должны написать 👉/reg@pidorochek_bot\n(Чтобы посмотреть список зарегистрированых участников📜 напишите 👉/showreg@pidorochek_bot)\nПосле того как все кто хотели зарегистрировались, прописываете 👉/pidor@pidorochek_bot\nЕсли вы хотите посмотреть другие доступные команды📋 напишите 👉/help@pidorochek_bot\n Да начнется ебля в сраку👉👌")
        except Exception as e:
            print(e)
            error_message(message, bot)

    @bot.message_handler(commands=['help'])
    def help_message(message):
        try:
            if message.from_user.id == adminId and message.chat.id == adminId:
                bot.send_message(message.chat.id, f"Команды для простых смертных:\n{const.private_commands}\nМои команды:\n{const.admin_commands}")
            elif message.chat.id == message.from_user.id:
                bot.send_message(message.chat.id, const.private_commands)
            else:
                bot.send_message(message.chat.id, const.commands)
        except Exception as e:
            print(e)
            error_message(message, bot)
    @bot.message_handler(commands=['reg'])
    def reg_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                if message.chat.type == 'private':
                    return wrong_chat_message(message, bot)
                else:
                    users = psql.user_exists(message.from_user.id, message.chat.id)
                    if users:
                        bot.send_message(message.chat.id, "Вы уже зарегистрировались🤡")
                    else:
                        user_id = int(message.from_user.id)
                        chat_id = int(message.chat.id)
                        first_name = str(message.from_user.first_name)
                        username = str(message.from_user.username)
                        date = int(message.date)
                        psql.add_user(user_id, chat_id, first_name, username, date)
                        bot.send_message(message.chat.id, "Вы успешно зарегистрировались🌈")
            except Exception as e:
                print(e)
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)
    @bot.message_handler(commands=['unreg'])
    def unreg_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                if message.chat.type == 'private':
                    return wrong_chat_message(message, bot)
                else:
                    users = psql.user_exists(message.from_user.id, message.chat.id)
                    if users:
                        psql.delete_user(users[0])
                        bot.send_message(message.chat.id, "Вы отменили регистрацию на участие🙅‍♂️ и проебали всю статистику\nА что поделать, такова жизнь🤷‍♂️")
                    else:
                        bot.send_message(message.chat.id, "Вы и так не зарегистрированы, нечего отменять🤡")

            except Exception as e:
                print(e)
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)

    @bot.message_handler(commands=['showreg'])
    def show_reg_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                if message.chat.type == 'private':
                    return wrong_chat_message(message, bot)
                else:
                    users = psql.get_reg_users(message.chat.id)
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
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)
    @bot.message_handler(commands=['achievements'])
    def achievements_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                if message.chat.type == 'private':
                    return wrong_chat_message(message, bot)
                else:
                    user = psql.user_exists(message.from_user.id, message.chat.id)
                    if user:
                        pidor_count = user[5]
                        achv_message = f"🏆Достижения {message.from_user.username if message.from_user.username else message.from_user.first_name} в чате \"{message.chat.title}\":\n\n"
                        if pidor_count >= 1:
                            achv_message += "✅\"Твоя первая анальная пробка\"🍍\n✍️Стать пидором 1 раз\n\n"
                        else:
                            achv_message += f"❌\"Твоя первая анальная пробка\"🍍\n✍️Стать пидором 1 раз\n🤖Еще {1 - pidor_count} раз(а)\n\n"
                        if pidor_count >= 3:
                            achv_message += "✅\"Добро пожаловать в Анал-Лэнд\"🍩\n✍️Стать пидором 3 раза\n\n"
                        else:
                            achv_message += f"❌\"Добро пожаловать в Анал-Лэнд\"🍩\n✍️Стать пидором 3 раза\n🤖Еще {3 - pidor_count} раз(а)\n\n"
                        if pidor_count >= 10:
                            achv_message += "✅\"Открой в себе Gachi-чакру\"🧘🏿\n✍️Стать пидором 10 раз\n\n"
                        else:
                            achv_message += f"❌\"Открой в себе Gachi-чакру\"🧘🏿\n✍️Стать пидором 10 раз\n🤖Еще {10 - pidor_count} раз(а)\n\n"
                        if pidor_count >= 100:
                            achv_message += "✅\"Путь к гейскому мастерству тернист и опасен\"🔥\n✍️Стать пидором 100\n\n"
                        else:
                            achv_message += f"❌\"Путь к гейскому мастерству тернист и опасен\"🔥\n✍️Стать пидором 100 раз\n🤖Еще {100 - pidor_count} раз(а)\n\n"
                        if pidor_count >= 300:
                            achv_message += "✅\"Отсос у тракториста\"🚜\n✍️Стать пидором 300 раз\n\n"
                        else:
                            achv_message += f"❌\"Отсос у тракториста\"🚜\n✍️Стать пидором 300 раз\n🤖Еще {300 - pidor_count} раз(а)\n\n"
                        if pidor_count >= 1000:
                            achv_message += "✅\"Король пидорской горы\"⛰\n✍️Стать пидором 1000 раз\n\n"
                        else:
                            achv_message += f"❌\"Король пидорской горы\"⛰\n✍️Стать пидором 1000 раз\n🤖Еще {1000 - pidor_count} раз(а)\n\n"
                        bot.send_message(message.chat.id, achv_message)
                    else:
                        bot.send_message(message.chat.id, "К сожалению ты не зарегистрирован на участие😔 Зарегистрируйся с помощью команды 👉/reg@pidorochek_bot")
            except Exception as e:
                print(e)
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)
    @bot.message_handler(commands=['pidor'])
    def pidor_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                cd = psql.get_cooldown(message.chat.id)
                if cd:
                    cooldown_time = psql.get_cooldown_time()[1]
                    time_cd = message.date - cd[2]
                    if time_cd >= cooldown_time:
                        psql.delete_cooldown(cd[0])
                    else:
                        temp_time = round((cooldown_time - time_cd)/3600)
                        if temp_time == 0:
                            temp_time = round((cooldown_time - time_cd)/60)
                            return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 осталось {temp_time} минут(ы)⏳")
                        elif temp_time == 21 or temp_time == 1:
                            return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 остался {temp_time} час⏳")
                        elif temp_time == 2 or temp_time == 3 or temp_time == 4 or temp_time == 22 or temp_time == 23:
                            return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 осталось {temp_time} часa⏳")
                        else:
                            return bot.send_message(message.chat.id, f"До следующего определения пидора🌈 осталось {temp_time} часов⏳")
                if message.chat.type == 'private':
                    return wrong_chat_message(message, bot)
                else:
                    psql.add_cooldown(message.chat.id, message.date)
                    users = psql.get_reg_users(message.chat.id)
                    if bool(len(users)):
                        pidor_index = random.randrange(len(users))
                        pidor = users[pidor_index][4] if users[pidor_index][4] else users[pidor_index][3]
                        win_phrase_index = random.randrange(len(const.win_pidor_phrase))
                        first_phrase_index = random.randrange(len(const.pidor_text))
                        while True:
                            second_phrase_index = random.randrange(len(const.pidor_text))
                            if first_phrase_index == second_phrase_index:
                                continue
                            else:
                                break
                        time.sleep(0.5)
                        bot.send_message(message.chat.id, f"{const.pidor_text[first_phrase_index]}")
                        time.sleep(1.5)
                        bot.send_message(message.chat.id, f"{const.pidor_text[second_phrase_index]}")
                        time.sleep(1.5)
                        bot.send_message(message.chat.id, f"{const.win_pidor_phrase[win_phrase_index]}@{pidor}")
                        pidor_count = users[pidor_index][5] + 1
                        psql.set_pidor_count(message.chat.id, users[pidor_index][1], pidor_count)
                        if pidor_count == 1:
                            bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidor_index][4] if users[pidor_index][4] else users[pidor_index][3]}\nTы открыл(a) достижение!!!\n\n✅\"Твоя первая анальная пробка\"🍍\n✍️Стать пидором 1 раза\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                        if pidor_count == 3:
                            bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidor_index][4] if users[pidor_index][4] else users[pidor_index][3]}\nTы открыл(a) достижение!!!\n\n✅\"Добро пожаловать в Анал-Лэнд\"🍩\n✍️Стать пидором 3 раза\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                        if pidor_count == 10:
                            bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidor_index][4] if users[pidor_index][4] else users[pidor_index][3]}\nTы открыл(a) достижение!!!\n\n✅\"Открой в себе Gachi-чакру\"🧘🏿\n✍️Стать пидором 10 раз\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                        if pidor_count == 100:
                            bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidor_index][4] if users[pidor_index][4] else users[pidor_index][3]}\nTы открыл(a) достижение!!!\n\n✅\"Путь к гейскому мастерству тернист и опасен\"🔥\n✍️Стать пидором 100\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                        if pidor_count == 300:
                            bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidor_index][4] if users[pidor_index][4] else users[pidor_index][3]}\nTы открыл(a) достижение!!!\n\n✅\"Отсос у тракториста\"🚜\n✍️Стать пидором 300 раз\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                        if pidor_count == 1000:
                            bot.send_message(message.chat.id, f"🥳Поздровляю, @{users[pidor_index][4] if users[pidor_index][4] else users[pidor_index][3]}\nTы открыл(a) достижение!!!\n\n✅\"Король пидорской горы\"⛰\n✍️Стать пидором 1000 раз\n\nЧтобы посмотреть все достижения, воспользуйся /achievements@pidorochek_bot")
                    else:
                        bot.send_message(message.chat.id, "К сожалению никто не зарегистрирован на участие😔 Зарегистрируйтесь с помощью команды 👉/reg@pidorochek_bot")
            except Exception as e:
                print(e)
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)
    @bot.message_handler(commands=['stats'])
    def stats_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                if message.chat.type == 'private':
                    return wrong_chat_message(message, bot)
                else:
                    users = psql.get_reg_users(message.chat.id)
                    if bool(len(users)):
                        stats_message_text = f"Статистика пидорасов чата \"{message.chat.title}\"👇\n"
                        users.sort(key=lambda x: x[5], reverse=True)
                        i = 0
                        for user in users:
                            if i == 0:
                                stats_message_text += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)🥇\n"
                            elif i == 1:
                                stats_message_text += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)🥈\n"
                            elif i == 2:
                                stats_message_text += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)🥉\n"
                            else:
                                stats_message_text += f"👨‍❤️‍💋‍👨 {user[4].rstrip() if not(user[4].rstrip() == 'None') else user[3].rstrip()} - {user[5]} раз(а)💩\n"
                            i += 1
                        bot.send_message(message.chat.id, stats_message_text)
                    else:
                        bot.send_message(message.chat.id, "Никто не зарегистрирован😭, пидорасов нет🙄\nЧтобы зарегистрироваться напишите 👉/reg@pidorochek_bot🙏")
            except Exception as e:
                print(e)
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)
    @bot.message_handler(commands=['updatedata'])
    def update_data_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                psql.update_data(message.from_user.id, str(message.from_user.username), str(message.from_user.first_name))
                bot.reply_to(message, f"Твои данные перезаписаны в ПидорБазу!📃\n👉Имя: {message.from_user.first_name}\n👉Никнейм: {message.from_user.username}")
            except Exception as e:
                print(e)
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)
    # @bot.message_handler(commands=['dev'])
    # def dev(message):
    #     test = psql.user_exists(266460350, -1001414157209)
    #     print(test[4].rstrip() if not(test[4].rstrip() == 'None') else test[3].rstrip())

    # нужно сделать удаление чата если к нему нет доступа
    @bot.message_handler(commands=['changecooldowntime'])
    def change_cooldown_time_message(message):
        try:
            psql = PostgreSQL(DATABASE, USER, PASSWORD, HOST, PORT)
            try:
                if message.from_user.id == adminId:
                    new_cd_time = message.text[20:]
                    try:
                        int(new_cd_time)
                    except ValueError:
                        return bot.send_message(message.chat.id, "Чето ты не правильно ввел, перепроверь написание команды!\nДолжно быть так /changecooldowntime <секунды>")
                    psql.set_cooldown_time(new_cd_time)
                    bot.send_message(message.chat.id, f"Кд успешно изменен на {new_cd_time}c")
                    chatIds = psql.get_all_chat_id()
                    for ids in chatIds:
                        try:
                            bot.send_message(ids[0], f"⌛️Кулдаун на определение пидораса был изменен\n\n🆕Теперь {new_cd_time}c")
                        except Exception as ex:
                            # потом можно сделать отловку не найденых чатов
                            print(ex)
                            bot.send_message(message.chat.id, f"❌Нет доступа к чату id: {ids[0]}")
            except Exception as e:
                print(e)
                error_message(message, bot)
            finally:
                psql.close()
        except Exception as err:
            print(err)
            error_message(message, bot)
    @bot.message_handler(content_types=['text'])
    def trigger_message(message):
        try:
            if not (message.chat.id == message.from_user.id):
                for trigger in const.triggers:
                    if trigger in message.text.lower():
                        temp_index = random.randrange(len(const.answer_triggers))
                        bot.reply_to(message, const.answer_triggers[temp_index])
                        break
        except Exception as e:
            print(e)
            error_message(message, bot)
    bot.infinity_polling()


if __name__ == '__main__':
    telegram_bot(os.environ.get('TOKEN'))