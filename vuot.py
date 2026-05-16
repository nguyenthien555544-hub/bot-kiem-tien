import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import random
import string
import sqlite3
import time
import os
from datetime import datetime
from flask import Flask
import threading

# ================= CẤU HÌNH BOT & API =================
BOT_TOKEN = "8803256348:AAH58katT66W1DrHvw445OTKv2rLGgh88r4"
ADMIN_ID = "8781909366" 

# UPTOLINK
API_UPTOLINK = "2f2a6f9894f02956c31f64fa2387a4d67cc36658"
TIEN_UPTO = 300
MAX_UPTO = 200

# LAYMA
API_LAYMA = "cfec12fecc530c92aa640fa0e68d10a7"
TIEN_LAYMA = 700
MAX_LAYMA = 2

HOA_HONG_REF = 50       
MIN_RUT = 10000

bot = telebot.TeleBot(BOT_TOKEN)

# ================= DATABASE =================
conn = sqlite3.connect('bot_upto_master.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER, total_tasks INTEGER DEFAULT 0, ref_by INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, user_id INTEGER, status TEXT, reward INTEGER, answer INTEGER, time_created REAL, date_str TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')

# Tự động thêm cột task_type nếu chưa có (Chống lỗi Database cũ)
try:
    cursor.execute("ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'uptolink'")
    conn.commit()
except:
    pass

cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bao_tri', 'off')")
conn.commit()

# ================= SERVER WEB RENDER (DASHBOARD ADMIN) =================
app = Flask('')

@app.route('/')
def home():
    cursor.execute("SELECT user_id, balance, total_tasks, ref_by FROM users ORDER BY total_tasks DESC")
    users = cursor.fetchall()
    
    html = """
    <html>
    <head>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>Trạm Quản Lý Bot</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; color: #fff; padding: 20px; }
            h2 { color: #e94560; text-align: center; }
            .container { max-width: 800px; margin: 0 auto; background: #16213e; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border: 1px solid #0f3460; padding: 12px; text-align: center; }
            th { background: #e94560; color: white; }
            tr:nth-child(even) { background-color: #1a1a2e; }
            .badge { background: #4caf50; padding: 5px 10px; border-radius: 5px; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class='container'>
            <h2>🚀 BẢNG THỐNG KÊ DÂN CÀY 🚀</h2>
            <p style='text-align:center;'>Hệ thống hoạt động 24/7 siêu mượt!</p>
            <table>
                <tr><th>ID Telegram</th><th>Số Dư (VNĐ)</th><th>Tổng Link</th><th>Người Mời</th></tr>
    """
    for u in users:
        html += f"<tr><td>{u[0]}</td><td style='color:#4caf50; font-weight:bold;'>{u[1]:,}đ</td><td><span class='badge'>{u[2]}</span></td><td>{u[3] if u[3] else 'Không'}</td></tr>"
    html += """
            </table>
        </div>
    </body>
    </html>
    """
    return html

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.start()

# ================= HỆ THỐNG KIỂM TRA BẢO TRÌ =================
def check_bao_tri():
    cursor.execute("SELECT value FROM settings WHERE key='bao_tri'")
    res = cursor.fetchone()
    return True if res and res[0] == 'on' else False

def is_maintenance(uid):
    return check_bao_tri() and str(uid) != ADMIN_ID

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# ================= GIAO DIỆN NÚT BẤM =================
def menu_chinh():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🚀 NGUỒN NHIỆM VỤ 🚀"))
    markup.row(KeyboardButton("👤 Thông Tin Acc"), KeyboardButton("💳 Rút Lúa"))
    markup.row(KeyboardButton("🎧 Trợ Giúp"), KeyboardButton("👥 Đại Lý (Mời Bạn)"))
    return markup

def menu_chon_nhiem_vu(uid):
    today = get_today_str()
    # Đếm số task Uptolink
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='uptolink'", (uid, today))
    count_upto = cursor.fetchone()[0]
    # Đếm số task Layma
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='layma'", (uid, today))
    count_layma = cursor.fetchone()[0]

    markup = InlineKeyboardMarkup()
    
    # Nút Layma (Đắt tiền)
    if count_layma < MAX_LAYMA:
        markup.row(InlineKeyboardButton(f"🔥 Lấy Mã SEO (+{TIEN_LAYMA}đ) [{count_layma}/{MAX_LAYMA}]", callback_data="get_layma"))
    else:
        markup.row(InlineKeyboardButton(f"🔥 Lấy Mã SEO (Hết lượt hôm nay)", callback_data="limit_reached"))

    # Nút Uptolink
    if count_upto < MAX_UPTO:
        markup.row(InlineKeyboardButton(f"🔗 Vượt Uptolink (+{TIEN_UPTO}đ) [{count_upto}/{MAX_UPTO}]", callback_data="get_uptolink"))
    else:
        markup.row(InlineKeyboardButton(f"🔗 Uptolink (Hết lượt hôm nay)", callback_data="limit_reached"))
        
    return markup

# ================= LỆNH ADMIN CONTROL =================
@bot.message_handler(commands=['tb', 'baotri'])
def admin_commands(message):
    user_id = str(message.chat.id)
    if user_id != ADMIN_ID: return
        
    cmd = message.text.split()[0]
    
    if cmd == '/tb':
        noidung = message.text.replace('/tb ', '').strip()
        if not noidung: return bot.send_message(user_id, "⚠️ Dùng: `/tb [nội dung]`")
            
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        tc = 0
        for u in users:
            try:
                bot.send_message(u[0], f"📢 *THÔNG BÁO TỪ ADMIN:*\n\n{noidung}", parse_mode="Markdown")
                tc += 1
            except: pass
        bot.send_message(user_id, f"✅ Đã bắn thông báo cho {tc} ae.")

    elif cmd == '/baotri':
        parts = message.text.split()
        if len(parts) > 1 and parts[1] in ['on', 'off']:
            cursor.execute("UPDATE settings SET value=? WHERE key='bao_tri'", (parts[1],))
            conn.commit()
            if parts[1] == 'on': bot.send_message(user_id, "🛠 **BẬT** bảo trì thành công.")
            else: bot.send_message(user_id, "✅ **TẮT** bảo trì thành công.")
        else:
            bot.send_message(user_id, "⚠️ Dùng: `/baotri on` hoặc `/baotri off`")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_duyet_tien(call):
    if str(call.message.chat.id) != ADMIN_ID: return
    parts = call.data.split('_')
    action, target_uid, amount = parts[1], int(parts[2]), int(parts[3])
    
    if action == 'duyet':
        bot.edit_message_text(f"{call.message.text}\n\n✅ **ĐÃ CHUYỂN TIỀN**", chat_id=ADMIN_ID, message_id=call.message.message_id)
        try: bot.send_message(target_uid, f"🎉 *TINH TINH!*\nLúa `{amount}đ` đã được Bank về ví của bạn. Cảm ơn đã cày cuốc!", parse_mode="Markdown")
        except: pass
    elif action == 'huy':
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_uid))
        conn.commit()
        bot.edit_message_text(f"{call.message.text}\n\n❌ **ĐÃ TỪ CHỐI & HOÀN TIỀN**", chat_id=ADMIN_ID, message_id=call.message.message_id)
        try: bot.send_message(target_uid, f"⚠️ Đơn rút `{amount}đ` bị HỦY (Sai STK hoặc gian lận). Tiền đã trả lại vào Bot.", parse_mode="Markdown")
        except: pass

# ================= XỬ LÝ LỆNH /START & CỘNG TIỀN =================
@bot.message_handler(commands=['start'])
def xu_ly_start(message):
    uid = message.chat.id
    if is_maintenance(uid):
        return bot.send_message(uid, "🚧 *HỆ THỐNG ĐANG BẢO TRÌ!* 🚧\n\nAdmin đang nâng cấp thêm tính năng mới, anh em vui lòng quay lại sau ít phút nhé!", parse_mode="Markdown")

    text = message.text
    parts = text.split()
    
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not cursor.fetchone():
        ref_id = None
        if len(parts) > 1 and parts[1].startswith('ref'):
            ref_id = parts[1].replace('ref', '')
            if str(ref_id) == str(uid): ref_id = None
        cursor.execute("INSERT INTO users (user_id, balance, total_tasks, ref_by) VALUES (?, 0, 0, ?)", (uid, ref_id))
        conn.commit()

    if len(parts) > 1 and parts[1].startswith('task'):
        task_id = parts[1]
        cursor.execute("SELECT status, user_id, reward, task_type FROM tasks WHERE task_id=?", (task_id,))
        task = cursor.fetchone()
        
        if task and task[0] == 'pending' and task[1] == uid:
            reward = task[2]
            t_type = task[3]
            
            # --- NẾU LÀ LAYMA: BẮT GIẢI TOÁN ---
            if t_type == 'layma':
                dau = random.choice(['+', '-'])
                if dau == '+':
                    a, b = random.randint(10, 30), random.randint(1, 20)
                    ans = a + b
                else:
                    a, b = random.randint(20, 50), random.randint(1, 19)
                    ans = a - b
                    
                cursor.execute("UPDATE tasks SET status='verifying', answer=?, time_created=? WHERE task_id=?", (ans, time.time(), task_id))
                conn.commit()
                
                msg_toan = (
                    "🛡️ *HỆ THỐNG XÁC MINH CHỐNG BOT* 🛡️\n"
                    "╔══════════════════════╗\n"
                    f"  🎁 Bạn vừa nhận: `+{reward}đ`\n"
                    "╚══════════════════════╝\n"
                    "👉 *Giải phép toán sau (Bạn có 60s):*\n\n"
                    f"🧮 ⟨  `{a} {dau} {b} = ?`  ⟩\n\n"
                    "_(Gõ đáp án bằng số gửi vào đây)_"
                )
                bot.send_message(uid, msg_toan, parse_mode="Markdown")
            
            # --- NẾU LÀ UPTOLINK: CỘNG THẲNG LÚA ---
            elif t_type == 'uptolink':
                cursor.execute("UPDATE users SET balance = balance + ?, total_tasks = total_tasks + 1 WHERE user_id=?", (reward, uid))
                cursor.execute("UPDATE tasks SET status='completed' WHERE task_id=?", (task_id,))
                
                # Trả hoa hồng ref
                cursor.execute("SELECT ref_by FROM users WHERE user_id=?", (uid,))
                ref_id = cursor.fetchone()[0]
                if ref_id:
                    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (HOA_HONG_REF, ref_id))
                    try: bot.send_message(ref_id, f"💸 *TING TING:* Cấp dưới vừa cày, bạn nhận `+{HOA_HONG_REF}đ` hoa hồng!", parse_mode="Markdown")
                    except: pass
                conn.commit()
                
                msg_ok = (
                    "⚡️ *NHIỆM VỤ HOÀN TẤT* ⚡️\n"
                    "╔═══════════════════╗\n"
                    f"  💵 Lúa về ví: `+{reward}đ`\n"
                    "╚═══════════════════╝\n"
                    "👉 Bấm *🚀 NGUỒN NHIỆM VỤ* để bào tiếp!"
                )
                bot.send_message(uid, msg_ok, parse_mode="Markdown", reply_markup=menu_chinh())

        else:
            bot.send_message(uid, "❌ Link nhiệm vụ không đúng hoặc đã hết hạn.")
    else:
        intro = (
            "👑 *CHÀO MỪNG ĐẾN VỚI HỆ THỐNG KIẾM TIỀN VIP* 👑\n\n"
            "💰 *Thu nhập thụ động - Rút tiền mỗi ngày*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🚀 *Quy trình lụm lúa:*\n"
            "1️⃣ Chọn nút *🚀 NGUỒN NHIỆM VỤ*.\n"
            "2️⃣ Lấy link đem ra Chrome vượt.\n"
            "3️⃣ Tiền auto nhảy vào ví.\n\n"
            f"💳 *Hỗ trợ:* Min rút chỉ từ `{MIN_RUT}đ`."
        )
        bot.send_message(uid, intro, parse_mode="Markdown", reply_markup=menu_chinh())

# ================= TOÁN CỦA LAYMA =================
@bot.message_handler(func=lambda m: m.text.strip().replace('-', '').isdigit())
def kiem_tra_toan(message):
    uid = message.chat.id
    if is_maintenance(uid): return bot.send_message(uid, "🚧 *HỆ THỐNG ĐANG BẢO TRÌ!* 🚧", parse_mode="Markdown")
    
    val = int(message.text)
    cursor.execute("SELECT task_id, answer, reward, time_created FROM tasks WHERE user_id=? AND status='verifying'", (uid,))
    data = cursor.fetchone()
    
    if data:
        tid, correct, rw, t_create = data
        if time.time() - t_create > 60:
            bot.send_message(uid, "⏰ Quá 60 giây! Mã đã hủy.")
            cursor.execute("UPDATE tasks SET status='expired' WHERE task_id=?", (tid,))
            conn.commit()
            return

        if val == correct:
            cursor.execute("UPDATE users SET balance = balance + ?, total_tasks = total_tasks + 1 WHERE user_id=?", (rw, uid))
            cursor.execute("UPDATE tasks SET status='completed' WHERE task_id=?", (tid,))
            
            cursor.execute("SELECT ref_by FROM users WHERE user_id=?", (uid,))
            ref_id = cursor.fetchone()[0]
            if ref_id:
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (HOA_HONG_REF, ref_id))
                try: bot.send_message(ref_id, f"💸 *TING TING:* Nhận `+{HOA_HONG_REF}đ` hoa hồng!", parse_mode="Markdown")
                except: pass
            conn.commit()
            
            msg_ok = (
                "🎊 *VƯỢT CAPTCHA XUẤT SẮC* 🎊\n"
                "╔═══════════════════╗\n"
                f"  💵 Lúa về ví: `+{rw}đ`\n"
                "╚═══════════════════╝\n"
                "👉 Tiếp tục cày thâu đêm nào!"
            )
            bot.send_message(uid, msg_ok, parse_mode="Markdown", reply_markup=menu_chinh())
        else:
            bot.send_message(uid, "❌ Sai bét rồi ông thần! Nhận nhiệm vụ mới đi.")
            cursor.execute("UPDATE tasks SET status='failed' WHERE task_id=?", (tid,))
            conn.commit()

# ================= MENU CHỨC NĂNG CHÍNH =================
@bot.message_handler(func=lambda m: m.text in ["🚀 NGUỒN NHIỆM VỤ 🚀", "🎧 Trợ Giúp", "👤 Thông Tin Acc", "👥 Đại Lý (Mời Bạn)", "💳 Rút Lúa"])
def handle_menu(message):
    uid = message.chat.id
    if is_maintenance(uid):
        return bot.send_message(uid, "🚧 *HỆ THỐNG ĐANG BẢO TRÌ!* Admin đang thêm tính năng, quay lại sau nha anh em!", parse_mode="Markdown")

    cmd = message.text

    if cmd == "🚀 NGUỒN NHIỆM VỤ 🚀":
        cursor.execute("SELECT task_id FROM tasks WHERE user_id=? AND status='verifying'", (uid,))
        if cursor.fetchone():
            return bot.send_message(uid, "⚠️ Bạn đang có một phép tính chưa giải xong kìa!")
            
        msg_hd = (
            "💎 *TRUNG TÂM KIẾM TIỀN VIP* 💎\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👇 *Vui lòng chọn 1 nguồn bên dưới để làm:* \n\n"
            f"🔥 **Layma (Mã SEO):** {TIEN_LAYMA}đ/link (Giới hạn {MAX_LAYMA}/ngày)\n"
            f"🔗 **Uptolink:** {TIEN_UPTO}đ/link (Giới hạn {MAX_UPTO}/ngày)"
        )
        bot.send_message(uid, msg_hd, parse_mode="Markdown", reply_markup=menu_chon_nhiem_vu(uid))
    
    elif cmd == "🎧 Trợ Giúp":
        ht = (
            "🛡️ *TỔNG ĐÀI HỖ TRỢ* 🛡️\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👤 Admin xử lý Bank: @vanminh2826\n"
            "👥 Group AE Cày Cuốc: https://t.me/botkiemlua"
        )
        bot.send_message(uid, ht, disable_web_page_preview=True, parse_mode="Markdown")

    elif cmd == "👤 Thông Tin Acc":
        cursor.execute("SELECT balance, total_tasks FROM users WHERE user_id=?", (uid,))
        d = cursor.fetchone()
        info = (
            "👤 *HỒ SƠ CỦA BẠN* 👤\n"
            "╔═══════════════════╗\n"
            f" 🆔 ID: `{uid}`\n"
            f" 💵 Số Dư: `{d[0]}đ`\n"
            f" 🎯 Đã vượt: `{d[1]} link`\n"
            "╚═══════════════════╝"
        )
        bot.send_message(uid, info, parse_mode="Markdown")

    elif cmd == "👥 Đại Lý (Mời Bạn)":
        link_ref = f"https://t.me/{bot.get_me().username}?start=ref{uid}"
        ref = (
            "🤝 *KIẾM TIỀN THỤ ĐỘNG* 🤝\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🎁 Nhận ngay `{HOA_HONG_REF}đ` khi bạn bè vượt thành công 1 link.\n\n"
            f"🔗 *Link mời của bạn:*\n`{link_ref}`"
        )
        bot.send_message(uid, ref, parse_mode="Markdown")

    elif cmd == "💳 Rút Lúa":
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        bal = cursor.fetchone()[0]
        if bal >= MIN_RUT:
            rut = (
                "🏦 *LÊN ĐƠN RÚT LÚA* 🏦\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💰 Có thể rút: `{bal}đ`\n\n"
                "✍️ *Nhập STK theo mẫu:*\n"
                "`NGÂN HÀNG - SỐ TK - TÊN CHỦ TK - SỐ TIỀN`"
            )
            m = bot.send_message(uid, rut, parse_mode="Markdown")
            bot.register_next_step_handler(m, process_withdraw, bal)
        else:
            bot.send_message(uid, f"⚠️ Số dư: `{bal}đ`. Phải đủ `{MIN_RUT}đ` mới rút được nhé ae!", parse_mode="Markdown")

# ================= TẠO LINK (UPTOLINK & LAYMA) =================
@bot.callback_query_handler(func=lambda call: call.data in ["get_uptolink", "get_layma", "limit_reached"])
def make_link(call):
    uid = call.message.chat.id
    if is_maintenance(uid): return bot.answer_callback_query(call.id, "🚧 HỆ THỐNG ĐANG BẢO TRÌ!", show_alert=True)
    
    if call.data == "limit_reached":
        return bot.answer_callback_query(call.id, "⚠️ Web này hôm nay đã cày max giới hạn rồi ông ơi!", show_alert=True)

    bot.edit_message_text("⏳ Đang cào link mới...", chat_id=uid, message_id=call.message.message_id)
    
    tid = 'task_' + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    target = f"https://telegram.me/{bot.get_me().username}?start={tid}"
    today = get_today_str()
    short_url = None

    try:
        if call.data == "get_uptolink":
            res = requests.get("https://uptolink.one/api", params={"api": API_UPTOLINK, "url": target}).json()
            short_url = res.get("shortenedUrl") if res.get("status") == "success" else None
            if short_url:
                cursor.execute("INSERT INTO tasks (task_id, user_id, task_type, status, reward, date_str) VALUES (?, ?, 'uptolink', 'pending', ?, ?)", (tid, uid, TIEN_UPTO, today))
                conn.commit()
                bot.send_message(uid, f"🔗 *UPTOLINK (+{TIEN_UPTO}đ):*\n`{short_url}`\n\n_(Vượt xong auto nhận tiền)_", parse_mode="Markdown")
                
        elif call.data == "get_layma":
            res = requests.get("https://api.layma.net/api/admin/shortlink/quicklink", params={"tokenUser": API_LAYMA, "url": target, "format": "json"}).json()
            short_url = res.get("html") if res.get("success") else None
            if short_url:
                cursor.execute("INSERT INTO tasks (task_id, user_id, task_type, status, reward, date_str) VALUES (?, ?, 'layma', 'pending', ?, ?)", (tid, uid, TIEN_LAYMA, today))
                conn.commit()
                bot.send_message(uid, f"🔥 *LAYMA SEO (+{TIEN_LAYMA}đ):*\n`{short_url}`\n\n_(Vượt xong quay lại giải toán lấy tiền)_", parse_mode="Markdown")

        if not short_url: bot.send_message(uid, "❌ API Web đang bận, nhấp lại nút đi ông.")
    except:
        bot.send_message(uid, "❌ Lỗi mạng máy chủ.")

# ================= RÚT TIỀN =================
def process_withdraw(message, max_amount):
    uid = message.chat.id
    stk_info = message.text
    bot.send_message(uid, "✅ *BILL ĐÃ LÊN!* Chờ Admin duyệt tiền nhé.", parse_mode="Markdown", reply_markup=menu_chinh())
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id=?", (uid,))
    conn.commit()
    
    if ADMIN_ID:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ Duyệt Lúa", callback_data=f"admin_duyet_{uid}_{max_amount}"), InlineKeyboardButton("❌ Hủy Đơn", callback_data=f"admin_huy_{uid}_{max_amount}"))
        try: bot.send_message(ADMIN_ID, f"🚨 *RÚT TIỀN*\nID: `{uid}`\nTiền: `{max_amount}đ`\nSTK:\n`{stk_info}`", parse_mode="Markdown", reply_markup=markup)
        except: pass

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
