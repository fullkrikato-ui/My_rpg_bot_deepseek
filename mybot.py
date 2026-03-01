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

# ---------- БД ----------
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            faction TEXT DEFAULT 'none',
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            exp_next INTEGER DEFAULT 100,
            hp INTEGER DEFAULT 30,
            max_hp INTEGER DEFAULT 30,
            mana INTEGER DEFAULT 15,
            max_mana INTEGER DEFAULT 15,
            gold INTEGER DEFAULT 100,
            humanity INTEGER DEFAULT 50,
            lilit_points INTEGER DEFAULT 0,
            lilit_chapter INTEGER DEFAULT 1,
            companion TEXT DEFAULT '',
            last_daily TEXT DEFAULT '',
            saw_lore INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            demon_kills INTEGER DEFAULT 0,
            pvp_rating INTEGER DEFAULT 1000,
            pvp_wins INTEGER DEFAULT 0,
            pvp_losses INTEGER DEFAULT 0
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
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            ach_id TEXT,
            achieved INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, ach_id)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pvp_queue (
            user_id INTEGER PRIMARY KEY,
            timestamp INTEGER
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pvp_battles (
            battle_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player1 INTEGER,
            player2 INTEGER,
            player1_hp INTEGER,
            player2_hp INTEGER,
            player1_mana INTEGER,
            player2_mana INTEGER,
            turn INTEGER,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            user_id INTEGER,
            friend_id INTEGER,
            status TEXT DEFAULT 'pending',
            PRIMARY KEY (user_id, friend_id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ---------- СТОРОНЫ ----------
FACTIONS = {
    'humans': {
        'name': '👼 Люди',
        'hp_bonus': 10,
        'humanity_bonus': 20,
        'desc': 'Защитники человечества, светлые воины'
    },
    'demons': {
        'name': '👹 Демоны',
        'hp_bonus': 20,
        'humanity_bonus': -20,
        'desc': 'Слуги тьмы, сильные и жестокие'
    },
    'revenge': {
        'name': '🖤 Месть',
        'hp_bonus': 15,
        'humanity_bonus': 0,
        'desc': 'Одиночки, идущие по трупам'
    }
}

# ---------- СПУТНИКИ ----------
COMPANIONS = {
    'Волк': {'bonus': 'damage', 'value': 3, 'desc': '+3 к урону'},
    'Тень': {'bonus': 'dodge', 'value': 10, 'desc': '+10% к уклонению'},
    'Дух': {'bonus': 'heal', 'value': 5, 'desc': '+5 HP после каждого боя'}
}

# ---------- КВЕСТЫ ----------
QUESTS = [
    {'name': 'Охотник', 'desc': 'Убить 5 демонов', 'target': 5, 'type': 'kill', 'reward': 100},
    {'name': 'Транжира', 'desc': 'Потратить 200 золота', 'target': 200, 'type': 'spend', 'reward': 50},
    {'name': 'Выживальщик', 'desc': 'Выжить в 5 боях', 'target': 5, 'type': 'survive', 'reward': 150},
    {'name': 'Романтик', 'desc': 'Провести время с Лилит', 'target': 1, 'type': 'lilit', 'reward': 200}
]

# ---------- ДОСТИЖЕНИЯ ----------
ACHIEVEMENTS = {
    'first_kill': {'name': '🔪 Первая кровь', 'desc': 'Убить первого демона', 'reward': 50},
    'butcher': {'name': '🩸 Мясник', 'desc': 'Убить 50 демонов', 'reward': 500},
    'rich': {'name': '💰 Жирный кот', 'desc': 'Накопить 1000 золота', 'reward': 200},
    'lover': {'name': '💕 Сердцеед', 'desc': 'Завоевать Лилит', 'reward': 300}
}

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

def is_admin(user_id):
    return user_id == ADMIN_ID

# ---------- КНОПКИ ----------
def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("⚔️ В бой"),
        KeyboardButton("💊 Лечение"),
        KeyboardButton("📜 Профиль"),
        KeyboardButton("💕 Лилит"),
        KeyboardButton("🌑 Выбор стороны"),
        KeyboardButton("📖 Лор"),
        KeyboardButton("🏪 Магазин"),
        KeyboardButton("🎒 Инвентарь"),
        KeyboardButton("📅 Квесты"),
        KeyboardButton("🏆 Достижения"),
        KeyboardButton("⚡ PvP"),
        KeyboardButton("👥 Друзья"),
        KeyboardButton("🐺 Спутник")
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
            (user_id, username, hp, max_hp, mana, max_mana, gold, humanity, lilit_chapter) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (uid, message.from_user.username, 30, 30, 15, 15, 100, 50, 1))
        conn.commit()
        
        welcome = """
🕯️ *Кровавый рассвет*

Ты открываешь глаза. Пепел. Тишина. Пустота.
Твоя деревня сожжена. Ты ничего не помнишь.

Голос внутри: *«Иди. Найди. Убей.»*

/profile — узнать, сколько в тебе человеческого
/fight — сразиться с демонами
/lilit — встретить ту, что изменит всё
/choice — выбрать сторону
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
        faction_name = FACTIONS.get(user[2], {}).get('name', '❌ Не выбрана')
        companion = user[13] if user[13] else '❌ Нет'
        text = (f"📜 *Профиль*\n"
                f"👤 @{user[1]}\n"
                f"⚔️ Сторона: {faction_name}\n"
                f"❤️ HP: {user[6]}/{user[7]}\n"
                f"💰 Золото: {user[10]}\n"
                f"🧠 Человечность: {user[11]}\n"
                f"💕 Лилит: {user[12]} (глава {user[13]})\n"
                f"🐺 Спутник: {companion}\n"
                f"⚡ PvP рейтинг: {user[20]}")
    else:
        text = "Сначала /start"
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- БОЙ ----------
@bot.message_handler(func=lambda message: message.text == "⚔️ В бой")
def fight_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    monsters = ["Гниющий", "Крикун", "Тень", "Пожиратель"]
    monster = random.choice(monsters)
    gold = random.randint(5, 15)
    humanity_change = random.randint(-3, -1)
    
    # Учёт спутника
    companion_bonus = 0
    if user[14] == 'Волк':
        companion_bonus = 3
    elif user[14] == 'Дух':
        humanity_change += 1
    
    new_humanity = user[11] + humanity_change
    if new_humanity < 0:
        new_humanity = 0
    if new_humanity > 100:
        new_humanity = 100
    
    update_user(uid, gold=user[10] + gold + companion_bonus, 
                humanity=new_humanity, wins=user[17] + 1,
                demon_kills=user[19] + 1)
    
    text = (f"⚔️ Ты сразился с {monster} и победил!\n"
            f"💰 +{gold + companion_bonus} золота\n"
            f"🧠 Человечность {humanity_change:+d}")
    
    if companion_bonus:
        text += f"\n🐺 Спутник помог: +{companion_bonus}💰"
    
    bot.reply_to(message, text)

# ---------- ЛЕЧЕНИЕ ----------
@bot.message_handler(func=lambda message: message.text == "💊 Лечение")
def heal_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if user and user[6] < user[7] and user[10] >= 10:
        update_user(uid, hp=user[7], gold=user[10] - 10)
        bot.reply_to(message, "💊 Ты восстановил HP за 10💰")
    else:
        bot.reply_to(message, "❌ Недостаточно золота или HP полное")

# ---------- ЛОР ----------
@bot.message_handler(func=lambda message: message.text == "📖 Лор")
def lore_cmd(message):
    lore = """
🕯️ *Кровавый рассвет*

Ты был воином. Ты сражался 1000 лет.
Ты видел, как твой полк сожрали Тени.
Ты предал. Ты выжил. Ты сгнил заживо.

Теперь ты в Подземелье, где нет выхода.
Где смерть — не конец, а только начало.

И там, среди тьмы, ты встретил ЕЁ.
Лилит. Демонесса с глазами, в которых можно утонуть.
    """
    bot.reply_to(message, lore, parse_mode='Markdown')

# ---------- ВЫБОР СТОРОНЫ ----------
@bot.message_handler(func=lambda message: message.text == "🌑 Выбор стороны")
def choice_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user[2] != 'none':
        faction_name = FACTIONS.get(user[2], {}).get('name', '')
        bot.reply_to(message, f"❌ Ты уже выбрал сторону: {faction_name}")
        return
    
    text = "🌑 *Выбери свою сторону:*\n\n"
    markup = InlineKeyboardMarkup(row_width=2)
    
    for f_id, f_data in FACTIONS.items():
        text += f"{f_data['name']} — {f_data['desc']}\n"
        markup.add(InlineKeyboardButton(f_data['name'], callback_data=f"faction_{f_id}"))
    
    bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("faction_"))
def faction_callback(call):
    uid = call.from_user.id
    faction = call.data.replace("faction_", "")
    f_data = FACTIONS[faction]
    
    user = get_user(uid)
    
    new_hp = user[6] + f_data['hp_bonus']
    new_max_hp = user[7] + f_data['hp_bonus']
    new_humanity = user[11] + f_data['humanity_bonus']
    
    update_user(uid, faction=faction, hp=new_hp, max_hp=new_max_hp, humanity=new_humanity)
    
    bot.edit_message_text(f"✅ Ты выбрал сторону: {f_data['name']}", uid, call.message.message_id)

# ---------- ЛИЛИТ ----------
@bot.message_handler(func=lambda message: message.text == "💕 Лилит")
def lilit_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    chapter = user[13]
    points = user[12]
    
    if chapter == 1:
        text = """
🌑 *Глава 1: Встреча*

Ты входишь в руины старого храма. Воздух спёртый, пахнет кровью и розами.

В центре зала стоит ОНА. Чёрное платье, белая кожа, красные глаза.
«Ты... не такой, как другие. Меня зовут Лилит. Я ждала тебя.»

Она касается твоей щеки. Её пальцы холодны, но по тебе идёт жар.
        """
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💫 Вернуться", callback_data="lilit_next"))
        bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)
    
    elif chapter == 2:
        text = """
💕 *Глава 2: Поцелуй*

«Ты стал чаще заглядывать. Я тебе нравлюсь?»

Она берёт твоё лицо в ладони. Её губы касаются твоих.
Холодные. Мягкие. Правильные.

«Теперь ты мой. Хочешь ты этого или нет.»
        """
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💋 Поцеловать", callback_data="lilit_next"))
        bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)
    
    elif chapter == 3:
        text = """
🔥 *Глава 3: Ночь*

Она ведёт тебя вглубь храма. Там, где только тьма и она.
«Ложись.»

Её тело наклоняется к тебе. Кожа к коже. Холод к теплу.
«Я покажу тебе ад... но ты попросишь добавки.»

Ночь длится вечность.
        """
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("❤️ Остаться", callback_data="lilit_next"))
        bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)
    
    elif chapter == 4:
        text = """
💔 *Глава 4: Выбор*

«Ты должен выбрать. Люди или демоны. Я или твоя месть.»

Её глаза блестят. Впервые ты видишь в них боль.
«Я люблю тебя, смертный. Выбирай.»
        """
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👼 Люди", callback_data="lilit_human"),
            InlineKeyboardButton("👹 Демоны", callback_data="lilit_demon"),
            InlineKeyboardButton("🖤 Месть", callback_data="lilit_revenge")
        )
        bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)
    
    elif chapter >= 5:
        endings = {
            5: "👼 Ты остался человеком. Лилит исчезла, но иногда ты слышишь её шёпот.",
            6: "👹 Ты стал демоном. Вы с Лилит вместе. Навсегда.",
            7: "🖤 Ты выбрал месть. Ты один. Но она гордится тобой.",
            8: "❤️ Вы примирили людей и демонов. Ты и Лилит — легенда."
        }
        bot.send_message(uid, endings.get(chapter, "💕 История завершена."))

@bot.callback_query_handler(func=lambda call: call.data == "lilit_next")
def lilit_next_callback(call):
    uid = call.from_user.id
    user = get_user(uid)
    new_chapter = user[13] + 1
    new_points = user[12] + 10
    update_user(uid, lilit_chapter=new_chapter, lilit_points=new_points)
    bot.edit_message_text("💕 Ты сделал шаг навстречу тьме...", uid, call.message.message_id)
    lilit_cmd(call.message)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lilit_"))
def lilit_choice_callback(call):
    uid = call.from_user.id
    choice = call.data.replace("lilit_", "")
    
    endings = {
        "human": 5,
        "demon": 6,
        "revenge": 7
    }
    
    if choice in endings:
        update_user(uid, lilit_chapter=endings[choice], faction=choice + 's')
        
        # Секретная концовка
        user = get_user(uid)
        if user[11] >= 80 and user[12] >= 100:
            update_user(uid, lilit_chapter=8)
    
    bot.edit_message_text("💕 Твой выбор сделан...", uid, call.message.message_id)
    lilit_cmd(call.message)

# ---------- МАГАЗИН ----------
@bot.message_handler(func=lambda message: message.text == "🏪 Магазин")
def shop_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💊 Зелье HP (20💰)", callback_data="buy_potion"),
        InlineKeyboardButton("💕 Подарок Лилит (50💰)", callback_data="buy_gift"),
        InlineKeyboardButton("🐺 Спутник Волк (100💰)", callback_data="buy_wolf"),
        InlineKeyboardButton("🌑 Спутник Тень (150💰)", callback_data="buy_shadow"),
        InlineKeyboardButton("👻 Спутник Дух (200💰)", callback_data="buy_spirit")
    )
    
    bot.send_message(uid, f"🏪 *Магазин*\n💰 Твоё золото: {user[10]}", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_potion")
def buy_potion(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[10] >= 20:
        update_user(uid, gold=user[10] - 20)
        add_item(uid, "Зелье HP")
        bot.answer_callback_query(call.id, "💊 Зелье куплено!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота")

@bot.callback_query_handler(func=lambda call: call.data == "buy_gift")
def buy_gift(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[10] >= 50:
        update_user(uid, gold=user[10] - 50, lilit_points=user[12] + 10)
        bot.answer_callback_query(call.id, "💕 Лилит будет рада!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота")

@bot.callback_query_handler(func=lambda call: call.data == "buy_wolf")
def buy_wolf(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[10] >= 100:
        update_user(uid, gold=user[10] - 100, companion='Волк')
        bot.answer_callback_query(call.id, "🐺 Волк теперь с тобой!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота")

@bot.callback_query_handler(func=lambda call: call.data == "buy_shadow")
def buy_shadow(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[10] >= 150:
        update_user(uid, gold=user[10] - 150, companion='Тень')
        bot.answer_callback_query(call.id, "🌑 Тень теперь с тобой!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота")

@bot.callback_query_handler(func=lambda call: call.data == "buy_spirit")
def buy_spirit(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[10] >= 200:
        update_user(uid, gold=user[10] - 200, companion='Дух')
        bot.answer_callback_query(call.id, "👻 Дух теперь с тобой!")
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

# ---------- КВЕСТЫ ----------
@bot.message_handler(func=lambda message: message.text == "📅 Квесты")
def daily_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    today = datetime.now().strftime("%Y-%m-%d")
    if user[15] == today:
        bot.reply_to(message, "❌ Квесты уже взяты. Приходи завтра.")
        return
    
    quest = random.choice(QUESTS)
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Принять", callback_data=f"quest_{quest['type']}_{quest['target']}_{quest['reward']}"))
    
    bot.send_message(uid, f"📅 *Квест*\n{quest['name']}: {quest['desc']}\nНаграда: {quest['reward']}💰", 
                    parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('quest_'))
def quest_callback(call):
    uid = call.from_user.id
    data = call.data.split('_')
    qtype = data[1]
    target = int(data[2])
    reward = int(data[3])
    
    update_user(uid, last_daily=datetime.now().strftime("%Y-%m-%d"), gold=get_user(uid)[10] + reward)
    bot.edit_message_text(f"✅ Квест принят! +{reward}💰", uid, call.message.message_id)

# ---------- ДОСТИЖЕНИЯ ----------
@bot.message_handler(func=lambda message: message.text == "🏆 Достижения")
def achievements_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT ach_id FROM achievements WHERE user_id=?", (uid,))
    achieved = [a[0] for a in cur.fetchall()]
    conn.close()
    
    # Проверка достижений
    if user[19] >= 1 and 'first_kill' not in achieved:
        add_item(uid, 'first_kill')
        update_user(uid, gold=user[10] + 50)
        bot.send_message(uid, "🏆 Достижение: 🔪 Первая кровь! +50💰")
    
    if user[19] >= 50 and 'butcher' not in achieved:
        add_item(uid, 'butcher')
        update_user(uid, gold=user[10] + 500)
        bot.send_message(uid, "🏆 Достижение: 🩸 Мясник! +500💰")
    
    if user[12] >= 100 and 'lover' not in achieved:
        add_item(uid, 'lover')
        update_user(uid, gold=user[10] + 300)
        bot.send_message(uid, "🏆 Достижение: 💕 Сердцеед! +300💰")
    
    text = "🏆 *Достижения*\n"
    for ach_id, ach in ACHIEVEMENTS.items():
        status = "✅" if ach_id in achieved else "❌"
        text += f"\n{status} *{ach['name']}* — {ach['desc']}\n   Награда: {ach['reward']}💰"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- PVP ----------
@bot.message_handler(func=lambda message: message.text == "⚡ PvP")
def pvp_menu(message):
    uid = message.from_user.id
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⏳ Очередь", callback_data="pvp_queue"),
        InlineKeyboardButton("📊 Топ", callback_data="pvp_top")
    )
    
    bot.send_message(uid, "⚡ *PvP режим*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pvp_top")
def pvp_top(call):
    uid = call.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT username, pvp_rating FROM users ORDER BY pvp_rating DESC LIMIT 10")
    top = cur.fetchall()
    conn.close()
    
    text = "📊 *Топ PvP*\n"
    for i, (name, rating) in enumerate(top, 1):
        text += f"\n{i}. @{name} — {rating}"
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "pvp_queue")
def pvp_queue(call):
    uid = call.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM pvp_queue WHERE user_id=?", (uid,))
    
    if cur.fetchone():
        bot.answer_callback_query(call.id, "❌ Ты уже в очереди")
    else:
        cur.execute("INSERT INTO pvp_queue (user_id, timestamp) VALUES (?, ?)", (uid, int(time.time())))
        conn.commit()
        bot.answer_callback_query(call.id, "⏳ Ты в очереди")
    
    conn.close()

# ---------- ДРУЗЬЯ ----------
@bot.message_handler(func=lambda message: message.text == "👥 Друзья")
def friends_cmd(message):
    uid = message.from_user.id
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("➕ Добавить", callback_data="friend_add"),
        InlineKeyboardButton("📋 Список", callback_data="friend_list")
    )
    
    bot.send_message(uid, "👥 *Друзья*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "friend_add")
def friend_add(call):
    uid = call.from_user.id
    bot.edit_message_text("🔍 Введи @username друга:", uid, call.message.message_id)
    bot.register_next_step_handler(call.message, add_friend)

def add_friend(message):
    uid = message.from_user.id
    target = message.text.strip().replace('@', '')
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE username=?", (target,))
    target_id = cur.fetchone()
    
    if not target_id:
        bot.reply_to(message, "❌ Пользователь не найден")
        conn.close()
        return
    
    target_id = target_id[0]
    
    cur.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, status) VALUES (?, ?, 'pending')", (uid, target_id))
    cur.execute("INSERT OR IGNORE INTO friends (user_id, friend_id, status) VALUES (?, ?, 'pending_received')", (target_id, uid))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Запрос отправлен @{target}")
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Принять", callback_data=f"friend_accept_{uid}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"friend_decline_{uid}")
    )
    bot.send_message(target_id, f"👥 @{message.from_user.username} хочет добавить тебя в друзья!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "friend_list")
def friend_list(call):
    uid = call.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT u.username FROM friends f
        JOIN users u ON f.friend_id = u.user_id
        WHERE f.user_id=? AND f.status='accepted'
    ''', (uid,))
    friends = cur.fetchall()
    conn.close()
    
    if not friends:
        bot.edit_message_text("👥 У тебя пока нет друзей.", uid, call.message.message_id)
        return
    
    text = "👥 *Твои друзья*\n"
    for (name,) in friends:
        text += f"\n• @{name}"
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('friend_accept_'))
def friend_accept(call):
    uid = call.from_user.id
    requester = int(call.data.replace('friend_accept_', ''))
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("UPDATE friends SET status='accepted' WHERE user_id=? AND friend_id=?", (uid, requester))
    cur.execute("UPDATE friends SET status='accepted' WHERE user_id=? AND friend_id=?", (requester, uid))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("✅ Ты принял запрос!", uid, call.message.message_id)
    bot.send_message(requester, f"✅ @{call.from_user.username} принял твой запрос!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('friend_decline_'))
def friend_decline(call):
    uid = call.from_user.id
    requester = int(call.data.replace('friend_decline_', ''))
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM friends WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)", 
                (uid, requester, requester, uid))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("❌ Запрос отклонён.", uid, call.message.message_id)

# ---------- СПУТНИК ----------
@bot.message_handler(func=lambda message: message.text == "🐺 Спутник")
def companion_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user[14]:
        comp = COMPANIONS.get(user[14], {})
        text = f"🐺 Твой спутник: *{user[14]}*\n{comp.get('desc', '')}"
    else:
        text = "🐺 У тебя нет спутника. Купи в магазине!"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- АДМИНКА ----------
@bot.message_handler(func=lambda message: message.text == "👑 Админ")
def admin_cmd(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
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
    cur.execute("SELECT AVG(lilit_points) FROM users")
    lilit_avg = cur.fetchone()[0] or 0
    cur.execute("SELECT COUNT(*) FROM users WHERE companion != ''")
    companions = cur.fetchone()[0]
    conn.close()
    
    text = (f"📊 *Статистика*\n👥 Игроков: {total}\n💰 Всего золота: {gold}\n"
            f"💕 Средние отношения: {lilit_avg:.1f}\n"
            f"🐺 Со спутниками: {companions}")
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
        update_user(target_id, gold=user[10] + amount)
        bot.reply_to(message, f"✅ Начислено {amount}💰")
    else:
        bot.reply_to(message, "❌ Пользователь не найден")

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    while True:
        try:
            print("🖤 Без казино, со сторонами. Кровавый рассвет продолжается.")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"💀 Ошибка: {e}. Перезапуск...")
            time.sleep(5)
