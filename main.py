from email import message
from telebot import types
import json
import telebot
import random
import time  # 1. Добавляем встроенный модуль для работы со временем
import sqlite3  # Подключаем встроенную базу данных


BOT_TOKEN = "8779703464:AAEH2SBc28Rc7v4iX5MniJ2dz1Rg3IK5qWI"  # Срочно поменяй в @BotFather!
bot = telebot.TeleBot(BOT_TOKEN)

balances = {}
bonus_cooldowns = {}
statuses = {}
farm_cooldowns = {}
user_businesses = {}
last_business_collect = {}
user_investments = {}
last_invest_collect = {}

# Функция, которая создает файл базы данных и таблицу внутри нее
def init_db():
    conn = sqlite3.connect("brat_base.db")
    cursor = conn.cursor()

    # Создаем таблицу 'users', где для каждого ID будет своя строка с балансом, статусом и т.д.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            status TEXT DEFAULT '🤡Лох🤡',
            business TEXT DEFAULT NULL,
            last_business_collect REAL DEFAULT 0,
            farm_cooldown REAL DEFAULT 0,
            bonus_cooldown REAL DEFAULT 0,
            invested_amount INTEGER DEFAULT 0,
            last_invest_collect REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


# Запускаем создание базы данных сразу при старте скрипта
init_db()


# Получить все данные игрока из базы данных
def get_user_data(user_id):
    conn = sqlite3.connect("brat_base.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT balance, status, business, last_business_collect, farm_cooldown, bonus_cooldown, invested_amount, last_invest_collect FROM users WHERE user_id = ?",
        (user_id,))
    row = cursor.fetchone()

    # Если юзера еще нет в базе, регистрируем его со стандартными значениями
    if row is None:
        current_time = time.time()
        cursor.execute("""
            INSERT INTO users (user_id, balance, status, business, last_business_collect, farm_cooldown, bonus_cooldown, invested_amount, last_invest_collect)
            VALUES (?, 0, '🤡Лох🤡', NULL, ?, 0, 0, 0, ?)
        """, (user_id, current_time, current_time))
        conn.commit()
        conn.close()
        # Возвращаем дефолтные значения
        return {
            "balance": 0, "status": "🤡Лох🤡", "business": None,
            "last_business_collect": current_time, "farm_cooldown": 0,
            "bonus_cooldown": 0, "invested_amount": 0, "last_invest_collect": current_time
        }

    conn.close()
    # Возвращаем данные в виде удобного словаря
    return {
        "balance": row[0], "status": row[1], "business": row[2],
        "last_business_collect": row[3], "farm_cooldown": row[4],
        "bonus_cooldown": row[5], "invested_amount": row[6], "last_invest_collect": row[7]
    }


# Обновить конкретное поле у игрока (например, баланс или статус)
def update_user_field(user_id, field_name, value):
    conn = sqlite3.connect("brat_base.db")
    cursor = conn.cursor()
    # Безопасно обновляем нужное поле по ID пользователя
    cursor.execute(f"UPDATE users SET {field_name} = ? WHERE user_id = ?", (value, user_id))
    conn.commit()
    conn.close()


def update_investments_income(user_id, chat_id):
    current_time = time.time()
    invested_amount = user_investments.get(user_id, 0)

    if invested_amount <= 0:
        return

    last_time = last_invest_collect.get(user_id, current_time)
    seconds_passed = current_time - last_time

    blocks_passed = int(seconds_passed // 600)

    if blocks_passed > 0:
        for _ in range(blocks_passed):
            if random.randint(1, 100) <= 10:
                invested_amount = int(invested_amount * 0.5)
                bot.send_message(chat_id, f"⚠ Кризис на рынке, брат! Твои инвестиции просели. На вкладе осталось: {invested_amount}🪙")
            else:
                invested_amount = int(invested_amount * 1.1)

        user_investments[user_id] = invested_amount
        last_invest_collect[user_id] = last_time + (blocks_passed * 600)

        if invested_amount <= 0:
            user_investments[user_id] = 0


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    if user_id not in balances:
        balances[user_id] = 0
    bot.send_message(message.chat.id, "42 брат! По всем командам пиши /commands. Про бота в /help")


@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "ЗАЧЕМ НУЖЕН ЭТОТ БОТ?\n"
        "Этого бота можно использовать для того чтобы скоротать пару минут. Или на крайняк если нечем заняться.\n"
        "ЧТО ТУТ МОЖНО ДЕЛАТЬ?\n"
        "В боте можно фармить коины, покупать статусы за которые ты будешь больше получать с фарма, покупать бизнесы, инвестировать, а также проиграть всё в казино!\n"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['commands'])
def send_commands(message):
    commands_text = (
        "Список крутых команд:\n"
        "/start - Запустить бота🟢\n"
        "/farm - Нафармить Братуха коины🪙\n"
        "/bonus - Получить бонус🎁\n"
        "/balance - Проверить свой счет💳\n"
        "/buy_status - Купить статус🛍️\n"
        "/buy_business [номер] - Купить пассивный бизнес🏢\n"
        "/casino [ставка] - Испытать удачу в казино🎲\n"
        "/invest [сумма] - Вложить коины под процент📈\n"
        "/help - О боте🤖"
    )
    bot.send_message(message.chat.id, commands_text)


@bot.message_handler(commands=['farm'])
def farm_coins(message):
    user_id = message.from_user.id
    data = get_user_data(user_id)  # Читаем из базы вместо словаря
    user_status = data["status"]
    current_time = time.time()
    cooldown_time = 3600

    last_time = data["farm_cooldown"]
    if current_time - last_time < cooldown_time:
        time_left = int(cooldown_time - (current_time - last_time))
        minutes_left = time_left // 60
        seconds_left = time_left % 60
        bot.send_message(message.chat.id, f"Тормози. Фармить можно будет только через {minutes_left} мин. {seconds_left} сек. ⏳")
        return

    if user_status == "🤡Лох🤡":
        rndcoins = random.randint(10, 25)
    elif user_status == "🤓Нормис🤓":
        rndcoins = random.randint(40, 80)
    elif user_status == "😎Пацан😎":
        rndcoins = random.randint(120, 200)
    elif user_status == "🔰Элита🔰":
        rndcoins = random.randint(350, 550)
    elif user_status == "💯Брат💯":
        rndcoins = random.randint(900, 1300)
    elif user_status == "✊42 Брат✊":
        rndcoins = random.randint(2500, 3800)
    elif user_status == "⚜️Легенда⚜️":
        rndcoins = random.randint(6000, 9000)
    else:
        return

    # Сохраняем новый баланс и КД в базу данных
    new_balance = data["balance"] + rndcoins
    update_user_field(user_id, "balance", new_balance)
    update_user_field(user_id, "farm_cooldown", current_time)

    bot.send_message(message.chat.id, f"Ты заработал {rndcoins} коинов. Сейчас у тебя: {new_balance}🪙")




# 3. НОВАЯ КОМАНДА ДЛЯ БОНУСА
@bot.message_handler(commands=['bonus'])
def get_bonus(message):
    user_id = message.from_user.id
    current_time = time.time()

    # 1. Забираем все свежие данные братухи из SQLite одной строчкой
    data = get_user_data(user_id)
    last_time = data["bonus_cooldown"]

    # 2. Проверяем кулдаун (30 минут = 1800 секунд)
    if current_time - last_time < 1800:
        time_left = int(1800 - (current_time - last_time))

        minutes_left = time_left // 60
        seconds_left = time_left % 60

        # Твой родной текст ответа с минутами и секундами
        bot.send_message(message.chat.id,
                         f"Тормози, братуха! Забрать бонус можно будет только через {minutes_left} мин. {seconds_left} сек.⏳")
        return

    # 3. Если кулдаун прошел, считаем новый баланс
    new_balance = data["balance"] + 50

    # 4. ОБНОВЛЯЕМ БАЗУ ДАННЫХ: Записываем новый баланс и новое время бонуса
    update_user_field(user_id, "balance", new_balance)
    update_user_field(user_id, "bonus_cooldown", current_time)

    # Твой родной победный текст
    bot.send_message(message.chat.id, f"Красава! Держи свой подгон в 50 коинов. Сейчас у тебя: {new_balance}🪙")


@bot.message_handler(commands=['balance'])
def check_balance(message):
    user_id = message.from_user.id

    # Сначала обновляем доходы (их мы перепишем чуть позже)
    # passive_coins = update_passive_income(user_id)
    # update_investment_income(user_id, message.chat.id)

    # ЧИТАЕМ ИЗ БАЗЫ: Получаем свежие данные игрока одной строчкой!
    data = get_user_data(user_id)

    current_balance = data["balance"]
    user_status = data["status"]
    invested_now = data["invested_amount"]

    # Твой неизмененный текст вывода!
    bot.send_message(message.chat.id,
                     f"На балансе: {current_balance} Братуха коинов🪙\nИнвестировано: {invested_now}💪\nТвой статус: {user_status}")


def update_passive_income(user_id):
    current_time = time.time()
    business = user_businesses.get(user_id, None)

    if not business:
        return 0

    if business == "🌯 Шаурмечная":
        income_per_minute = 5
    elif business == "🎮 Компьютерный клуб":
        income_per_minute = 30
    elif business == "🏎️ Автомойка":
        income_per_minute = 150
    else:
        return 0

    last_time = last_business_collect.get(user_id, current_time)
    seconds_passed = current_time - last_time
    blocks_passed = int(seconds_passed // 300)  # 5 минут

    if blocks_passed > 0:
        income_per_block = income_per_minute * 5
        total_income = blocks_passed * income_per_block

        if user_id not in balances:
            balances[user_id] = 0
        balances[user_id] += total_income
        last_business_collect[user_id] = last_time + (blocks_passed * 300)

        return total_income

    return 0



@bot.message_handler(commands=['buy_business'])
def buy_business(message):
    user_id = message.from_user.id
    current_balance = balances.get(user_id, 0)
    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "Доступные бизнесы:\n1. Шаурмечная (250🪙) - Для покупки напиши /buy_business 1\n2. Пк клуб (1200🪙) - Для покупки напиши /buy_business 2\n3. Автомойка (5000🪙) - Для покупки напиши /buy_business 3")
        return

    choice = args[1]

    if choice == "1":
        if current_balance >= 250:
            balances[user_id] -= 250
            user_businesses[user_id] = "🌯 Шаурмечная"
            last_business_collect[user_id] = time.time()  # Фиксируем время покупки
            bot.send_message(message.chat.id,"Поздравляю, ты купил Шаурмечную! Теперь тебе капает пассивный доход 5🪙 в 5 минут!")
        else:
            bot.send_message(message.chat.id, "Недостаточно коинов, нужно 250 брат")

    elif choice == "2":
        if current_balance >= 1200:
            balances[user_id] -= 1200
            user_businesses[user_id] = "🎮 Компьютерный клуб"
            last_business_collect[user_id] = time.time()
            bot.send_message(message.chat.id, "Поздравляю, ты открыл Компьютерный клуб! Доход 30🪙 в 5 минут!")
        else:
            bot.send_message(message.chat.id, "Недостаточно коинов, нужно 1200 брат")

    elif choice == "3":
        if current_balance >= 5000:
            balances[user_id] -= 5000
            user_businesses[user_id] = "🏎️ Автомойка"
            last_business_collect[user_id] = time.time()
            bot.send_message(message.chat.id,
                             "Уоу, ты открыл целую Автомойку! Доход 150🪙 в минуту, ты чертов гений бизнеса!")
        else:
            bot.send_message(message.chat.id, "Недостаточно коинов, нужно 5000 брат")
    else:
        bot.send_message(message.chat.id, "Нет такого бизнеса, брат. Выбирай от 1 до 3.")


@bot.message_handler(commands=['buy_status'])
def send_shop(message):
    user_id = message.from_user.id
    current_balance = balances.get(user_id, 0)
    user_status = statuses.get(user_id, "🤡Лох🤡")

    # ---- ПОКУПКА СТАТУСА НОРМИС ----
    if user_status == "🤡Лох🤡":
        if current_balance >= 150:
            balances[user_id] -= 150
            statuses[user_id] = "🤓Нормис🤓"
            bot.send_message(message.chat.id, f"Поздравляю, твой статус нормис! У тебя взяли за это 150 коинов")
        else:
            bot.send_message(message.chat.id, f"Для покупки нового статуса, необходимо иметь 150 коинов! Твой баланс: {current_balance}🪙")

    # ---- ПОКУПКА СТАТУСА ПАЦАН ----
    elif user_status == "🤓Нормис🤓":
        if current_balance >= 500:
            balances[user_id] -= 500
            statuses[user_id] = "😎Пацан😎"
            bot.send_message(message.chat.id, f"Поздравляю, твой статус пацан! У тебя взяли за это 500 коинов")
        else:
            bot.send_message(message.chat.id, f"Для покупки нового статуса, необходимо иметь 500 коинов! Твой баланс: {current_balance}🪙")

    # ---- ПОКУПКА СТАТУСА ЭЛИТА ----
    elif user_status == "😎Пацан😎":
        if current_balance >= 1500:
            balances[user_id] -= 1500
            statuses[user_id] = "🔰Элита🔰"
            bot.send_message(message.chat.id, f"Красава, твой статус элита! У тебя взяли за это 1500 коинов")
        else:
            bot.send_message(message.chat.id, f"Для покупки нового статуса, необходимо иметь 1500 коинов! Твой баланс: {current_balance}🪙")

     # ---- ПОКУПКА СТАТУСА БРАТ ----
    elif user_status == "🔰Элита🔰":
        if current_balance >= 4200:
            balances[user_id] -= 4200
            statuses[user_id] = "💯Брат💯"
            bot.send_message(message.chat.id, f"Красава, твой статус брат! У тебя взяли за это 4200 коинов")
        else:
            bot.send_message(message.chat.id, f"Для покупки нового статуса, необходимо иметь 4200 коинов! Твой баланс: {current_balance}🪙")

        # ---- ПОКУПКА СТАТУСА 42 БРАТ ----
    elif user_status == "💯Брат💯":
        if current_balance >= 12000:
            balances[user_id] -= 12000
            statuses[user_id] = "✊42 Брат✊"
            bot.send_message(message.chat.id, f"Красава, твой статус 42 брат! У тебя взяли за это 12000 коинов")
        else:
            bot.send_message(message.chat.id, f"Для покупки нового статуса, необходимо иметь 12000 коинов! Твой баланс: {current_balance}🪙")

    # ---- ПОКУПКА СТАТУСА ЛЕГЕНДА ----
    elif user_status == "✊42 Брат✊":
        if current_balance >= 30000:
            balances[user_id] -= 30000
            statuses[user_id] = "⚜️Легенда⚜️"
            bot.send_message(message.chat.id, f"Братуха, у тебя теперь статус легенды! У тебя взяли за это 30000 коинов")
        else:
            bot.send_message(message.chat.id, f"Для покупки нового статуса, необходимо иметь 30000 коинов! Твой баланс: {current_balance}🪙")

    else:
        bot.send_message(message.chat.id, "Ты достиг максимума!")


@bot.message_handler(commands=['casino'])
def play_casino(message):
    user_id = message.from_user.id
    data = get_user_data(user_id)  # Читаем из базы
    current_balance = data["balance"]

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        bot.send_message(message.chat.id, "Введи сумму ставки! Пример: /casino 50")
        return

    bet = int(args[1])
    if bet <= 0 or current_balance < bet:
        bot.send_message(message.chat.id, "Ставка неверна или мало коинов!")
        return

    result = random.choice(["win", "lose"])

    if result == "win":
        new_balance = current_balance + bet
        bot.send_message(message.chat.id, f"Повезло! Ты выиграл {bet} коинов. Сейчас у тебя: {new_balance}🪙")
    else:
        new_balance = current_balance - bet
        bot.send_message(message.chat.id, f"Не повезло! Ты слил {bet} коинов. Сейчас у тебя: {new_balance}🪙")

    update_user_field(user_id, "balance", new_balance)  # Сохраняем в базу


@bot.message_handler(commands=['invest'])
def invest_coins(message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    current_balance = data["balance"]

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        bot.send_message(message.chat.id, "Брат, введи сумму для инвестиций!")
        return

    amount = int(args[1])
    if amount <= 0 or current_balance < amount:
        bot.send_message(message.chat.id, "Недостаточно коинов или сумма неверна!")
        return

    new_balance = current_balance - amount
    new_invested = data["invested_amount"] + amount

    # Записываем в базу данных
    update_user_field(user_id, "balance", new_balance)
    update_user_field(user_id, "invested_amount", new_invested)
    update_user_field(user_id, "last_invest_collect", time.time())

    bot.send_message(message.chat.id, f"Молодец, ты инвестировал {amount} коинов. Теперь тебе капают +10% каждые 10 минут. Проверить вклад можно в /balance")





@bot.message_handler(content_types=['text'])
def echo_all(message: types.Message):
    bot.send_message(message.chat.id, "Неизвестная команда. Все доступные команды /commands")

if __name__ == "__main__":
    print("Бот успешно запущен...")
    bot.infinity_polling()