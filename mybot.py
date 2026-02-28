import telebot
import sqlite3
import random
import time
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ---------- КОНФИГ ----------
TOKEN = os.environ.get('TOKEN', '8781969917:AAExzTzuTzLxn0_kh-HpRCrhKLG0FbmOrr4')
bot = telebot.TeleBot(TOKEN)

# ---------- БД ----------
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            class TEXT DEFAULT 'Падший',
            hp INTEGER DEFAULT 20,
            max_hp INTEGER DEFAULT 20,
            gold INTEGER DEFAULT 0,
            exp INTEGER DEFAULT 0,
            aura TEXT DEFAULT 'Кровавая жажда',
            combo_count INTEGER DEFAULT 0,
            last_action TEXT DEFAULT '',
            saw_lore INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            deaths INTEGER DEFAULT 0,
            demon_kills INTEGER DEFAULT 0,
            ending TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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
        'condition': lambda u: u[5] <= 0 and u[12] >= 5 and u[6] <= 10,
        'text': """
🪦 *Ты падаешь на холодный камень. Тьма забирает тебя навсегда.*
Бездна шепчет: «Ты был никем. Стал ничем.»

**ИГРА ОКОНЧЕНА.**
Удали чат и начни сначала, если осмелишься.
        """
    },
    'victory': {
        'condition': lambda u: u[11] >= 100,  # 100 побед
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
        'condition': lambda u: u[13] >= 100 and u[12] >= 50,  # 100 убийств демонов, 50 смертей
        'text': """
👹 *Ты чувствуешь, как тьма прорастает в тебе.*
Ты больше не человек. Ты — то, что убивал.
Демоны кланяются. Ты — их король.

**Ты навсегда остаёшься в Подземелье.**
Но теперь ты здесь хозяин.
        """
    }
}

# ---------- КОМБО ----------
COMBOS = {
    ('bleed', 'strike'): {'name': '💥 Кровавый разрез', 'dmg_mult': 2.5, 'text': 'Ты вонзаешь клинок глубже, разрывая плоть!'},
    ('shadow', 'backstab'): {'name': '💀 Удар из тени', 'dmg_mult': 3.0, 'text': 'Ты выходишь из тени и наносишь сокрушительный удар!'},
    ('rage', 'cleave'): {'name': '🌀 Яростный вихрь', 'dmg_mult': 2.0, 'text': 'В ярости ты крушишь всё вокруг!'}
}

# ---------- ПРОВЕРКА КОНЦОВОК ----------
def check_ending(user_id):
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    
    for ending_id, ending in ENDINGS.items():
        if ending['condition'](user) and user[14] == '':
            cur.execute("UPDATE users SET ending=? WHERE user_id=?", (ending_id, user_id))
            conn.commit()
            conn.close()
            return ending['text']
    conn.close()
    return None

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
            (user_id, username, class, hp, max_hp, gold, exp, aura, combo_count, last_action, saw_lore, wins, deaths, demon_kills, ending) 
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (uid, message.from_user.username, 'Падший', 20, 20, 0, 0, 'Кровавая жажда', 0, '', 0, 0, 0, 0, ''))
        conn.commit()
        
        # Показываем предысторию новым
        bot.reply_to(message, LORE_TEXT, parse_mode='Markdown')
        bot.send_message(uid, 
            "🕯️ Ты очнулся в луже собственной мочи. Воняет тленом и твоим страхом.\n\n"
            "/profile — посмотри, сколько дерьма в тебе осталось\n"
            "/fight — встреться с тем, кто порвёт тебя на куски\n"
            "/heal — продай последнее за здоровье, жалкий червь\n"
            "/lore — перечитать историю своего падения\n"
            "/aura — посмотреть свою ауру\n"
            "/fate — узнать свою судьбу")
    else:
        if user[10] == 0:  # saw_lore = 0
            bot.reply_to(message, LORE_TEXT, parse_mode='Markdown')
            cur.execute("UPDATE users SET saw_lore = 1 WHERE user_id=?", (uid,))
            conn.commit()
        else:
            # Проверяем, не наступила ли концовка
            ending = check_ending(uid)
            if ending:
                bot.send_message(uid, ending)
            else:
                bot.reply_to(message, "Ты снова здесь. Смерть скучает по тебе.")
    conn.close()

# ---------- ЛОР ----------
@bot.message_handler(commands=['lore'])
def lore_cmd(message):
    bot.reply_to(message, LORE_TEXT, parse_mode='Markdown')

# ---------- СУДЬБА ----------
@bot.message_handler(commands=['fate'])
def fate_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    conn.close()
    
    if user[14]:
        bot.reply_to(message, f"Твоя судьба уже решена:\n{ENDINGS[user[14]]['text']}")
    else:
        text = (f"📊 Твоя статистика:\n"
                f"⚔️ Побед: {user[11]}\n"
                f"💀 Смертей: {user[12]}\n"
                f"👹 Убито демонов: {user[13]}\n"
                f"💰 Золота: {user[5]}\n"
                f"✨ Опыта: {user[6]}\n\n"
                f"Судьба ещё не решена. Сражайся дальше.")
        bot.reply_to(message, text)

# ---------- АУРА ----------
@bot.message_handler(commands=['aura'])
def aura_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT aura FROM users WHERE user_id=?", (uid,))
    aura = cur.fetchone()[0]
    conn.close()
    
    desc = AURAS[aura]['desc']
    bot.reply_to(message, f"🌫️ Твоя аура: *{aura}*\n{desc}", parse_mode='Markdown')

# ---------- ПРОФИЛЬ ----------
@bot.message_handler(commands=['profile'])
def profile_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    conn.close()
    
    if user:
        text = (f"📜 Имя: {user[2]}\n"
                f"🩸 Кровь: {user[3]}/{user[4]}\n"
                f"💰 Золото: {user[5]}\n"
                f"✨ Опыт: {user[6]}\n"
                f"🌫️ Аура: {user[7]}\n"
                f"⚔️ Побед: {user[11]}\n"
                f"💀 Смертей: {user[12]}\n"
                f"👹 Убито демонов: {user[13]}\n\n"
                "Ты ещё жив. Пока.")
    else:
        text = "Сначала /start. Или ты уже мёртв?"
    bot.reply_to(message, text)

# ---------- МЕНЮ БОЯ ----------
def fight_menu(monster_name, monster_hp, player_hp, aura):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("⚔️ Атака", callback_data="fight_attack"),
        InlineKeyboardButton("🔥 Аура", callback_data="fight_aura"),
        InlineKeyboardButton("💥 Комбо", callback_data="fight_combo"),
        InlineKeyboardButton("🧪 Зелье", callback_data="fight_potion"),
        InlineKeyboardButton("🏃 Сбежать", callback_data="fight_run")
    )
    return f"👹 *{monster_name}* (HP: {monster_hp})\n❤️ Твоё HP: {player_hp}\n🌫️ Аура: {aura}", markup

# ---------- МЕНЮ АТАК ----------
def attack_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🗡️ Обычный", callback_data="attack_normal"),
        InlineKeyboardButton("💪 Мощный", callback_data="attack_heavy"),
        InlineKeyboardButton("🌀 Рассекающий", callback_data="attack_sweep"),
        InlineKeyboardButton("🔪 Кровоточащий", callback_data="attack_bleed"),
        InlineKeyboardButton("🔙 Назад", callback_data="fight_back")
    )
    return "Выбери тип атаки:", markup

# ---------- НАЧАЛО БОЯ ----------
@bot.message_handler(commands=['fight'])
def fight_start(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    
    if not user:
        bot.reply_to(message, "Мёртвые не сражаются. /start")
        conn.close()
        return
    
    # Выбираем монстра
    monster_name = random.choice(list(MONSTERS.keys()))
    monster = MONSTERS[monster_name].copy()
    monster['hp'] = monster['hp'] + random.randint(-5, 5)
    monster['current_hp'] = monster['hp']
    
    # Сохраняем состояние боя
    cur.execute('''
        UPDATE users SET 
        combo_count=0, 
        last_action='' 
        WHERE user_id=?
    ''', (uid,))
    conn.commit()
    conn.close()
    
    # Сохраняем монстра в памяти (в реальном проекте лучше в БД)
    # Для простоты будем хранить в словаре (в памяти)
    # В Render это не сработает, нужно хранить в БД, но для начала сойдёт
    global fight_state
    if 'fight_state' not in globals():
        fight_state = {}
    fight_state[uid] = {
        'monster': monster,
        'monster_name': monster_name,
        'monster_hp': monster['current_hp'],
        'monster_max_hp': monster['hp'],
        'player_hp': user[3]
    }
    
    text, markup = fight_menu(monster_name, monster['current_hp'], user[3], user[7])
    bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)

# ---------- ОБРАБОТКА КНОПОК ----------
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    uid = call.from_user.id
    data = call.data
    
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    
    if data == "fight_attack":
        text, markup = attack_menu()
        bot.edit_message_text(text, uid, call.message.message_id, reply_markup=markup)
    
    elif data == "fight_back":
        # Возврат в главное меню боя
        if uid in fight_state:
            text, markup = fight_menu(
                fight_state[uid]['monster_name'],
                fight_state[uid]['monster_hp'],
                fight_state[uid]['player_hp'],
                user[7]
            )
            bot.edit_message_text(text, uid, call.message.message_id, parse_mode='Markdown', reply_markup=markup)
    
    elif data.startswith("attack_"):
        attack_type = data.replace("attack_", "")
        
        if uid not in fight_state:
            bot.answer_callback_query(call.id, "Бой не найден!")
            return
        
        monster = fight_state[uid]
        monster_name = monster['monster_name']
        monster_hp = monster['monster_hp']
        player_hp = monster['player_hp']
        
        # Базовая атака
        base_dmg = random.randint(5, 12)
        
        # Модификаторы от атаки
        if attack_type == "heavy":
            base_dmg = int(base_dmg * 1.5)
            attack_text = "💪 Мощный замах"
        elif attack_type == "sweep":
            base_dmg = int(base_dmg * 1.2)
            attack_text = "🌀 Рассекающий удар"
        elif attack_type == "bleed":
            base_dmg = int(base_dmg * 0.8)
            attack_text = "🔪 Кровоточащий (кровотечение)"
        else:
            attack_text = "🗡️ Обычный удар"
        
        # Проверка комбо
        combo_mult = 1.0
        combo_text = ""
        last_action = user[9]
        combo_count = user[8]
        
        combo_key = (last_action, attack_type)
        if combo_key in COMBOS:
            combo = COMBOS[combo_key]
            combo_mult = combo['dmg_mult']
            combo_text = f"\n💥 *КОМБО*: {combo['name']}!\n{combo['text']}"
            cur.execute("UPDATE users SET combo_count = combo_count + 1, last_action='' WHERE user_id=?", (uid,))
        else:
            cur.execute("UPDATE users SET last_action=? WHERE user_id=?", (attack_type, uid))
        
        # Расчёт урона
        damage = int(base_dmg * combo_mult)
        monster_hp -= damage
        
        # Атака монстра
        monster_attack = random.choice(MONSTERS[monster_name]['attacks'])
        monster_dmg = MONSTERS[monster_name]['dmg'] + random.randint(-2, 2)
        
        # Уклонение от ауры
        if user[7] == 'Мгла' and random.random() < 0.2:
            monster_dmg = 0
            dodge_text = "\n🌫️ Ты уклоняешься от атаки!"
        else:
            dodge_text = ""
        
        player_hp -= monster_dmg
        
        result = (f"{attack_text}: {damage} урона{combo_text}\n"
                  f"👹 {monster_name} использует *{monster_attack}* и наносит {monster_dmg} урона{dodge_text}")
        
        # Проверка смерти монстра
        if monster_hp <= 0:
            reward_gold = random.randint(5, 20)
            reward_exp = 10
            cur.execute('''
                UPDATE users SET 
                gold = gold + ?,
                exp = exp + ?,
                hp = ?,
                wins = wins + 1,
                demon_kills = demon_kills + 1
                WHERE user_id=?
            ''', (reward_gold, reward_exp, player_hp, uid))
            conn.commit()
            
            result += f"\n💀 Монстр повержен! +{reward_gold}💰 +{reward_exp}✨"
            bot.edit_message_text(result, uid, call.message.message_id)
            del fight_state[uid]
            
            # Проверка концовки
            ending = check_ending(uid)
            if ending:
                bot.send_message(uid, ending)
        
        # Проверка смерти игрока
        elif player_hp <= 0:
            cur.execute('''
                UPDATE users SET 
                hp = max_hp,
                gold = gold - 5,
                deaths = deaths + 1
                WHERE user_id=?
            ''', (uid,))
            conn.commit()
            
            result += f"\n💔 Ты погиб... Воскрес в таверне (-5💰)"
            bot.edit_message_text(result, uid, call.message.message_id)
            del fight_state[uid]
            
            # Проверка концовки
            ending = check_ending(uid)
            if ending:
                bot.send_message(uid, ending)
        
        else:
            # Обновляем состояние
            cur.execute("UPDATE users SET hp=? WHERE user_id=?", (player_hp, uid))
            conn.commit()
            fight_state[uid]['monster_hp'] = monster_hp
            fight_state[uid]['player_hp'] = player_hp
            
            result += f"\n\n{monster_name} ❤️ {monster_hp}\nТвоё ❤️ {player_hp}"
            text, markup = fight_menu(monster_name, monster_hp, player_hp, user[7])
            bot.edit_message_text(result + "\n\nПродолжаем бой:", uid, call.message.message_id)
            bot.send_message(uid, text, parse_mode='Markdown', reply_markup=markup)
    
    elif data == "fight_run":
        if uid in fight_state:
            del fight_state[uid]
        bot.edit_message_text("🏃 Ты сбежал. Трус.", uid, call.message.message_id)
    
    conn.close()

# ---------- ЛЕЧЕНИЕ ----------
@bot.message_handler(commands=['heal'])
def heal_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    
    if user and user[3] < user[4] and user[5] >= 10:
        cur.execute("UPDATE users SET hp = max_hp, gold = gold - 10 WHERE user_id=?", (uid,))
        conn.commit()
        bot.reply_to(message,
            "🩸 Ты жалко протягиваешь руку к алтарю.\n"
            "Тьма жрёт твоё золото и нехотя зализывает раны.\n"
            "-10💰 (дешевле, чем гроб)\n"
            "❤️ Здоровье восстановлено. Радуйся, пока можешь.")
    else:
        bot.reply_to(message,
            "❌ Недостаточно золота, нищеброд.\n"
            "Иди в бой и умри, как мужчина.")
    conn.close()

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    while True:
        try:
            print("🖤 Бот запущен. Мрак приветствует тебя.")
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"💀 Бот упал: {e}. Перезапуск через 5 секунд...")
            time.sleep(5)
