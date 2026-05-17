import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests
import random
import string
import sqlite3
import time
import os
from datetime import datetime
from flask import Flask, request
import threading

# ================= CẤU HÌNH BOT & API CƠ BẢN =================
BOT_TOKEN = "8803256348:AAH58katT66W1DrHvw445OTKv2rLGgh88r4"
ADMIN_ID = "8781909366" 
ADMIN_USERNAME = "@vanminh2826"
MAX_UPTO = 200
LINK_MB = "https://mbbank.onelink.me/QPF5?pid=SF%20Email%20Warmup&c=SF_Email_WarmUP_AppInstall&af_force_deeplink=true&af_dp=mbbank%3A%2F%2F&referral_code=39OIJCU6S6FMDBPLDVAAX"
HOA_HONG_REF = 50       

bot = telebot.TeleBot(BOT_TOKEN)

# ================= DATABASE & LƯU TRỮ VĨNH VIỄN =================
conn = sqlite3.connect('bot_upto_master.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER, total_tasks INTEGER DEFAULT 0, ref_by INTEGER, status TEXT DEFAULT 'active')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (task_id TEXT PRIMARY KEY, user_id INTEGER, status TEXT, reward INTEGER, answer INTEGER, time_created REAL, date_str TEXT, task_type TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, info TEXT, status TEXT DEFAULT 'pending', time_created REAL)''')

# Nạp Cài Đặt Mặc Định Lần Đầu
defaults = [
    ('bao_tri', 'off'),
    ('api_uptolink', '2f2a6f9894f02956c31f64fa2387a4d67cc36658'),
    ('tien_upto', '350'),
    ('tien_mb', '70000'),
    ('min_rut', '10000'),
    ('start_msg', '👑 *CHÀO MỪNG ĐẾN VỚI HỆ THỐNG KIẾM TIỀN VIP* 👑\n\n💰 *Thu nhập thụ động - Rút tiền mỗi ngày*\n\n🚀 *Quy trình lụm lúa:*\n1️⃣ Chọn nút *🚀 NGUỒN NHIỆM VỤ*.\n2️⃣ Cày Link hoặc Đăng ký App để bào tiền.\n\n💳 *Hỗ trợ:* Min rút siêu thấp rút thẳng Bank/Momo.')
]
for k, v in defaults:
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
conn.commit()

# Hàm lấy cài đặt từ DB
def get_set(key):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else ""

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
    return True if get_set('bao_tri') == 'on' else False

def is_maintenance(uid):
    return check_bao_tri() and str(uid) != ADMIN_ID

def get_today_str():
    return datetime.now().strftime("%Y-%m-%d")

# ================= SERVER WEB RENDER (DASHBOARD ADMIN NÂNG CẤP) =================
app = Flask(__name__)

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
    cursor.execute("SELECT user_id, balance, total_tasks, status FROM users ORDER BY total_tasks DESC")
    users = cursor.fetchall()
    tong_mem = len(users)
    tong_link = sum(u[2] for u in users)
    tong_du = sum(u[1] for u in users)

    # Đơn rút tiền
    cursor.execute("SELECT id, user_id, amount, info FROM withdrawals WHERE status='pending' ORDER BY id DESC")
    withdrawals = cursor.fetchall()

    html = f"""
    <html>
    <head>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <title>HT TOOL - VVIP DASHBOARD</title>
        <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700&family=Inter:wght@400;600&display=swap');
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Inter', sans-serif; background: #0b0f19; color: #f8fafc; overflow-x: hidden; }}
            .navbar {{ background: #111827; padding: 15px 20px; display: flex; align-items: center; border-bottom: 1px solid #1f2937; position: sticky; top: 0; z-index: 100; }}
            .menu-btn {{ font-size: 24px; color: #38bdf8; cursor: pointer; background: none; border: none; margin-right: 15px; }}
            .logo {{ font-family: 'Orbitron', sans-serif; font-size: 18px; color: #38bdf8; font-weight: bold; text-transform: uppercase; }}
            
            .sidebar {{ position: fixed; top: 55px; left: -250px; width: 250px; height: calc(100vh - 55px); background: #111827; transition: 0.3s; padding: 20px 0; border-right: 1px solid #1f2937; z-index: 99; }}
            .sidebar.active {{ left: 0; }}
            .sidebar a {{ display: flex; align-items: center; justify-content: space-between; padding: 15px 25px; color: #94a3b8; text-decoration: none; font-size: 15px; border-left: 3px solid transparent; cursor: pointer; transition: 0.2s; }}
            .sidebar a:hover, .sidebar a.active {{ background: #1f2937; color: #38bdf8; border-left-color: #38bdf8; }}
            .sidebar a i {{ margin-right: 10px; width: 20px; }}

            .main-content {{ padding: 20px; transition: 0.3s; }}
            .tab-content {{ display: none; animation: fadeIn 0.3s; }}
            .tab-content.active {{ display: block; }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            
            .uptime-box {{ background: linear-gradient(135deg, #0ea5e9 0%, #3b82f6 100%); padding: 15px; border-radius: 12px; text-align: center; font-weight: bold; font-size: 16px; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3); }}
            
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 25px; }}
            .stat-box {{ background: #1f2937; padding: 20px; border-radius: 12px; border: 1px solid #374151; }}
            .stat-box h3 {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; margin-bottom: 8px; }}
            .stat-box p {{ font-size: 20px; font-weight: 700; color: #fff; font-family: 'Orbitron', sans-serif; }}
            
            .card {{ background: #1f2937; border-radius: 12px; border: 1px solid #374151; padding: 20px; margin-bottom: 20px; }}
            .card h3 {{ color: #38bdf8; margin-bottom: 15px; font-size: 16px; border-bottom: 1px solid #374151; padding-bottom: 10px; }}
            
            .table-container {{ overflow-x: auto; }}
            table {{ width: 100%; border-collapse: collapse; min-width: 500px; }}
            th, td {{ padding: 12px 10px; text-align: left; border-bottom: 1px solid #374151; font-size: 13px; }}
            th {{ background: #111827; color: #94a3b8; text-transform: uppercase; }}
            
            .btn {{ padding: 6px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; text-decoration: none; color: white; display: inline-block; cursor: pointer; border: none; margin-right: 5px; }}
            .btn-green {{ background: #10b981; }} .btn-red {{ background: #ef4444; }} .btn-blue {{ background: #3b82f6; }}
            .badge-red {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 3px 6px; border-radius: 4px; font-size: 10px; }}
            
            /* Form Cài đặt */
            .input-group {{ margin-bottom: 15px; }}
            .input-group label {{ display: block; color: #94a3b8; font-size: 13px; margin-bottom: 5px; }}
            .input-group input, .input-group textarea {{ width: 100%; padding: 10px; background: #0b0f19; border: 1px solid #374151; color: white; border-radius: 6px; font-family: inherit; }}
            .btn-save {{ width: 100%; padding: 12px; background: #38bdf8; color: #0b0f19; font-weight: bold; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; }}
        </style>
    </head>
    <body>
        <div class="navbar">
            <button class="menu-btn" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>
            <div class="logo">HT TOOL ADMIN</div>
        </div>

        <div class="sidebar" id="sidebar">
            <a onclick="switchTab('tab1', this)" class="menu-item active"><div><i class="fas fa-chart-line"></i> Tổng Quan</div></a>
            <a onclick="switchTab('tab_duyet', this)" class="menu-item"><div><i class="fas fa-file-invoice-dollar"></i> Duyệt Rút Lúa</div> <span style="background:#ef4444;color:white;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:bold;">{len(withdrawals)}</span></a>
            <a onclick="switchTab('tab2', this)" class="menu-item"><div><i class="fas fa-users"></i> Quản Lý User</div></a>
            <a onclick="switchTab('tab3', this)" class="menu-item"><div><i class="fas fa-cogs"></i> Cài Đặt API & Giá</div></a>
            <a onclick="switchTab('tab4', this)" class="menu-item"><div><i class="fas fa-bullhorn"></i> Gửi Thông Báo</div></a>
        </div>

        <div class="main-content" id="main">
            <div id="tab1" class="tab-content active">
                <div class="uptime-box"><i class="fas fa-clock"></i> Thời gian Bot sống: {uptime_str}</div>
                <div class="stats-grid">
                    <div class="stat-box"><h3><i class="fas fa-users"></i> Tổng Mem</h3><p>{tong_mem}</p></div>
                    <div class="stat-box"><h3><i class="fas fa-link"></i> Link Đã Cày</h3><p>{tong_link}</p></div>
                    <div class="stat-box"><h3><i class="fas fa-wallet"></i> Lúa Tồn Đọng</h3><p style="color:#10b981;">{tong_du:,}đ</p></div>
                    <div class="stat-box"><h3><i class="fas fa-clock"></i> Đơn Chờ Duyệt</h3><p style="color:#ef4444;">{len(withdrawals)}</p></div>
                </div>
            </div>

            <div id="tab_duyet" class="tab-content">
                <div class="card">
                    <h3><i class="fas fa-money-check-alt"></i> DANH SÁCH YÊU CẦU RÚT TIỀN</h3>
                    <div class="table-container">
                        <table>
                            <tr><th>Mã</th><th>ID User</th><th>Số Tiền</th><th>Thông tin Ngân Hàng</th><th>Hành Động</th></tr>
    """
    for w in withdrawals:
        html += f"""
                            <tr>
                                <td>#{w[0]}</td><td>{w[1]}</td><td style='color:#10b981;font-weight:bold;'>{w[2]:,}đ</td><td>{w[3]}</td>
                                <td>
                                    <a href="/admin/don/{w[0]}/accept" class="btn btn-green"><i class="fas fa-check"></i> Duyệt</a>
                                    <a href="/admin/don/{w[0]}/reject" class="btn btn-red"><i class="fas fa-times"></i> Hủy</a>
                                </td>
                            </tr>
        """
    html += f"""
                        </table>
                    </div>
                </div>
            </div>

            <div id="tab2" class="tab-content">
                <div class="card">
                    <h3><i class="fas fa-users-cog"></i> Danh Sách Tài Khoản</h3>
                    <div class="table-container">
                        <table>
                            <tr><th>ID Telegram</th><th>Trạng Thái</th><th>Số Dư</th><th>Tổng Link</th><th>Hành Động</th></tr>
    """
    for u in users:
        stt = "Active" if u[3] == 'active' else "<span class='badge-red'>Banned</span>"
        btn = f"<a href='/{ADMIN_ID}/ban/{u[0]}' class='btn btn-red'>BAN</a>" if u[3] == 'active' else f"<a href='/{ADMIN_ID}/unban/{u[0]}' class='btn btn-green'>MỞ</a>"
        html += f"<tr><td>{u[0]}</td><td>{stt}</td><td style='color:#10b981;font-weight:bold;'>{u[1]:,}đ</td><td>{u[2]}</td><td>{btn}</td></tr>"
    
    html += f"""
                        </table>
                    </div>
                </div>
            </div>

            <div id="tab3" class="tab-content">
                <div class="card">
                    <h3><i class="fas fa-sliders-h"></i> THAY ĐỔI CẤU HÌNH HỆ THỐNG</h3>
                    <form action="/admin/save_settings" method="POST">
                        <div class="input-group">
                            <label>🔑 Token API Vượt Link (Uptolink, Cuty...):</label>
                            <input type="text" name="api_uptolink" value="{get_set('api_uptolink')}">
                        </div>
                        <div class="stats-grid">
                            <div class="input-group">
                                <label>💵 Tiền thưởng 1 Link (đ):</label>
                                <input type="number" name="tien_upto" value="{get_set('tien_upto')}">
                            </div>
                            <div class="input-group">
                                <label>🏦 Tiền thưởng cài MB Bank (đ):</label>
                                <input type="number" name="tien_mb" value="{get_set('tien_mb')}">
                            </div>
                            <div class="input-group">
                                <label>💳 Min Rút Lúa (đ):</label>
                                <input type="number" name="min_rut" value="{get_set('min_rut')}">
                            </div>
                        </div>
                        <div class="input-group">
                            <label>📝 Lời chào lúc bấm /start (Viết văn tùy thích):</label>
                            <textarea name="start_msg" rows="6">{get_set('start_msg')}</textarea>
                        </div>
                        <button type="submit" class="btn-save"><i class="fas fa-save"></i> LƯU THAY ĐỔI</button>
                    </form>
                </div>
            </div>

            <div id="tab4" class="tab-content">
                <div class="card">
                    <h3><i class="fas fa-bullhorn"></i> PHÁT LOA TOÀN SERVER</h3>
                    <form action="/admin/broadcast" method="POST">
                        <div class="input-group">
                            <label>Nhập nội dung muốn thông báo tới TẤT CẢ AE:</label>
                            <textarea name="tb_msg" rows="5" placeholder="Ví dụ: Đã update link mới, ae vào cày..."></textarea>
                        </div>
                        <button type="submit" class="btn-save" style="background:#ef4444; color:white;"><i class="fas fa-paper-plane"></i> GỬI THÔNG BÁO NGAY</button>
                    </form>
                </div>
            </div>

        </div>

        <script>
            function toggleSidebar() {{ document.getElementById('sidebar').classList.toggle('active'); }}
            function switchTab(tabId, element) {{
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
                element.classList.add('active');
                document.getElementById('sidebar').classList.remove('active');
            }}
        </script>
    </body>
    </html>
    """
    return html

# --- ROUTE XỬ LÝ FORM TỪ WEB ---
@app.route('/admin/save_settings', methods=['POST'])
def save_settings():
    for key, val in request.form.items():
        cursor.execute("UPDATE settings SET value=? WHERE key=?", (val, key))
    conn.commit()
    return "<script>alert('Đã lưu cấu hình mới. Áp dụng ngay lập tức!'); window.location.href='/';</script>"

@app.route('/admin/broadcast', methods=['POST'])
def broadcast():
    msg = request.form.get('tb_msg')
    if msg:
        cursor.execute("SELECT user_id FROM users")
        for u in cursor.fetchall():
            try: bot.send_message(u[0], f"📢 *THÔNG BÁO TỪ ADMIN*\n\n{msg}", parse_mode="Markdown")
            except: pass
    return "<script>alert('Đã bắn thông báo cho toàn bộ Dân Cày!'); window.location.href='/';</script>"

@app.route('/admin/don/<int:did>/<action>')
def xu_ly_don_web(did, action):
    cursor.execute("SELECT user_id, amount FROM withdrawals WHERE id=? AND status='pending'", (did,))
    don = cursor.fetchone()
    if don:
        uid, amount = don[0], don[1]
        if action == 'accept':
            cursor.execute("UPDATE withdrawals SET status='accepted' WHERE id=?", (did,))
            try: bot.send_message(uid, f"🎉 *TINH TINH!*\nLệnh rút `{amount:,}đ` của bạn đã được Admin chuyển khoản thành công!", parse_mode="Markdown")
            except: pass
        elif action == 'reject':
            cursor.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (did,))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid)) # Hoàn tiền
            try: bot.send_message(uid, f"⚠️ *ĐƠN BỊ HỦY!*\nĐơn rút `{amount:,}đ` bị TỪ CHỐI (Sai STK). Tiền đã trả lại vào Bot.", parse_mode="Markdown")
            except: pass
        conn.commit()
    return "<script>window.location.href='/';</script>"

@app.route(f'/{ADMIN_ID}/ban/<int:uid>')
def ban_user(uid):
    cursor.execute("UPDATE users SET status='banned' WHERE user_id=?", (uid,))
    conn.commit()
    return f"<script>window.location.href='/';</script>"

@app.route(f'/{ADMIN_ID}/unban/<int:uid>')
def unban_user(uid):
    cursor.execute("UPDATE users SET status='active' WHERE user_id=?", (uid,))
    conn.commit()
    return f"<script>window.location.href='/';</script>"

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

    tien_mb = int(get_set('tien_mb'))
    photo_id = message.photo[-1].file_id
    markup_duyet = InlineKeyboardMarkup()
    markup_duyet.row(
        InlineKeyboardButton(f"✅ DUYỆT +{tien_mb:,}đ", callback_data=f"bank_duyet_{uid}"),
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
    tien_mb = int(get_set('tien_mb'))
    
    if action == 'duyet':
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (tien_mb, target_uid))
        conn.commit()
        bot.edit_message_caption("✅ *ĐÃ DUYỆT ĐƠN VÀ CỘNG TIỀN THÀNH CÔNG!*", chat_id=ADMIN_ID, message_id=call.message.message_id, parse_mode="Markdown")
        try: bot.send_message(target_uid, f"🎉 *CHÚC MỪNG!*\nAdmin đã duyệt thành công nhiệm vụ MB Bank của bạn.\n\n💵 Lúa về ví: `+{tien_mb:,}đ`\n👉 Bấm Rút Lúa ngay thôi ae!", parse_mode="Markdown")
        except: pass
    elif action == 'huy':
        bot.edit_message_caption("❌ *ĐÃ TỪ CHỐI BỨC ẢNH NÀY!*", chat_id=ADMIN_ID, message_id=call.message.message_id, parse_mode="Markdown")
        try: bot.send_message(target_uid, f"⚠️ *THÔNG BÁO TỪ ADMIN*\nNhiệm vụ MB Bank của bạn bị TỪ CHỐI do ảnh không hợp lệ.\n\n🎧 Cần hỗ trợ liên hệ {ADMIN_USERNAME}", parse_mode="Markdown")
        except: pass

# ================= LỆNH ADMIN CONTROL (BACKUP) =================
@bot.message_handler(commands=['tb', 'baotri'])
def admin_commands(message):
    user_id = str(message.chat.id)
    if user_id != ADMIN_ID: return
        
    cmd = message.text.split()[0]
    if cmd == '/tb':
        bot.send_message(user_id, "👉 Sếp hãy dùng tính năng GỬI THÔNG BÁO trên trang Web Dashboard cho tiện nhé!")

    elif cmd == '/baotri':
        parts = message.text.split()
        if len(parts) > 1 and parts[1] in ['on', 'off']:
            cursor.execute("UPDATE settings SET value=? WHERE key='bao_tri'", (parts[1],))
            conn.commit()
            bot.send_message(user_id, f"🛠 Trạng thái bảo trì: **{parts[1].upper()}**")
        else:
            bot.send_message(user_id, "⚠️ Dùng: `/baotri on` hoặc `/baotri off`")

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
        # Lấy lời chào từ Setting trên Web
        msg_start = get_set('start_msg')
        bot.send_message(uid, msg_start, parse_mode="Markdown", reply_markup=menu_chinh())

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
        tien_mb = int(get_set('tien_mb'))
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(f"🏦 Nhiệm Vụ Bank (+{tien_mb:,}đ)", callback_data="menu_bank"))
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
        min_rut = int(get_set('min_rut'))
        
        if bal >= min_rut:
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
            bot.send_message(uid, f"⚠️ Số dư của bạn: `{bal:,}đ`.\n\n❌ *Chưa đủ điều kiện rút!* Phải cày đủ Min rút là `{min_rut:,}đ` nhé ae!", parse_mode="Markdown")

def process_withdraw(message, max_amount):
    uid = message.chat.id
    stk_info = message.text
    
    # TRỪ TIỀN VÀ LƯU ĐƠN LÊN WEB ADMIN
    cursor.execute("UPDATE users SET balance = 0 WHERE user_id=?", (uid,))
    cursor.execute("INSERT INTO withdrawals (user_id, amount, info, time_created) VALUES (?, ?, ?, ?)", (uid, max_amount, stk_info, time.time()))
    conn.commit()
    
    bot.send_message(uid, "✅ *ĐƠN ĐÃ LÊN HỆ THỐNG!*\nChờ Admin kiểm tra và duyệt tiền nhé.", parse_mode="Markdown", reply_markup=menu_chinh())
    
    # Báo qua Telegram cho Sếp biết để lên Web check
    try: bot.send_message(ADMIN_ID, f"🚨 *CÓ ĐƠN RÚT LÚA MỚI*\nID: `{uid}`\nTiền: `{max_amount:,}đ`\n👉 Sếp hãy mở link Web Dashboard, sang Tab **Duyệt Rút Lúa** để chuyển khoản nhé!", parse_mode="Markdown")
    except: pass

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
        tien_mb = int(get_set('tien_mb'))
        msg = f"""🚀 *NHIỆM VỤ ĐẶC BIỆT: TẢI APP MB BANK* 🚀
━━━━━━━━━━━━━━━━━━
💰 *Thưởng nóng:* `{tien_mb:,}đ` vào ví Bot.

📝 *HƯỚNG DẪN CÁC BƯỚC:*
1️⃣ Bấm vào link dưới đây để Tải App:
👉 [TẢI MB BANK TẠI ĐÂY]({LINK_MB})
2️⃣ Mở App lên, tiến hành Đăng ký tài khoản và Xác thực khuôn mặt (eKYC) thành công. *(Lưu ý không thoát app giữa chừng)*.
3️⃣ Đăng ký xong, bạn Đăng nhập vào App MB Bank.
4️⃣ Chụp lại **Ảnh màn hình** tài khoản của bạn (Phải rõ ràng, không lấy ảnh mạng).
5️⃣ **Gửi trực tiếp bức ảnh đó vào khung chat này.**

⏳ Admin sẽ kiểm tra và cộng ngay `{tien_mb:,}đ` cho bạn!"""
        bot.edit_message_text(msg, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown", disable_web_page_preview=True)

    elif call.data == "menu_link":
        today = get_today_str()
        tien_upto = int(get_set('tien_upto'))
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='uptolink'", (uid, today))
        count_upto = cursor.fetchone()[0]

        markup = InlineKeyboardMarkup()
        if count_upto < MAX_UPTO:
            markup.row(InlineKeyboardButton(f"🔗 Vượt Uptolink (+{tien_upto}đ) [{count_upto}/{MAX_UPTO}]", callback_data="get_uptolink"))
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

        # Lấy API KEY và TIỀN thưởng từ Web Dashboard
        api_upto_hientai = get_set('api_uptolink')
        tien_upto_hientai = int(get_set('tien_upto'))

        try:
            res = requests.get("https://uptolink.one/api", params={"api": api_upto_hientai, "url": target}).json()
            short_url = res.get("shortenedUrl") if res.get("status") == "success" else None
            if short_url:
                cursor.execute("INSERT INTO tasks (task_id, user_id, task_type, status, reward, date_str) VALUES (?, ?, 'uptolink', 'pending', ?, ?)", (tid, uid, tien_upto_hientai, today))
                conn.commit()
                bot.send_message(uid, f"🔗 *UPTOLINK (+{tien_upto_hientai}đ):*\n`{short_url}`\n\n_(Vượt xong quay lại Bot giải toán nhận tiền)_", parse_mode="Markdown")
            else:
                bot.send_message(uid, "❌ API Web đang bận hoặc Sai Token, nhấp lại nút đi ông.")
        except:
            bot.send_message(uid, "❌ Lỗi mạng máy chủ.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
