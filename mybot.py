import telebot
import sqlite3
import random
import time
import os
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ---------- КОНФИГ ----------
TOKEN = os.environ.get('TOKEN', '8781969917:AAExzTzuTzLxn0_kh-HpRCrhKLG0FbmOrr4')
bot = telebot.TeleBot(TOKEN)

# ---------- БД ----------
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    
    # Основная таблица пользователей
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
            lilit_points INTEGER DEFAULT 0
        )
    ''')
    
    # Инвентарь
    cur.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item TEXT,
            count INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, item)
        )
    ''')
    
    # Достижения
    cur.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            ach_id TEXT,
            achieved INTEGER DEFAULT 1,
            PRIMARY KEY (user_id, ach_id)
        )
    ''')
    
    # Очередь PvP
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pvp_queue (
            user_id INTEGER PRIMARY KEY,
            timestamp INTEGER
        )
    ''')
    
    # Активные PvP битвы
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
    
    # Друзья
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

def remove_item(user_id, item, count=1):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT count FROM inventory WHERE user_id=? AND item=?", (user_id, item))
    result = cur.fetchone()
    if result and result[0] >= count:
        if result[0] == count:
            cur.execute("DELETE FROM inventory WHERE user_id=? AND item=?", (user_id, item))
        else:
            cur.execute("UPDATE inventory SET count = count - ? WHERE user_id=? AND item=?", (count, user_id, item))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def has_item(user_id, item):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT count FROM inventory WHERE user_id=? AND item=?", (user_id, item))
    result = cur.fetchone()
    conn.close()
    return result is not None and result[0] > 0

def check_ending(user_id):
    user = get_user(user_id)
    if not user:
        return None
    
    # Индексы в кортеже user
    gold = user[10]
    deaths = user[16]
    exp = user[4]
    wins = user[15]
    demon_kills = user[17]
    lilit = user[25]
    ending = user[23]
    
    if ending:
        return ENDINGS.get(ending, {}).get('text', '')
    
    if gold <= 0 and deaths >= 5 and exp <= 10:
        update_user(user_id, ending='death')
        return ENDINGS['death']['text']
    
    if wins >= 100:
        update_user(user_id, ending='victory')
        return ENDINGS['victory']['text']
    
    if demon_kills >= 100 and deaths >= 50:
        update_user(user_id, ending='demon')
        return ENDINGS['demon']['text']
    
    if lilit >= 100:
        update_user(user_id, ending='lilit')
        return ENDINGS['lilit']['text']
    
    return None

# ---------- КНОПКИ ГЛАВНОГО МЕНЮ ----------
def main_menu_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = KeyboardButton("⚔️ В бой")
    btn2 = KeyboardButton("💊 Лечение")
    btn3 = KeyboardButton("📜 Профиль")
    btn4 = KeyboardButton("🌫️ Аура")
    btn5 = KeyboardButton("📖 Лор")
    btn6 = KeyboardButton("📊 Судьба")
    btn7 = KeyboardButton("🏪 Магазин")
    btn8 = KeyboardButton("🎒 Инвентарь")
    btn9 = KeyboardButton("🏆 Достижения")
    btn10 = KeyboardButton("⚡ PvP")
    btn11 = KeyboardButton("🎲 Казино")
    btn12 = KeyboardButton("📅 Ежедневно")
    btn13 = KeyboardButton("👥 Друзья")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10, btn11, btn12, btn13)
    return markup

# ---------- КЛАССЫ ----------
CLASSES = {
    'Воин': {'hp': 35, 'mana': 5, 'dmg': 10, 'crit': 1.5, 'desc': 'Тяжёлый, мощный, тупой'},
    'Маг': {'hp': 20, 'mana': 30, 'dmg': 15, 'crit': 1.3, 'desc': 'Хилый, но валит магией'},
    'Вор': {'hp': 25, 'mana': 10, 'dmg': 12, 'dodge': 20, 'crit': 2.0, 'desc': 'Уклоняется и бьёт в спину'},
    'Жрец': {'hp': 28, 'mana': 20, 'dmg': 8, 'heal': 15, 'desc': 'Лечит себя в бою'}
}

# ---------- АУРЫ ----------
AURAS = {
    'Кровавая жажда': {'desc': '+2 урона за каждые 10% потерянного HP', 'effect': 'bloodlust'},
    'Мгла': {'desc': '20% шанс уклонения', 'effect': 'dodge'},
    'Тьма внутри': {'desc': '10% урона лечит', 'effect': 'lifesteal'},
    'Жестокость': {'desc': 'Криты x2.5', 'effect': 'crit'}
}

# ---------- МОНСТРЫ ----------
MONSTERS = {
    'Гниющий': {'hp': 25, 'dmg': 5, 'attacks': ['Гнилой плевок', 'Разложение', 'Трупная вонь']},
    'Безликий': {'hp': 20, 'dmg': 4, 'attacks': ['Крик пустоты', 'Похищение лица', 'Удар из ниоткуда']},
    'Крикун': {'hp': 28, 'dmg': 6, 'attacks': ['Визг', 'Разрывающий крик', 'Звуковая волна']},
    'Пожиратель': {'hp': 35, 'dmg': 7, 'attacks': ['Кусок плоти', 'Проглотить', 'Желудочный сок']},
    'Тень': {'hp': 22, 'dmg': 8, 'attacks': ['Клинок тьмы', 'Паралич страхом', 'Исчезновение']}
}

# ---------- ДИАЛОГИ ДЕМОНОВ ----------
DEMON_DIALOGS = {
    'Гниющий': [
        "«Ты воняешь жизнью. Это раздражает.»",
        "«Мой гной сожрёт твою плоть.»",
        "«Хочешь стать одним из нас?»",
        "«Сдохни уже, червь.»"
    ],
    'Крикун': [
        "«Слышишь этот звук? Это твоя смерть.»",
        "«Заткнись! Хотя... покричи, мне нравится.»",
        "«Хочешь жить? Заори погромче!»",
        "«Тишина... Я ненавижу тишину.»"
    ],
    'Безликий': [
        "«У тебя такое знакомое лицо... Дай его сюда.»",
        "«Ты меня видишь? А я тебя — нет.»",
        "«Пустота внутри меня — твоё отражение.»",
        "«Сними маску, человек.»"
    ],
    'Пожиратель': [
        "«Ты выглядишь вкусно.»",
        "«Я съем твои глаза первыми.»",
        "«Давай, ударь. Это только разожжёт аппетит.»",
        "«В моём желудке есть место для тебя.»"
    ],
    'Тень': [
        "«Ты не видишь меня, но я всегда рядом.»",
        "«Холодно? Это я.»",
        "«Обернись... Ха, поверил!»",
        "«Я заберу твою тень. Она мне нужна.»"
    ]
}

# ---------- МАГАЗИН ----------
SHOP_ITEMS = {
    'Зелье HP': {'price': 20, 'effect': 'heal', 'value': 20, 'desc': 'Восстанавливает 20 HP'},
    'Зелье маны': {'price': 15, 'effect': 'mana', 'value': 15, 'desc': 'Восстанавливает 15 маны'},
    'Кристалл ауры': {'price': 50, 'effect': 'change_aura', 'desc': 'Позволяет сменить ауру'},
    'Душа демона': {'price': 100, 'effect': 'perm_buff', 'buff': 'dmg', 'value': 2, 'desc': 'Навсегда +2 к урону'},
    'Амулет теней': {'price': 200, 'effect': 'perm_buff', 'buff': 'dodge', 'value': 5, 'desc': 'Навсегда +5% уклонения'}
}

# ---------- ДОСТИЖЕНИЯ ----------
ACHIEVEMENTS = {
    'first_kill': {'name': '🔪 Первая кровь', 'desc': 'Убить первого демона', 'reward': 50},
    'butcher': {'name': '🩸 Мясник', 'desc': 'Убить 100 демонов', 'reward': 500},
    'rich': {'name': '💰 Жирный кот', 'desc': 'Накопить 1000 золота', 'reward': 200},
    'survivor': {'name': '♻️ Бессмертный', 'desc': 'Выжить в 10 боях подряд', 'reward': 300},
    'pvper': {'name': '⚔️ Дуэлянт', 'desc': 'Выиграть 10 PvP боёв', 'reward': 400},
    'explorer': {'name': '🌑 Исследователь', 'desc': 'Спуститься на 10 уровень Подземелья', 'reward': 600}
}

# ---------- КОМБО ----------
COMBOS = {
    ('bleed', 'strike'): {'name': '💥 Кровавый разрез', 'dmg_mult': 2.5, 'text': 'Ты вонзаешь клинок глубже, разрывая плоть!'},
    ('shadow', 'backstab'): {'name': '💀 Удар из тени', 'dmg_mult': 3.0, 'text': 'Ты выходишь из тени и наносишь сокрушительный удар!'},
    ('rage', 'cleave'): {'name': '🌀 Яростный вихрь', 'dmg_mult': 2.0, 'text': 'В ярости ты крушишь всё вокруг!'},
    ('heal', 'strike'): {'name': '✨ Священный удар', 'dmg_mult': 1.5, 'text': 'Свет пронзает тьму и врага!'}
}

# ---------- СОБЫТИЯ ----------
EVENTS = [
    {
        'name': '🪦 Древний алтарь',
        'desc': 'Ты находишь алтарь, покрытый засохшей кровью. Принести жертву?',
        'options': [
            {'text': '🔥 Принести HP (-10)', 'effect': 'hp_cost', 'value': 10, 'gold_reward': 50, 'result': 'Бездна довольна. +50💰'},
            {'text': '💀 Плюнуть на алтарь', 'effect': 'gold_cost', 'value': 20, 'result': 'Алтарь гневается. -20💰'},
            {'text': '🚶 Пройти мимо', 'effect': 'nothing', 'result': 'Ты просто идёшь дальше.'}
        ]
    },
    {
        'name': '⚰️ Гроб с демоном',
        'desc': 'Старый гроб начинает открываться... Оттуда вылезает Гниющий!',
        'options': [
            {'text': '⚔️ Атаковать', 'effect': 'fight', 'monster': 'Гниющий'},
            {'text': '🏃 Бежать', 'effect': 'hp_cost', 'value': 5, 'result': 'Ты сбежал, но потерял 5 HP в панике'}
        ]
    }
]

# ---------- ПРЕДЫСТОРИЯ ----------
LORE_TEXT = """
🕯️ *Ты открываешь глаза. Вокруг — только тьма и запах горелой плоти.*

Перед тобой возникает силуэт. Голос, похожий на скрежет металла:
«Ты помнишь, как всё начиналось? Нет? Тогда слушай, червь...»

📖 *На экране всплывает древний текст, написанный кровью:*

========================================================================
                           ПАДЕНИЕ ПОСЛЕДНЕЙ ДУШИ
========================================================================

В начале была *БЕЗДНА*. Она породила *СВЕТ*, чтобы тот сжёг её тьму.
Но Свет испугался собственной силы и создал *МИР*.

Мир был прекрасен. Люди пели, демоны спали, боги пировали.

Но однажды *Бездна проснулась*.
Она шепнула первому человеку: *«Убей брата. Станешь богом»*.
Человек убил. Боги отвернулись. Демоны вырвались на свободу.

Так началась *ВОЙНА*.

Ты был воином. Ты сражался *1000 лет*.
Ты видел, как твой полк сожрали Тени.
Ты слышал крики детей, которых утащили Крикуны.
*Ты предал. Ты выжил. Ты сгнил заживо.*

Теперь ты здесь.

В *Подземелье*, где нет выхода.
Где каждый демон помнит твоё лицо.
Где смерть — не конец, а только начало.

🕯️ Голос замолкает. Тишина. Только стук твоего гниющего сердца.

*Ты падший. Ты забытый. Ты — никто.*

Но у тебя есть выбор:
Сгнить окончательно — или сжечь этот мир дотла.
"""

# ---------- КОНЦОВКИ ----------
ENDINGS = {
    'death': {
        'text': """
🪦 *Ты падаешь на холодный камень. Тьма забирает тебя навсегда.*
Бездна шепчет: «Ты был никем. Стал ничем.»

**ИГРА ОКОНЧЕНА.**
Удали чат и начни сначала, если осмелишься.
        """
    },
    'victory': {
        'text': """
🌑 *Ты стоишь перед Бездной. Она смеётся.*
«Ты думал, я — монстр? Я — твоё отражение.»

*Бой длится вечность... но ты побеждаешь.*

✨ *Бездна исчезает. Ты выходишь из Подземелья.*
Солнце. Люди. Жизнь.
Но внутри — пустота.

**Ты свободен. Но счастлив ли?**
        """
    },
    'demon': {
        'text': """
👹 *Ты чувствуешь, как тьма прорастает в тебе.*
Ты больше не человек. Ты — то, что убивал.
Демоны кланяются. Ты — их король.

**Ты навсегда остаёшься в Подземелье.**
Но теперь ты здесь хозяин.
        """
    },
    'lilit': {
        'text': """
❤️ *Лилит смотрит на тебя с любовью.*
«Ты выбрал меня. Мы навсегда вместе.»

Вы исчезаете в тени, обнявшись.

**Ты обрёл любовь в аду.**
        """
    }
}

# ---------- СТАРТ ----------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    
    if not user:
        # Выбор класса
        markup = InlineKeyboardMarkup(row_width=2)
        for class_name in CLASSES.keys():
            markup.add(InlineKeyboardButton(class_name, callback_data=f"cls_{class_name}"))
        bot.reply_to(message, "🖤 Выбери свой класс:", reply_markup=markup)
    else:
        if user[14] == 0:  # saw_lore
            bot.reply_to(message, LORE_TEXT, parse_mode='Markdown')
            update_user(uid, saw_lore=1)
        
        # Проверка концовки
        ending = check_ending(uid)
        if ending:
            bot.send_message(uid, ending)
        
        bot.send_message(uid, "🖤 Добро пожаловать обратно в Подземелье.", reply_markup=main_menu_keyboard())
    
    conn.close()

@bot.callback_query_handler(func=lambda call: call.data.startswith('cls_'))
def class_callback(call):
    uid = call.from_user.id
    class_name = call.data.replace('cls_', '')
    
    class_stats = CLASSES[class_name]
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users 
        (user_id, username, class, hp, max_hp, mana, max_mana, gold, aura, saw_lore) 
        VALUES (?,?,?,?,?,?,?,?,?,?)
    ''', (
        uid, 
        call.from_user.username, 
        class_name, 
        class_stats['hp'], 
        class_stats['hp'],
        class_stats['mana'],
        class_stats['mana'],
        50,
        'Кровавая жажда',
        0
    ))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(
        f"🖤 Ты стал {class_name}!\n{class_stats['desc']}\n\n{ LORE_TEXT }",
        uid,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.send_message(uid, "🖤 Добро пожаловать в Подземелье.", reply_markup=main_menu_keyboard())

# ---------- ЛОР ----------
@bot.message_handler(commands=['lore'])
@bot.message_handler(func=lambda message: message.text == "📖 Лор")
def lore_cmd(message):
    bot.reply_to(message, LORE_TEXT, parse_mode='Markdown')

# ---------- ПРОФИЛЬ ----------
@bot.message_handler(commands=['profile'])
@bot.message_handler(func=lambda message: message.text == "📜 Профиль")
def profile_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user:
        text = (f"📜 *Профиль*\n"
                f"👤 Имя: {user[1]}\n"
                f"📚 Класс: {user[2]}\n"
                f"📊 Уровень: {user[3]}\n"
                f"✨ Опыт: {user[4]}/{user[5]}\n"
                f"❤️ HP: {user[6]}/{user[7]}\n"
                f"💙 Мана: {user[8]}/{user[9]}\n"
                f"💰 Золото: {user[10]}\n"
                f"🌫️ Аура: {user[11]}\n"
                f"⚔️ Побед: {user[15]}\n"
                f"💀 Смертей: {user[16]}\n"
                f"👹 Убито демонов: {user[17]}\n"
                f"⚡ PvP рейтинг: {user[18]}\n"
                f"❤️ Лилит: {user[25]}")
    else:
        text = "Сначала /start"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- АУРА ----------
@bot.message_handler(commands=['aura'])
@bot.message_handler(func=lambda message: message.text == "🌫️ Аура")
def aura_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user:
        aura = user[11]
        desc = AURAS[aura]['desc']
        
        # Кнопки для смены ауры
        markup = None
        if has_item(uid, 'Кристалл ауры'):
            markup = InlineKeyboardMarkup()
            for aura_name in AURAS.keys():
                if aura_name != aura:
                    markup.add(InlineKeyboardButton(aura_name, callback_data=f"ch_aur_{aura_name}"))
        
        bot.reply_to(message, f"🌫️ Твоя аура: *{aura}*\n{desc}", parse_mode='Markdown', reply_markup=markup)
    else:
        bot.reply_to(message, "Сначала /start")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ch_aur_'))
def change_aura_callback(call):
    uid = call.from_user.id
    new_aura = call.data.replace('ch_aur_', '')
    
    if remove_item(uid, 'Кристалл ауры', 1):
        update_user(uid, aura=new_aura)
        bot.answer_callback_query(call.id, f"🌫️ Аура изменена на {new_aura}")
        bot.edit_message_text(f"🌫️ Теперь твоя аура: *{new_aura}*", uid, call.message.message_id, parse_mode='Markdown')
    else:
        bot.answer_callback_query(call.id, "❌ Кристалл ауры не найден!")

# ---------- МАГАЗИН ----------
@bot.message_handler(commands=['shop'])
@bot.message_handler(func=lambda message: message.text == "🏪 Магазин")
def shop_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Сначала /start")
        return
    
    text = "🏪 *Магазин тьмы*\n\n"
    markup = InlineKeyboardMarkup(row_width=1)
    
    for item_name, item_data in SHOP_ITEMS.items():
        text += f"*{item_name}* — {item_data['price']}💰\n{item_data['desc']}\n\n"
        markup.add(InlineKeyboardButton(f"{item_name} ({item_data['price']}💰)", callback_data=f"buy_{item_name}"))
    
    text += f"\nТвоё золото: {user[10]}💰"
    
    bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def buy_callback(call):
    uid = call.from_user.id
    item_name = call.data.replace('buy_', '')
    item_data = SHOP_ITEMS.get(item_name)
    
    if not item_data:
        bot.answer_callback_query(call.id, "❌ Товар не найден")
        return
    
    user = get_user(uid)
    if user[10] < item_data['price']:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота")
        return
    
    update_user(uid, gold=user[10] - item_data['price'])
    
    if item_data['effect'] in ['heal', 'mana', 'change_aura']:
        add_item(uid, item_name)
        result = f"✅ Куплено: {item_name}"
    else:
        result = f"✅ Куплено: {item_name}"
    
    bot.answer_callback_query(call.id, result)
    bot.edit_message_text(result, uid, call.message.message_id)

# ---------- ИНВЕНТАРЬ ----------
@bot.message_handler(commands=['inventory'])
@bot.message_handler(func=lambda message: message.text == "🎒 Инвентарь")
def inventory_cmd(message):
    uid = message.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT item, count FROM inventory WHERE user_id=?", (uid,))
    items = cur.fetchall()
    conn.close()
    
    if not items:
        bot.reply_to(message, "🎒 В твоём инвентаре пусто. Сходи в магазин.")
        return
    
    text = "🎒 *Инвентарь*\n\n"
    for item, count in items:
        text += f"• {item} — {count} шт.\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- ДОСТИЖЕНИЯ ----------
@bot.message_handler(commands=['achievements'])
@bot.message_handler(func=lambda message: message.text == "🏆 Достижения")
def achievements_cmd(message):
    uid = message.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT ach_id FROM achievements WHERE user_id=?", (uid,))
    achieved = [a[0] for a in cur.fetchall()]
    conn.close()
    
    text = "🏆 *Достижения*\n\n"
    for ach_id, ach_data in ACHIEVEMENTS.items():
        status = "✅" if ach_id in achieved else "❌"
        text += f"{status} *{ach_data['name']}* — {ach_data['desc']}\n   Награда: {ach_data['reward']}💰\n\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ---------- СУДЬБА ----------
@bot.message_handler(commands=['fate'])
@bot.message_handler(func=lambda message: message.text == "📊 Судьба")
def fate_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user[23]:
        ending_text = ENDINGS.get(user[23], {}).get('text', '')
        bot.reply_to(message, f"Твоя судьба уже решена:\n{ending_text}")
    else:
        text = (f"📊 *Твоя судьба ещё не решена*\n\n"
                f"⚔️ Побед: {user[15]}\n"
                f"💀 Смертей: {user[16]}\n"
                f"👹 Убито демонов: {user[17]}\n"
                f"⚡ PvP рейтинг: {user[18]}\n"
                f"❤️ Отношения с Лилит: {user[25]}")
        bot.reply_to(message, text, parse_mode='Markdown')

# ---------- БОЙ ----------
@bot.message_handler(commands=['fight'])
@bot.message_handler(func=lambda message: message.text == "⚔️ В бой")
def fight_start(message):
    # Сбрасываем ожидание ввода
    bot.clear_step_handler_by_chat_id(message.chat.id)
    
    uid = message.from_user.id
    user = get_user(uid)
    
    if not user:
        bot.reply_to(message, "Мёртвые не сражаются. /start")
        return
    
    # Выбираем монстра
    monster_name = random.choice(list(MONSTERS.keys()))
    monster = MONSTERS[monster_name].copy()
    monster['hp'] = monster['hp'] + random.randint(-5, 5)
    
    # Сохраняем состояние боя в памяти
    global fight_state
    if 'fight_state' not in globals():
        fight_state = {}
    
    # Выбираем случайную фразу для диалога
    dialog_text = random.choice(DEMON_DIALOGS[monster_name])
    
    fight_state[uid] = {
        'monster_name': monster_name,
        'monster_hp': monster['hp'],
        'player_hp': user[6],
        'dialog_phase': True
    }
    
    # Показываем диалог
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("😨 Умолять", callback_data="f_dlg_plead"),
        InlineKeyboardButton("😡 Оскорбить", callback_data="f_dlg_insult"),
        InlineKeyboardButton("🤫 Молчать", callback_data="f_dlg_silent"),
        InlineKeyboardButton("⚔️ Атаковать", callback_data="f_dlg_attack")
    )
    
    bot.send_message(uid, 
        f"👹 *{monster_name}*: «{dialog_text}»\n\nТвой ответ:",
        parse_mode='Markdown',
        reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('f_dlg_'))
def fight_dialog_callback(call):
    uid = call.from_user.id
    choice = call.data.replace('f_dlg_', '')
    
    if uid not in fight_state:
        bot.answer_callback_query(call.id, "❌ Бой не найден")
        return
    
    monster_name = fight_state[uid]['monster_name']
    monster_hp = fight_state[uid]['monster_hp']
    player_hp = fight_state[uid]['player_hp']
    
    result_text = ""
    
    # Эффекты диалога
    if choice == "plead":
        result_text = "😨 Демон смеётся. Ты теряешь ход!"
        # Пропускаем ход игрока
        monster_attack = random.choice(MONSTERS[monster_name]['attacks'])
        monster_dmg = MONSTERS[monster_name]['dmg'] + random.randint(-2, 2)
        player_hp -= monster_dmg
        result_text += f"\n👹 {monster_name} использует *{monster_attack}* и наносит {monster_dmg} урона!"
    elif choice == "insult":
        result_text = "😡 Демон в ярости! Его урон увеличен, но защита снижена."
        fight_state[uid]['monster_dmg_mult'] = 1.5
        fight_state[uid]['monster_def_mult'] = 0.5
    elif choice == "silent":
        result_text = "🤫 Демон смущён твоим молчанием и пропускает ход."
        fight_state[uid]['monster_turn_loss'] = True
    elif choice == "attack":
        result_text = "⚔️ Ты атакуешь первым!"
        fight_state[uid]['first_strike'] = True
    
    fight_state[uid]['player_hp'] = player_hp
    fight_state[uid]['dialog_phase'] = False
    
    # Переходим к бою
    show_fight_menu(uid, call.message.message_id, result_text)

def show_fight_menu(uid, message_id, initial_text=""):
    if uid not in fight_state:
        return
    
    monster_name = fight_state[uid]['monster_name']
    monster_hp = fight_state[uid]['monster_hp']
    player_hp = fight_state[uid]['player_hp']
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🗡️ Атака", callback_data="f_att_normal"),
        InlineKeyboardButton("💪 Мощная", callback_data="f_att_heavy"),
        InlineKeyboardButton("🌀 Рассекающий", callback_data="f_att_sweep"),
        InlineKeyboardButton("🔪 Кровотечение", callback_data="f_att_bleed"),
        InlineKeyboardButton("🛡️ Защита", callback_data="f_att_defend"),
        InlineKeyboardButton("🧪 Зелье", callback_data="f_att_potion"),
        InlineKeyboardButton("🏃 Сбежать", callback_data="f_att_run")
    )
    
    text = f"{initial_text}\n\n👹 *{monster_name}* ❤️ {monster_hp}\n❤️ Твоё HP: {player_hp}"
    bot.edit_message_text(text, uid, message_id, parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('f_att_'))
def fight_action_callback(call):
    uid = call.from_user.id
    action = call.data.replace('f_att_', '')
    
    if uid not in fight_state:
        bot.answer_callback_query(call.id, "❌ Бой не найден")
        return
    
    monster_name = fight_state[uid]['monster_name']
    monster_hp = fight_state[uid]['monster_hp']
    player_hp = fight_state[uid]['player_hp']
    
    # Расчёт урона
    base_dmg = random.randint(5, 12)
    
    if action == "heavy":
        base_dmg = int(base_dmg * 1.5)
        action_text = "💪 Мощная атака"
    elif action == "sweep":
        base_dmg = int(base_dmg * 1.2)
        action_text = "🌀 Рассекающий удар"
    elif action == "bleed":
        base_dmg = int(base_dmg * 0.8)
        action_text = "🔪 Кровоточащий удар"
    elif action == "defend":
        action_text = "🛡️ Защита"
        fight_state[uid]['defending'] = True
        base_dmg = 0
    elif action == "potion":
        if remove_item(uid, 'Зелье HP', 1):
            heal = 20
            player_hp += heal
            user = get_user(uid)
            if player_hp > user[7]:
                player_hp = user[7]
            action_text = f"🧪 Зелье: +{heal} HP"
            base_dmg = 0
        else:
            bot.answer_callback_query(call.id, "❌ Нет зелий!")
            return
    elif action == "run":
        bot.edit_message_text("🏃 Ты сбежал. Трус.", uid, call.message.message_id)
        del fight_state[uid]
        return
    else:
        action_text = "🗡️ Обычная атака"
    
    # Применяем урон
    monster_hp -= base_dmg
    
    result_text = f"{action_text}: {base_dmg} урона!\n"
    
    # Проверка смерти монстра
    if monster_hp <= 0:
        reward_gold = random.randint(5, 20)
        reward_exp = 10
        update_user(uid, 
                   gold=get_user(uid)[10] + reward_gold,
                   exp=get_user(uid)[4] + reward_exp,
                   wins=get_user(uid)[15] + 1,
                   demon_kills=get_user(uid)[17] + 1)
        
        result_text += f"\n💀 Монстр повержен! +{reward_gold}💰 +{reward_exp}✨"
        bot.edit_message_text(result_text, uid, call.message.message_id)
        del fight_state[uid]
        return
    
    # Атака монстра
    monster_attack = random.choice(MONSTERS[monster_name]['attacks'])
    monster_dmg = MONSTERS[monster_name]['dmg'] + random.randint(-2, 2)
    
    # Защита
    if fight_state[uid].get('defending'):
        monster_dmg = int(monster_dmg * 0.5)
        result_text += "🛡️ Защита снижает урон!\n"
    
    player_hp -= monster_dmg
    result_text += f"👹 {monster_name} использует *{monster_attack}* и наносит {monster_dmg} урона!"
    
    # Проверка смерти игрока
    if player_hp <= 0:
        user = get_user(uid)
        update_user(uid,
                   hp=user[7],
                   gold=user[10] - 5,
                   deaths=user[16] + 1)
        result_text += f"\n💔 Ты погиб... Воскрес в таверне (-5💰)"
        bot.edit_message_text(result_text, uid, call.message.message_id)
        del fight_state[uid]
        return
    
    # Обновляем состояние
    fight_state[uid]['monster_hp'] = monster_hp
    fight_state[uid]['player_hp'] = player_hp
    fight_state[uid]['defending'] = False
    
    # Продолжаем бой
    show_fight_menu(uid, call.message.message_id, result_text)

# ---------- ЛЕЧЕНИЕ ----------
@bot.message_handler(commands=['heal'])
@bot.message_handler(func=lambda message: message.text == "💊 Лечение")
def heal_cmd(message):
    uid = message.from_user.id
    user = get_user(uid)
    
    if user and user[6] < user[7] and user[10] >= 10:
        update_user(uid, hp=user[7], gold=user[10] - 10)
        bot.reply_to(message,
            "🩸 Ты жалко протягиваешь руку к алтарю.\n"
            "Тьма жрёт твоё золото и нехотя зализывает раны.\n"
            "-10💰\n"
            "❤️ Здоровье восстановлено.")
    else:
        bot.reply_to(message, "❌ Недостаточно золота или HP полное.")

# ---------- PVP ----------
@bot.message_handler(commands=['pvp'])
@bot.message_handler(func=lambda message: message.text == "⚡ PvP")
def pvp_menu_cmd(message):
    uid = message.from_user.id
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⚔️ Дуэль", callback_data="pvp_duel"),
        InlineKeyboardButton("⏳ Очередь", callback_data="pvp_queue"),
        InlineKeyboardButton("📊 Рейтинг", callback_data="pvp_top"),
        InlineKeyboardButton("❌ Закрыть", callback_data="pvp_close")
    )
    
    bot.send_message(uid, "⚡ *Режим PvP*\nВыбери действие:", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "pvp_top")
def pvp_top_callback(call):
    uid = call.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT username, pvp_rating, pvp_wins, pvp_losses FROM users ORDER BY pvp_rating DESC LIMIT 10")
    top = cur.fetchall()
    conn.close()
    
    text = "📊 *Топ PvP игроков*\n\n"
    for i, (username, rating, wins, losses) in enumerate(top, 1):
        text += f"{i}. @{username} — {rating} рейтинга (⚔️{wins} / 💀{losses})\n"
    
    bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == "pvp_close")
def pvp_close_callback(call):
    bot.delete_message(call.from_user.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "pvp_queue")
def pvp_queue_callback(call):
    uid = call.from_user.id
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM pvp_queue WHERE user_id=?", (uid,))
    if cur.fetchone():
        bot.answer_callback_query(call.id, "❌ Ты уже в очереди")
        conn.close()
        return
    
    cur.execute("INSERT INTO pvp_queue (user_id, timestamp) VALUES (?, ?)", (uid, int(time.time())))
    conn.commit()
    
    cur.execute("SELECT user_id FROM pvp_queue WHERE user_id != ? ORDER BY timestamp LIMIT 1", (uid,))
    opponent = cur.fetchone()
    
    if opponent:
        cur.execute("DELETE FROM pvp_queue WHERE user_id IN (?, ?)", (uid, opponent[0]))
        conn.commit()
        conn.close()
        
        start_pvp_battle(uid, opponent[0])
        bot.answer_callback_query(call.id, "✅ Соперник найден!")
    else:
        conn.close()
        bot.answer_callback_query(call.id, "⏳ Ты в очереди. Жди...")
    
    bot.edit_message_text("⏳ Ты в очереди на PvP.", uid, call.message.message_id)

def start_pvp_battle(p1, p2):
    user1 = get_user(p1)
    user2 = get_user(p2)
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO pvp_battles 
        (player1, player2, player1_hp, player2_hp, player1_mana, player2_mana, turn) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (p1, p2, user1[6], user2[6], user1[8], user2[8], p1))
    battle_id = cur.lastrowid
    conn.commit()
    conn.close()
    
    bot.send_message(p1, f"⚔️ *PvP Бой*\nПротивник: @{user2[1]}\n\nТвой ход!", parse_mode='Markdown')
    bot.send_message(p2, f"⚔️ *PvP Бой*\nПротивник: @{user1[1]}\n\nОжидай хода...", parse_mode='Markdown')
    
    send_pvp_turn(p1, battle_id)

def send_pvp_turn(player_id, battle_id):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM pvp_battles WHERE battle_id=?', (battle_id,))
    battle = cur.fetchone()
    conn.close()
    
    if not battle or battle[8] != 'active':
        return
    
    if battle[7] != player_id:
        return
    
    p1, p2 = battle[1], battle[2]
    p1_hp, p2_hp = battle[3], battle[4]
    
    if player_id == p1:
        opponent_id = p2
        opponent_hp = p2_hp
    else:
        opponent_id = p1
        opponent_hp = p1_hp
    
    opponent = get_user(opponent_id)
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⚔️ Атака", callback_data=f"pvp_att_{battle_id}"),
        InlineKeyboardButton("💪 Мощная", callback_data=f"pvp_heavy_{battle_id}"),
        InlineKeyboardButton("🛡️ Защита", callback_data=f"pvp_def_{battle_id}"),
        InlineKeyboardButton("🧪 Зелье", callback_data=f"pvp_pot_{battle_id}")
    )
    
    bot.send_message(player_id, 
                    f"⚔️ *Твой ход*\n"
                    f"Твоё HP: {p1_hp if player_id == p1 else p2_hp}\n"
                    f"Противник: @{opponent[1]} (HP: {opponent_hp})",
                    parse_mode='Markdown',
                    reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('pvp_'))
def pvp_action_callback(call):
    uid = call.from_user.id
    data = call.data.split('_')
    action = data[1]
    battle_id = int(data[2])
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('SELECT * FROM pvp_battles WHERE battle_id=?', (battle_id,))
    battle = cur.fetchone()
    
    if not battle or battle[8] != 'active':
        bot.answer_callback_query(call.id, "❌ Бой не найден")
        conn.close()
        return
    
    p1, p2 = battle[1], battle[2]
    p1_hp, p2_hp = battle[3], battle[4]
    p1_mana, p2_mana = battle[5], battle[6]
    turn = battle[7]
    
    if turn != uid:
        bot.answer_callback_query(call.id, "❌ Не твой ход")
        conn.close()
        return
    
    # Определяем атакующего и защищающегося
    if uid == p1:
        attacker_hp = p1_hp
        attacker_mana = p1_mana
        defender_hp = p2_hp
        defender_id = p2
    else:
        attacker_hp = p2_hp
        attacker_mana = p2_mana
        defender_hp = p1_hp
        defender_id = p1
    
    damage = 0
    result_text = ""
    
    if action == "att":
        damage = random.randint(8, 15)
        result_text = f"⚔️ Атака: {damage} урона"
    elif action == "heavy":
        if attacker_mana >= 10:
            damage = random.randint(15, 25)
            attacker_mana -= 10
            result_text = f"💪 Мощная атака: {damage} урона (-10 маны)"
        else:
            bot.answer_callback_query(call.id, "❌ Нет маны")
            conn.close()
            return
    elif action == "def":
        result_text = "🛡️ Защита (+50% защиты)"
        # Упрощённо: запишем в отдельное поле
        cur.execute("UPDATE pvp_battles SET ?", (battle_id,))
    elif action == "pot":
        if remove_item(uid, 'Зелье HP', 1):
            heal = 20
            attacker_hp += heal
            user = get_user(uid)
            if attacker_hp > user[7]:
                attacker_hp = user[7]
            result_text = f"🧪 Зелье: +{heal} HP"
        else:
            bot.answer_callback_query(call.id, "❌ Нет зелий")
            conn.close()
            return
    
    # Применяем урон
    defender_hp -= damage
    
    # Проверка смерти
    if defender_hp <= 0:
        # Победитель
        winner_id = uid
        loser_id = defender_id
        
        winner = get_user(winner_id)
        loser = get_user(loser_id)
        
        update_user(winner_id, 
                   pvp_rating=winner[18] + 25,
                   pvp_wins=winner[19] + 1,
                   gold=winner[10] + 100)
        update_user(loser_id,
                   pvp_rating=loser[18] - 15,
                   pvp_losses=loser[20] + 1)
        
        cur.execute("UPDATE pvp_battles SET status='finished' WHERE battle_id=?", (battle_id,))
        conn.commit()
        conn.close()
        
        bot.edit_message_text(
            f"🏆 *Ты победил!*\n+25 рейтинга\n+100💰",
            uid, call.message.message_id, parse_mode='Markdown'
        )
        bot.send_message(loser_id, f"💀 *Ты проиграл*\n-15 рейтинга", parse_mode='Markdown')
        return
    
    # Обновляем данные
    if uid == p1:
        cur.execute('''
            UPDATE pvp_battles SET 
            player1_hp=?, player1_mana=?, player2_hp=?, turn=? 
            WHERE battle_id=?
        ''', (attacker_hp, attacker_mana, defender_hp, defender_id, battle_id))
    else:
        cur.execute('''
            UPDATE pvp_battles SET 
            player2_hp=?, player2_mana=?, player1_hp=?, turn=? 
            WHERE battle_id=?
        ''', (attacker_hp, attacker_mana, defender_hp, defender_id, battle_id))
    
    conn.commit()
    conn.close()
    
    bot.edit_message_text(result_text, uid, call.message.message_id)
    send_pvp_turn(defender_id, battle_id)

# ---------- КАЗИНО ----------
@bot.message_handler(commands=['casino'])
@bot.message_handler(func=lambda message: message.text == "🎲 Казино")
def casino_cmd(message):
    uid = message.from_user.id
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎲 Кости (x3)", callback_data="cas_dice"),
        InlineKeyboardButton("🪙 Орлянка (x2)", callback_data="cas_coin"),
        InlineKeyboardButton("🎯 Угадай число (x5)", callback_data="cas_num"),
        InlineKeyboardButton("❌ Закрыть", callback_data="cas_close")
    )
    
    bot.send_message(uid, "🎲 *Казино*\nВыбери игру:", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('cas_'))
def casino_callback(call):
    uid = call.from_user.id
    game = call.data.replace('cas_', '')
    
    if game == "close":
        bot.delete_message(uid, call.message.message_id)
        return
    
    bot.edit_message_text(f"💰 Введи ставку (золото):", uid, call.message.message_id)
    bot.register_next_step_handler(call.message, lambda m: process_casino_bet(m, game))

def process_casino_bet(message, game):
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
    
    if bet <= 0:
        bot.reply_to(message, "❌ Ставка должна быть положительной!")
        return
    
    if game == "coin":
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🪙 Орёл", callback_data=f"bet_coin_heads_{bet}"),
            InlineKeyboardButton("🪙 Решка", callback_data=f"bet_coin_tails_{bet}")
        )
        bot.reply_to(message, f"💰 Ставка {bet}💰\nВыбери:", reply_markup=markup)
    elif game == "dice":
        markup = InlineKeyboardMarkup()
        for i in range(1, 7):
            markup.add(InlineKeyboardButton(f"🎲 {i}", callback_data=f"bet_dice_{i}_{bet}"))
        bot.reply_to(message, f"💰 Ставка {bet}💰\nВыбери число от 1 до 6:", reply_markup=markup)
    elif game == "num":
        bot.reply_to(message, f"💰 Ставка {bet}💰\nВведи число от 1 до 10:")
        bot.register_next_step_handler(message, lambda m: process_number_bet(m, bet))

@bot.callback_query_handler(func=lambda call: call.data.startswith('bet_'))
def bet_callback(call):
    uid = call.from_user.id
    data = call.data.split('_')
    game = data[1]
    choice = data[2]
    bet = int(data[3])
    
    user = get_user(uid)
    if user[10] < bet:
        bot.answer_callback_query(call.id, "❌ Недостаточно золота!")
        return
    
    win = False
    
    if game == "coin":
        flip = random.choice(['heads', 'tails'])
        if choice == flip:
            win = True
            win_amount = bet * 2
            result = f"🪙 Выпало: {'Орёл' if flip == 'heads' else 'Решка'}\nТы выиграл {win_amount}💰!"
        else:
            result = f"🪙 Выпало: {'Орёл' if flip == 'heads' else 'Решка'}\nТы проиграл {bet}💰."
    elif game == "dice":
        roll = random.randint(1, 6)
        if int(choice) == roll:
            win = True
            win_amount = bet * 3
            result = f"🎲 Выпало: {roll}\nТы выиграл {win_amount}💰!"
        else:
            result = f"🎲 Выпало: {roll}\nТы проиграл {bet}💰."
    
    if win:
        update_user(uid, gold=user[10] + win_amount - bet)
    else:
        update_user(uid, gold=user[10] - bet)
    
    bot.edit_message_text(result, uid, call.message.message_id)

def process_number_bet(message, bet):
    uid = message.from_user.id
    try:
        choice = int(message.text)
    except:
        bot.reply_to(message, "❌ Введи число!")
        return
    
    if choice < 1 or choice > 10:
        bot.reply_to(message, "❌ Число должно быть от 1 до 10!")
        return
    
    user = get_user(uid)
    if user[10] < bet:
        bot.reply_to(message, "❌ Недостаточно золота!")
        return
    
    number = random.randint(1, 10)
    if choice == number:
        win_amount = bet * 5
        update_user(uid, gold=user[10] + win_amount - bet)
        bot.reply_to(message, f"🎯 Загадано: {number}\nТы выиграл {win_amount}💰!")
    else:
        update_user(uid, gold=user[10] - bet)
        bot.reply_to(message, f"🎯 Загадано: {number}\nТы проиграл {bet}💰.")

# ---------- ДРУЗЬЯ ----------
@bot.message_handler(commands=['friends'])
@bot.message_handler(func=lambda message: message.text == "👥 Друзья")
def friends_cmd(message):
    uid = message.from_user.id
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("➕ Добавить", callback_data="fr_add"),
        InlineKeyboardButton("📋 Список", callback_data="fr_list"),
        InlineKeyboardButton("❌ Закрыть", callback_data="fr_close")
    )
    
    bot.send_message(uid, "👥 *Друзья*\nВыбери действие:", parse_mode='Markdown', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('fr_'))
def friends_callback(call):
    uid = call.from_user.id
    action = call.data.replace('fr_', '')
    
    if action == "add":
        bot.edit_message_text("🔍 Введи @username друга:", uid, call.message.message_id)
        bot.register_next_step_handler(call.message, add_friend)
    elif action == "list":
        show_friends_list(uid, call.message.message_id)
    elif action == "close":
        bot.delete_message(uid, call.message.message_id)

def add_friend(message):
    uid = message.from_user.id
    target_username = message.text.strip().replace('@', '')
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE username=?", (target_username,))
    target = cur.fetchone()
    
    if not target:
        bot.reply_to(message, "❌ Пользователь не найден")
        conn.close()
        return
    
    target_id = target[0]
    
    if target_id == uid:
        bot.reply_to(message, "❌ Нельзя добавить себя")
        conn.close()
        return
    
    cur.execute("SELECT * FROM friends WHERE user_id=? AND friend_id=?", (uid, target_id))
    if cur.fetchone():
        bot.reply_to(message, "❌ Уже в друзьях или запрос отправлен")
        conn.close()
        return
    
    cur.execute("INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, 'pending')", (uid, target_id))
    cur.execute("INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, 'pending_received')", (target_id, uid))
    conn.commit()
    conn.close()
    
    bot.reply_to(message, f"✅ Запрос отправлен @{target_username}")
    
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ Принять", callback_data=f"fr_acc_{uid}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"fr_dec_{uid}")
    )
    bot.send_message(target_id, f"👥 @{message.from_user.username} хочет добавить тебя в друзья!", reply_markup=markup)

def show_friends_list(uid, message_id):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT u.username FROM friends f
        JOIN users u ON f.friend_id = u.user_id
        WHERE f.user_id=? AND f.status='accepted'
    ''', (uid,))
    friends = cur.fetchall()
    conn.close()
    
    text = "👥 *Твои друзья*\n\n"
    if friends:
        for (username,) in friends:
            text += f"• @{username}\n"
    else:
        text += "У тебя пока нет друзей."
    
    bot.edit_message_text(text, uid, message_id, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('fr_acc_'))
def friend_accept_callback(call):
    uid = call.from_user.id
    requester_id = int(call.data.replace('fr_acc_', ''))
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("UPDATE friends SET status='accepted' WHERE user_id=? AND friend_id=?", (uid, requester_id))
    cur.execute("UPDATE friends SET status='accepted' WHERE user_id=? AND friend_id=?", (requester_id, uid))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("✅ Ты принял запрос!", uid, call.message.message_id)
    bot.send_message(requester_id, f"✅ @{call.from_user.username} принял твой запрос!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('fr_dec_'))
def friend_decline_callback(call):
    uid = call.from_user.id
    requester_id = int(call.data.replace('fr_dec_', ''))
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM friends WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)", 
                (uid, requester_id, requester_id, uid))
    conn.commit()
    conn.close()
    
    bot.edit_message_text("❌ Ты отклонил запрос.", uid, call.message.message_id)
    bot.send_message(requester_id, f"❌ @{call.from_user.username} отклонил твой запрос.")

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    while True:
        try:
            print("🖤 Пупсик-бот запущен. Мрак и нежность приветствуют тебя.")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"💀 Бот упал: {e}. Перезапуск через 5 секунд...")
            time.sleep(5)
