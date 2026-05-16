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

# ================= CẤU HÌNH SERVER WEB CHO RENDER =================
app = Flask('')

@app.route('/')
def home():
    return "HT SYSTEM IS RUNNING ULTRA SMOOTH 24/7!"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.start()

# ================= CẤU HÌNH BOT & API =================
BOT_TOKEN = "8803256348:AAH58katT66W1DrHvw445OTKv2rLGgh88r4"
ADMIN_ID = "8781909366" 

API_UPTOLINK = "2f2a6f9894f02956c31f64fa2387a4d67cc36658"
TIEN_UPTO = 300
MAX_UPTO = 200

HOA_HONG_REF = 50       
MIN_RUT = 10000

bot = telebot.TeleBot(BOT_TOKEN)

# ================= DATABASE =================
conn = sqlite3.connect('bot_upto_master.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER, total_tasks INTEGER DEFAULT 0, ref_by INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, user_id INTEGER, status TEXT, reward INTEGER, answer INTEGER, time_created REAL, date_str TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bao_tri', 'off')")
conn.commit()

def check_bao_tri():
    cursor.execute("SELECT value FROM settings WHERE key='bao_tri'")
    res = cursor.fetchone()
    return True if res and res[0] == 'on' else False

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# ================= GIAO DIỆN NÚT BẤM =================
def menu_chinh():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🎯 Nhiệm Vụ"))
    markup.row(KeyboardButton("🎧 Hỗ Trợ"), KeyboardButton("👥 Giới Thiệu"))
    markup.row(KeyboardButton("👤 Acc"), KeyboardButton("💳 Rút Tiền"))
    return markup

def menu_chon_nhiem_vu(uid):
    today = get_today_str()
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed'", (uid, today))
    count_upto = cursor.fetchone()[0]

    markup = InlineKeyboardMarkup()
    if count_upto < MAX_UPTO:
        markup.row(InlineKeyboardButton(f"🔗 Uptolink (+{TIEN_UPTO}đ) [{count_upto}/{MAX_UPTO}]", callback_data="get_uptolink"))
    else:
        markup.row(InlineKeyboardButton(f"🔗 Uptolink (Đã hết {MAX_UPTO} lượt hôm nay)", callback_data="limit_reached"))
    return markup

# ================= LỆNH ADMIN CONTROL =================
@bot.message_handler(commands=['tb', 'baotri'])
def admin_commands(message):
    user_id = str(message.chat.id)
    if user_id != ADMIN_ID: return
        
    cmd = message.text.split()[0]
    
    if cmd == '/tb':
        noidung = message.text.replace('/tb ', '').strip()
        if not noidung or noidung == '/tb':
            bot.send_message(user_id, "⚠️ Cú pháp: `/tb [nội dung]`")
            return
            
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        tc = 0
        for u in users:
            try:
                bot.send_message(u[0], f"📢 **THÔNG BÁO TỪ ADMIN:**\n\n{noidung}", parse_mode="Markdown")
                tc += 1
            except: pass
        bot.send_message(user_id, f"✅ Đã gửi thông báo thành công cho {tc} ae.")

    elif cmd == '/baotri':
        parts = message.text.split()
        if len(parts) > 1 and parts[1] in ['on', 'off']:
            cursor.execute("UPDATE settings SET value=? WHERE key='bao_tri'", (parts[1],))
            conn.commit()
            if parts[1] == 'on': bot.send_message(user_id, "🛠 **BẬT** bảo trì hệ thống thành công.")
            else: bot.send_message(user_id, "✅ **TẮT** bảo trì hệ thống thành công.")
        else:
            bot.send_message(user_id, "⚠️ Cú pháp: `/baotri on` hoặc `/baotri off`")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def admin_duyet_tien(call):
    if str(call.message.chat.id) != ADMIN_ID: return
    parts = call.data.split('_')
    action, target_uid, amount = parts[1], int(parts[2]), int(parts[3])
    
    if action == 'duyet':
        bot.edit_message_text(f"{call.message.text}\n\n✅ **ĐÃ DUYỆT CHUYỂN TIỀN**", chat_id=ADMIN_ID, message_id=call.message.message_id)
        try: bot.send_message(target_uid, f"🎉 **TINH TINH!**\nAdmin đã duyệt đơn và chuyển `{amount}đ` vào tài khoản của bạn. Check ví nhé!", parse_mode="Markdown")
        except: pass
    elif action == 'huy':
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_uid))
        conn.commit()
        bot.edit_message_text(f"{call.message.text}\n\n❌ **ĐÃ TỪ CHỐI & HOÀN TIỀN**", chat_id=ADMIN_ID, message_id=call.message.message_id)
        try: bot.send_message(target_uid, f"⚠️ Đơn rút `{amount}đ` bị từ chối do lỗi thông tin. Tiền đã được hoàn lại vào số dư Bot.", parse_mode="Markdown")
        except: pass

# ================= XỬ LÝ LỆNH /START & XÁC MINH PHÉP TÍNH =================
@bot.message_handler(commands=['start'])
def xu_ly_start(message):
    if check_bao_tri() and str(message.chat.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "🛠 **Hệ thống đang bảo trì để nâng cấp.**\nVui lòng quay lại sau ít phút!")
        return

    user_id = message.chat.id
    text = message.text
    parts = text.split()
    
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        ref_id = None
        if len(parts) > 1 and parts[1].startswith('ref'):
            ref_id = parts[1].replace('ref', '')
            if str(ref_id) == str(user_id): ref_id = None
        cursor.execute("INSERT INTO users (user_id, balance, total_tasks, ref_by) VALUES (?, 0, 0, ?)", (user_id, ref_id))
        conn.commit()

    # KHI VƯỢT LINK NHẢY VỀ -> BẮT GIẢI TOÁN (+ HOẶC -) CHỐNG BOT
    if len(parts) > 1 and parts[1].startswith('task'):
        task_id = parts[1]
        cursor.execute("SELECT status, user_id, reward FROM tasks WHERE task_id=?", (task_id,))
        task = cursor.fetchone()
        
        if task and task[0] == 'pending' and task[1] == user_id:
            reward = task[2]
            
            # Tạo phép tính ngẫu nhiên + hoặc -
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
                "🎉 *VƯỢT LINK THÀNH CÔNG* 🎉\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "🤖 *Hệ thống cần xác minh bạn không phải là Tool Auto.*\n"
                "👉 *Vui lòng giải phép tính sau (Có hiệu lực trong 60s):*\n\n"
                f"🧮 ⟨  `{a} {dau} {b} = ?`  ⟩\n\n"
                "*(Gõ đáp án bằng số và gửi vào đây để nhận thưởng)*\n"
                "━━━━━━━━━━━━━━━━━━"
            )
            bot.send_message(user_id, msg_toan, parse_mode="Markdown")
        else:
            bot.send_message(user_id, "❌ Mã nhiệm vụ không hợp lệ hoặc đã hết hạn giải toán.")
    else:
        intro_text = (
            "👋 **Chào mừng bạn đến với Vượt Link Kiếm Tiền Free!**\n\n"
            "💰 Nơi biến thời gian rảnh thành thu nhập thụ động uy tín 100%.\n\n"
            "🚀 **Cách kiếm lúa nhanh:**\n"
            "1️⃣ Bấm nút **🎯 Nhiệm Vụ** để lấy link cày.\n"
            "2️⃣ Vượt link qua trình duyệt web.\n"
            "3️⃣ Trở lại đây giải toán xác minh cực dễ để nhận tiền mặt.\n\n"
            f"💳 **Thanh toán:** Min rút cực thấp chỉ từ **{MIN_RUT}đ** về Momo/Ngân hàng."
        )
        bot.send_message(user_id, intro_text, parse_mode="Markdown", reply_markup=menu_chinh())

# ================= CHECK ĐÁP ÁN TOÁN & CỘNG TIỀN =================
@bot.message_handler(func=lambda m: m.text.strip().replace('-', '').isdigit())
def kiem_tra_toan(message):
    if check_bao_tri() and str(message.chat.id) != ADMIN_ID: return
    user_id = message.chat.id
    val = int(message.text)
    
    cursor.execute("SELECT task_id, answer, reward, time_created FROM tasks WHERE user_id=? AND status='verifying'", (user_id,))
    data = cursor.fetchone()
    
    if data:
        tid, correct, rw, t_create = data
        if time.time() - t_create > 60:
            bot.send_message(user_id, "⏰ **HẾT GIỜ!** Bạn không giải toán trong 60s, mã đã bị huỷ.")
            cursor.execute("UPDATE tasks SET status='expired' WHERE task_id=?", (tid,))
            conn.commit()
            return

        if val == correct:
            cursor.execute("UPDATE users SET balance = balance + ?, total_tasks = total_tasks + 1 WHERE user_id=?", (rw, user_id))
            cursor.execute("UPDATE tasks SET status='completed' WHERE task_id=?", (tid,))
            
            # Trả hoa hồng ref
            cursor.execute("SELECT ref_by FROM users WHERE user_id=?", (user_id,))
            ref_id = cursor.fetchone()[0]
            if ref_id:
                cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (HOA_HONG_REF, ref_id))
                try: bot.send_message(ref_id, f"💸 **HOA HỒNG ĐẠI LÝ:** Cấp dưới vừa hoàn thành nhiệm vụ, bạn được cộng `+{HOA_HONG_REF}đ`!")
                except: pass
            conn.commit()
            
            msg_ok = (
                "🎊 *CHÍNH XÁC - LÚA ĐÃ VỀ* 🎊\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 **Tiền thưởng:** `+{rw}đ`\n"
                "💳 Tiền đã cộng trực tiếp vào ví của bạn.\n\n"
                "👉 Tiếp tục bấm **🎯 Nhiệm Vụ** để bào tiếp!"
            )
            bot.send_message(user_id, msg_ok, parse_mode="Markdown", reply_markup=menu_chinh())
        else:
            bot.send_message(user_id, "❌ Sai rồi ông ơi! Thử lại nhiệm vụ khác nha.")
            cursor.execute("UPDATE tasks SET status='failed' WHERE task_id=?", (tid,))
            conn.commit()

# ================= MENU CHỨC NĂNG CHÍNH =================
@bot.message_handler(func=lambda m: m.text in ["🎯 Nhiệm Vụ", "🎧 Hỗ Trợ", "👤 Acc", "👥 Giới Thiệu", "💳 Rút Tiền"])
def handle_menu(message):
    if check_bao_tri() and str(message.chat.id) != ADMIN_ID:
        bot.send_message(message.chat.id, "🛠 **Hệ thống đang bảo trì, vui lòng quay lại sau!**")
        return

    uid = message.chat.id
    cmd = message.text

    if cmd == "🎯 Nhiệm Vụ":
        cursor.execute("SELECT task_id FROM tasks WHERE user_id=? AND status='verifying'", (uid,))
        if cursor.fetchone():
            bot.send_message(uid, "⚠️ Bạn đang có một phép tính chưa giải xong!")
            return
            
        # Bảng hướng dẫn nhiệm vụ đẹp mắt
        msg_hd_nv = (
            "🎯 *HƯỚNG DẪN CÀY LÚA NHANH* 🎯\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Bấm chọn Server nhiệm vụ khả dụng bên dưới.\n"
            "2️⃣ Vượt qua các lớp captcha/lấy mã trên trình duyệt.\n"
            "3️⃣ Web sẽ tự động nhảy về Telegram.\n"
            "4️⃣ Giải phép toán cực nhanh để lúa nhảy vào ví.\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "👇 **CHỌN NHIỆM VỤ CỦA BẠN:**"
        )
        bot.send_message(uid, msg_hd_nv, parse_mode="Markdown", reply_markup=menu_chon_nhiem_vu(uid))
    
    elif cmd == "🎧 Hỗ Trợ":
        ho_tro_msg = (
            "🎧 **TRUNG TÂM HỖ TRỢ HỆ THỐNG** 🎧\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "Mọi thắc mắc về lỗi link, lỗi rút tiền vui lòng liên hệ:\n\n"
            "👤 **Admin trực ban:** @vanminh2826\n"
            "👥 **Group Giao Lưu:** https://t.me/botkiemlua\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(uid, ho_tro_msg, disable_web_page_preview=True, parse_mode="Markdown")

    elif cmd == "👤 Acc":
        # Thống kê cá nhân
        cursor.execute("SELECT balance, total_tasks FROM users WHERE user_id=?", (uid,))
        user_data = cursor.fetchone()
        
        # Thống kê hệ thống toàn bot
        cursor.execute("SELECT COUNT(*) FROM users")
        total_global_users = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(total_tasks) FROM users")
        total_global_links = cursor.fetchone()[0] or 0
        
        # Lấy Bảng xếp hạng Top 3 mời Ref
        cursor.execute("SELECT ref_by, COUNT(*) as count FROM users WHERE ref_by IS NOT NULL GROUP BY ref_by ORDER BY count DESC LIMIT 3")
        top_refs = cursor.fetchall()
        
        bxh_text = ""
        hang_icon = ["🥇", "🥈", "🥉"]
        for idx, row in enumerate(top_refs):
            bxh_text += f"{hang_icon[idx]} ID `{row[0]}`: **{row[1]} thành viên**\n"
        if not bxh_text: bxh_text = "Chưa có dữ liệu xếp hạng."

        msg_info = (
            "👤 *THÔNG TIN TÀI KHOẢN* 👤\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **Mã ID:** `{uid}`\n"
            f"💵 **Số dư hiện tại:** `{user_data[0]}đ`\n"
            f"🎯 **Bạn đã vượt:** `{user_data[1]} link`\n\n"
            "📊 *THỐNG KÊ TOÀN HỆ THỐNG*\n"
            f"👥 **Tổng người dùng:** `{total_global_users} người`\n"
            f"🔗 **Tổng link đã vượt:** `{total_global_links} lượt`\n\n"
            "🏆 *TOP 3 ĐẠI LÝ TUYỂN REF TRÙM*\n"
            f"{bxh_text}"
            "━━━━━━━━━━━━━━━━━━"
        )
        bot.send_message(uid, msg_info, parse_mode="Markdown")

    elif cmd == "👥 Giới Thiệu":
        link_ref = f"https://t.me/{bot.get_me().username}?start=ref{uid}"
        msg_ref = (
            "👥 *CHƯƠNG TRÌNH ĐẠI LÝ* 👥\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"💰 Kiếm lúa thụ động! Nhận ngay `{HOA_HONG_REF}đ` hoa hồng mỗi khi bạn bè của bạn vượt thành công 1 link.\n\n"
            f"🔗 **Link mời độc quyền của bạn:**\n`{link_ref}`\n\n"
            "*(Chạm vào link để tự động copy gửi đi rải nhé!)*"
        )
        bot.send_message(uid, msg_ref, parse_mode="Markdown")

    elif cmd == "💳 Rút Tiền":
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
        bal = cursor.fetchone()[0]
        if bal >= MIN_RUT:
            msg_rut = (
                "🏦 *HƯỚNG DẪN RÚT TIỀN* 🏦\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 **Số dư rút khả dụng:** `{bal}đ`\n\n"
                "✍️ *Hãy điền thông tin rút tiền theo mẫu sau và gửi vào chat:*\n"
                "👉 `TÊN NGÂN HÀNG HOẶC MOMO + SỐ TÀI KHOẢN + TÊN CHỦ TÀI KHOẢN + SỐ TIỀN CẦN RÚT`"
            )
            m = bot.send_message(uid, msg_rut, parse_mode="Markdown")
            bot.register_next_step_handler(m, process_withdraw, bal)
        else:
            msg_loi = (
                "⚠️ *SỐ DƯ CHƯA ĐỦ ĐIỀU KIỆN RÚT* ⚠️\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💵 **Số dư hiện tại:** `{bal}đ`\n"
                f"🎯 **Hạn mức tối thiểu:** `{MIN_RUT}đ`\n\n"
                f"👉 Cố gắng cày thêm `{MIN_RUT - bal}đ` nữa để rút lúa nhé ae!"
            )
            bot.send_message(uid, msg_loi, parse_mode="Markdown")

# ================= TẠO LINK KHỞI CHẠY API =================
@bot.callback_query_handler(func=lambda call: call.data in ["get_uptolink", "limit_reached"])
def make_link(call):
    uid = call.message.chat.id
    
    if call.data == "limit_reached":
        bot.answer_callback_query(call.id, "⚠️ Bạn đã chạm giới hạn 200 lượt của hệ thống hôm nay rồi!", show_alert=True)
        return

    bot.edit_message_text("⏳ Đang khởi tạo link nhiệm vụ...", chat_id=uid, message_id=call.message.message_id)
    
    tid = 'task_' + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    target = f"https://telegram.me/{bot.get_me().username}?start={tid}"
    today = get_today_str()
    
    try:
        res = requests.get("https://uptolink.one/api", params={"api": API_UPTOLINK, "url": target}).json()
        short_url = res.get("shortenedUrl") if res.get("status") == "success" else None
        
        if short_url:
            cursor.execute("INSERT INTO tasks (task_id, user_id, status, reward, date_str) VALUES (?, ?, 'pending', ?, ?)", (tid, uid, TIEN_UPTO, today))
            conn.commit()
            msg = f"🔗 **NHIỆM VỤ UPTOLINK (+{TIEN_UPTO}đ):**\n\n`{short_url}`\n\n*(Vượt link xong trình duyệt sẽ đẩy bạn quay lại đây để giải toán nhận tiền)*"
            bot.send_message(uid, msg, parse_mode="Markdown")
        else:
            bot.send_message(uid, "❌ Hệ thống nhà cung cấp bận, thử lại sau.")
            
    except Exception as e:
        print("Lỗi API:", e)
        bot.send_message(uid, "❌ Đường truyền lỗi. Thử lại sau.")

# ================= XỬ LÝ ĐƠN RÚT TIỀN GỬI ADMIN =================
def process_withdraw(message, max_amount):
    uid = message.chat.id
    stk_info = message.text
    
    msg_xac_nhan = (
        "✅ *GỬI ĐƠN YÊU CẦU THÀNH CÔNG!*\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💳 **Thông tin thanh toán:**\n`{stk_info}`\n\n"
        "⏳ Ban quản trị hệ thống sẽ check và chuyển khoản sớm nhất cho bạn trong 24h."
    )
    bot.send_message(uid, msg_xac_nhan, parse_mode="Markdown", reply_markup=menu_chinh())
    
    # Khấu trừ số dư tạm thời (trừ toàn bộ số dư của user)
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id=?", (uid,))
    conn.commit()
    
    if ADMIN_ID:
        markup_admin = InlineKeyboardMarkup()
        markup_admin.row(
            InlineKeyboardButton("✅ Đã Chuyển Tiền", callback_data=f"admin_duyet_{uid}_{max_amount}"),
            InlineKeyboardButton("❌ Hủy & Hoàn Tiền", callback_data=f"admin_huy_{uid}_{max_amount}")
        )
        bill_msg = (
            "🚨 **YÊU CẦU RÚT TIỀN MỚI** 🚨\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 **ID Thành viên:** `{uid}`\n"
            f"💰 **Tổng số dư yêu cầu rút:** `{max_amount}đ`\n"
            f"💳 **Thông tin chi tiết:**\n`{stk_info}`\n"
            "━━━━━━━━━━━━━━━━━━"
        )
        try: bot.send_message(ADMIN_ID, bill_msg, parse_mode="Markdown", reply_markup=markup_admin)
        except: pass

# ================= KHỞI CHẠY HỆ THỐNG VVIP RENDER =================
if __name__ == "__main__":
    print("🚀 BẬT MÁY CHỦ WEB CHỐNG SẬP CHO RENDER...")
    keep_alive()
    print("🤖 BOT 'VƯỢT LINK KIẾM TIỀN FREE' ĐÃ ONLINE!")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
