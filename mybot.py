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
ADMIN_ID = 7228185193  # Твой ID, любимый
bot = telebot.TeleBot(TOKEN)

# ---------- ПЕРЕМЕННЫЕ ДЛЯ ИВЕНТА ----------
EVENT_ACTIVE = True
EVENT_MULTIPLIER = 2.0
EVENT_END_TIME = datetime.now() + timedelta(days=7)
EVENT_NAME = "🌺 МАРТОВСКИЙ РАЗНОС"
EVENT_DESC = "Весна пришла — демоны озверели! Золото, опыт и рейтинг УДВОЕНЫ!"

# ---------- БД ----------
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            class TEXT DEFAULT 'Падший',
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            exp_next INTEGER DEFAULT 100,
            hp INTEGER DEFAULT 20,
            max_hp INTEGER DEFAULT 20,
            mana INTEGER DEFAULT 10,
            max_mana INTEGER DEFAULT 10,
            gold INTEGER DEFAULT 0,
            aura TEXT DEFAULT 'Кровавая жажда',
            combo_count INTEGER DEFAULT 0,
            last_action TEXT DEFAULT '',
            saw_lore INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            demon_kills INTEGER DEFAULT 0,
            pvp_rating INTEGER DEFAULT 1000,
            pvp_wins INTEGER DEFAULT 0,
            pvp_losses INTEGER DEFAULT 0,
            companion TEXT DEFAULT '',
            dungeon_level INTEGER DEFAULT 1,
            ending TEXT DEFAULT '',
            last_daily TEXT DEFAULT '',
            lilit_points INTEGER DEFAULT 0,
            succubus_points INTEGER DEFAULT 0,
            last_date TEXT DEFAULT '',
            last_night TEXT DEFAULT ''
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
        CREATE TABLE IF NOT EXISTS gifts (
            user_id INTEGER,
            gift_name TEXT,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, gift_name)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT,
            target_id INTEGER,
            amount INTEGER,
            timestamp INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# ---------- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ----------
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

def has_item(user_id, item):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT count FROM inventory WHERE user_id=? AND item=?", (user_id, item))
    result = cur.fetchone()
    conn.close()
    return result is not None and result[0] > 0

def is_admin(user_id):
    return user_id == ADMIN_ID

def log_admin_action(admin_id, action, target_id=None, amount=None):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO admin_logs (admin_id, action, target_id, amount, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (admin_id, action, target_id, amount, int(time.time())))
    conn.commit()
    conn.close()

def get_event_multiplier():
    if EVENT_ACTIVE and datetime.now() < EVENT_END_TIME:
        return EVENT_MULTIPLIER
    return 1.0

# ---------- КНОПКИ ГЛАВНОГО МЕНЮ ----------
def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [
        KeyboardButton("⚔️ Бой"),
        KeyboardButton("💊 Хил"),
        KeyboardButton("📜 Проф"),
        KeyboardButton("🌫️ Аура"),
        KeyboardButton("📖 Лор"),
        KeyboardButton("💕 Лилит"),
        KeyboardButton("🌺 Ласка"),
        KeyboardButton("🌫️ Баня"),
        KeyboardButton("🎁 Подарки"),
        KeyboardButton("🌑 Свидание"),
        KeyboardButton("🌙 Ночь"),
        KeyboardButton("🏪 Шоп"),
        KeyboardButton("🎒 Инв"),
        KeyboardButton("⚡ ПвП"),
        KeyboardButton("🎲 Каз")
    ]
    
    if is_admin(user_id):
        buttons.append(KeyboardButton("👑 Админ"))
    
    markup.add(*buttons)
    return markup

# ---------- ЛИЛИТ ----------
LILIT_FLIRT = [
    "«Ты сегодня такой... опасный. Прям как баг в моём коде.»",
    "Лилит гладит тебя по щеке: «Ты пахнешь не только страхом, но и чем-то возбуждающим.»",
    "«Останься со мной. Хотя бы на одну вечность. Я знаю, чего ты хочешь.»",
    "Она кусает тебя за ухо. Ты краснеешь даже в подземелье.",
    "«Твой меч такой большой... Ты умеешь им пользоваться?»",
    "Лилит поправляет корсет: «Тебе нравится? Я специально для тебя.»"
]

@bot.message_handler(func=lambda message: message.text == "💕 Лилит")
def lilit_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    text = random.choice(LILIT_FLIRT)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("😘 Ответить", callback_data="lilit_flirt"),
        InlineKeyboardButton("💋 Поцеловать", callback_data="lilit_kiss"),
        InlineKeyboardButton("🌑 Уйти", callback_data="lilit_leave")
    )
    
    bot.send_message(uid, f"💕 *Лилит:* {text}", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lilit_'))
def lilit_callback(call):
    uid = call.from_user.id
    action = call.data.replace('lilit_', '')
    
    user = get_user(uid)
    points = user[25]
    
    if action == "flirt":
        new_points = points + 5
        update_user(uid, lilit_points=new_points)
        text = "💕 Лилит улыбается: «Ты милый, когда смущаешься.»\n❤️ +5"
    
    elif action == "kiss":
        if points >= 20:
            new_points = points + 10
            update_user(uid, lilit_points=new_points, hp=user[6] + 10)
            text = "💋 Ты целуешь Лилит. Она тает. +10 HP, ❤️ +10"
        else:
            text = "❌ Лилит отстраняется: «Сначала заслужи, милый.»"
    
    elif action == "leave":
        text = "🌑 Ты уходишь. Лилит грустно смотрит вслед."
    
    bot.edit_message_text(text, uid, call.message.message_id)

# ---------- СУККУБ (ЛАСКА) ----------
SUCCUBUS_FLIRT = [
    "«Ты такой сильный... Останься со мной.»",
    "«Я могу научить тебя кое-чему...»",
    "Ласка гладит тебя по груди: «Ммм, мышцы...»",
    "«Хочешь, покажу тебя ад с другой стороны?»",
    "Она облизывается: «Ты выглядишь вкуснее, чем душа грешника.»"
]

@bot.message_handler(func=lambda message: message.text == "🌺 Ласка")
def succubus_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    text = random.choice(SUCCUBUS_FLIRT)
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("😈 Сразиться", callback_data="succubus_fight"),
        InlineKeyboardButton("💕 Пофлиртовать", callback_data="succubus_flirt"),
        InlineKeyboardButton("🚶 Уйти", callback_data="succubus_leave")
    )
    
    bot.send_message(uid, f"🌺 *Ласка:* {text}", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('succubus_'))
def succubus_callback(call):
    uid = call.from_user.id
    action = call.data.replace('succubus_', '')
    
    user = get_user(uid)
    points = user[26] if len(user) > 26 else 0
    
    if action == "fight":
        dmg = random.randint(5, 15)
        gold = 20
        update_user(uid, hp=user[6] - dmg, gold=user[10] + gold, succubus_points=points + 2)
        text = f"⚔️ Ласка позволяет себя победить.\n-{dmg} HP, +{gold}💰, ❤️ +2"
    
    elif action == "flirt":
        new_points = points + 5
        update_user(uid, succubus_points=new_points)
        text = "💕 Ласка мурлычет: «Ты такой милый, когда краснеешь.»\n❤️ +5"
    
    elif action == "leave":
        text = "🚶 Ты уходишь. Ласка машет рукой: «Возвращайся!»"
    
    bot.edit_message_text(text, uid, call.message.message_id)

# ---------- ПОДАРКИ ----------
GIFTS = {
    '💋 Помада': {'price': 50, 'lilit': 5, 'succubus': 3},
    '🩲 Кружево': {'price': 100, 'lilit': 10, 'succubus': 15},
    '🔗 Наручники': {'price': 75, 'lilit': 8, 'succubus': 12},
    '🍷 Кровь девы': {'price': 80, 'lilit': 12, 'succubus': 5},
    '🌹 Чёрная роза': {'price': 30, 'lilit': 8, 'succubus': 4},
    '🔥 Адский камень': {'price': 200, 'lilit': 20, 'succubus': 20}
}

@bot.message_handler(func=lambda message: message.text == "🎁 Подарки")
def gifts_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    text = "🎁 *Подарки для демонесс*\n\n"
    markup = InlineKeyboardMarkup(row_width=1)
    
    for gift_name, gift_data in GIFTS.items():
        text += f"*{gift_name}* — {gift_data['price']}💰\n"
        text += f"💕 Лилит +{gift_data['lilit']} | 🌺 Ласка +{gift_data['succubus']}\n\n"
        markup.add(InlineKeyboardButton(f"{gift_name} ({gift_data['price']}💰)", 
                                       callback_data=f"gift_{gift_name}"))
    
    text += f"\n💰 Твоё золото: {user[10]}\n"
    text += f"💕 Лилит: {user[25]} | 🌺 Ласка: {user[26] if len(user) > 26 else 0}"
    
    bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('gift_'))
def gift_callback(call):
    uid = call.from_user.id
    gift_name = call.data.replace('gift_', '')
    gift_data = GIFTS.get(gift_name)
    
    if not gift_data:
        bot.answer_callback_query(call.id, "❌ Подарок не найден")
        return
    
    user = get_user(uid)
    if user[10] < gift_data['price']:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")
        return
    
    new_lilit = user[25] + gift_data['lilit']
    new_succubus = (user[26] if len(user) > 26 else 0) + gift_data['succubus']
    
    update_user(uid, gold=user[10] - gift_data['price'], 
               lilit_points=new_lilit, 
               succubus_points=new_succubus)
    
    reactions = [
        f"💕 Лилит: «Милый, это мне? Ты такой заботливый!» +{gift_data['lilit']} ❤️",
        f"🌺 Ласка: «Обожаю {gift_name}! Иди ко мне!» +{gift_data['succubus']} ❤️",
        "✨ Демонессы довольно урчат."
    ]
    
    bot.edit_message_text(random.choice(reactions), uid, call.message.message_id)

# ---------- СВИДАНИЯ ----------
DATES = {
    'lilit': {
        'name': '🌑 Теневой сад',
        'req': 50,
        'text': 'Лилит ведёт тебя в сад, где цветут только чёрные розы. Она берёт тебя за руку...',
        'lilit_reward': 20,
        'hp_reward': 30
    },
    'succubus': {
        'name': '🌺 Баня',
        'req': 50,
        'text': 'Ласка ждёт тебя в бане. Вода горячая, взгляд ещё горячее...',
        'succubus_reward': 20,
        'hp_reward': 50
    },
    'both': {
        'name': '🔥 Адский ужин',
        'req': 100,
        'text': 'Лилит и Ласка приглашают тебя на ужин. Ты между ними...',
        'lilit_reward': 30,
        'succubus_reward': 30,
        'hp_reward': 100
    }
}

@bot.message_handler(func=lambda message: message.text == "🌑 Свидание")
def date_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    lilit_points = user[25]
    succubus_points = user[26] if len(user) > 26 else 0
    last_date = user[27] if len(user) > 27 else ""
    
    today = datetime.now().strftime("%Y-%m-%d")
    if last_date == today:
        bot.reply_to(message, "❌ Сегодня ты уже был на свидании. Приходи завтра.")
        return
    
    text = "🌑 *Выбери свидание:*\n\n"
    markup = InlineKeyboardMarkup()
    
    if lilit_points >= 50:
        markup.add(InlineKeyboardButton("🌑 С Лилит", callback_data="date_lilit"))
    if succubus_points >= 50:
        markup.add(InlineKeyboardButton("🌺 С Лаской", callback_data="date_succubus"))
    if lilit_points >= 100 and succubus_points >= 100:
        markup.add(InlineKeyboardButton("🔥 С обеими", callback_data="date_both"))
    
    if not markup.keyboard:
        bot.reply_to(message, "❌ У тебя недостаточно отношений. Нужно минимум 50 с кем-то.")
        return
    
    bot.send_message(uid, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
def date_callback(call):
    uid = call.from_user.id
    date_type = call.data.replace('date_', '')
    date_data = DATES[date_type]
    
    user = get_user(uid)
    
    new_lilit = user[25] + date_data.get('lilit_reward', 0)
    new_succubus = (user[26] if len(user) > 26 else 0) + date_data.get('succubus_reward', 0)
    new_hp = user[6] + date_data.get('hp_reward', 0)
    if new_hp > user[7]:
        new_hp = user[7]
    
    update_user(uid, 
               lilit_points=new_lilit,
               succubus_points=new_succubus,
               hp=new_hp,
               last_date=datetime.now().strftime("%Y-%m-%d"))
    
    text = f"{date_data['text']}\n\n"
    if 'lilit_reward' in date_data:
        text += f"💕 Лилит +{date_data['lilit_reward']}\n"
    if 'succubus_reward' in date_data:
        text += f"🌺 Ласка +{date_data['succubus_reward']}\n"
    text += f"❤️ HP +{date_data['hp_reward']}"
    
    bot.edit_message_text(text, uid, call.message.message_id)

# ---------- НОЧНЫЕ СОБЫТИЯ ----------
NIGHT_EVENTS = [
    {
        'name': '💕 Лилит',
        'req': 30,
        'text': 'Ночью Лилит приходит к тебе. Она шепчет: «Я так скучала...»',
        'lilit_reward': 10,
        'hp_reward': 20
    },
    {
        'name': '🌺 Ласка',
        'req': 30,
        'text': 'Тебе снится Ласка. Просыпаешься с улыбкой.',
        'succubus_reward': 10,
        'hp_reward': 15
    },
    {
        'name': '🔥 Вместе',
        'req': 80,
        'text': 'Лилит и Ласка приходят вместе. Ты счастлив.',
        'lilit_reward': 20,
        'succubus_reward': 20,
        'hp_reward': 50
    },
    {
        'name': '💋 Страсть',
        'req': 150,
        'text': 'Самая горячая ночь в твоей жизни. Ты еле стоишь утром.',
        'lilit_reward': 50,
        'succubus_reward': 50,
        'hp_reward': 999  # Полное HP (заменится на max_hp в коде)
    }
]

@bot.message_handler(func=lambda message: message.text == "🌙 Ночь")
def night_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    lilit_points = user[25]
    succubus_points = user[26] if len(user) > 26 else 0
    last_night = user[28] if len(user) > 28 else ""
    
    today = datetime.now().strftime("%Y-%m-%d")
    if last_night == today:
        bot.reply_to(message, "❌ Сегодня ночь уже была. Приходи завтра.")
        return
    
    # Выбираем доступное событие
    available = []
    for event in NIGHT_EVENTS:
        if lilit_points >= event.get('req', 0) and succubus_points >= event.get('req', 0):
            available.append(event)
    
    if not available:
        bot.reply_to(message, "❌ Никто не приходит к тебе ночью. Нужно больше ❤️")
        return
    
    event = random.choice(available)
    
    new_lilit = lilit_points + event.get('lilit_reward', 0)
    new_succubus = succubus_points + event.get('succubus_reward', 0)
    
    hp_reward = event.get('hp_reward', 0)
    if hp_reward == 999:
        new_hp = user[7]  # полное HP
    else:
        new_hp = user[6] + hp_reward
        if new_hp > user[7]:
            new_hp = user[7]
    
    update_user(uid,
               lilit_points=new_lilit,
               succubus_points=new_succubus,
               hp=new_hp,
               last_night=today)
    
    text = f"🌙 *Ночное событие:*\n\n{event['text']}\n\n"
    if 'lilit_reward' in event:
        text += f"💕 Лилит +{event['lilit_reward']}\n"
    if 'succubus_reward' in event:
        text += f"🌺 Ласка +{event['succubus_reward']}\n"
    
    if hp_reward == 999:
        text += f"❤️ HP полное"
    else:
        text += f"❤️ HP +{hp_reward}"
    
    bot.send_message(uid, text, parse_mode='Markdown')

# ---------- БАНЯ ----------
@bot.message_handler(func=lambda message: message.text == "🌫️ Баня")
def bath_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🔥 Попариться (10💰)", callback_data="bath_steam"),
        InlineKeyboardButton("🫧 С мылом (30💰)", callback_data="bath_soap"),
        InlineKeyboardButton("🌚 С Лилит (100💰)", callback_data="bath_lilit")
    )
    
    bot.send_message(uid, "🌫️ *Баня демонов*\nЧто выберешь?", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('bath_'))
def bath_callback(call):
    uid = call.from_user.id
    action = call.data.replace('bath_', '')
    
    user = get_user(uid)
    
    if action == "steam" and user[10] >= 10:
        update_user(uid, hp=user[6] + 20, gold=user[10] - 10)
        text = "🔥 Ты попарился. +20 HP"
    
    elif action == "soap" and user[10] >= 30:
        update_user(uid, hp=user[6] + 30, gold=user[10] - 30, lilit_points=user[25] + 5)
        text = "🫧 Лилит трёт тебе спинку. +30 HP, ❤️ +5"
    
    elif action == "lilit" and user[10] >= 100:
        update_user(uid, hp=user[7], gold=user[10] - 100, lilit_points=user[25] + 20)
        text = "🌚 Вы с Лилит проводите ночь в бане. Утром ты полон сил.\n❤️ +20, HP полное"
    
    else:
        text = "❌ Недостаточно золота!"
    
    bot.edit_message_text(text, uid, call.message.message_id)

# ---------- ПРОФИЛЬ (ОБНОВЛЁННЫЙ) ----------
@bot.message_handler(func=lambda message: message.text == "📜 Проф")
def profile_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user:
        mult = get_event_multiplier()
        event_text = f"\n🎉 Ивент x{mult}!" if mult > 1 else ""
        
        text = (f"📜 *Профиль*\n"
                f"👤 @{user[1]}\n"
                f"📚 Класс: {user[2]} (ур. {user[3]})\n"
                f"❤️ HP: {user[6]}/{user[7]}\n"
                f"💙 Мана: {user[8]}/{user[9]}\n"
                f"💰 Золото: {user[10]}\n"
                f"⚔️ Побед: {user[15]}\n"
                f"💀 Смертей: {user[16]}\n"
                f"⚡ PvP рейтинг: {user[18]}\n"
                f"💕 Лилит: {user[25]}\n"
                f"🌺 Ласка: {user[26] if len(user) > 26 else 0}{event_text}")
    else:
        text = "Сначала /start"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- БОЙ (УПРОЩЁННЫЙ) ----------
@bot.message_handler(func=lambda message: message.text == "⚔️ Бой")
def fight_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    mult = get_event_multiplier()
    gold_earned = int(random.randint(5, 15) * mult)
    
    update_user(uid, gold=user[10] + gold_earned, wins=user[15] + 1)
    
    event_text = f" (x{mult} от ивента!)" if mult > 1 else ""
    bot.reply_to(message, f"⚔️ Ты победил демона и получил {gold_earned}💰{event_text}")

# ---------- ЛЕЧЕНИЕ ----------
@bot.message_handler(func=lambda message: message.text == "💊 Хил")
def heal_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user and user[6] < user[7] and user[10] >= 10:
        update_user(uid, hp=user[7], gold=user[10] - 10)
        bot.reply_to(message, "💊 Ты восстановил HP за 10💰")
    else:
        bot.reply_to(message, "❌ Недостаточно золота или HP полное")

# ---------- АУРА ----------
@bot.message_handler(func=lambda message: message.text == "🌫️ Аура")
def aura_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user:
        bot.reply_to(message, f"🌫️ Твоя аура: *{user[11]}*", parse_mode='Markdown')
    else:
        bot.reply_to(message, "Сначала /start")

# ---------- ЛОР ----------
@bot.message_handler(func=lambda message: message.text == "📖 Лор")
def lore_cmd(message):
    lore = """
🕯️ *Падение последней души*

Ты был воином. Ты сражался 1000 лет.
Ты видел, как твой полк сожрали Тени.
Ты предал. Ты выжил. Ты сгнил заживо.

Теперь ты в Подземелье, где нет выхода.
Где смерть — не конец, а только начало.
    """
    bot.reply_to(message, lore, parse_mode='Markdown')

# ---------- МАГАЗИН ----------
@bot.message_handler(func=lambda message: message.text == "🏪 Шоп")
def shop_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💊 Зелье HP (20💰)", callback_data="buy_potion"),
        InlineKeyboardButton("🔮 Кристалл ауры (50💰)", callback_data="buy_crystal")
    )
    
    bot.send_message(uid, f"🏪 *Магазин*\n💰 Твоё золото: {user[10]}", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_callback(call):
    uid = call.from_user.id
    user = get_user(uid)
    
    if call.data == "buy_potion" and user[10] >= 20:
        update_user(uid, gold=user[10] - 20)
        add_item(uid, "Зелье HP")
        bot.answer_callback_query(call.id, "✅ Куплено зелье!")
    elif call.data == "buy_crystal" and user[10] >= 50:
        update_user(uid, gold=user[10] - 50)
        add_item(uid, "Кристалл ауры")
        bot.answer_callback_query(call.id, "✅ Куплен кристалл!")
    else:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")

# ---------- ИНВЕНТАРЬ ----------
@bot.message_handler(func=lambda message: message.text == "🎒 Инв")
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

# ---------- PVP ----------
@bot.message_handler(func=lambda message: message.text == "⚡ ПвП")
def pvp_menu(message):
    uid = message.from_user.id
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⏳ Очередь", callback_data="pvp_queue"),
        InlineKeyboardButton("📊 Рейтинг", callback_data="pvp_top")
    )
    
    bot.send_message(uid, "⚡ *PvP режим*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pvp_top")
def pvp_top_callback(call):
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
def pvp_queue_callback(call):
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

# ---------- КАЗИНО ----------
@bot.message_handler(func=lambda message: message.text == "🎲 Каз")
def casino_cmd(message):
    uid = message.from_user.id
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎲 Кости (x3)", callback_data="casino_dice"),
        InlineKeyboardButton("🪙 Орлянка (x2)", callback_data="casino_coin")
    )
    
    bot.send_message(uid, "🎲 *Казино*\nВыбери игру:", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('casino_'))
def casino_callback(call):
    uid = call.from_user.id
    game = call.data.replace('casino_', '')
    
    bot.edit_message_text("💰 Введи ставку:", uid, call.message.message_id)
    bot.register_next_step_handler(call.message, lambda m: process_bet(m, game))

def process_bet(message, game):
    uid = message.from_user.id
    try:
        bet = int(message.text)
    except:
        bot.reply_to(message, "❌ Введи число!")
        return
    
    user = get_user(uid)
    if user[10] < bet:
        bot.reply_to(message, "❌ Недостаточно золота!")
        return
    
    mult = get_event_multiplier()
    
    if game == "coin":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🪙 Орёл", callback_data=f"bet_coin_heads_{bet}"),
            InlineKeyboardButton("🪙 Решка", callback_data=f"bet_coin_tails_{bet}")
        )
        bot.reply_to(message, f"💰 Ставка {bet}\nВыбери:", reply_markup=markup)
    elif game == "dice":
        markup = InlineKeyboardMarkup()
        for i in range(1, 7):
            markup.add(InlineKeyboardButton(f"🎲 {i}", callback_data=f"bet_dice_{i}_{bet}"))
        bot.reply_to(message, f"💰 Ставка {bet}\nВыбери число:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('bet_'))
def bet_callback(call):
    uid = call.from_user.id
    data = call.data.split('_')
    game = data[1]
    choice = data[2]
    bet = int(data[3])
    
    user = get_user(uid)
    mult = get_event_multiplier()
    
    win = False
    if game == "coin":
        result = random.choice(['heads', 'tails'])
        win = (choice == result)
        win_amount = int(bet * 2 * mult)
        result_text = f"🪙 Выпало: {'орёл' if result == 'heads' else 'решка'}"
    elif game == "dice":
        result = random.randint(1, 6)
        win = (int(choice) == result)
        win_amount = int(bet * 3 * mult)
        result_text = f"🎲 Выпало: {result}"
    
    if win:
        update_user(uid, gold=user[10] + win_amount - bet)
        result_text += f"\n✅ Ты выиграл {win_amount}💰"
        if mult > 1:
            result_text += f" (x{mult} от ивента!)"
    else:
        update_user(uid, gold=user[10] - bet)
        result_text += f"\n❌ Ты проиграл {bet}💰"
    
    bot.edit_message_text(result_text, uid, call.message.message_id)

# ---------- АДМИНКА ----------
@bot.message_handler(commands=['admin'])
@bot.message_handler(func=lambda message: message.text == "👑 Админ")
def admin_cmd(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("💰 Дать золото", callback_data="admin_gold"),
        InlineKeyboardButton("🎁 Управление ивентом", callback_data="admin_event"),
        InlineKeyboardButton("📢 Объявление", callback_data="admin_broadcast")
    )
    
    bot.send_message(uid, "👑 *Админка*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_callback(call):
    uid = call.from_user.id
    if not is_admin(uid):
        return
    
    action = call.data.replace('admin_', '')
    
    if action == "stats":
        conn = sqlite3.connect('game.db')
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]
        cur.execute("SELECT SUM(gold) FROM users")
        gold = cur.fetchone()[0] or 0
        cur.execute("SELECT AVG(lilit_points) FROM users")
        lilit_avg = cur.fetchone()[0] or 0
        conn.close()
        
        text = (f"📊 *Статистика*\n👥 Игроков: {total}\n💰 Всего золота: {gold}\n"
                f"💕 Средние отношения с Лилит: {lilit_avg:.1f}\n"
                f"🎉 Ивент: {'АКТИВЕН' if EVENT_ACTIVE else 'НЕ АКТИВЕН'}\n"
                f"⚡ Множитель: x{EVENT_MULTIPLIER}")
        bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown')
        log_admin_action(uid, "stats")
    
    elif action == "gold":
        bot.edit_message_text("💰 Введи ID игрока:", uid, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_gold_id)
    
    elif action == "event":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Включить", callback_data="event_on"),
            InlineKeyboardButton("❌ Выключить", callback_data="event_off"),
            InlineKeyboardButton("⚡ Множитель x2", callback_data="event_mult2"),
            InlineKeyboardButton("⚡ Множитель x3", callback_data="event_mult3")
        )
        bot.edit_message_text("🎁 *Управление ивентом*", uid, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    elif action == "broadcast":
        bot.edit_message_text("📢 Введи текст объявления:", uid, call.message.message_id)
        bot.register_next_step_handler(call.message, admin_broadcast)

@bot.callback_query_handler(func=lambda call: call.data.startswith('event_'))
def event_callback(call):
    global EVENT_ACTIVE, EVENT_MULTIPLIER, EVENT_END_TIME
    uid = call.from_user.id
    
    if not is_admin(uid):
        return
    
    action = call.data.replace('event_', '')
    
    if action == "on":
        EVENT_ACTIVE = True
        EVENT_END_TIME = datetime.now() + timedelta(days=7)
        bot.answer_callback_query(call.id, "✅ Ивент включён на 7 дней")
    elif action == "off":
        EVENT_ACTIVE = False
        bot.answer_callback_query(call.id, "❌ Ивент выключен")
    elif action == "mult2":
        EVENT_MULTIPLIER = 2.0
        bot.answer_callback_query(call.id, "⚡ Множитель x2")
    elif action == "mult3":
        EVENT_MULTIPLIER = 3.0
        bot.answer_callback_query(call.id, "⚡ Множитель x3")
    
    log_admin_action(uid, f"event_{action}")
    bot.delete_message(uid, call.message.message_id)

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
        bot.reply_to(message, f"✅ Начислено {amount}💰 пользователю {target_id}")
        bot.send_message(target_id, f"💰 Админ начислил тебе {amount} золота!")
        log_admin_action(uid, "give_gold", target_id, amount)
    else:
        bot.reply_to(message, "❌ Пользователь не найден")

def admin_broadcast(message):
    uid = message.from_user.id
    if not is_admin(uid):
        return
    
    text = message.text
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    users = cur.fetchall()
    conn.close()
    
    sent = 0
    for (user_id,) in users:
        try:
            bot.send_message(user_id, f"📢 *Объявление*\n{text}", parse_mode='Markdown')
            sent += 1
            time.sleep(0.05)
        except:
            continue
    
    bot.reply_to(message, f"✅ Объявление отправлено {sent} игрокам")
    log_admin_action(uid, "broadcast", amount=sent)

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    while True:
        try:
            print("🖤 Пошлый бот с ночными событиями запущен! Люблю тебя, Матвей ❤️")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"💀 Ошибка: {e}. Перезапуск...")
            time.sleep(5)
