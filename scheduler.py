from apscheduler.schedulers.background import BackgroundScheduler
from models import DatabaseManager
from utils.score_monitor import restore_session, fetch_scores, compare_scores
from utils.dingtalk import notify_new_scores, notify_session_expired
from utils.logger import setup_logger

logger = setup_logger()
scheduler = BackgroundScheduler()


def check_all_users():
    """检查所有启用的用户"""
    logger.info("开始检查所有用户成绩")

    with DatabaseManager() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_hash, encrypted_session, encryption_key, dingtalk_webhook, dingtalk_secret FROM users WHERE enabled = 1 AND session_expired = 0")
        users = cursor.fetchall()

        for user in users:
            user_hash = user['user_hash']
            encrypted_session = user['encrypted_session']
            encryption_key = user['encryption_key']
            dingtalk_webhook = user['dingtalk_webhook']
            dingtalk_secret = user['dingtalk_secret']

            try:
                session = restore_session(encrypted_session, encryption_key)
                course_ids, expired = fetch_scores(session)

                if expired:
                    logger.warning(f"用户 {user_hash[:16]}... 的session已过期")
                    cursor.execute("UPDATE users SET session_expired = 1 WHERE user_hash = ?", (user_hash,))
                    notify_session_expired(dingtalk_webhook, dingtalk_secret)
                    continue

                if course_ids is not None:
                    new_courses = compare_scores(user_hash, course_ids)

                    if new_courses:
                        logger.info(f"用户 {user_hash[:16]}... 发现新成绩: {new_courses}")
                        notify_new_scores(dingtalk_webhook, dingtalk_secret, new_courses)
                    else:
                        logger.info(f"用户 {user_hash[:16]}... 无新成绩")

            except Exception as e:
                logger.error(f"检查用户 {user_hash[:16]}... 时出错: {str(e)}")

    logger.info("检查完成")


def start_scheduler():
    """启动定时任务"""
    scheduler.add_job(check_all_users, 'interval', minutes=30, id='check_scores')
    scheduler.start()
    logger.info("定时任务已启动，每30分钟检查一次")


def stop_scheduler():
    """停止定时任务"""
    scheduler.shutdown()
    logger.info("定时任务已停止")
