from flask import Flask, render_template, request, jsonify
from models import init_db, DatabaseManager, hash_user_id
from utils.crypto import generate_key, encrypt_session
from utils.score_monitor import serialize_session
from utils.dingtalk import notify_new_scores, notify_session_expired
from main import simulate_login
from utils.session_manager import get_session, reset_session
from scheduler import start_scheduler, stop_scheduler
import os
import atexit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

init_db()
start_scheduler()
atexit.register(stop_scheduler)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/admin')
def admin():
    return render_template('admin.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    """用户登录并存储session"""
    data = request.json
    user_account = data.get('user_account')
    user_password = data.get('user_password')
    dingtalk_webhook = data.get('dingtalk_webhook', '')
    dingtalk_secret = data.get('dingtalk_secret', '')

    if not user_account or not user_password:
        return jsonify({'success': False, 'message': '学号和密码不能为空'})

    if not dingtalk_webhook or not dingtalk_secret:
        return jsonify({'success': False, 'message': '钉钉Webhook和签名密钥不能为空'})

    try:
        reset_session()
        if not simulate_login(user_account, user_password):
            return jsonify({'success': False, 'message': '登录失败'})

        session = get_session()
        session_data = serialize_session(session)

        encryption_key = generate_key()
        encrypted_session = encrypt_session(session_data, encryption_key)

        user_hash = hash_user_id(user_account)

        with DatabaseManager() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_hash, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret, enabled, session_expired)
                VALUES (?, ?, ?, ?, ?, 1, 0)
            """, (user_hash, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret))

        return jsonify({'success': True, 'message': '登录成功，已开始监控'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/users', methods=['GET'])
def api_users():
    """获取用户列表"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_hash, enabled, session_expired, created_at, updated_at FROM users")
        users = [dict(row) for row in cursor.fetchall()]
    return jsonify({'success': True, 'users': users})


@app.route('/api/users/<user_hash>/toggle', methods=['POST'])
def api_toggle_user(user_hash):
    """切换用户启用状态"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET enabled = 1 - enabled WHERE user_hash = ?", (user_hash,))
    return jsonify({'success': True})


@app.route('/api/check', methods=['POST'])
def api_check():
    """手动触发检测"""
    from scheduler import check_all_users
    check_all_users()
    return jsonify({'success': True, 'message': '检测已触发'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
