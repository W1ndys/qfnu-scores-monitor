from apscheduler.schedulers.background import BackgroundScheduler
from models import DatabaseManager
from utils.score_monitor import restore_session, fetch_scores, compare_scores
from utils.dingtalk import notify_new_scores, notify_session_expired
from utils.logger import setup_logger

logger = setup_logger()
scheduler = BackgroundScheduler()


def check_single_user(user_account):
    """检查单个用户的成绩"""
    logger.info(f"开始检查用户 {user_account} 的成绩")

    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_account, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret FROM users WHERE user_account = ?",
            (user_account,),
        )
        user = cursor.fetchone()

        if not user:
            return {"success": False, "message": "用户不存在"}

        try:
            session = restore_session(user["encrypted_session"], user["encryption_key"])
            page_hash, scores, expired = fetch_scores(session)

            if expired:
                logger.warning(f"用户 {user_account} 的session已过期")
                cursor.execute(
                    "UPDATE users SET session_expired = 1 WHERE user_account = ?",
                    (user_account,),
                )
                notify_session_expired(user["dingtalk_webhook"], user["dingtalk_secret"])
                return {"success": True, "message": "Session已过期，已发送通知", "status": "expired"}

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
            "SELECT user_account, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret FROM users WHERE enabled = 1 AND session_expired = 0"
        )
        users = cursor.fetchall()

        for user in users:
            user_account = user["user_account"]
            encrypted_session = user["encrypted_session"]
            encryption_key = user["encryption_key"]
            dingtalk_webhook = user["dingtalk_webhook"]
            dingtalk_secret = user["dingtalk_secret"]

            try:
                session = restore_session(encrypted_session, encryption_key)
                page_hash, scores, expired = fetch_scores(session)

                if expired:
                    logger.warning(f"用户 {user_account} 的session已过期")
                    cursor.execute(
                        "UPDATE users SET session_expired = 1 WHERE user_account = ?",
                        (user_account,),
                    )
                    notify_session_expired(dingtalk_webhook, dingtalk_secret)
                    continue

                if page_hash is not None and scores is not None:
                    new_courses = compare_scores(user_account, page_hash, scores)

                    if new_courses:
                        logger.info(
                            f"用户 {user_account} 发现新成绩: {len(new_courses)}门"
                        )
                        notify_new_scores(
                            dingtalk_webhook, dingtalk_secret, new_courses
                        )
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
