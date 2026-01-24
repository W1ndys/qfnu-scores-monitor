from apscheduler.schedulers.background import BackgroundScheduler
from models import DatabaseManager
from utils.score_monitor import restore_session, fetch_scores, compare_scores, serialize_session
from utils.dingtalk import notify_new_scores, notify_session_expired
from utils.crypto import encrypt_session, decrypt_session
from utils.logger import logger
scheduler = BackgroundScheduler()

MAX_LOGIN_ATTEMPTS = 3  # 验证码识别最大尝试次数


def try_relogin(user_account, encrypted_password, encryption_key):
    """尝试重新登录，最多尝试3次"""
    from main import simulate_login
    from utils.session_manager import get_session, reset_session

    try:
        # 解密密码
        password = decrypt_session(encrypted_password, encryption_key)
    except Exception as e:
        logger.error(f"用户 {user_account} 密码解密失败: {str(e)}")
        return None

    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        try:
            logger.info(f"用户 {user_account} 尝试重新登录 (第{attempt}次)")
            reset_session()

            if simulate_login(user_account, password):
                session = get_session()
                session_data = serialize_session(session)
                new_encrypted_session = encrypt_session(session_data, encryption_key)
                logger.info(f"用户 {user_account} 重新登录成功")
                return new_encrypted_session

        except Exception as e:
            logger.warning(f"用户 {user_account} 第{attempt}次登录尝试失败: {str(e)}")

    logger.error(f"用户 {user_account} 重新登录失败，已达最大尝试次数")
    return None


def handle_expired_session(cursor, user, dingtalk_webhook, dingtalk_secret):
    """处理过期的 Session，尝试自动重新登录"""
    user_account = user["user_account"]
    encrypted_password = user["encrypted_password"]
    encryption_key = user["encryption_key"]

    # 如果没有存储密码，直接标记过期
    if not encrypted_password:
        logger.warning(f"用户 {user_account} 未存储密码，无法自动重新登录")
        cursor.execute(
            "UPDATE users SET session_expired = 1 WHERE user_account = ?",
            (user_account,),
        )
        notify_session_expired(dingtalk_webhook, dingtalk_secret)
        return False

    # 尝试重新登录
    new_encrypted_session = try_relogin(user_account, encrypted_password, encryption_key)

    if new_encrypted_session:
        # 更新 session（静默重登，不通知用户）
        cursor.execute(
            "UPDATE users SET encrypted_session = ?, session_expired = 0 WHERE user_account = ?",
            (new_encrypted_session, user_account),
        )
        logger.info(f"用户 {user_account} Session 已自动更新")
        return True
    else:
        # 登录失败，标记过期
        cursor.execute(
            "UPDATE users SET session_expired = 1 WHERE user_account = ?",
            (user_account,),
        )
        notify_session_expired(dingtalk_webhook, dingtalk_secret)
        return False


def check_single_user(user_account):
    """检查单个用户的成绩"""
    logger.info(f"开始检查用户 {user_account} 的成绩")

    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_account, encrypted_password, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret FROM users WHERE user_account = ?",
            (user_account,),
        )
        user = cursor.fetchone()

        if not user:
            return {"success": False, "message": "用户不存在"}

        try:
            session = restore_session(user["encrypted_session"], user["encryption_key"])
            page_hash, scores, expired = fetch_scores(session)

            if expired:
                logger.warning(f"用户 {user_account} 的session已过期，尝试自动重新登录")

                if handle_expired_session(cursor, user, user["dingtalk_webhook"], user["dingtalk_secret"]):
                    return {"success": True, "message": "Session已过期，已自动重新登录", "status": "relogin"}
                else:
                    return {"success": True, "message": "Session已过期，自动登录失败，已发送通知", "status": "expired"}

            if page_hash is not None and scores is not None:
                new_courses = compare_scores(user_account, page_hash, scores)

                if new_courses:
                    logger.info(f"用户 {user_account} 发现新成绩: {len(new_courses)}门")
                    notify_new_scores(user["dingtalk_webhook"], user["dingtalk_secret"], new_courses)
                    return {"success": True, "message": f"发现 {len(new_courses)} 门新成绩，已发送通知", "status": "new_scores", "count": len(new_courses)}
                else:
                    logger.info(f"用户 {user_account} 无新成绩")
                    return {"success": True, "message": "暂无新成绩", "status": "no_change"}

            return {"success": False, "message": "获取成绩失败"}

        except Exception as e:
            logger.error(f"检查用户 {user_account} 时出错: {str(e)}")
            return {"success": False, "message": str(e)}


def check_all_users():
    """检查所有启用的用户"""
    logger.info("开始检查所有用户成绩")

    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_account, encrypted_password, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret FROM users WHERE enabled = 1 AND session_expired = 0"
        )
        users = cursor.fetchall()

        for user in users:
            user_account = user["user_account"]
            dingtalk_webhook = user["dingtalk_webhook"]
            dingtalk_secret = user["dingtalk_secret"]

            try:
                session = restore_session(user["encrypted_session"], user["encryption_key"])
                page_hash, scores, expired = fetch_scores(session)

                if expired:
                    logger.warning(f"用户 {user_account} 的session已过期，尝试自动重新登录")
                    handle_expired_session(cursor, user, dingtalk_webhook, dingtalk_secret)
                    continue

                if page_hash is not None and scores is not None:
                    new_courses = compare_scores(user_account, page_hash, scores)

                    if new_courses:
                        logger.info(f"用户 {user_account} 发现新成绩: {len(new_courses)}门")
                        notify_new_scores(dingtalk_webhook, dingtalk_secret, new_courses)
                    else:
                        logger.info(f"用户 {user_account} 无新成绩")

            except Exception as e:
                logger.error(f"检查用户 {user_account} 时出错: {str(e)}")

    logger.info("检查完成")


def start_scheduler():
    """启动定时任务"""
    scheduler.add_job(check_all_users, "interval", minutes=5, id="check_scores")
    scheduler.start()
    logger.info("定时任务已启动，每5分钟检查一次")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
    logger.info("定时任务已停止")
