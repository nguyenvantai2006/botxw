import telebot
import mysql.connector
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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
        'ask_code': "Vui lòng nhập code XWorld bạn muốn chia sẻ:",
        'thanks': "✅ Cảm ơn bạn! Code đã được ghi nhận và đang chờ Admin duyệt."
    },
    'id': {
        'welcome': "Selamat datang di Stasiun Kode XWorld!\nApa yang ingin Anda lakukan hari ini?",
        'btn_get': "🎁 Dapatkan Kode XWorld",
        'btn_send': "📤 Kirim Kode",
        'empty_codes': "Stok kode sedang kosong. Silakan kembali lagi nanti!",
        'here_are_codes': "Ini kode XWorld keren Anda (ketuk untuk menyalin):\n\n",
        'ask_code': "Silakan masukkan kode XWorld yang ingin Anda bagikan:",
        'thanks': "✅ Terima kasih! Kode telah dicatat dan menunggu persetujuan Admin."
    }
}

# Biến lưu trữ ngôn ngữ tạm thời của người dùng (Mặc định là 'vi')
user_langs = {}

# Hàm kết nối Database
# Hàm kết nối Database (Đã lên Cloud Aiven)
def get_db():
    return mysql.connector.connect(
        host="mysql-17c9d10f-vantai20102006-20d3.h.aivencloud.com", # Copy ở dòng Host
        port=22942,                                                  # Copy ở dòng Port
        user="avnadmin",                                             # Copy ở dòng User
        password="AVNS_OpoLnQKnRraW_SOz0MB",                                 # Bấm vào biểu tượng con mắt ở dòng Password để xem và chép vào đây
        database="defaultdb"                                         # Copy ở dòng Database name
    )

# ----------------- GIAO DIỆN NGƯỜI DÙNG -----------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Bước 1: Hiển thị bảng chọn ngôn ngữ
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
    
    # XỬ LÝ KHI NGƯỜI DÙNG BẤM CHỌN NGÔN NGỮ
    if call.data.startswith("lang_"):
        # Lấy ra đuôi 'vi' hoặc 'id' từ callback_data
        lang_code = call.data.split("_")[1] 
        user_langs[user_id] = lang_code # Lưu vào bộ nhớ
        
        # Đổi tin nhắn chọn ngôn ngữ thành Menu chính
        markup = InlineKeyboardMarkup()
        markup.row_width = 2
        markup.add(
            InlineKeyboardButton(TEXTS[lang_code]['btn_get'], callback_data="get_code"),
            InlineKeyboardButton(TEXTS[lang_code]['btn_send'], callback_data="send_code")
        )
        bot.edit_message_text(TEXTS[lang_code]['welcome'], call.message.chat.id, call.message.message_id, reply_markup=markup)
        return

    # Xác định ngôn ngữ của người dùng đang bấm (nếu chưa chọn thì mặc định là tiếng Việt)
    lang = user_langs.get(user_id, 'vi')

    # XỬ LÝ MENU CHÍNH
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
    lang = user_langs.get(user_id, 'vi') # Lấy ngôn ngữ để reply cho chuẩn
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO gift_codes (code, user_id) VALUES (%s, %s)", (user_code, user_id))
    db.commit()
    db.close()
    
    bot.reply_to(message, TEXTS[lang]['thanks'])
    
    # Thông báo cho Admin (Vẫn giữ nguyên tiếng Việt cho bạn dễ đọc)
    bot.send_message(ADMIN_ID, f"🔔 Có code mới chờ duyệt!\nNgười gửi (ID): {user_id}\nCode: `{user_code}`", parse_mode='Markdown')


# ----------------- TÍNH NĂNG QUẢN TRỊ VIÊN (ADMIN) -----------------
# (Khu vực này mình không dịch vì chỉ có bạn - Admin dùng)

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
            bot.reply_to(message, f"⚠️ Không tìm thấy code nào có ID: {code_id} trong kho.")
            
        db.close()
        
    except IndexError:
        bot.reply_to(message, "⚠️ Cú pháp sai! Hãy gõ: /delete <ID_của_code> (hoặc /del <ID>)")
    except Exception as e:
        bot.reply_to(message, f"Lỗi: {e}")

# Kích hoạt bot
print("🚀 Bot đang chạy...")
# --- ĐOẠN CODE LÁCH LUẬT RENDER (TẠO WEB GIẢ) ---
from flask import Flask
import threading
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "🚀 Trạm Code XWorld đang hoạt động 24/7!"

def run_web():
    # Render sẽ tự cấp Port, mình lấy Port đó để chạy web
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# Chạy trang web giả trên một luồng (thread) chạy ngầm
threading.Thread(target=run_web).start()

# Kích hoạt bot Telegram chạy song song
print("🚀 Bot đang chạy...")
bot.infinity_polling()