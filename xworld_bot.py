import os
import threading
import telebot
import mysql.connector
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# 1. CẤU HÌNH THÔNG TIN
TOKEN = '8852529291:AAFkf8zsbrNYupS0euCYjwewpQrOD0dy59o'
ADMIN_ID = 6765343155  # Điền số ID của bạn vào đây (không có ngoặc kép)
bot = telebot.TeleBot(TOKEN)

# 2. BỘ TỪ ĐIỂN ĐA NGÔN NGỮ (VI & ID)
TEXTS = {
    'vi': {
        'welcome': "Chào mừng đến với Trạm Code XWorld!\nBạn muốn làm gì hôm nay?",
        'btn_get': "🎁 Nhận Code XWorld",
        'btn_send': "📤 Gửi Code",
        'empty_codes': "Tạm thời kho code đang trống. Bạn hãy quay lại sau nhé!",
        'here_are_codes': "Code XWorld xịn xò của bạn đây (chạm để copy):\n\n",
        'ask_code': "Vui lòng nhập code XWorld muốn chia sẻ:",
        'thanks': "✅ Cảm ơn bạn! Code đã được ghi nhận và đang chờ Admin duyệt."
    },
    'id': {
        'welcome': "Selamat datang di Stasiun Kode XWorld!\nApa yang ingin Anda lakukan hari ini?",
        'btn_get': "🎁 Dapatkan Kode XWorld",
        'btn_send': "📤 Kirim Kode",
        'empty_codes': "Stok kode sedang kosong. Silakan kembali lagi nanti!",
        'here_are_codes': "Ini kode XWorld keren Anda (ketuk untuk menyalin):\n\n",
        'ask_code': "Silakan masukkan kode XWorld yang ingin Anda bagikan:",
        'thanks': "✅ Terima kasih! Kode telah dicatat và menunggu persetujuan Admin."
    }
}

# Biến lưu trữ ngôn ngữ tạm thời của người dùng (Mặc định là 'vi')
user_langs = {}

# Hàm kết nối Database (Đã lên Cloud Aiven)
def get_db():
    return mysql.connector.connect(
        host="mysql-17c9d10f-vantai20102006-20d3.h.aivencloud.com",
        port=22942,
        user="avnadmin",
        password="AVNS_OpoLnQKnRraW_SOz0MB",
        database="defaultdb"
    )

# ----------------- GIAO DIỆN NGƯỜI DÙNG -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        InlineKeyboardButton("🇻🇳 Tiếng Việt", callback_data="lang_vi"),
        InlineKeyboardButton("🇮🇩 Indonesia", callback_data="lang_id")
    )
    bot.reply_to(message, "Please select your language / Vui lòng chọn ngôn ngữ:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    
    if call.data.startswith("lang_"):
        lang_code = call.data.split("_")[1] 
        user_langs[user_id] = lang_code 
        
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton(TEXTS[lang_code]['btn_get'], callback_data="get_code"),
            InlineKeyboardButton(TEXTS[lang_code]['btn_send'], callback_data="send_code")
        )
        bot.edit_message_text(TEXTS[lang_code]['welcome'], call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    lang = user_langs.get(user_id, 'vi')

    if call.data == "get_code":
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT code FROM gift_codes WHERE status = 'approved'")
        codes = cursor.fetchall()
        db.close()
        
        if codes:
            code_text = "\n".join([f"🔥 `{c[0]}`" for c in codes])
            bot.send_message(call.message.chat.id, f"{TEXTS[lang]['here_are_codes']}{code_text}", parse_mode='Markdown')
        else:
            bot.send_message(call.message.chat.id, TEXTS[lang]['empty_codes'])
            
    elif call.data == "send_code":
        msg = bot.send_message(call.message.chat.id, TEXTS[lang]['ask_code'])
        bot.register_next_step_handler(msg, process_code_step)

def process_code_step(message):
    user_code = message.text.strip()
    user_id = message.from_user.id
    lang = user_langs.get(user_id, 'vi')
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO gift_codes (code, user_id) VALUES (%s, %s)", (user_code, user_id))
    db.commit()
    db.close()
    
    bot.reply_to(message, TEXTS[lang]['thanks'])
    bot.send_message(ADMIN_ID, f"🔔 Có code mới chờ duyệt!\nNgười gửi (ID): {user_id}\nCode: `{user_code}`", parse_mode='Markdown')


# ----------------- TÍNH NĂNG QUẢN TRỊ VIÊN (ADMIN) -----------------
@bot.message_handler(commands=['pending'])
def view_pending_codes(message):
    if message.from_user.id != ADMIN_ID:
        return bot.reply_to(message, "⛔ Bạn không có quyền dùng lệnh này!")
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, code FROM gift_codes WHERE status = 'pending'")
    pending_codes = cursor.fetchall()
    db.close()
    
    if pending_codes:
        text = "📋 DANH SÁCH CODE CHỜ DUYỆT:\n\n"
        for code in pending_codes:
            text += f"ID {code[0]} | Code: `{code[1]}`\n"
        text += "\n👉 Dùng lệnh: /approve <ID> để duyệt."
        bot.reply_to(message, text, parse_mode='Markdown')
    else:
        bot.reply_to(message, "Không có code nào đang chờ duyệt!")

@bot.message_handler(commands=['approve'])
def approve_code(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        code_id = message.text.split()[1]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE gift_codes SET status = 'approved' WHERE id = %s", (code_id,))
        db.commit()
        db.close()
        
        bot.reply_to(message, f"✅ Đã duyệt thành công code có ID: {code_id}.")
    except IndexError:
        bot.reply_to(message, "⚠️ Cú pháp sai! Hãy gõ: /approve <ID_của_code>")
    except Exception as e:
        bot.reply_to(message, f"Lỗi: {e}")

@bot.message_handler(commands=['delete', 'del'])
def delete_code(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        code_id = message.text.split()[1]
        db = get_db()
        cursor = db.cursor()
        cursor.execute("DELETE FROM gift_codes WHERE id = %s", (code_id,))
        db.commit()
        
        if cursor.rowcount > 0:
            bot.reply_to(message, f"🗑️ Đã xóa vĩnh viễn code có ID: {code_id} khỏi hệ thống!")
        else:
            bot.reply_to(message, f"⚠️ Không tìm thấy code có ID: {code_id} trong kho.")
            
        db.close()
    except IndexError:
        bot.reply_to(message, "⚠️ Cú pháp sai! Hãy gõ: /delete <ID_của_code>")
    except Exception as e:
        bot.reply_to(message, f"Lỗi: {e}")


# ----------------- KHỞI TẠO WEB GIẢ & CHẠY BOT 24/7 -----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 Trạm Code XWorld đang hoạt động 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Chạy web giả ở background thread
threading.Thread(target=run_web, daemon=True).start()

if __name__ == "__main__":
    while True:
        try:
            print("🚀 Bot đang chạy và sẵn sàng nhận lệnh...")
            bot.infinity_polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"⚠️ Bot bị rớt mạng hoặc lỗi: {e}, đang tự khởi động lại...")