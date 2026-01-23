from flask import Flask, render_template, request, jsonify
from models import init_db, DatabaseManager
from utils.crypto import generate_key, encrypt_session
from utils.score_monitor import serialize_session
from dotenv import load_dotenv
from main import simulate_login
from utils.session_manager import get_session, reset_session
from scheduler import start_scheduler, stop_scheduler
import os
import atexit


load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)

FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))

init_db()
start_scheduler()
atexit.register(stop_scheduler)


# ========== 页面路由 ==========
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return "", 204


# ========== API 路由 ==========
@app.route("/api/import", methods=["POST"])
def api_import():
    """导入用户数据"""
    data = request.json
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"success": False, "message": "请输入数据"})

    lines = text.strip().split("\n")
    if len(lines) != 4:
        return jsonify({"success": False, "message": "格式错误，需要4行数据：学号、密码、Webhook URL、签名密钥"})

    user_account = lines[0].strip()
    user_password = lines[1].strip()
    dingtalk_webhook = lines[2].strip()
    dingtalk_secret = lines[3].strip()

    if not all([user_account, user_password, dingtalk_webhook, dingtalk_secret]):
        return jsonify({"success": False, "message": "所有字段都不能为空"})

    try:
        reset_session()
        if not simulate_login(user_account, user_password):
            return jsonify({"success": False, "message": "登录失败，请检查学号和密码"})

        session = get_session()
        session_data = serialize_session(session)

        encryption_key = generate_key()
        encrypted_session = encrypt_session(session_data, encryption_key)

        with DatabaseManager() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO users (user_account, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret, enabled, session_expired)
                VALUES (?, ?, ?, ?, ?, 1, 0)
            """,
                (
                    user_account,
                    encrypted_session,
                    encryption_key,
                    dingtalk_webhook,
                    dingtalk_secret,
                ),
            )

        return jsonify({"success": True, "message": f"用户 {user_account} 导入成功，已开始监控"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/api/users", methods=["GET"])
def api_users():
    """获取用户列表"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_account, enabled, session_expired, created_at, updated_at FROM users"
        )
        users = [dict(row) for row in cursor.fetchall()]
    return jsonify({"success": True, "users": users})


@app.route("/api/users/<user_account>", methods=["DELETE"])
def api_delete_user(user_account):
    """删除用户"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE user_account = ?", (user_account,))
        cursor.execute("DELETE FROM scores WHERE user_account = ?", (user_account,))
    return jsonify({"success": True, "message": f"用户 {user_account} 已删除"})


@app.route("/api/users/<user_account>/toggle", methods=["POST"])
def api_toggle_user(user_account):
    """切换用户启用状态"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET enabled = 1 - enabled WHERE user_account = ?",
            (user_account,),
        )
    return jsonify({"success": True})


@app.route("/api/check", methods=["POST"])
def api_check():
    """手动触发检测"""
    from scheduler import check_all_users

    check_all_users()
    return jsonify({"success": True, "message": "检测已触发"})


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT)
