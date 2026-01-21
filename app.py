from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
from models import init_db, DatabaseManager
from utils.crypto import generate_key, encrypt_session
from utils.score_monitor import serialize_session
from utils.dingtalk import notify_new_scores, notify_session_expired
from main import simulate_login
from utils.session_manager import get_session, reset_session
from scheduler import start_scheduler, stop_scheduler
import os
import atexit
import hashlib

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)

# 管理员密码配置 - 建议通过环境变量设置
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
ADMIN_PASSWORD_HASH = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

init_db()
start_scheduler()
atexit.register(stop_scheduler)


# ========== 管理员鉴权装饰器 ==========
def admin_required(f):
    """管理员登录验证装饰器"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_logged_in"):
            if request.is_json:
                return (
                    jsonify(
                        {"success": False, "message": "请先登录", "redirect": "/admin"}
                    ),
                    401,
                )
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)

    return decorated_function


# ========== 页面路由 ==========
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/admin")
def admin():
    """管理后台 - 需要登录"""
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    return render_template("admin.html")


@app.route("/admin/login")
def admin_login():
    """管理员登录页面"""
    return render_template("admin_login.html")


@app.route("/favicon.ico")
def favicon():
    """返回空响应以避免 404 错误"""
    return "", 204


# ========== API 路由 ==========


@app.route("/api/admin/login", methods=["POST"])
def api_admin_login():
    """管理员登录 API"""
    data = request.json
    password = data.get("password")

    if not password:
        return jsonify({"success": False, "message": "请输入密码"})

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if password_hash == ADMIN_PASSWORD_HASH:
        session["admin_logged_in"] = True
        return jsonify({"success": True, "message": "登录成功"})
    else:
        return jsonify({"success": False, "message": "密码错误"})


@app.route("/api/admin/logout", methods=["POST"])
def api_admin_logout():
    """管理员登出 API"""
    session.pop("admin_logged_in", None)
    return jsonify({"success": True, "message": "已登出"})


@app.route("/api/admin/check", methods=["GET"])
def api_admin_check():
    """检查管理员登录状态"""
    return jsonify({"logged_in": session.get("admin_logged_in", False)})


@app.route("/api/login", methods=["POST"])
def api_login():
    """用户登录并存储session"""
    data = request.json
    user_account = data.get("user_account")
    user_password = data.get("user_password")
    dingtalk_webhook = data.get("dingtalk_webhook", "")
    dingtalk_secret = data.get("dingtalk_secret", "")
    enabled = data.get("enabled", True)

    if not user_account or not user_password:
        return jsonify({"success": False, "message": "学号和密码不能为空"})

    if not dingtalk_webhook or not dingtalk_secret:
        return jsonify({"success": False, "message": "钉钉Webhook和签名密钥不能为空"})

    try:
        reset_session()
        if not simulate_login(user_account, user_password):
            return jsonify({"success": False, "message": "登录失败"})

        session = get_session()
        session_data = serialize_session(session)

        encryption_key = generate_key()
        encrypted_session = encrypt_session(session_data, encryption_key)

        with DatabaseManager() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO users (user_account, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret, enabled, session_expired)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
                (
                    user_account,
                    encrypted_session,
                    encryption_key,
                    dingtalk_webhook,
                    dingtalk_secret,
                    1 if enabled else 0,
                ),
            )

        return jsonify(
            {
                "success": True,
                "message": (
                    "登录成功，已开始监控" if enabled else "登录成功，监控已暂停"
                ),
            }
        )

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})


@app.route("/api/users", methods=["GET"])
@admin_required
def api_users():
    """获取用户列表"""
    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_account, enabled, session_expired, created_at, updated_at FROM users"
        )
        users = [dict(row) for row in cursor.fetchall()]
    return jsonify({"success": True, "users": users})


@app.route("/api/users/<user_account>/toggle", methods=["POST"])
@admin_required
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
@admin_required
def api_check():
    """手动触发检测"""
    from scheduler import check_all_users

    check_all_users()
    return jsonify({"success": True, "message": "检测已触发"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5201, debug=True)
