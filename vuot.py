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

# ================= CẤU HÌNH BOT CƠ BẢN =================
BOT_TOKEN = "8803256348:AAH58katT66W1DrHvw445OTKv2rLGgh88r4"
ADMIN_ID = "8781909366" 
ADMIN_USERNAME = "@vanminh2826"
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
    ('max_upto', '200'),
    ('api_bbmkts', 'c3217254268503da6667fab4'),
    ('tien_bbmkts', '400'),
    ('max_bbmkts', '1'),
    ('tien_mb', '70000'),
    ('link_mb', 'https://mbbank.onelink.me/QPF5?pid=SF%20Email%20Warmup&c=SF_Email_WarmUP_AppInstall&af_force_deeplink=true&af_dp=mbbank%3A%2F%2F&referral_code=39OIJCU6S6FMDBPLDVAAX'),
    ('min_rut', '10000'),
    ('link_group', 'https://t.me/botkiemlua_group'),
    ('start_msg', '👑 *CHÀO MỪNG ĐẾN VỚI HỆ THỐNG KIẾM TIỀN VIP* 👑\n\n💰 *Thu nhập thụ động - Rút tiền mỗi ngày*\n\n🚀 *Quy trình lụm lúa:*\n1️⃣ Chọn nút *🚀 NGUỒN NHIỆM VỤ*.\n2️⃣ Cày Link hoặc Đăng ký App để bào tiền.\n\n💳 *Hỗ trợ:* Min rút siêu thấp rút thẳng Bank/Thẻ Cào.')
]
for k, v in defaults:
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
conn.commit()

# Hàm lấy cài đặt từ DB
def get_set(key, default_val=""):
    cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
    res = cursor.fetchone()
    return res[0] if res else default_val

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
    uptime_sec = int(time.time() - START_TIME)
    d, h, m, s = uptime_sec // 86400, (uptime_sec % 86400) // 3600, (uptime_sec % 3600) // 60, uptime_sec % 60
    uptime_str = f"{d} Ngày {h:02d}:{m:02d}:{s:02d}"

    cursor.execute("SELECT user_id, balance, total_tasks, status FROM users ORDER BY total_tasks DESC")
    users = cursor.fetchall()
    tong_mem = len(users)
    tong_link = sum(u[2] for u in users)
    tong_du = sum(u[1] for u in users)

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
            .navbar {{ background: #111827; padding: 15px 20px; display: flex; align-items: center; border-bottom: 1px solid #1f2937; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.5); }}
            .menu-btn {{ font-size: 24px; color: #38bdf8; cursor: pointer; background: none; border: none; margin-right: 15px; }}
            .logo {{ font-family: 'Orbitron', sans-serif; font-size: 18px; color: #38bdf8; font-weight: bold; text-transform: uppercase; text-shadow: 0 0 10px rgba(56, 189, 248, 0.5); }}
            
            .sidebar {{ position: fixed; top: 55px; left: -250px; width: 250px; height: calc(100vh - 55px); background: #111827; transition: 0.3s; padding: 20px 0; border-right: 1px solid #1f2937; z-index: 99; overflow-y: auto; }}
            .sidebar.active {{ left: 0; }}
            .sidebar a {{ display: flex; align-items: center; justify-content: space-between; padding: 15px 25px; color: #94a3b8; text-decoration: none; font-size: 14px; border-left: 3px solid transparent; cursor: pointer; transition: 0.2s; }}
            .sidebar a:hover, .sidebar a.active {{ background: #1f2937; color: #38bdf8; border-left-color: #38bdf8; }}
            .sidebar a i {{ margin-right: 10px; width: 20px; }}

            .main-content {{ padding: 20px; transition: 0.3s; }}
            .tab-content {{ display: none; animation: fadeIn 0.3s; }}
            .tab-content.active {{ display: block; }}
            @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            
            .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px; }}
            .stat-box {{ background: #1f2937; padding: 15px; border-radius: 12px; border: 1px solid #374151; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .stat-box h3 {{ font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 5px; }}
            .stat-box p {{ font-size: 18px; font-weight: bold; color: #fff; }}
            
            .card {{ background: #1f2937; border-radius: 12px; border: 1px solid #374151; padding: 15px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }}
            .card h3 {{ color: #38bdf8; margin-bottom: 15px; font-size: 15px; border-bottom: 1px solid #374151; padding-bottom: 10px; text-transform: uppercase; }}
            
            .table-container {{ overflow-x: auto; }}
            table {{ width: 100%; border-collapse: collapse; min-width: 500px; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #374151; font-size: 13px; }}
            th {{ background: #111827; color: #94a3b8; }}
            
            .btn {{ padding: 6px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; text-decoration: none; color: white; display: inline-block; cursor: pointer; border: none; margin-right: 5px; transition: 0.2s; }}
            .btn:hover {{ opacity: 0.8; }}
            .btn-green {{ background: #10b981; }} .btn-red {{ background: #ef4444; }} .btn-blue {{ background: #3b82f6; }}
            .badge-red {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; padding: 3px 6px; border-radius: 4px; font-size: 10px; font-weight:bold; }}
            .badge-green {{ background: rgba(16, 185, 129, 0.2); color: #10b981; padding: 3px 6px; border-radius: 4px; font-size: 10px; font-weight:bold; }}
            
            /* Form Cài đặt */
            .input-group {{ margin-bottom: 12px; }}
            .input-group label {{ display: block; color: #94a3b8; font-size: 12px; margin-bottom: 4px; font-weight:bold; }}
            .input-group input, .input-group textarea, .input-group select {{ width: 100%; padding: 8px; background: #0b0f19; border: 1px solid #374151; color: white; border-radius: 6px; }}
            .btn-save {{ width: 100%; padding: 12px; background: #38bdf8; color: #0b0f19; font-weight: bold; border: none; border-radius: 6px; font-size: 14px; cursor: pointer; text-transform: uppercase; box-shadow: 0 4px 10px rgba(56, 189, 248, 0.3); }}
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
            <a onclick="switchTab('tab3', this)" class="menu-item"><div><i class="fas fa-cogs"></i> Cài Đặt Nâng Cao</div></a>
            <a onclick="switchTab('tab4', this)" class="menu-item"><div><i class="fas fa-bullhorn"></i> Gửi TB Server</div></a>
        </div>

        <div class="main-content">
            <div id="tab1" class="tab-content active">
                <div class="card" style="text-align:center; color:#38bdf8; font-weight:bold; font-size: 18px;"><i class="fas fa-satellite-dish"></i> Bot Uptime: {uptime_str}</div>
                <div class="stats-grid">
                    <div class="stat-box"><h3>Tổng Mem</h3><p>{len(users)}</p></div>
                    <div class="stat-box"><h3>Link Đã Cày</h3><p>{tong_link}</p></div>
                    <div class="stat-box"><h3>Lúa Đang Tồn</h3><p style="color:#10b981;">{tong_du:,}đ</p></div>
                    <div class="stat-box"><h3>Đơn Chờ Duyệt</h3><p style="color:#ef4444;">{len(withdrawals)}</p></div>
                </div>
            </div>

            <div id="tab_duyet" class="tab-content">
                <div class="card">
                    <h3><i class="fas fa-money-check-alt"></i> DANH SÁCH YÊU CẦU RÚT TIỀN / ĐỔI THẺ</h3>
                    <div class="table-container">
                        <table>
                            <tr><th>Mã</th><th>ID User</th><th>Tiền</th><th>Thông tin</th><th>Hành Động</th></tr>
    """
    for w in withdrawals:
        html += f"""<tr>
            <td>#{w[0]}</td><td>{w[1]}</td><td style='color:#10b981;font-weight:bold;'>{w[2]:,}đ</td><td>{w[3]}</td>
            <td>
                <a href="/admin/don/{w[0]}/accept" class="btn btn-green"><i class="fas fa-check"></i> Duyệt Bill</a>
                <a href="/admin/don/{w[0]}/reject" class="btn btn-red"><i class="fas fa-times"></i> Hủy & Hoàn Tiền</a>
            </td>
        </tr>"""
    
    html += f"""
                        </table>
                    </div>
                </div>
            </div>

            <div id="tab2" class="tab-content">
                <div class="card">
                    <h3><i class="fas fa-users-cog"></i> TÀI KHOẢN DÂN CÀY</h3>
                    <div class="table-container">
                        <table>
                            <tr><th>ID</th><th>Số Dư</th><th>Link</th><th>Trạng Thái</th></tr>
    """
    for u in users:
        if u[3] == 'active':
            stt = "<span class='badge-green'>Bình thường</span>"
            btn = f"<a href='/{ADMIN_ID}/ban/{u[0]}' class='btn btn-red'><i class='fas fa-ban'></i> BAN ID</a>"
        else:
            stt = "<span class='badge-red'>Bị Khóa (BAN)</span>"
            btn = f"<a href='/{ADMIN_ID}/unban/{u[0]}' class='btn btn-green'><i class='fas fa-unlock'></i> MỞ BAN</a>"
            
        html += f"<tr><td>{u[0]}</td><td style='color:#10b981;font-weight:bold;'>{u[1]:,}đ</td><td>{u[2]}</td><td>{stt}<br><br>{btn}</td></tr>"
    
    html += f"""
                        </table>
                    </div>
                </div>
            </div>

            <div id="tab3" class="tab-content">
                <div class="card">
                    <form action="/admin/save_settings" method="POST">
                        <h3><i class="fas fa-server"></i> TRẠNG THÁI SERVER</h3>
                        <div class="input-group">
                            <label>Bảo trì Bot (Tạm dừng mọi hoạt động):</label>
                            <select name="bao_tri">
                                <option value="off" {"selected" if get_set('bao_tri') == 'off' else ""}>🟢 ĐANG HOẠT ĐỘNG (OFF BẢO TRÌ)</option>
                                <option value="on" {"selected" if get_set('bao_tri') == 'on' else ""}>🔴 TẠM KHÓA SERVER (ON BẢO TRÌ)</option>
                            </select>
                        </div>
                        <div class="input-group"><label>🌐 Link Nhóm Giao Lưu (Sẽ hiện trong Lệnh Start & Trợ Giúp):</label><input type="text" name="link_group" value="{get_set('link_group')}"></div>

                        <hr style="border-color:#374151; margin:15px 0;">
                        <h3><i class="fas fa-link"></i> Nguồn Uptolink</h3>
                        <div class="input-group"><label>API Token:</label><input type="text" name="api_uptolink" value="{get_set('api_uptolink')}"></div>
                        <div style="display:flex;gap:10px;">
                            <div class="input-group" style="flex:1;"><label>Giá (đ):</label><input type="number" name="tien_upto" value="{get_set('tien_upto')}"></div>
                            <div class="input-group" style="flex:1;"><label>Lượt Max/Ngày:</label><input type="number" name="max_upto" value="{get_set('max_upto')}"></div>
                        </div>
                        
                        <hr style="border-color:#374151; margin:15px 0;">
                        <h3><i class="fas fa-link"></i> Nguồn BBMKTS</h3>
                        <div class="input-group"><label>API Token:</label><input type="text" name="api_bbmkts" value="{get_set('api_bbmkts')}"></div>
                        <div style="display:flex;gap:10px;">
                            <div class="input-group" style="flex:1;"><label>Giá (đ):</label><input type="number" name="tien_bbmkts" value="{get_set('tien_bbmkts')}"></div>
                            <div class="input-group" style="flex:1;"><label>Lượt Max/Ngày:</label><input type="number" name="max_bbmkts" value="{get_set('max_bbmkts')}"></div>
                        </div>

                        <hr style="border-color:#374151; margin:15px 0;">
                        <h3><i class="fas fa-wallet"></i> Nhiệm Vụ App & Rút Tiền</h3>
                        <div class="input-group"><label>Link tải MB Bank của Admin:</label><input type="text" name="link_mb" value="{get_set('link_mb')}"></div>
                        <div style="display:flex;gap:10px;">
                            <div class="input-group" style="flex:1;"><label>Tiền tải MB (đ):</label><input type="number" name="tien_mb" value="{get_set('tien_mb')}"></div>
                            <div class="input-group" style="flex:1;"><label>Min Rút (đ):</label><input type="number" name="min_rut" value="{get_set('min_rut')}"></div>
                        </div>
                        <div class="input-group">
                            <label>📝 Lời chào lúc bấm /start:</label>
                            <textarea name="start_msg" rows="4">{get_set('start_msg')}</textarea>
                        </div>
                        <button type="submit" class="btn-save"><i class="fas fa-save"></i> LƯU TẤT CẢ THAY ĐỔI</button>
                    </form>
                </div>
            </div>

            <div id="tab4" class="tab-content">
                <div class="card">
                    <h3><i class="fas fa-bullhorn"></i> GỬI THÔNG BÁO TOÀN SERVER</h3>
                    <form action="/admin/broadcast" method="POST">
                        <div class="input-group">
                            <label>Nhập nội dung (Hỗ trợ định dạng Markdown):</label>
                            <textarea name="tb_msg" rows="5" placeholder="Ví dụ: Đã update link mới, ae vào cày..."></textarea>
                        </div>
                        <button type="submit" class="btn-save" style="background:#ef4444; color:white;"><i class="fas fa-paper-plane"></i> GỬI NGAY CHO DÂN CÀY</button>
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
    return "<script>alert('Đã gửi thông báo!'); window.location.href='/';</script>"

@app.route('/admin/don/<int:did>/<action>')
def xu_ly_don_web(did, action):
    cursor.execute("SELECT user_id, amount, info FROM withdrawals WHERE id=? AND status='pending'", (did,))
    don = cursor.fetchone()
    if don:
        uid, amount, info = don[0], don[1], don[2]
        if action == 'accept':
            cursor.execute("UPDATE withdrawals SET status='accepted' WHERE id=?", (did,))
            
            # TẠO BILL THANH TOÁN XỊN SÒ GỬI CHO KHÁCH
            bill_msg = f"""🧾 *BIÊN LAI THANH TOÁN* 🧾
━━━━━━━━━━━━━━━━━━
✅ *Trạng thái:* Thành công
💰 *Số tiền:* `{amount:,}đ`
📝 *Nội dung:* {info}
⏱️ *Thời gian:* `{datetime.now().strftime('%H:%M %d/%m/%Y')}`
━━━━━━━━━━━━━━━━━━
🎉 *Cảm ơn bạn đã cày cuốc cùng HT TOOL!*"""
            if "THẺ:" in info:
                bill_msg += "\n\n⚠️ *Lưu ý:* Vui lòng kiểm tra tin nhắn Bot để nhận Mã Thẻ và Seri từ Admin!"
                
            try: bot.send_message(uid, bill_msg, parse_mode="Markdown")
            except: pass
            
        elif action == 'reject':
            cursor.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (did,))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, uid)) # Hoàn tiền
            
            bill_msg = f"""🧾 *BIÊN LAI THANH TOÁN* 🧾
━━━━━━━━━━━━━━━━━━
❌ *Trạng thái:* BỊ TỪ CHỐI / HỦY BỎ
💰 *Số tiền hoàn lại:* `{amount:,}đ`
📝 *Nội dung:* {info}
⚠️ *Lý do:* Sai thông tin Ngân hàng/Thẻ cào hoặc phát hiện gian lận.
━━━━━━━━━━━━━━━━━━
👉 Tiền đã được hoàn lại vào ví Bot của bạn."""
            try: bot.send_message(uid, bill_msg, parse_mode="Markdown")
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

# ================= RÚT TIỀN / ĐỔI THẺ (CHỐNG LỖI GẮT) =================
def input_rut_bank(message, max_amount):
    uid = message.chat.id
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (max_amount, uid))
    cursor.execute("INSERT INTO withdrawals (user_id, amount, info, time_created) VALUES (?, ?, ?, ?)", (uid, max_amount, f"BANK: {message.text}", time.time()))
    conn.commit()
    bot.send_message(uid, "✅ *ĐƠN BANK ĐÃ LÊN HỆ THỐNG!*\nChờ Admin duyệt và nhận Bill nhé.", parse_mode="Markdown", reply_markup=menu_chinh())
    try: bot.send_message(ADMIN_ID, f"🚨 *CÓ ĐƠN BANK MỚI*\nTiền: `{max_amount:,}đ`", parse_mode="Markdown")
    except: pass

def input_doi_the(message, max_amount):
    uid = message.chat.id
    text = message.text.strip().upper()
    
    try:
        if '-' not in text: raise Exception()
        mang, gia_str = text.split('-')
        mang = mang.strip()
        # Chuyển đổi linh hoạt: 10k, 10.000, 10,000 đều thành 10000
        gia = int(gia_str.strip().lower().replace('k', '000').replace(',', '').replace('.', ''))
        
        # Bắt lỗi nhập mệnh giá bậy bạ
        valid = [10000, 20000, 50000, 100000, 200000, 500000]
        if gia not in valid:
            bot.send_message(uid, "❌ *MỆNH GIÁ KHÔNG HỢP LỆ!*\n\n⚠️ Hệ thống chỉ hỗ trợ thẻ: `10k, 20k, 50k, 100k, 200k, 500k`.\n🚫 Mấy loại 15k, 23k, 40k... GHI VÀO SẼ BỊ TỪ CHỐI!\n\n👉 Vui lòng vào lại mục *💳 Rút Lúa* để đặt lệnh lại.", parse_mode="Markdown", reply_markup=menu_chinh())
            return
            
        if gia > max_amount:
            bot.send_message(uid, f"❌ Số dư của bạn không đủ để đổi thẻ {gia:,}đ!", reply_markup=menu_chinh())
            return
            
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (gia, uid))
        cursor.execute("INSERT INTO withdrawals (user_id, amount, info, time_created) VALUES (?, ?, ?, ?)", (uid, gia, f"THẺ: {mang} - {gia}", time.time()))
        conn.commit()
        bot.send_message(uid, f"✅ *ĐÃ LÊN ĐƠN ĐỔI THẺ {mang} {gia:,}đ!*\nVui lòng chờ Admin trả Thẻ + Seri vào tin nhắn này nhé.", parse_mode="Markdown", reply_markup=menu_chinh())
        
        try: bot.send_message(ADMIN_ID, f"🚨 *CÓ ĐƠN THẺ CÀO MỚI*\nLoại: {mang} - {gia:,}đ", parse_mode="Markdown")
        except: pass

    except:
        bot.send_message(uid, "❌ *BẠN NHẬP SAI ĐỊNH DẠNG!*\nVui lòng vào mục *💳 Rút Lúa* và làm lại từ đầu.", parse_mode="Markdown", reply_markup=menu_chinh())

@bot.callback_query_handler(func=lambda call: call.data.startswith("rut_"))
def chon_kieu_rut(call):
    uid = call.message.chat.id
    kieu = call.data.split("_")[1]
    
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (uid,))
    bal = cursor.fetchone()[0]
    min_rut = int(get_set('min_rut'))
    
    if bal < min_rut:
        return bot.edit_message_text(f"❌ Số dư của bạn là: `{bal:,}đ`. Cần cày đủ Min Rút là `{min_rut:,}đ` nhé!", chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
        
    if kieu == "bank":
        m = bot.edit_message_text(f"🏦 *RÚT VỀ NGÂN HÀNG / MOMO*\n💰 Đang có: `{bal:,}đ`\n\n✍️ Nhập thông tin theo mẫu:\n`NGÂN HÀNG - SỐ TÀI KHOẢN - TÊN`", chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
        bot.register_next_step_handler(m, input_rut_bank, bal)
    elif kieu == "the":
        huong_dan = (
            f"💳 *ĐỔI THẺ CÀO ĐIỆN THOẠI*\n"
            f"💰 Số dư đang có: `{bal:,}đ`\n\n"
            f"✍️ *HƯỚNG DẪN:* Nhập chính xác theo mẫu:\n"
            f"`TÊN NHÀ MẠNG - MỆNH GIÁ`\n"
            f"*(Ví dụ: VIETTEL - 10k)*\n\n"
            f"⚠️ *LƯU Ý CỰC KỲ QUAN TRỌNG:*\n"
            f"Chỉ chấp nhận các mệnh giá chuẩn: `10k, 20k, 50k, 100k, 200k, 500k`.\n"
            f"Ai cố tình ghi 15k, 40k... hệ thống sẽ không duyệt và hoàn tiền!"
        )
        m = bot.edit_message_text(huong_dan, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
        bot.register_next_step_handler(m, input_doi_the, bal)

# ================= MENU CHỨC NĂNG =================
@bot.message_handler(func=lambda m: m.text in ["🚀 NGUỒN NHIỆM VỤ 🚀", "🎧 Trợ Giúp", "👤 Thông Tin Acc", "👥 Đại Lý (Mời Bạn)", "💳 Rút Lúa", "🏆 Bảng Xếp Hạng"])
def handle_menu(message):
    uid = message.chat.id
    check_user(uid)
    if is_banned(uid): return bot.send_message(uid, "🚫 *Tài khoản bị khóa!*", parse_mode="Markdown")
    if is_maintenance(uid): return bot.send_message(uid, "🚧 *SERVER ĐANG BẢO TRÌ!* Vui lòng quay lại sau.", parse_mode="Markdown")

    cmd = message.text

    if cmd == "🚀 NGUỒN NHIỆM VỤ 🚀":
        today = get_today_str()
        
        # Đếm Uptolink
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='uptolink'", (uid, today))
        c_upto = cursor.fetchone()[0]
        m_upto = int(get_set('max_upto', 200))
        
        # Đếm BBMKTS
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='bbmkts'", (uid, today))
        c_bb = cursor.fetchone()[0]
        m_bb = int(get_set('max_bbmkts', 1))

        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton(f"🏦 Tải App MB (+{int(get_set('tien_mb')):,}đ)", callback_data="menu_bank"))
        markup.row(InlineKeyboardButton(f"🔗 Cày Uptolink [{c_upto}/{m_upto}]", callback_data="get_uptolink"))
        markup.row(InlineKeyboardButton(f"🔗 Cày BBMKTS [{c_bb}/{m_bb}]", callback_data="get_bbmkts"))
        
        bot.send_message(uid, "👇 *BẢNG NHIỆM VỤ HÔM NAY:*", parse_mode="Markdown", reply_markup=markup)
    
    elif cmd == "💳 Rút Lúa":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🏦 Rút Ngân Hàng", callback_data="rut_bank"), InlineKeyboardButton("💳 Đổi Thẻ Cào", callback_data="rut_the"))
        bot.send_message(uid, f"💰 Chọn phương thức nhận tiền:", parse_mode="Markdown", reply_markup=markup)
            
    elif cmd == "🏆 Bảng Xếp Hạng":
        markup = InlineKeyboardMarkup()
        markup.row(InlineKeyboardButton("🥇 Top Cày Link", callback_data="bxh_link"), InlineKeyboardButton("🔥 Top Ref", callback_data="bxh_ref"))
        bot.send_message(uid, "🏆 Chọn bảng xếp hạng:", reply_markup=markup)
        
    elif cmd == "🎧 Trợ Giúp":
        ht = f"🛡️ *TỔNG ĐÀI HỖ TRỢ* 🛡️\n━━━━━━━━━━━━━━━━━━\n👤 Admin xử lý Lỗi & Duyệt tiền: {ADMIN_USERNAME}\n\n👥 *Tham gia Nhóm Giao lưu để nhận thêm kèo mới:*\n👉 {get_set('link_group')}"
        bot.send_message(uid, ht, disable_web_page_preview=True, parse_mode="Markdown")
        
    elif cmd == "👤 Thông Tin Acc":
        cursor.execute("SELECT balance, total_tasks FROM users WHERE user_id=?", (uid,))
        d = cursor.fetchone()
        bot.send_message(uid, f"👤 *HỒ SƠ CỦA BẠN*\n╔═══════════════════╗\n 🆔 ID: `{uid}`\n 💵 Số Dư: `{d[0]:,}đ`\n 🎯 Đã cày: `{d[1]} nhiệm vụ`\n╚═══════════════════╝", parse_mode="Markdown")
        
    elif cmd == "👥 Đại Lý (Mời Bạn)":
        bot.send_message(uid, f"🤝 Thưởng: `{HOA_HONG_REF}đ`/link\n🔗 Link:\n`https://t.me/{bot.get_me().username}?start=ref{uid}`", parse_mode="Markdown")

# ================= API VƯỢT LINK (UPTOLINK & BBMKTS) =================
@bot.callback_query_handler(func=lambda call: call.data in ["get_uptolink", "get_bbmkts", "bxh_link", "bxh_ref", "menu_bank"])
def handle_tasks(call):
    uid = call.message.chat.id
    check_user(uid)
    if is_banned(uid) or is_maintenance(uid): return
    today = get_today_str()

    if call.data == "get_uptolink":
        c_upto = cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='uptolink'", (uid, today)).fetchone()[0]
        if c_upto >= int(get_set('max_upto', 200)): return bot.answer_callback_query(call.id, "⚠️ Hết lượt Uptolink hôm nay!", show_alert=True)
        
        bot.edit_message_text("⏳ Đang cào link Uptolink...", chat_id=uid, message_id=call.message.message_id)
        tid = 'task_' + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        target = f"https://telegram.me/{bot.get_me().username}?start={tid}"
        try:
            res = requests.get("https://uptolink.one/api", params={"api": get_set('api_uptolink'), "url": target}).json()
            if res.get("status") == "success":
                cursor.execute("INSERT INTO tasks (task_id, user_id, task_type, status, reward, date_str) VALUES (?, ?, 'uptolink', 'pending', ?, ?)", (tid, uid, int(get_set('tien_upto')), today))
                conn.commit()
                msg_link = f"🔗 *UPTOLINK (+{get_set('tien_upto')}đ):*\n`{res['shortenedUrl']}`\n\n💡 *HƯỚNG DẪN:* Nhấn vào link trên -> Xác minh Captcha -> Tìm nút 'Lấy mã' -> Vượt xong quay lại Bot giải toán để nhận lúa!"
                bot.send_message(uid, msg_link, parse_mode="Markdown")
            else: bot.send_message(uid, "❌ API Uptolink bận.")
        except: bot.send_message(uid, "❌ Lỗi mạng máy chủ.")

    elif call.data == "get_bbmkts":
        c_bb = cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND date_str=? AND status='completed' AND task_type='bbmkts'", (uid, today)).fetchone()[0]
        if c_bb >= int(get_set('max_bbmkts', 1)): return bot.answer_callback_query(call.id, "⚠️ Hết lượt BBMKTS hôm nay!", show_alert=True)
        
        bot.edit_message_text("⏳ Đang cào link BBMKTS...", chat_id=uid, message_id=call.message.message_id)
        tid = 'task_' + ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        target = f"https://telegram.me/{bot.get_me().username}?start={tid}"
        
        api_url = f"https://bbmkts.com/dapi?token={get_set('api_bbmkts')}&longurl={requests.utils.quote(target)}"
        try:
            res = requests.get(api_url).json()
            if res.get("status") == "success":
                cursor.execute("INSERT INTO tasks (task_id, user_id, task_type, status, reward, date_str) VALUES (?, ?, 'bbmkts', 'pending', ?, ?)", (tid, uid, int(get_set('tien_bbmkts')), today))
                conn.commit()
                msg_link = f"🔗 *BBMKTS (+{get_set('tien_bbmkts')}đ):*\n`{res['bbmktsUrl']}`\n\n💡 *HƯỚNG DẪN:* Bấm vào link -> Lướt tìm nút lấy mã -> Vượt xong quay lại Bot giải toán để nhận lúa!"
                bot.send_message(uid, msg_link, parse_mode="Markdown")
            else: bot.send_message(uid, f"❌ Lỗi BBMKTS: {res.get('message', 'Unkown')}")
        except: bot.send_message(uid, "❌ Lỗi mạng máy chủ BBMKTS.")

    elif call.data == "menu_bank":
        tien_mb = int(get_set('tien_mb'))
        msg = f"""🚀 *NHIỆM VỤ ĐẶC BIỆT: TẢI APP MB BANK* 🚀
💰 *Thưởng nóng:* `{tien_mb:,}đ`

📝 *HƯỚNG DẪN CHI TIẾT (ĐỌC KỸ TRÁNH MẤT TIỀN):*
Bước 1️⃣: Xóa app MB Bank cũ (nếu có trong máy). Nhấn vào link tải app bên dưới.
👉 *Link Tải App:* {get_set('link_mb')}
Bước 2️⃣: Mở app lên, chọn "Đăng ký ngay". Nhập SĐT, xác minh mã OTP.
Bước 3️⃣: Chụp mặt trước/sau CCCD và quay video khuôn mặt (eKYC).
Bước 4️⃣: Điền thông tin cá nhân. Tới phần Chọn Tài Khoản thì chọn loại Tài Khoản Miễn Phí.
Bước 5️⃣: **QUAN TRỌNG NHẤT:** MB Bank sẽ gửi Mật Khẩu về tin nhắn SMS. Bạn BẮT BUỘC phải dùng mật khẩu đó để ĐĂNG NHẬP lại vào App MB Bank lần đầu tiên.
Bước 6️⃣: Chụp ảnh Màn hình chính (Đã đăng nhập thành công) gửi vào đây để nhận tiền!

⏳ *Admin sẽ kiểm tra cực kỹ, làm đúng 100% lúa sẽ về ví!*"""
        bot.edit_message_text(msg, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown", disable_web_page_preview=True)

    elif call.data == "bxh_link":
        cursor.execute("SELECT user_id, total_tasks FROM users WHERE total_tasks > 0 ORDER BY total_tasks DESC LIMIT 10")
        msg = "🥇 *TOP CÀY CHAY*\n" + "\n".join([f"`{str(r[0])[:-3]}***` ➔ {r[1]} link" for r in cursor.fetchall()])
        bot.edit_message_text(msg, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
        
    elif call.data == "bxh_ref":
        cursor.execute("SELECT ref_by, COUNT(*) as c FROM users WHERE ref_by IS NOT NULL GROUP BY ref_by ORDER BY c DESC LIMIT 10")
        msg = "🔥 *TOP TUYỂN REF*\n" + "\n".join([f"`{str(r[0])[:-3]}***` ➔ {r[1]} mem" for r in cursor.fetchall()])
        bot.edit_message_text(msg, chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")

# ================= XỬ LÝ ẢNH TẢI APP & DUYỆT =================
@bot.message_handler(content_types=['photo'])
def xu_ly_anh(message):
    uid = message.chat.id
    if is_banned(uid) or is_maintenance(uid): return
    bot.reply_to(message, "✅ Đã nhận được ảnh! Hệ thống đã chuyển lên Admin, vui lòng chờ duyệt.")
    tien = int(get_set('tien_mb'))
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(f"✅ Duyệt {tien:,}đ", callback_data=f"bank_duyet_{uid}"), InlineKeyboardButton("❌ Hủy", callback_data=f"bank_huy_{uid}"))
    try: bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"🚨 *CÓ ĐƠN DUYỆT MB MỚI*\nID: `{uid}`", parse_mode="Markdown", reply_markup=markup)
    except: pass

@bot.callback_query_handler(func=lambda call: call.data.startswith('bank_'))
def duyet_bank(call):
    if str(call.message.chat.id) != ADMIN_ID: return
    action, uid = call.data.split('_')[1], int(call.data.split('_')[2])
    tien = int(get_set('tien_mb'))
    if action == 'duyet':
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (tien, uid))
        conn.commit()
        bot.edit_message_caption("✅ ĐÃ DUYỆT CỘNG TIỀN", chat_id=ADMIN_ID, message_id=call.message.message_id)
        
        bill_msg = f"""🧾 *BIÊN LAI THANH TOÁN* 🧾
━━━━━━━━━━━━━━━━━━
✅ *Trạng thái:* Thành công
💰 *Tiền thưởng MB:* `+{tien:,}đ`
⏱️ *Thời gian:* `{datetime.now().strftime('%H:%M %d/%m/%Y')}`
━━━━━━━━━━━━━━━━━━
🎉 *Cảm ơn bạn đã cày cuốc cùng HT TOOL!*"""
        try: bot.send_message(uid, bill_msg, parse_mode="Markdown")
        except: pass
    else:
        bot.edit_message_caption("❌ ĐÃ TỪ CHỐI ẢNH", chat_id=ADMIN_ID, message_id=call.message.message_id)
        try: bot.send_message(uid, f"⚠️ *THÔNG BÁO:* Ảnh nhiệm vụ MB Bank của bạn BỊ TỪ CHỐI do không hợp lệ hoặc sai luồng đăng ký.", parse_mode="Markdown")
        except: pass

# ================= XÁC MINH ROBOT GIẢI TOÁN / START =================
@bot.message_handler(commands=['start'])
def xu_ly_start(message):
    uid = message.chat.id
    check_user(uid)
    if is_banned(uid): return bot.send_message(uid, "🚫 *Tài khoản bị khóa vi phạm chính sách!*", parse_mode="Markdown")
    if is_maintenance(uid): return bot.send_message(uid, "🚧 *SERVER ĐANG BẢO TRÌ!*", parse_mode="Markdown")
    
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith('ref'):
        ref_id = parts[1].replace('ref', '')
        if str(ref_id) != str(uid):
            cursor.execute("UPDATE users SET ref_by=? WHERE user_id=? AND ref_by IS NULL", (ref_id, uid))
            conn.commit()

    if len(parts) > 1 and parts[1].startswith('task'):
        tid = parts[1]
        task = cursor.execute("SELECT reward FROM tasks WHERE task_id=? AND status='pending' AND user_id=?", (tid, uid)).fetchone()
        if task:
            a, b = random.randint(10, 30), random.randint(1, 20)
            ans = a + b
            cursor.execute("UPDATE tasks SET status='verifying', answer=?, time_created=? WHERE task_id=?", (ans, time.time(), tid))
            conn.commit()
            
            c = list(set([ans, ans+1, ans-2, ans+5]))[:4]
            if ans not in c: c[0] = ans
            random.shuffle(c)
            markup = InlineKeyboardMarkup()
            markup.row(InlineKeyboardButton(f"{c[0]}", callback_data=f"chk_{tid.split('_')[1]}_{c[0]}"), InlineKeyboardButton(f"{c[1]}", callback_data=f"chk_{tid.split('_')[1]}_{c[1]}"))
            markup.row(InlineKeyboardButton(f"{c[2]}", callback_data=f"chk_{tid.split('_')[1]}_{c[2]}"), InlineKeyboardButton(f"{c[3]}", callback_data=f"chk_{tid.split('_')[1]}_{c[3]}"))
            bot.send_message(uid, f"🧮 Xác minh Robot để nhận tiền:\n`{a} + {b} = ?`", parse_mode="Markdown", reply_markup=markup)
        else: bot.send_message(uid, "❌ Link nhiệm vụ đã hết hạn hoặc mã sai.")
    else: 
        # Hiển thị lời chào kèm Link Nhóm
        msg = f"{get_set('start_msg')}\n\n👥 *Tham gia Nhóm Hỗ Trợ/Giao Lưu:*\n👉 {get_set('link_group')}"
        bot.send_message(uid, msg, parse_mode="Markdown", reply_markup=menu_chinh())

@bot.callback_query_handler(func=lambda call: call.data.startswith('chk_'))
def check_toan(call):
    uid = call.message.chat.id
    tid, val = f"task_{call.data.split('_')[1]}", int(call.data.split('_')[2])
    data = cursor.execute("SELECT answer, reward, time_created FROM tasks WHERE task_id=? AND status='verifying'", (tid,)).fetchone()
    if not data: return bot.edit_message_text("❌ Mã không hợp lệ.", chat_id=uid, message_id=call.message.message_id)
        
    ans, rw, t = data
    if time.time() - t > 60:
        cursor.execute("UPDATE tasks SET status='expired' WHERE task_id=?", (tid,))
        conn.commit()
        return bot.edit_message_text("⏰ Quá 60s! Nhiệm vụ đã bị hủy.", chat_id=uid, message_id=call.message.message_id)

    if val == ans:
        cursor.execute("UPDATE users SET balance = balance + ?, total_tasks = total_tasks + 1 WHERE user_id=?", (rw, uid))
        cursor.execute("UPDATE tasks SET status='completed' WHERE task_id=?", (tid,))
        ref = cursor.execute("SELECT ref_by FROM users WHERE user_id=?", (uid,)).fetchone()[0]
        if ref: cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (HOA_HONG_REF, ref))
        conn.commit()
        bot.edit_message_text(f"🎊 Chính xác! Tiền cộng vào ví: `+{rw}đ`", chat_id=uid, message_id=call.message.message_id, parse_mode="Markdown")
    else:
        cursor.execute("UPDATE tasks SET status='failed' WHERE task_id=?", (tid,))
        conn.commit()
        bot.edit_message_text("❌ Tính toán sai bét! Nhiệm vụ thất bại.", chat_id=uid, message_id=call.message.message_id)

if __name__ == "__main__":
    threading.Thread(target=run_server).start()
    bot.infinity_polling()
