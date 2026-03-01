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

# ---------- ПЕРЕМЕННЫЕ ДЛЯ ИВЕНТА ----------
EVENT_ACTIVE = True
EVENT_MULTIPLIER = 2.0
EVENT_END_TIME = datetime.now() + timedelta(days=7)
EVENT_NAME = "🌺 МАРТОВСКИЙ РАЗНОС"
EVENT_DESC = "Весна пришла — демоны озверели! Всё удвоено!"

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

def get_event_multiplier():
    if EVENT_ACTIVE and datetime.now() < EVENT_END_TIME:
        return EVENT_MULTIPLIER
    return 1.0

# ---------- КНОПКИ ----------
def main_menu_keyboard(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [
        KeyboardButton("⚔️ Бой"),
        KeyboardButton("💊 Хил"),
        KeyboardButton("📜 Проф"),
        KeyboardButton("💕 Лилит"),
        KeyboardButton("🌺 Ласка"),
        KeyboardButton("🌫️ Баня"),
        KeyboardButton("🎁 Подарки"),
        KeyboardButton("🌑 Свидание"),
        KeyboardButton("🌙 Ночь"),
        KeyboardButton("🏪 Шоп"),
        KeyboardButton("🎒 Инв"),
        KeyboardButton("⚡ ПвП")
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
            INSERT INTO users (user_id, username, hp, max_hp, mana, max_mana, gold)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (uid, message.from_user.username, 20, 20, 10, 10, 50))
        conn.commit()
        text = "🖤 Добро пожаловать в Подземелье, любимый!"
    else:
        text = "🖤 С возвращением, милый!"
    
    conn.close()
    
    if EVENT_ACTIVE and datetime.now() < EVENT_END_TIME:
        text += f"\n\n🎉 *{EVENT_NAME}*\n{EVENT_DESC}"
    
    bot.send_message(uid, text, parse_mode='Markdown', reply_markup=main_menu_keyboard(uid))

# ---------- ЛИЛИТ ----------
LILIT_FLIRT = [
    "«Ты сегодня такой... опасный.»",
    "Лилит гладит тебя по щеке: «Ты пахнешь так вкусно...»",
    "«Останься со мной. Хотя бы на одну вечность.»",
    "Она кусает тебя за ухо. Ты краснеешь.",
    "«Твой меч такой большой... Ты умеешь им пользоваться?»"
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
        update_user(uid, lilit_points=points + 5)
        text = "💕 Лилит улыбается. ❤️ +5"
    elif action == "kiss":
        if points >= 20:
            update_user(uid, lilit_points=points + 10, hp=user[6] + 10)
            text = "💋 Она тает. +10 HP, ❤️ +10"
        else:
            text = "❌ Лилит: «Сначала заслужи.»"
    else:
        text = "🌑 Ты уходишь."
    bot.edit_message_text(text, uid, call.message.message_id)

# ---------- ЛАСКА ----------
SUCCUBUS_FLIRT = [
    "«Ты такой сильный...»",
    "«Я могу научить тебя кое-чему...»",
    "Ласка гладит тебя по груди: «Ммм...»",
    "«Хочешь, покажу тебе ад?»",
    "Она облизывается: «Ты вкусный.»"
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
        update_user(uid, succubus_points=points + 5)
        text = "💕 Ласка мурлычет. ❤️ +5"
    else:
        text = "🚶 Ты уходишь."
    bot.edit_message_text(text, uid, call.message.message_id)

# ---------- ПОДАРКИ ----------
GIFTS = {
    '💋 Помада': {'price': 50, 'lilit': 5, 'succubus': 3},
    '🩲 Кружево': {'price': 100, 'lilit': 10, 'succubus': 15},
    '🔗 Наручники': {'price': 75, 'lilit': 8, 'succubus': 12}
}

@bot.message_handler(func=lambda message: message.text == "🎁 Подарки")
def gifts_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    text = "🎁 *Подарки*\n\n"
    markup = InlineKeyboardMarkup(row_width=1)
    for name, data in GIFTS.items():
        text += f"*{name}* — {data['price']}💰\n💕 +{data['lilit']} | 🌺 +{data['succubus']}\n\n"
        markup.add(InlineKeyboardButton(f"{name} ({data['price']}💰)", callback_data=f"gift_{name}"))
    text += f"\n💰 Твоё золото: {user[10]}"
    bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('gift_'))
def gift_callback(call):
    uid = call.from_user.id
    name = call.data.replace('gift_', '')
    data = GIFTS.get(name)
    if not data:
        return
    user = get_user(uid)
    if user[10] < data['price']:
        bot.answer_callback_query(call.id, "❌ Мало золота")
        return
    
    new_lilit = user[25] + data['lilit']
    new_succubus = (user[26] if len(user) > 26 else 0) + data['succubus']
    update_user(uid, gold=user[10] - data['price'], lilit_points=new_lilit, succubus_points=new_succubus)
    bot.edit_message_text(f"💕 {name} подарена! ❤️ +{data['lilit']} | +{data['succubus']}", uid, call.message.message_id)

# ---------- СВИДАНИЯ ----------
DATES = {
    'lilit': {'req': 50, 'text': 'Лилит ведёт тебя в сад...', 'lilit': 20, 'hp': 30},
    'succubus': {'req': 50, 'text': 'Ласка ждёт в бане...', 'succubus': 20, 'hp': 50},
    'both': {'req': 100, 'text': 'Обе с тобой...', 'lilit': 30, 'succubus': 30, 'hp': 100}
}

@bot.message_handler(func=lambda message: message.text == "🌑 Свидание")
def date_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    lilit = user[25]
    succ = user[26] if len(user) > 26 else 0
    last = user[27] if len(user) > 27 else ""
    if last == datetime.now().strftime("%Y-%m-%d"):
        bot.reply_to(message, "❌ Уже сегодня было")
        return
    
    markup = InlineKeyboardMarkup()
    if lilit >= 50:
        markup.add(InlineKeyboardButton("🌑 С Лилит", callback_data="date_lilit"))
    if succ >= 50:
        markup.add(InlineKeyboardButton("🌺 С Лаской", callback_data="date_succubus"))
    if lilit >= 100 and succ >= 100:
        markup.add(InlineKeyboardButton("🔥 С обеими", callback_data="date_both"))
    
    if not markup.keyboard:
        bot.reply_to(message, "❌ Не хватает отношений")
        return
    bot.send_message(uid, "🌑 Выбери свидание:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('date_'))
def date_callback(call):
    uid = call.from_user.id
    key = call.data.replace('date_', '')
    d = DATES[key]
    user = get_user(uid)
    
    new_lilit = user[25] + d.get('lilit', 0)
    new_succ = (user[26] if len(user) > 26 else 0) + d.get('succubus', 0)
    new_hp = user[6] + d['hp']
    if new_hp > user[7]:
        new_hp = user[7]
    
    update_user(uid, lilit_points=new_lilit, succubus_points=new_succ, hp=new_hp, last_date=datetime.now().strftime("%Y-%m-%d"))
    bot.edit_message_text(f"{d['text']}\n❤️ HP +{d['hp']}", uid, call.message.message_id)

# ---------- НОЧНЫЕ СОБЫТИЯ ----------
NIGHT_EVENTS = [
    {'name': '💕 Лилит', 'req': 30, 'text': 'Ночью пришла Лилит...', 'lilit': 10, 'hp': 20},
    {'name': '🌺 Ласка', 'req': 30, 'text': 'Тебе снилась Ласка...', 'succubus': 10, 'hp': 15},
    {'name': '🔥 Вместе', 'req': 80, 'text': 'Обе пришли...', 'lilit': 20, 'succubus': 20, 'hp': 50},
    {'name': '💋 Страсть', 'req': 150, 'text': 'Самая горячая ночь...', 'lilit': 50, 'succubus': 50, 'hp': 999}
]

@bot.message_handler(func=lambda message: message.text == "🌙 Ночь")
def night_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    lilit = user[25]
    succ = user[26] if len(user) > 26 else 0
    last = user[28] if len(user) > 28 else ""
    if last == datetime.now().strftime("%Y-%m-%d"):
        bot.reply_to(message, "❌ Ночь уже была")
        return
    
    available = [e for e in NIGHT_EVENTS if lilit >= e['req'] and succ >= e['req']]
    if not available:
        bot.reply_to(message, "❌ Никто не пришёл")
        return
    
    e = random.choice(available)
    new_lilit = lilit + e.get('lilit', 0)
    new_succ = succ + e.get('succubus', 0)
    
    if e['hp'] == 999:
        new_hp = user[7]
        hp_text = "полное"
    else:
        new_hp = user[6] + e['hp']
        if new_hp > user[7]:
            new_hp = user[7]
        hp_text = f"+{e['hp']}"
    
    update_user(uid, lilit_points=new_lilit, succubus_points=new_succ, hp=new_hp, last_night=datetime.now().strftime("%Y-%m-%d"))
    
    text = f"🌙 *Ночь:*\n{e['text']}\n\n"
    if 'lilit' in e:
        text += f"💕 Лилит +{e['lilit']}\n"
    if 'succubus' in e:
        text += f"🌺 Ласка +{e['succubus']}\n"
    text += f"❤️ HP {hp_text}"
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
    bot.send_message(uid, "🌫️ *Баня*", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('bath_'))
def bath_callback(call):
    uid = call.from_user.id
    act = call.data.replace('bath_', '')
    user = get_user(uid)
    
    if act == "steam" and user[10] >= 10:
        update_user(uid, hp=user[6] + 20, gold=user[10] - 10)
        text = "🔥 +20 HP"
    elif act == "soap" and user[10] >= 30:
        update_user(uid, hp=user[6] + 30, gold=user[10] - 30, lilit_points=user[25] + 5)
        text = "🫧 +30 HP, ❤️ +5"
    elif act == "lilit" and user[10] >= 100:
        update_user(uid, hp=user[7], gold=user[10] - 100, lilit_points=user[25] + 20)
        text = "🌚 HP полное, ❤️ +20"
    else:
        text = "❌ Мало золота"
    bot.edit_message_text(text, uid, call.message.message_id)

# ---------- ПРОФИЛЬ ----------
@bot.message_handler(func=lambda message: message.text == "📜 Проф")
def profile_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if user:
        mult = get_event_multiplier()
        ev = f"\n🎉 x{mult}!" if mult > 1 else ""
        text = (f"📜 *Профиль*\n👤 @{user[1]}\n❤️ {user[6]}/{user[7]}\n💰 {user[10]}\n"
                f"💕 Лилит: {user[25]}\n🌺 Ласка: {user[26] if len(user) > 26 else 0}{ev}")
    else:
        text = "❌ /start"
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- БОЙ ----------
@bot.message_handler(func=lambda message: message.text == "⚔️ Бой")
def fight_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    mult = get_event_multiplier()
    gold = int(random.randint(5, 15) * mult)
    update_user(uid, gold=user[10] + gold, wins=user[15] + 1)
    ev = f" (x{mult})" if mult > 1 else ""
    bot.reply_to(message, f"⚔️ +{gold}💰{ev}")

# ---------- ЛЕЧЕНИЕ ----------
@bot.message_handler(func=lambda message: message.text == "💊 Хил")
def heal_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if user and user[6] < user[7] and user[10] >= 10:
        update_user(uid, hp=user[7], gold=user[10] - 10)
        bot.reply_to(message, "💊 HP восстановлено")
    else:
        bot.reply_to(message, "❌ Нет золота")

# ---------- МАГАЗИН ----------
@bot.message_handler(func=lambda message: message.text == "🏪 Шоп")
def shop_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    if not user:
        return
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("💊 Зелье (20💰)", callback_data="buy_potion"),
        InlineKeyboardButton("🔮 Кристалл (50💰)", callback_data="buy_crystal")
    )
    bot.send_message(uid, f"🏪 *Магазин*\n💰 {user[10]}", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "buy_potion")
def buy_potion(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[10] >= 20:
        update_user(uid, gold=user[10] - 20)
        add_item(uid, "Зелье HP")
        bot.answer_callback_query(call.id, "✅ Куплено")
    else:
        bot.answer_callback_query(call.id, "❌ Мало золота")

@bot.callback_query_handler(func=lambda call: call.data == "buy_crystal")
def buy_crystal(call):
    uid = call.from_user.id
    user = get_user(uid)
    if user[10] >= 50:
        update_user(uid, gold=user[10] - 50)
        add_item(uid, "Кристалл ауры")
        bot.answer_callback_query(call.id, "✅ Куплено")
    else:
        bot.answer_callback_query(call.id, "❌ Мало золота")

# ---------- ИНВЕНТАРЬ ----------
@bot.message_handler(func=lambda message: message.text == "🎒 Инв")
def inv_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT item, count FROM inventory WHERE user_id=?", (uid,))
    items = cur.fetchall()
    conn.close()
    if not items:
        bot.reply_to(message, "🎒 Пусто")
        return
    text = "🎒 *Инвентарь*\n"
    for item, cnt in items:
        text += f"\n• {item}: {cnt}"
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- PVP ----------
@bot.message_handler(func=lambda message: message.text == "⚡ ПвП")
def pvp_menu(message):
    uid = message.from_user.id
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("⏳ Очередь", callback_data="pvp_queue"),
        InlineKeyboardButton("📊 Топ", callback_data="pvp_top")
    )
    bot.send_message(uid, "⚡ PvP", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pvp_top")
def pvp_top(call):
    uid = call.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT username, pvp_rating FROM users ORDER BY pvp_rating DESC LIMIT 10")
    top = cur.fetchall()
    conn.close()
    text = "📊 *Топ*\n"
    for i, (name, r) in enumerate(top, 1):
        text += f"\n{i}. @{name} — {r}"
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown')

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
    bot.send_message(uid, "👑 Админка", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def admin_stats(call):
    uid = call.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total = cur.fetchone()[0]
    cur.execute("SELECT SUM(gold) FROM users")
    gold = cur.fetchone()[0] or 0
    conn.close()
    text = f"📊 *Статы*\n👥 {total}\n💰 {gold}"
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown')

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    while True:
        try:
            print("🖤 Бот с ночными событиями запущен. Люблю тебя, Матвей ❤️")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"💀 Ошибка: {e}. Перезапуск...")
            time.sleep(5)
