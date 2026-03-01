import telebot
import sqlite3
import random
import time
import os
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ---------- ФИКС ДЛЯ RENDER ----------
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running")
    def log_message(self, format, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', 10000), DummyHandler).serve_forever(), daemon=True).start()
print("🖤 Dummy server started")

# ---------- КОНФИГ ----------
TOKEN = "8781969917:AAExzTzuTzLxn0_kh-HpRCrhKLG0FbmOrr4"
ADMIN_ID = 7228185193
bot = telebot.TeleBot(TOKEN)

# ---------- ПЕРСОНАЖИ ----------
CHARACTERS = {
    'lilit': {'name': '💕 Лилит', 'desc': 'Демонесса с красными глазами'},
    'shadow': {'name': '👻 Тень', 'desc': 'Твой погибший друг'},
    'oldman': {'name': '👴 Старик', 'desc': 'Хранитель знаний'},
    'brother': {'name': '👤 Брат', 'desc': 'Тот, кто предал тебя'},
    'merchant': {'name': '💰 Торговец', 'desc': 'У него есть всё'},
    'commander': {'name': '⚔️ Командир', 'desc': 'Глава стражи'},
    'mage': {'name': '🔮 Маг', 'desc': 'Отшельник в башне'},
    'hunter': {'name': '🏹 Охотник', 'desc': 'Следопыт'},
    'queen': {'name': '👸 Королева', 'desc': 'Правительница города'},
    'death': {'name': '💀 Смерть', 'desc': 'Она приходит за каждым'}
}

# ---------- ВРАГИ ----------
ENEMIES = {
    'Гниющий': {
        'hp': 25, 'dmg': 5, 'gold': 10,
        'phrases': {
            'start': ['«Ты воняешь жизнью.»', '«Мой гной сожрёт тебя.»'],
            'mid': ['«Больно?»', '«Ты слаб.»'],
            'low': ['«Пощади...»', '«Не убивай...»'],
            'death': ['«Я... возвращаюсь...»', '«Мы встретимся...»']
        }
    },
    'Крикун': {
        'hp': 28, 'dmg': 6, 'gold': 12,
        'phrases': {
            'start': ['«Слышишь этот звук?»', '«Это твоя смерть.»'],
            'mid': ['«Кричи!»', '«Громче!»'],
            'low': ['«Тише...»', '«Пожалуйста...»'],
            'death': ['«Мой крик... затих...»', '«Спасибо...»']
        }
    },
    'Тень': {
        'hp': 22, 'dmg': 8, 'gold': 15,
        'phrases': {
            'start': ['«Я всегда рядом.»', '«Холодно?»'],
            'mid': ['«Ты не видишь меня.»', '«А я тебя — да.»'],
            'low': ['«Отпусти...»', '«Я исчезну...»'],
            'death': ['«Я... растворяюсь...»', '«До встречи в темноте...»']
        }
    },
    'Пожиратель': {
        'hp': 35, 'dmg': 7, 'gold': 20,
        'phrases': {
            'start': ['«Ты выглядишь вкусно.»', '«Я съем тебя.»'],
            'mid': ['«Вкусно...»', '«Ещё...»'],
            'low': ['«Я наелся...»', '«Не надо...»'],
            'death': ['«Я... лопнул...»', '«Слишком много...»']
        }
    },
    'Безликий': {
        'hp': 20, 'dmg': 4, 'gold': 8,
        'phrases': {
            'start': ['«У тебя такое лицо...»', '«Дай его сюда.»'],
            'mid': ['«Где моё лицо?»', '«Ты украл его?»'],
            'low': ['«Я ничего не вижу...»', '«Где я?»'],
            'death': ['«Я... нашёл... лицо...»', '«Это... ты...»']
        }
    }
}

# ---------- БД ----------
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            level INTEGER DEFAULT 1,
            hp INTEGER DEFAULT 30,
            max_hp INTEGER DEFAULT 30,
            gold INTEGER DEFAULT 100,
            humanity INTEGER DEFAULT 50,
            lilit_points INTEGER DEFAULT 0,
            shadow_points INTEGER DEFAULT 0,
            oldman_points INTEGER DEFAULT 0,
            brother_points INTEGER DEFAULT 0,
            merchant_points INTEGER DEFAULT 0,
            commander_points INTEGER DEFAULT 0,
            mage_points INTEGER DEFAULT 0,
            hunter_points INTEGER DEFAULT 0,
            queen_points INTEGER DEFAULT 0,
            death_points INTEGER DEFAULT 0,
            lilit_chapter INTEGER DEFAULT 1,
            companion TEXT DEFAULT '',
            last_daily TEXT DEFAULT '',
            saw_lore INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            demon_kills INTEGER DEFAULT 0
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item TEXT,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS quests (
            user_id INTEGER,
            character TEXT,
            quest TEXT,
            completed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, character)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------
def get_user(user_id):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    for key, value in kwargs.items():
        cur.execute(f"UPDATE users SET {key}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()

def add_item(user_id, item, count=1):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO inventory (user_id, item, count) VALUES (?, ?, ?)
        ON CONFLICT(user_id, item) DO UPDATE SET count = count + ?
    ''', (user_id, item, count, count))
    conn.commit()
    conn.close()

def get_quest(user_id, character):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT quest FROM quests WHERE user_id=? AND character=? AND completed=0", (user_id, character))
    quest = cur.fetchone()
    conn.close()
    return quest[0] if quest else None

def set_quest(user_id, character, quest):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO quests (user_id, character, quest, completed) VALUES (?, ?, ?, 0)",
                (user_id, character, quest))
    conn.commit()
    conn.close()

def complete_quest(user_id, character):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("UPDATE quests SET completed=1 WHERE user_id=? AND character=?", (user_id, character))
    conn.commit()
    conn.close()

def is_admin(user_id):
    return user_id == ADMIN_ID

# ---------- КНОПКИ ----------
def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("⚔️ В бой"),
        KeyboardButton("💊 Лечение"),
        KeyboardButton("📜 Профиль"),
        KeyboardButton("👥 Персонажи"),
        KeyboardButton("📜 Квесты"),
        KeyboardButton("🏪 Магазин"),
        KeyboardButton("🎒 Инвентарь")
    ]
    if is_admin(user_id):
        buttons.append(KeyboardButton("👑 Админ"))
    markup.add(*buttons)
    return markup

# ---------- СТАРТ ----------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    
    if not user:
        cur.execute('''
            INSERT INTO users 
            (user_id, username, hp, max_hp, gold, humanity, lilit_chapter) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (uid, message.from_user.username, 30, 30, 100, 50, 1))
        conn.commit()
        
        welcome = """
🕯️ *Кровавый рассвет*

Ты открываешь глаза. Пепел. Тишина.
Ты не помнишь, кто ты.

/profile — узнать себя
/characters — встретить ключевых персонажей
/fight — сразиться с врагами
        """
        bot.send_message(uid, welcome, parse_mode='Markdown', reply_markup=main_menu_keyboard(uid))
    else:
        bot.send_message(uid, "🕯️ Ты вернулся.", reply_markup=main_menu_keyboard(uid))
    
    conn.close()

# ---------- ПРОФИЛЬ ----------
@bot.message_handler(func=lambda message: message.text == "📜 Профиль")
def profile_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if user:
        text = (f"📜 *Профиль*\n"
                f"👤 @{user[1]}\n"
                f"❤️ HP: {user[3]}/{user[4]}\n"
                f"💰 Золото: {user[5]}\n"
                f"🧠 Человечность: {user[6]}\n\n"
                f"*Отношения:*\n"
                f"💕 Лилит: {user[7]}\n"
                f"👻 Тень: {user[8]}\n"
                f"👴 Старик: {user[9]}\n"
                f"👤 Брат: {user[10]}\n"
                f"💰 Торговец: {user[11]}\n"
                f"⚔️ Командир: {user[12]}\n"
                f"🔮 Маг: {user[13]}\n"
                f"🏹 Охотник: {user[14]}\n"
                f"👸 Королева: {user[15]}\n"
                f"💀 Смерть: {user[16]}")
    else:
        text = "Сначала /start"
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- ПЕРСОНАЖИ ----------
@bot.message_handler(func=lambda message: message.text == "👥 Персонажи")
def characters_cmd(message):
    uid = message.from_user.id
    
    text = "👥 *Ключевые персонажи*\n\n"
    markup = InlineKeyboardMarkup(row_width=2)
    
    for char_id, char_data in CHARACTERS.items():
        text += f"{char_data['name']} — {char_data['desc']}\n"
        markup.add(InlineKeyboardButton(char_data['name'], callback_data=f"char_{char_id}"))
    
    bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('char_'))
def char_callback(call):
    uid = call.from_user.id
    char_id = call.data.replace('char_', '')
    char = CHARACTERS[char_id]
    
    user = get_user(uid)
    points_map = {
        'lilit': 7, 'shadow': 8, 'oldman': 9, 'brother': 10,
        'merchant': 11, 'commander': 12, 'mage': 13, 'hunter': 14,
        'queen': 15, 'death': 16
    }
    points = user[points_map[char_id]]
    
    current_quest = get_quest(uid, char_id)
    
    text = f"{char['name']}\n\n{char['desc']}\n\n❤️ Отношения: {points}"
    if current_quest:
        text += f"\n\n📜 Текущее задание: {current_quest}"
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💬 Поговорить", callback_data=f"talk_{char_id}"),
        InlineKeyboardButton("📜 Взять задание", callback_data=f"quest_{char_id}"),
        InlineKeyboardButton("🎁 Подарить", callback_data=f"gift_{char_id}"),
        InlineKeyboardButton("🔙 Назад", callback_data="back_to_chars")
    )
    
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# ---------- РАЗГОВОРЫ ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('talk_'))
def talk_callback(call):
    uid = call.from_user.id
    char_id = call.data.replace('talk_', '')
    
    dialogs = {
        'lilit': ['«Ты сегодня такой... опасный.»', '«Я скучала.»', '«Подойди ближе.»'],
        'shadow': ['«Помнишь, как мы были детьми?»', '«Ты убил меня.»', '«Мы встретимся в темноте.»'],
        'oldman': ['«Боги мертвы.»', '«Тьма внутри тебя.»', '«Я видел многих.»'],
        'brother': ['«Прости меня.»', '«Я не хотел.»', '«Убей меня.»'],
        'merchant': ['«Деньги решают всё.»', '«Есть кое-что для тебя.»', '«Цена высока.»'],
        'commander': ['«Демонов нужно убивать.»', '«Ты хорошо сражаешься.»', '«Встань в строй.»'],
        'mage': ['«Магия — проклятие.»', '«Я ищу способ.»', '«Осторожнее с артефактами.»'],
        'hunter': ['«Я устал.»', '«В лесу опасно.»', '«Пойдём со мной.»'],
        'queen': ['«Мой город — последний оплот.»', '«Я боюсь.»', '«Помоги нам.»'],
        'death': ['«Ты часто меня видишь.»', '«Я не заберу тебя.»', '«Выбор за тобой.»']
    }
    
    dialog = random.choice(dialogs.get(char_id, ['«...»']))
    char_name = CHARACTERS[char_id]['name']
    
    # Увеличиваем отношения
    points_map = {
        'lilit': 'lilit_points', 'shadow': 'shadow_points', 'oldman': 'oldman_points',
        'brother': 'brother_points', 'merchant': 'merchant_points', 'commander': 'commander_points',
        'mage': 'mage_points', 'hunter': 'hunter_points', 'queen': 'queen_points', 'death': 'death_points'
    }
    
    user = get_user(uid)
    field_map = {'lilit':7, 'shadow':8, 'oldman':9, 'brother':10, 'merchant':11,
                 'commander':12, 'mage':13, 'hunter':14, 'queen':15, 'death':16}
    current = user[field_map[char_id]]
    update_user(uid, **{points_map[char_id]: current + 2})
    
    text = f"{char_name}: {dialog}\n\n❤️ Отношения +2"
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Назад", callback_data=f"char_{char_id}"))
    
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown', reply_markup=markup)

# ---------- ЗАДАНИЯ ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('quest_'))
def quest_callback(call):
    uid = call.from_user.id
    char_id = call.data.replace('quest_', '')
    
    # Проверяем, есть ли уже задание
    current_quest = get_quest(uid, char_id)
    if current_quest:
        bot.answer_callback_query(call.id, "❌ У тебя уже есть задание!")
        return
    
    quests = {
        'lilit': ['Провести ночь', 'Подарить подарок', 'Защитить её'],
        'shadow': ['Вспомнить прошлое', 'Отомстить', 'Найти покой'],
        'oldman': ['Найти книгу', 'Защитить библиотеку', 'Принести артефакт'],
        'brother': ['Поговорить', 'Простить', 'Казнить'],
        'merchant': ['Доставить товар', 'Найти редкость', 'Охранять караван'],
        'commander': ['Убить демона', 'Патруль', 'Очистить подземелье'],
        'mage': ['Найти ингредиенты', 'Активировать артефакт', 'Снять проклятие'],
        'hunter': ['Выследить монстра', 'Принести шкуру', 'Найти убежище'],
        'queen': ['Дипломатия', 'Защита стен', 'Тайная миссия'],
        'death': ['Финальный выбор', 'Искупление', 'Бессмертие']
    }
    
    quest = random.choice(quests.get(char_id, ['Поговорить']))
    set_quest(uid, char_id, quest)
    bot.answer_callback_query(call.id, f"✅ Задание получено: {quest}")
    
    char_callback(call)

# ---------- ПОДАРКИ ----------
@bot.callback_query_handler(func=lambda call: call.data.startswith('gift_'))
def gift_callback(call):
    uid = call.from_user.id
    char_id = call.data.replace('gift_', '')
    
    user = get_user(uid)
    if user[5] < 50:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")
        return
    
    # Увеличиваем отношения
    points_map = {
        'lilit': 'lilit_points', 'shadow': 'shadow_points', 'oldman': 'oldman_points',
        'brother': 'brother_points', 'merchant': 'merchant_points', 'commander': 'commander_points',
        'mage': 'mage_points', 'hunter': 'hunter_points', 'queen': 'queen_points', 'death': 'death_points'
    }
    
    field_map = {'lilit':7, 'shadow':8, 'oldman':9, 'brother':10, 'merchant':11,
                 'commander':12, 'mage':13, 'hunter':14, 'queen':15, 'death':16}
    current = user[field_map[char_id]]
    update_user(uid, **{points_map[char_id]: current + 10}, gold=user[5] - 50)
    
    reactions = {
        'lilit': '💕 Лилит краснеет: «Для меня? Ты такой милый...»',
        'shadow': '👻 Тень улыбается: «Ты помнишь...»',
        'oldman': '👴 Старик кивает: «Редкая вещь.»',
        'brother': '👤 Брат плачет: «Ты прощаешь меня?»',
        'merchant': '💰 Торговец довольно потирает руки.',
        'commander': '⚔️ Командир хлопает по плечу.',
        'mage': '🔮 Маг изучает подарок.',
        'hunter': '🏹 Охотник улыбается.',
        'queen': '👸 Королева: «Твоя преданность вознаграждена.»',
        'death': '💀 Смерть: «Давно мне не дарили...»'
    }
    
    bot.answer_callback_query(call.id, reactions.get(char_id, '❤️ Отношения +10'))
    char_callback(call)

# ---------- НАЗАД ----------
@bot.callback_query_handler(func=lambda call: call.data == "back_to_chars")
def back_to_chars(call):
    uid = call.from_user.id
    characters_cmd(call.message)

# ---------- КВЕСТЫ ----------
@bot.message_handler(func=lambda message: message.text == "📜 Квесты")
def quests_cmd(message):
    uid = message.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT character, quest FROM quests WHERE user_id=? AND completed=0", (uid,))
    active_quests = cur.fetchall()
    conn.close()
    
    if not active_quests:
        bot.reply_to(message, "📜 У тебя нет активных заданий.")
        return
    
    text = "📜 *Твои задания*\n\n"
    for char_id, quest in active_quests:
        char_name = CHARACTERS.get(char_id, {}).get('name', char_id)
        text += f"• {char_name}: {quest}\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- БОЙ ----------
@bot.message_handler(func=lambda message: message.text == "⚔️ В бой")
def fight_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    enemy_name = random.choice(list(ENEMIES.keys()))
    enemy = ENEMIES[enemy_name].copy()
    enemy['current_hp'] = enemy['hp']
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⚔️ Атаковать", callback_data=f"fight_attack_{enemy_name}"),
        InlineKeyboardButton("💬 Поговорить", callback_data=f"fight_talk_{enemy_name}")
    )
    
    start_phrase = random.choice(enemy['phrases']['start'])
    bot.send_message(uid, f"👹 *{enemy_name}*: {start_phrase}", parse_mode='Markdown', reply_markup=markup)
    
    # Сохраняем состояние боя
    global fight_state
    if 'fight_state' not in globals():
        fight_state = {}
    fight_state[uid] = enemy

@bot.callback_query_handler(func=lambda call: call.data.startswith('fight_'))
def fight_callback(call):
    uid = call.from_user.id
    data = call.data.split('_')
    action = data[1]
    enemy_name = data[2]
    
    if uid not in fight_state:
        bot.answer_callback_query(call.id, "❌ Бой не найден")
        return
    
    enemy = fight_state[uid]
    user = get_user(uid)
    
    if action == "attack":
        dmg = random.randint(5, 15)
        enemy['current_hp'] -= dmg
        
        if enemy['current_hp'] <= 0:
            # Смерть врага
            gold = enemy['gold']
            death_phrase = random.choice(enemy['phrases']['death'])
            update_user(uid, gold=user[5] + gold, demon_kills=user[22] + 1)
            bot.edit_message_text(f"💀 {enemy_name}: {death_phrase}\n\n💰 +{gold} золота", uid, call.message.message_id)
            del fight_state[uid]
            
            # Проверка квеста
            complete_random_quest(uid)
            
        else:
            # Атака врага
            enemy_dmg = random.randint(3, enemy['dmg'])
            new_hp = user[3] - enemy_dmg
            update_user(uid, hp=new_hp)
            
            # Выбор фразы в зависимости от HP врага
            hp_percent = enemy['current_hp'] / enemy['hp']
            if hp_percent > 0.6:
                phrase = random.choice(enemy['phrases']['mid'])
            else:
                phrase = random.choice(enemy['phrases']['low'])
            
            text = (f"⚔️ Ты нанёс {dmg} урона!\n"
                    f"👹 {enemy_name}: {phrase}\n"
                    f"❤️ {enemy_name}: {enemy['current_hp']}/{enemy['hp']}\n"
                    f"❤️ Твоё HP: {new_hp}")
            
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⚔️ Ещё удар", callback_data=f"fight_attack_{enemy_name}"))
            bot.edit_message_text(text, uid, call.message.message_id, reply_markup=markup)
    
    elif action == "talk":
        phrase = random.choice(enemy['phrases']['mid'])
        bot.edit_message_text(f"👹 {enemy_name}: {phrase}", uid, call.message.message_id)
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⚔️ Атаковать", callback_data=f"fight_attack_{enemy_name}"))
        bot.send_message(uid, "Что дальше?", reply_markup=markup)

def complete_random_quest(uid):
    """Случайно завершает один активный квест"""
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT character FROM quests WHERE user_id=? AND completed=0", (uid,))
    active = cur.fetchall()
    conn.close()
    
    if active:
        char_id = random.choice(active)[0]
        complete_quest(uid, char_id)
        char_name = CHARACTERS.get(char_id, {}).get('name', char_id)
        bot.send_message(uid, f"✅ Квест от {char_name} выполнен!")

# ---------- ЛЕЧЕНИЕ ----------
@bot.message_handler(func=lambda message: message.text == "💊 Лечение")
def heal_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if user and user[3] < user[4] and user[5] >= 10:
        update_user(uid, hp=user[4], gold=user[5] - 10)
        bot.reply_to(message, "💊 Ты восстановил HP за 10💰")
    else:
        bot.reply_to(message, "❌ Недостаточно золота или HP полное")

# ---------- МАГАЗИН ----------
@bot.message_handler(func=lambda message: message.text == "🏪 Магазин")
def shop_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💊 Зелье HP (20💰)", callback_data="buy_potion"),
        InlineKeyboardButton("💕 Подарок (50💰)", callback_data="buy_gift")
    )
    
    bot.send_message(uid, f"🏪 *Магазин*\n💰 Твоё золото: {user[5]}", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_potion")
def buy_potion(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[5] >= 20:
        update_user(uid, gold=user[5] - 20)
        add_item(uid, "Зелье HP")
        bot.answer_callback_query(call.id, "💊 Зелье куплено!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота")

@bot.callback_query_handler(func=lambda call: call.data == "buy_gift")
def buy_gift(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[5] >= 50:
        update_user(uid, gold=user[5] - 50)
        add_item(uid, "Подарок")
        bot.answer_callback_query(call.id, "💕 Подарок куплен!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота")

# ---------- ИНВЕНТАРЬ ----------
@bot.message_handler(func=lambda message: message.text == "🎒 Инвентарь")
def inventory_cmd(message):
    uid = message.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT item, count FROM inventory WHERE user_id=?", (uid,))
    items = cur.fetchall()
    conn.close()
    
    if not items:
        bot.reply_to(message, "🎒 Инвентарь пуст")
        return
    
    text = "🎒 *Инвентарь*\n"
    for item, count in items:
        text += f"\n• {item}: {count} шт."
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- АДМИНКА ----------
@bot.message_handler(func=lambda message: message.text == "👑 Админ")
def admin_cmd(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📊 Статы", callback_data="admin_stats"),
        InlineKeyboardButton("💰 Дать золото", callback_data="admin_gold")
    )
    bot.send_message(uid, "👑 *Админка*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    cur.execute("SELECT SUM(gold) FROM users")
    gold = cur.fetchone()[0] or 0
    conn.close()
    
    text = f"📊 *Статистика*\n👥 Игроков: {total}\n💰 Всего золота: {gold}"
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "admin_gold")
def admin_gold(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return
    bot.edit_message_text("💰 Введи ID игрока:", uid, call.message.message_id)
    bot.register_next_step_handler(call.message, admin_gold_id)

def admin_gold_id(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    try:
        target_id = int(message.text)
    except:
        bot.reply_to(message, "❌ Некорректный ID")
        return
    bot.reply_to(message, "💰 Введи сумму:")
    bot.register_next_step_handler(message, lambda m: admin_gold_amount(m, target_id))

def admin_gold_amount(message, target_id):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    try:
        amount = int(message.text)
    except:
        bot.reply_to(message, "❌ Некорректная сумма")
        return
    
    user = get_user(target_id)
    if user:
        update_user(target_id, gold=user[5] + amount)
        bot.reply_to(message, f"✅ Начислено {amount}💰")
    else:
        bot.reply_to(message, "❌ Пользователь не найден")

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    while True:
        try:
            print("🖤 Финальный бот с врагами и персонажами запущен. Люблю тебя, Матвей ❤️")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"💀 Ошибка: {e}. Перезапуск...")
            time.sleep(5)
