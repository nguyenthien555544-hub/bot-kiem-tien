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

# ================= MỐC THỜI GIAN ĐỂ TÍNH UPTIME =================
START_TIME = time.time()

# ================= CẤU HÌNH BOT & API =================
BOT_TOKEN = "8803256348:AAH58katT66W1DrHvw445OTKv2rLGgh88r4"
ADMIN_ID = "8781909366" 
ADMIN_USERNAME = "@vanminh2826"

# UPTOLINK
API_UPTOLINK = "2f2a6f9894f02956c31f64fa2387a4d67cc36658"
TIEN_UPTO = 350
MAX_UPTO = 200

# NHIỆM VỤ BANK
LINK_MB = "https://mbbank.onelink.me/QPF5?pid=SF%20Email%20Warmup&c=SF_Email_WarmUP_AppInstall&af_force_deeplink=true&af_dp=mbbank%3A%2F%2F&referral_code=39OIJCU6S6FMDBPLDVAAX"
TIEN_MB = 70000

HOA_HONG_REF = 50       
MIN_RUT = 10000

bot = telebot.TeleBot(BOT_TOKEN)

# ================= DATABASE =================
conn = sqlite3.connect('bot_upto_master.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER, total_tasks INTEGER DEFAULT 0, ref_by INTEGER)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, user_id INTEGER, status TEXT, reward INTEGER, answer INTEGER, time_created REAL, date_str TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')

try: cursor.execute("ALTER TABLE tasks ADD COLUMN task_type TEXT DEFAULT 'uptolink'")
except: pass
try: cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
except: pass

cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('bao_tri', 'off')")
conn.commit()

# ================= FIX LỖI UPTIME BỊ RESET =================
cursor.execute("SELECT value FROM settings WHERE key='start_time'")
res_time = cursor.fetchone()
if not res_time:
    START_TIME = time.time()
    cursor.execute("INSERT INTO settings (key, value) VALUES ('start_time', ?)", (str(START_TIME),))
    conn.commit()
else:
    START_TIME = float(res_time[0])

# ================= HỆ THỐNG QUẢN LÝ USER =================
def check_user(uid):
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (uid,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, balance, total_tasks, ref_by, status) VALUES (?, 0, 0, NULL, 'active')", (uid,))
        conn.commit()

def is_banned(uid):
    cursor.execute("SELECT status FROM users WHERE user_id=?", (uid,))
    res = cursor.fetchone()
    return True if res and res[0] == 'banned' else False

def check_bao_tri():
    cursor.execute("SELECT value FROM settings WHERE key='bao_tri'")
    res = cursor.fetchone()
    return True if res and res[0] == 'on' else False

def is_maintenance(uid):
    return check_bao_tri() and str(uid) != ADMIN_ID

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# ================= SERVER WEB RENDER (DASHBOARD ADMIN NÂNG CẤP) =================
app = Flask('')

@app.route('/')
def home():
    # Tính Uptime
    uptime_sec = int(time.time() - START_TIME)
    d = uptime_sec // 86400
    h = (uptime_sec % 86400) // 3600
    m = (uptime_sec % 3600) // 60
    s = uptime_sec % 60
    uptime_str = f"{d} Ngày {h:02d}:{m:02d}:{s:02d}"

    # Thống kê
    cursor.execute("SELECT user_id, balance, total_tasks, ref_by, status FROM users ORDER BY total_tasks DESC")
    users = cursor.fetchall()
    tong_mem = len(users)
    tong_link = sum(u[2] for u in users)
    tong_du = sum(u[1] for u in users)

    # HTML Giao diện
    html = f"""
    <html>
    <head>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>HT TOOL - ADMIN PANEL</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Inter:wght@400;600&display=swap');
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Inter', sans-serif; background: #0b0f19; color: #f8fafc; overflow-x: hidden; }}
            
            /* Navbar & Sidebar */
            .navbar {{ background: #111827; padding: 15px 20px; display: flex; align-items: center; border-bottom: 1px solid #1f2937; position: sticky; top: 0; z-index: 100; }}
            .menu-btn {{ font-size: 24px; color: #38bdf8; cursor: pointer; background: none; border: none; outline: none; margin-right: 15px; }}
            .logo {{ font-family: 'Orbitron', sans-serif; font-size: 18px; color: #38bdf8; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }}
            
            .sidebar {{ position: fixed; top: 55px; left: -250px; width: 250px; height: calc(100vh - 55px); background: #111827; transition: 0.3s; padding: 20px 0; border-right: 1px solid #1f2937; z-index: 99; box-shadow: 2px 0 10px rgba(0,0,0,0.5); }}
            .sidebar.active {{ left: 0; }}
            .sidebar a {{ display: block; padding: 15px 25px; color: #94a3b8; text-decoration: none; font-size: 16px; border-left: 3px solid transparent; transition: 0.2s; cursor: pointer; }}
            .sidebar a:hover, .sidebar a.active {{ background: #1f2937; color: #38bdf8; border-left-color: #38bdf8; }}
            .sidebar a i {{ margin-right: 10px; width: 20px; text-align: center; }}

            /* Main Content & Tabs */
            .main-content {{ padding: 20px; transition: 0.3s; margin-left: 0; }}
            .tab-content {{ display: none; animation: fadeIn 0.3s; }}
            .tab-content.active {{ display: block; }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            
            .uptime-box {{ background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%); padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3); }}
            
            /* Thống kê Grid */
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 25px; }}
            .stat-box {{ background: #1f2937; padding: 20px; border-radius: 12px; border: 1px solid #374151; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .stat-box h3 {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; }}
            .stat-box p {{ font-size: 20px; font-weight: 700; color: #fff; font-family: 'Orbitron', sans-serif; }}
            .text-green {{ color: #10b981 !important; }}
            .text-gold {{ color: #fbbf24 !important; }}

            /* Table */
            .table-container {{ background: #1f2937; border-radius: 12px; overflow-x: auto; border: 1px solid #374151; }}
            table {{ width: 100%; border-collapse: collapse; min-width: 600px; }}
            th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #374151; font-size: 14px; }}
            th {{ background: #111827; color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 12px; }}
            tr:hover {{ background: #374151; }}
            .badge-green {{ background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }}
            .badge-red {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; }}
            .btn {{ padding: 5px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; text-decoration: none; display: inline-block; text-align: center; transition: 0.2s; }}
            .btn-ban {{ background: #ef4444; color: #fff; }}
            .btn-ban:hover {{ background: #dc2626; }}
            .btn-unban {{ background: #10b981; color: #fff; }}
            
            /* Card Setting */
            .setting-card {{ background: #1f2937; padding: 20px; border-radius: 12px; border: 1px solid #374151; margin-bottom: 15px; }}
            .setting-card h3 {{ color: #38bdf8; margin-bottom: 15px; font-size: 16px; border-bottom: 1px solid #374151; padding-bottom: 10px; }}
            .setting-item {{ display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 14px; color: #cbd5e1; border-bottom: 1px dashed #374151; padding-bottom: 5px; }}
            .setting-item span:last-child {{ font-weight: bold; color: #fff; }}

        </style>
    </head>
    <body>
        <div class="navbar">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>
            <div class="logo">HT TOOL ADMIN</div>
        </div>

        <div class="sidebar" id="sidebar">
            <a onclick="switchTab('tab1', this)" class="menu-item active"><i class="fas fa-chart-line"></i> Bảng Tổng Quan</a>
            <a onclick="switchTab('tab2', this)" class="menu-item"><i class="fas fa-users"></i> Quản Lý Dân Cày</a>
            <a onclick="switchTab('tab3', this)" class="menu-item"><i class="fas fa-cogs"></i> Cài Đặt Server</a>
        </div>

        <div class="main-content" id="main">
            <div id="tab1" class="tab-content active">
                <div class="uptime-box">
                    <i class="fas fa-clock"></i> Thời gian Bot sống: {uptime_str}
                </div>
                <div class="stats-grid">
                    <div class="stat-box"><h3><i class="fas fa-users"></i> Tổng Mem</h3><p>{tong_mem}</p></div>
                    <div class="stat-box"><h3><i class="fas fa-link"></i> Link Đã Cày</h3><p>{tong_link}</p></div>
                    <div class="stat-box"><h3><i class="fas fa-wallet"></i> Lúa Tồn Đọng</h3><p class="text-green">{tong_du:,}đ</p></div>
                    <div class="stat-box"><h3><i class="fas fa-gift"></i> Rate App MB</h3><p class="text-gold">{TIEN_MB:,}đ</p></div>
                </div>
            </div>

            <div id="tab2" class="tab-content">
                <h3 style="color: #38bdf8; margin-bottom: 15px;"><i class="fas fa-users-cog"></i> Danh Sách ID Telegram</h3>
                <div class="table-container">
                    <table>
                        <tr><th>ID Telegram</th><th>Trạng Thái</th><th>Số Dư</th><th>Tổng Link</th><th>Hành Động</th></tr>
    """
    for u in users:
        status_html = "<span class='badge-green'>Hoạt động</span>" if u[4] == 'active' else "<span class='badge-red'>Bị Khóa</span>"
        action_btn = f"<a href='/{ADMIN_ID}/ban/{u[0]}' class='btn btn-ban'><i class='fas fa-ban'></i> BAN</a>" if u[4] == 'active' else f"<a href='/{ADMIN_ID}/unban/{u[0]}' class='btn btn-unban'><i class='fas fa-unlock'></i> MỞ</a>"
        html += f"<tr><td>{u[0]}</td><td>{status_html}</td><td class='text-green' style='font-weight:bold;'>{u[1]:,}đ</td><td>{u[2]}</td><td>{action_btn}</td></tr>"
    
    html += f"""
                    </table>
                </div>
            </div>

            <div id="tab3" class="tab-content">
                <div class="setting-card">
                    <h3><i class="fas fa-sliders-h"></i> Thông Số Trả Thưởng</h3>
                    <div class="setting-item"><span>Tiền Vượt Link (Uptolink):</span> <span class="text-green">{TIEN_UPTO}đ</span></div>
                    <div class="setting-item"><span>Tiền Tải App (MB Bank):</span> <span class="text-gold">{TIEN_MB:,}đ</span></div>
                    <div class="setting-item"><span>Hoa hồng giới thiệu (Ref):</span> <span>{HOA_HONG_REF}đ</span></div>
                    <div class="setting-item"><span>Min Rút Lúa:</span> <span class="text-green">{MIN_RUT:,}đ</span></div>
                </div>
                <div class="setting-card">
                    <h3><i class="fas fa-server"></i> Cấu Hình Hệ Thống</h3>
                    <div class="setting-item"><span>ID Admin Root:</span> <span>{ADMIN_ID}</span></div>
                    <div class="setting-item"><span>Giới hạn Uptolink/Ngày:</span> <span>{MAX_UPTO} link</span></div>
                    <div class="setting-item"><span>Bảo trì Server (Lệnh):</span> <span>/baotri on/off</span></div>
                </div>
            </div>

        </div>

        <script>
            // Đóng mở Menu Sidebar
            function toggleSidebar() {{
                document.getElementById('sidebar').classList.toggle('active');
            }}

            // Hàm chuyển đổi các Tab (Hoạt động mượt không cần load lại web)
            function switchTab(tabId, element) {{
                // 1. Ẩn tất cả nội dung Tab
                let tabs = document.getElementsByClassName('tab-content');
                for(let i = 0; i < tabs.length; i++) {{
                    tabs[i].classList.remove('active');
                }}
                
                // 2. Tắt hiệu ứng sáng ở tất cả các nút Menu
                let menuItems = document.getElementsByClassName('menu-item');
                for(let i = 0; i < menuItems.length; i++) {{
                    menuItems[i].classList.remove('active');
                }}

                // 3. Hiện Tab được chọn và Làm sáng Menu vừa bấm
                document.getElementById(tabId).classList.add('active');
                element.classList.add('active');

                // 4. Tự động đóng menu trượt trên điện thoại sau khi chọn xong
                document.getElementById('sidebar').classList.remove('active');
            }}
        </script>
    </body>
    </html>
    """
    return html

@app.route(f'/{ADMIN_ID}/ban/<int:uid>')
def ban_user(uid):
    cursor.execute("UPDATE users SET status='banned' WHERE user_id=?", (uid,))
    conn.commit()
    return f"<script>alert('ĐÃ KHÓA MÕM TÀI KHOẢN {uid}!'); window.location.href='/';</script>"

@app.route(f'/{ADMIN_ID}/unban/<int:uid>')
def unban_user(uid):
    cursor.execute("UPDATE users SET status='active' WHERE user_id=?", (uid,))
    conn.commit()
    return f"<script>alert('ĐÃ MỞ KHÓA TÀI KHOẢN {uid}!'); window.location.href='/';</script>"

def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_server)
    t.start()

# ================= GIAO DIỆN NÚT BẤM TELEGRAM =================
def menu_chinh():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("🚀 NGUỒN NHIỆM VỤ 🚀"))
    markup.row(KeyboardButton("👤 Thông Tin Acc"), KeyboardButton("💳 Rút Lúa"))
    markup.row(KeyboardButton("🏆 Bảng Xếp Hạng"), KeyboardButton("👥 Đại Lý (Mời Bạn)"))
    markup.row(KeyboardButton("🎧 Trợ Giúp"))
    return markup

# ================= ẢNH CHỤP MÀN HÌNH (NHIỆM VỤ BANK) =================
@bot.message_handler(content_types=['photo'])
def xu_ly_anh_mb(message):
    uid = message.chat.id
    check_user(uid)
    if is_banned(uid): return bot.send_message(uid, "🚫 *Tài khoản của bạn đã bị BAN vĩnh viễn!*", parse_mode="Markdown")
    if is_maintenance(uid): return bot.send_message(uid, "🚧 HỆ THỐNG ĐANG BẢO TRÌ!")

    msg_ack = f"✅ *Đã nhận được thông tin!*\n\n⏳ Hệ thống đã chuyển ảnh của bạn lên Admin, vui lòng đợi Admin kiểm tra và duyệt lúa.\n\n🎧 Có thắc mắc gì liên hệ Admin {ADMIN_USERNAME}"
    bot.reply_to(message, msg_ack, parse_mode="Markdown")

    photo_id = message.photo[-1].file_id
    markup_duyet = InlineKeyboardMarkup()
    markup_duyet.row(
        InlineKeyboardButton(f"✅ DUYỆT +{TIEN_MB:,}đ", callback_data=f"bank_duyet_{uid}"),
        InlineKeyboardButton("❌ TỪ CHỐI (Ảnh Fake)", callback_data=f"bank_huy_{uid}")
    )
    caption = f"🚨 *YÊU CẦU DUYỆT NHIỆM VỤ MB BANK*\n━━━━━━━━━━━━━━━━━━\n👤 ID Thành viên: `{uid}`\n👉 Bấm nút bên dưới để cộng tiền hoặc từ chối!"
    try: bot.send_photo(ADMIN_ID, photo_id, caption=caption, parse_mode="Markdown", reply_markup=markup_duyet)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('bank_'))
def admin_xu_ly_bank(call):
    if str(call.message.chat.id) != ADMIN_ID: return
    parts = call.data.split('_')
    action = parts[1]
    target_uid = int(parts[2])
    
    if action == 'duyet':
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (TIEN_MB, target_uid))
        conn.commit()
        bot.edit_message_caption("✅ *ĐÃ DUYỆT ĐƠN VÀ CỘNG TIỀN THÀNH CÔNG!*", chat_id=ADMIN_ID, message_id=call.message.message_id, parse_mode="Markdown")
        try: bot.send_message(target_uid, f"🎉 *CHÚC MỪNG!*\nAdmin đã kiểm tra và duyệt thành công nhiệm vụ MB Bank của bạn.\n\n💵 Lúa về ví: `+{TIEN_MB:,}đ`\n👉 Bấm Rút Lúa ngay thôi ae!", parse_mode="Markdown")
        except: pass
    elif action == 'huy':
        bot.edit_message_caption("❌ *ĐÃ TỪ CHỐI BỨC ẢNH NÀY!*", chat_id=ADMIN_ID, message_id=call.message.message_id, parse_mode="Markdown")
        try: bot.send_message(target_uid, f"⚠️ *THÔNG BÁO TỪ ADMIN*\nNhiệm vụ MB Bank của bạn bị TỪ CHỐI do ảnh cung cấp không hợp lệ, đăng ký sai luồng hoặc bạn dùng ảnh mạng gian lận.\n\n🎧 Cần hỗ trợ liên hệ {ADMIN_USERNAME}", parse_mode="Markdown")
        except: pass

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
def admin_duyet_tien_rut(call):
    if str(call.message.chat.id) != ADMIN_ID: return
    parts = call.data.split('_')
    action, target_uid, amount = parts[1], int(parts[2]), int(parts[3])
    
    if action == 'duyet':
        bot.edit_message_text(f"{call.message.text}\n\n✅ **ĐÃ CHUYỂN TIỀN VỀ BANK/MOMO**", chat_id=ADMIN_ID, message_id=call.message.message_id)
        try: bot.send_message(target_uid, f"🎉 *TINH TINH!*\nLúa `{amount}đ` đã được Bank về ví của bạn. Cảm ơn đã cày cuốc!", parse_mode="Markdown")
        except: pass
    elif action == 'huy':
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_uid))
        conn.commit()
        bot.edit_message_text(f"{call.message.text}\n\n❌ **ĐÃ TỪ CHỐI & HOÀN TIỀN**", chat_id=ADMIN_ID, message_id=call.message.message_id)
        try: bot.send_message(target_uid, f"⚠️ Đơn rút `{amount}đ` bị HỦY (Sai STK hoặc gian lận). Tiền đã trả lại vào Bot.", parse_mode="Markdown")
        except: pass

# ================= XỬ LÝ LỆNH /START & VƯỢT LINK =================
@bot.message_handler(commands=['start'])
def xu_ly_start(message):
    uid = message.chat.id
    check_user(uid)
    if is_banned(uid): return bot.send_message(uid, "🚫 *Tài khoản của bạn đã bị khóa vi phạm chính sách!*", parse_mode="Markdown")
    if is_maintenance(uid): return bot.send_message(uid, "🚧 *HỆ THỐNG ĐANG BẢO TRÌ!* Quay lại sau nhé ae!", parse_mode="Markdown")

    text = message.text
    parts = text.split()
    
    # Xử lý Ref
    if len(parts) > 1 and parts[1].startswith('ref'):
        ref_id = parts[1].replace('ref', '')
        if str(ref_id) != str(uid):
            cursor.execute("UPDATE users SET ref_by=? WHERE user_id=? AND ref_by IS NULL", (ref_id, uid))
            conn.commit()

    if len(parts) > 1 and parts[1].startswith('task'):
        task_id = parts[1]
        cursor.execute("SELECT status, user_id, reward, task_type FROM tasks WHERE task_id=?", (task_id,))
        task = cursor.fetchone()
        
        if task and task[0] == 'pending' and task[1] == uid:
            reward = task[2]
            
            dau = random.choice(['+', '-'])
            if dau == '+':
                a, b = random.randint(10, 30), random.randint(1, 20)
                ans = a + b
            else:
                a, b = random.randint(20, 50), random.randint(1, 19)
                ans = a - b
                
            cursor.execute("UPDATE tasks SET status='verifying', answer=?, time_created=? WHERE task_id=?", (ans, time.time(), task_id))
            conn.commit()
            
            sai1 = ans + random.choice([1, 2, 3])
            sai2 = ans - random.choice([1, 2, 3])
            sai3 = ans + random.choice([4, 5, 10])
            
            choices = list(set([ans, sai1, sai2, sai3]))
            while len(choices) < 4:
                choices.append(ans + random.randint(11, 20))
                choices = list(set(choices))
            random.shuffle(choices)

            tid_code = task_id.split('_')[1]
            markup_toan = InlineKeyboardMarkup()
            markup_toan.row(
                InlineKeyboardButton(f"{choices[0]}", callback_data=f"chk_{tid_code}_{choices[0]}"),
                InlineKeyboardButton(f"{choices[1]}", callback_data=f"chk_{tid_code}_{choices[1]}")
            )
            markup_toan.row(
                InlineKeyboardButton(f"{choices[2]}", callback_data=f"chk_{tid_code}_{choices[2]}"),
                InlineKeyboardButton(f"{choices[3]}", callback_data=f"chk_{tid_code}_{choices[3]}")
            )
            
            msg_toan = (
                "🛡️ *HỆ THỐNG XÁC MINH ROBOT* 🛡️\n"
                "╔══════════════════════╗\n"
                f"  🎁 Vượt link thành công: `+{reward}đ`\n"
                "╚══════════════════════╝\n"
                "👉 *Chạm vào ĐÁP ÁN ĐÚNG bên dưới (60s):*\n\n"
                f"🧮 ⟨  `{a} {dau} {b} = ?`  ⟩"
            )
            bot.send_message(uid, msg_toan, parse_mode="Markdown", reply_markup=markup_toan)
        else:
            bot.send_message(uid, "❌ Link nhiệm vụ không đúng hoặc đã hết hạn.")
    else:
        intro = (
            "👑 *CHÀO MỪNG ĐẾN VỚI HỆ THỐNG KIẾM TIỀN VIP* 👑\n\n"
            "💰 *Thu nhập thụ động - Rút tiền mỗi ngày*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🚀 *Quy trình lụm lúa:*\n"
            "1️⃣ Chọn nút *🚀 NGUỒN NHIỆM VỤ*.\n"
            "2️⃣ Cày Link hoặc Đăng ký App để bào tiền.\n\n"
            f"💳 *Hỗ trợ:* Min rút siêu thấp chỉ từ `{MIN_RUT}đ`."
        )
        bot.send_message(uid, intro, parse_mode="Markdown", reply_markup=menu_chinh())

# ================= CHECK TRẮC NGHIỆM =================
@bot.callback_query_handler(func=lambda call: call.data.startswith('chk_'))
def check_toan_inline(call):
    uid = call.message.chat.id
    check_user(uid)
    if is_banned(uid): return bot.answer_callback_query(call.id, "🚫 Tài khoản bị khóa!", show_alert=True)
    if is_maintenance(uid): return bot.answer_callback_query(call.id, "🚧 HỆ THỐNG ĐANG BẢO TRÌ!", show_alert=True)
    
    parts = call.data.split('_')
    tid = f"task_{parts[1]}"
    val = int(parts[2])
    
    cursor.execute("SELECT answer, reward, time_created FROM tasks WHERE task_id=? AND status='verifying'", (tid,))
    data = cursor.fetchone()
    
    if not data:
        return bot.edit_message_text("❌ Mã nhiệm vụ không tồn tại hoặc đã được nhận thưởng.", chat_id=uid, message_id=call.message.message_id)
        
    correct, rw, t_create = data
    if time.time() - t_create > 60:
        bot.edit_message_text("⏰ Quá 60 giây! Mã đã hủy.", chat_id=uid, message_id=call.message.message_id)
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
            try: bot.send_message(ref_id, f"💸 *TING TING:* Nhận `+{HOA_HONG_REF}đ` hoa hồng cày cuốc!", parse_mode="Markdown")
            except: pass
        conn.commit()
        
        msg_ok = (
            "🎊 *CHÍNH XÁC - LÚA VỀ VÍ* 🎊\n"
            "╔═══════════════════╗\n"
            f"  💵 Tiền thưởng cộng thêm: `+{rw}đ`\n"
            "╚═══════════════════╝\n"
            "👉 Tiếp tục cày thâu đêm nào!"
        )
        bot.edit_message_text(msg_ok, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("❌ Sai bét rồi ông thần! Nhiệm vụ này tạch, vui lòng nhận link mới.", chat_id=uid, message_id=call.message.message_id)
        cursor.execute("UPDATE tasks SET status='failed' WHERE task_id=?", (tid,))
        conn.commit()

# ================= MENU CHỨC NĂNG CHÍNH =================
@bot.message_handler(func=lambda m: m.text in ["🚀 NGUỒN NHIỆM VỤ 🚀", "🎧 Trợ Giúp", "👤 Thông Tin Acc", "👥 Đại Lý (Mời Bạn)", "💳 Rút Lúa", "🏆 Bảng Xếp Hạng"])
def handle_menu(message):
    uid = message.chat.id
    check_user(uid)
    if is_banned(uid): return bot.send_message(uid, "🚫 *Tài khoản của bạn đã bị khóa!*", parse_mode="Markdown")
    if is_maintenance(uid): return bot.send_message(uid, "🚧 *HỆ THỐNG ĐANG BẢO TRÌ!* Quay lại sau nha anh em!", parse_mode="Markdown")

    cmd = message.text

    if cmd == "🚀 NGUỒN NHIỆM VỤ 🚀":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🏦 Nhiệm Vụ Bank (Tiền To)", callback_data="menu_bank"))
        markup.row(InlineKeyboardButton("🔗 Nhiệm Vụ Vượt Link", callback_data="menu_link"))
        bot.send_message(uid, "👇 *VUI LÒNG CHỌN LOẠI NHIỆM VỤ:*", parse_mode="Markdown", reply_markup=markup)
    
    elif cmd == "🏆 Bảng Xếp Hạng":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🥇 Top Cày Link", callback_data="bxh_link"), InlineKeyboardButton("🔥 Top Mời Ref", callback_data="bxh_ref"))
        bot.send_message(uid, "🏆 *BẢNG XẾP HẠNG SERVER*\n\nChọn danh mục bạn muốn xem:", parse_mode="Markdown", reply_markup=markup)

    elif cmd == "🎧 Trợ Giúp":
        ht = (
            "🛡️ *TỔNG ĐÀI HỖ TRỢ* 🛡️\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"👤 Admin xử lý Bank & Lỗi: {ADMIN_USERNAME}\n"
            "👥 Group Giao Lưu: https://t.me/botkiemlua"
        )
        bot.send_message(uid, ht, disable_web_page_preview=True, parse_mode="Markdown")

    elif cmd == "👤 Thông Tin Acc":
        cursor.execute("SELECT balance, total_tasks FROM users WHERE user_id=?", (uid,))
        d = cursor.fetchone()
        info = (
            "👤 *HỒ SƠ CỦA BẠN* 👤\n"
            "╔═══════════════════╗\n"
            f" 🆔 ID: `{uid}`\n"
            f" 💵 Số Dư: `{d[0]:,}đ`\n"
            f" 🎯 Đã cày: `{d[1]} nhiệm vụ`\n"
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
        res = cursor.fetchone()
        bal = res[0] if res else 0
        
        if bal >= MIN_RUT:
            rut = (
                "🏦 *LÊN ĐƠN RÚT LÚA* 🏦\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"💰 Có thể rút: `{bal:,}đ`\n\n"
                "✍️ *Nhập thông tin theo mẫu và gửi vào đây:*\n"
                "`NGÂN HÀNG - SỐ TK - TÊN CHỦ TK - SỐ TIỀN`"
            )
            m = bot.send_message(uid, rut, parse_mode="Markdown")
            bot.register_next_step_handler(m, process_withdraw, bal)
        else:
            bot.send_message(uid, f"⚠️ Số dư của bạn: `{bal:,}đ`.\n\n❌ *Chưa đủ điều kiện rút!* Phải cày đủ Min rút là `{MIN_RUT:,}đ` nhé ae!", parse_mode="Markdown")

# ================= XỬ LÝ NHIỆM VỤ CON & BXH =================
@bot.callback_query_handler(func=lambda call: call.data in ["menu_bank", "menu_link", "get_uptolink", "limit_reached", "bxh_link", "bxh_ref"])
def handle_sub_menus(call):
    uid = call.message.chat.id
    check_user(uid)
    if is_banned(uid): return bot.answer_callback_query(call.id, "🚫 Tài khoản bị khóa!", show_alert=True)
    if is_maintenance(uid): return bot.answer_callback_query(call.id, "🚧 HỆ THỐNG ĐANG BẢO TRÌ!", show_alert=True)

    if call.data == "bxh_link":
        cursor.execute("SELECT user_id, total_tasks FROM users WHERE total_tasks > 0 ORDER BY total_tasks DESC LIMIT 10")
        rows = cursor.fetchall()
        msg = "🥇 *TOP 10 CÀY CHAY CHĂM CHỈ*\n━━━━━━━━━━━━━━━━━━\n"
        for i, r in enumerate(rows):
            masked_id = str(r[0])[:-3] + "***"
            msg += f"{i+1}. ID: `{masked_id}` ➔ **{r[1]}** link\n"
        bot.edit_message_text(msg, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
        
    elif call.data == "bxh_ref":
        cursor.execute("SELECT ref_by, COUNT(*) as c FROM users WHERE ref_by IS NOT NULL GROUP BY ref_by ORDER BY c DESC LIMIT 10")
        rows = cursor.fetchall()
        msg = "🔥 *TOP 10 CHÚA TỂ TUYỂN REF*\n━━━━━━━━━━━━━━━━━━\n"
        for i, r in enumerate(rows):
            masked_id = str(r[0])[:-3] + "***"
            msg += f"{i+1}. ID: `{masked_id}` ➔ **{r[1]}** người\n"
        bot.edit_message_text(msg, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")

    elif call.data == "menu_bank":
        msg = f"""🚀 *NHIỆM VỤ ĐẶC BIỆT: TẢI APP MB BANK* 🚀
━━━━━━━━━━━━━━━━━━
💰 *Thưởng nóng:* `{TIEN_MB:,}đ` vào ví Bot.

📝 *HƯỚNG DẪN CÁC BƯỚC:*
1️⃣ Bấm vào link dưới đây để Tải App:
👉 [TẢI MB BANK TẠI ĐÂY]({LINK_MB})
2️⃣ Mở App lên, tiến hành Đăng ký tài khoản và Xác thực khuôn mặt (eKYC) thành công. *(Lưu ý không thoát app giữa chừng)*.
3️⃣ Đăng ký xong, bạn Đăng nhập vào App MB Bank.
4️⃣ Chụp lại **Ảnh màn hình** tài khoản của bạn (Phải rõ ràng, không lấy ảnh mạng).
5️⃣ **Gửi trực tiếp bức ảnh đó vào khung chat này.**

⏳ Admin sẽ kiểm tra và cộng ngay `{TIEN_MB:,}đ` cho bạn!"""
        bot.edit_message_text(msg, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown", disable_web_page_preview=True)

    elif call.data == "menu_link":
        today = get_today_str()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='uptolink'", (uid, today))
        count_upto = cursor.fetchone()[0]

        markup = InlineKeyboardMarkup()
        if count_upto < MAX_UPTO:
            markup.row(InlineKeyboardButton(f"🔗 Vượt Uptolink (+{TIEN_UPTO}đ) [{count_upto}/{MAX_UPTO}]", callback_data="get_uptolink"))
        else:
            markup.row(InlineKeyboardButton(f"🔗 Uptolink (Hết lượt hôm nay)", callback_data="limit_reached"))
        
        bot.edit_message_text("👇 *BẤM ĐỂ NHẬN LINK VƯỢT:*", chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown", reply_markup=markup)

    elif call.data == "limit_reached":
        bot.answer_callback_query(call.id, "⚠️ Web này hôm nay đã cày max giới hạn rồi ông ơi!", show_alert=True)

    elif call.data == "get_uptolink":
        bot.edit_message_text("⏳ Đang cào link mới...", chat_id=uid, message_id=call.message.message_id)
        tid = 'task_' + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        target = f"https://telegram.me/{bot.get_me().username}?start={tid}"
        today = get_today_str()

        try:
            res = requests.get("https://uptolink.one/api", params={"api": API_UPTOLINK, "url": target}).json()
            short_url = res.get("shortenedUrl") if res.get("status") == "success" else None
            if short_url:
                cursor.execute("INSERT INTO tasks (task_id, user_id, task_type, status, reward, date_str) VALUES (?, ?, 'uptolink', 'pending', ?, ?)", (tid, uid, TIEN_UPTO, today))
                conn.commit()
                bot.send_message(uid, f"🔗 *UPTOLINK (+{TIEN_UPTO}đ):*\n`{short_url}`\n\n_(Vượt xong quay lại Bot giải toán nhận tiền)_", parse_mode="Markdown")
            else:
                bot.send_message(uid, "❌ API Web đang bận, nhấp lại nút đi ông.")
        except:
            bot.send_message(uid, "❌ Lỗi mạng máy chủ.")

# ================= RÚT TIỀN THÔNG THƯỜNG =================
def process_withdraw(message, max_amount):
    uid = message.chat.id
    stk_info = message.text
    bot.send_message(uid, "✅ *BILL ĐÃ LÊN!* Chờ Admin kiểm tra và duyệt tiền nhé.", parse_mode="Markdown", reply_markup=menu_chinh())
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id=?", (uid,))
    conn.commit()
    
    if ADMIN_ID:
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("✅ Duyệt Lúa", callback_data=f"admin_duyet_{uid}_{max_amount}"), InlineKeyboardButton("❌ Hủy Đơn", callback_data=f"admin_huy_{uid}_{max_amount}"))
        try: bot.send_message(ADMIN_ID, f"🚨 *LỆNH RÚT TIỀN MỚI*\nID: `{uid}`\nTiền: `{max_amount:,}đ`\nSTK:\n`{stk_info}`", parse_mode="Markdown", reply_markup=markup)
        except: pass

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
