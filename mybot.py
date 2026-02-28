import telebot
import sqlite3
import random

TOKEN = '8781969917:AAExzTzuTzLxn0_kh-HpRCrhKLG0FbmOrr4requirements.txt'
bot = telebot.TeleBot(TOKEN)

# ---------- БД ----------
def init_db():
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            class TEXT,
            hp INTEGER,
            max_hp INTEGER,
            gold INTEGER DEFAULT 0,
            exp INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------- СТАРТ ----------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (user_id, username, class, hp, max_hp, gold, exp) VALUES (?,?,?,?,?,?,?)",
                    (uid, message.from_user.username, "Падший", 20, 20, 0, 0))
        conn.commit()
        bot.reply_to(message, 
            "🕯️ Ты открываешь глаза. Вокруг — сырая земля и запах тлена.\n"
            "Голос в голове шепчет:\n"
            "«Ты умер. Но смерть не приняла тебя.\n"
            "Добро пожаловать в Подземелье, из которого нет выхода.\n"
            "Только кровь. Только сталь. Только боль.»\n\n"
            "/profile — узнать, сколько в тебе ещё жизни\n"
            "/fight — встретить смерть лицом к лицу\n"
            "/heal — продать душу за здоровье")
    else:
        bot.reply_to(message, "Ты снова здесь. Смерть ждёт.")
    conn.close()

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
                f"💰 Цена твоей души: {user[5]}\n"
                f"👁️‍🗨️ Опыт страданий: {user[6]}\n\n"
                "Ты ещё жив. Пока.")
    else:
        text = "Сначала /start. Или ты уже мёртв?"
    bot.reply_to(message, text)

# ---------- БОЙ ----------
@bot.message_handler(commands=['fight'])
def fight_cmd(message):
    uid = message.from_user.id
    conn = sqlite3.connect('game.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    user = cur.fetchone()
    if not user:
        bot.reply_to(message, "Мёртвые не сражаются. /start")
        conn.close()
        return

    monsters = ["Гниющий", "Безликий", "Крикун", "Пожиратель", "Тень"]
    monster_name = random.choice(monsters)
    monster_hp = random.randint(10, 25)
    monster_dmg = random.randint(2, 7)
    player_dmg = random.randint(5, 15)

    monster_hp -= player_dmg
    result = f"⚔️ Ты вонзаешь клинок в {monster_name}. Кровь брызжет во тьму.\n"

    if monster_hp <= 0:
        reward_gold = random.randint(5, 20)
        reward_exp = 10
        cur.execute("UPDATE users SET gold = gold + ?, exp = exp + ? WHERE user_id=?", (reward_gold, reward_exp, uid))
        conn.commit()
        result += (f"💀 {monster_name} падает. Его душа растворяется.\n"
                   f"+{reward_gold} золота (кровь павших)\n"
                   f"+{reward_exp} опыта (твоя боль не напрасна)")
    else:
        user_hp = user[3] - monster_dmg
        if user_hp <= 0:
            user_hp = user[4]
            cur.execute("UPDATE users SET hp = ?, gold = gold - 5 WHERE user_id=?", (user_hp, uid))
            result += (f"👹 {monster_name} разрывает тебя.\n"
                       f"Холод. Темнота. Тишина.\n"
                       f"Ты открываешь глаза у костра в таверне.\n"
                       f"Смерть отпустила тебя... но забрала часть души.\n"
                       f"-5💰")
        else:
            cur.execute("UPDATE users SET hp = ? WHERE user_id=?", (user_hp, uid))
            result += (f"👹 {monster_name} впивается в тебя. Боль пронзает плоть.\n"
                       f"Терпи. Или умри.")
        conn.commit()
    conn.close()
    bot.reply_to(message, result)

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
            "🩸 Ты протягиваешь руку к тёмному алтарю.\n"
            "Жертва принята. Раны затягиваются.\n"
            "Но цена высока...\n"
            "-10💰\n"
            "❤️ Здоровье восстановлено")
    else:
        bot.reply_to(message, "❌ Недостаточно золота. Или ты ещё не достаточно истёк кровью.")
    conn.close()

bot.polling()