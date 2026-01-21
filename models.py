import sqlite3
import hashlib
import os
from datetime import datetime


class DatabaseManager:
    """数据库管理类，支持自动迁移和上下文管理"""

    DB_PATH = "monitor.db"

    # 定义表结构
    SCHEMA = {
        'users': {
            'user_hash': 'TEXT PRIMARY KEY',
            'encrypted_session': 'TEXT NOT NULL',
            'encryption_key': 'TEXT NOT NULL',
            'dingtalk_webhook': 'TEXT',
            'dingtalk_secret': 'TEXT',
            'enabled': 'INTEGER DEFAULT 1',
            'session_expired': 'INTEGER DEFAULT 0',
            'created_at': 'TEXT DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TEXT DEFAULT CURRENT_TIMESTAMP'
        },
        'scores': {
            'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
            'user_hash': 'TEXT NOT NULL',
            'course_ids': 'TEXT NOT NULL',
            'updated_at': 'TEXT DEFAULT CURRENT_TIMESTAMP'
        }
    }

    def __init__(self):
        self.conn = None
        self._ensure_db_exists()
        self._migrate()

    def _ensure_db_exists(self):
        """确保数据库文件和目录存在"""
        db_dir = os.path.dirname(self.DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    def _migrate(self):
        """自动迁移数据库结构"""
        conn = sqlite3.connect(self.DB_PATH)
        cursor = conn.cursor()

        for table_name, columns in self.SCHEMA.items():
            # 检查表是否存在
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            if not cursor.fetchone():
                # 创建表
                cols = ', '.join([f"{col} {dtype}" for col, dtype in columns.items()])
                cursor.execute(f"CREATE TABLE {table_name} ({cols})")
            else:
                # 检查并添加缺失的列
                cursor.execute(f"PRAGMA table_info({table_name})")
                existing_cols = {row[1] for row in cursor.fetchall()}

                for col, dtype in columns.items():
                    if col not in existing_cols:
                        # 添加缺失的列
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} {dtype}")

        conn.commit()
        conn.close()

    def __enter__(self):
        """进入上下文管理器"""
        self.conn = sqlite3.connect(self.DB_PATH)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()
        return False


def hash_user_id(user_account):
    """生成用户哈希"""
    return hashlib.sha256(user_account.encode()).hexdigest()


# 初始化数据库
def init_db():
    """初始化数据库（兼容旧代码）"""
    DatabaseManager()
