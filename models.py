import sqlite3
import os
import time
import threading
from typing import Optional, ClassVar
from queue import Queue, Empty
from contextlib import contextmanager


def get_timestamp():
    """获取当前时间戳（秒）"""
    return int(time.time())


class ConnectionPool:
    """SQLite 连接池实现"""

    def __init__(self, db_path, max_connections=5, timeout=30.0):
        self.db_path = db_path
        self.max_connections = max_connections
        self.timeout = timeout
        self._pool = Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._created_connections = 0
        self._initialized = False

    def _create_connection(self):
        """创建新的数据库连接"""
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.timeout,
            check_same_thread=False,  # 允许多线程使用
            isolation_level=None,  # 自动提交模式，手动控制事务
        )
        conn.row_factory = sqlite3.Row

        # 启用 WAL 模式和其他优化
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")  # 平衡性能和安全
        conn.execute("PRAGMA cache_size=-64000")  # 64MB 缓存
        conn.execute("PRAGMA temp_store=MEMORY")  # 临时表存储在内存
        conn.execute("PRAGMA busy_timeout=30000")  # 30秒忙等待超时

        return conn

    def get_connection(self):
        """从连接池获取连接"""
        try:
            conn = self._pool.get_nowait()
            # 检查连接是否有效
            try:
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                # 连接无效，创建新连接
                with self._lock:
                    self._created_connections -= 1
                return self._get_or_create_connection()
        except Empty:
            return self._get_or_create_connection()

    def _get_or_create_connection(self):
        """获取或创建新连接"""
        with self._lock:
            if self._created_connections < self.max_connections:
                self._created_connections += 1
                return self._create_connection()

        # 已达最大连接数，等待可用连接
        try:
            conn = self._pool.get(timeout=self.timeout)
            try:
                conn.execute("SELECT 1")
                return conn
            except sqlite3.Error:
                with self._lock:
                    self._created_connections -= 1
                return self._get_or_create_connection()
        except Empty:
            raise sqlite3.OperationalError("连接池超时：无法获取数据库连接")

    def release_connection(self, conn):
        """归还连接到连接池"""
        if conn:
            try:
                # 重置连接状态
                conn.rollback()
                self._pool.put_nowait(conn)
            except Exception:
                # 如果归还失败，关闭连接
                with self._lock:
                    self._created_connections -= 1
                try:
                    conn.close()
                except Exception:
                    pass

    def close_all(self):
        """关闭所有连接"""
        while True:
            try:
                conn = self._pool.get_nowait()
                try:
                    conn.close()
                except Exception:
                    pass
            except Empty:
                break
        with self._lock:
            self._created_connections = 0


class DatabaseManager:
    """数据库管理类，支持连接池、WAL模式和上下文管理"""

    DB_PATH: ClassVar[str] = "monitor.db"
    _pool: ClassVar[Optional[ConnectionPool]] = None
    _pool_lock: ClassVar[threading.Lock] = threading.Lock()
    _migrated: ClassVar[bool] = False
    _migrate_lock: ClassVar[threading.Lock] = threading.Lock()

    # 定义表结构
    SCHEMA = {
        "users": {
            "user_account": "TEXT PRIMARY KEY",
            "encrypted_password": "TEXT",
            "encrypted_session": "TEXT NOT NULL",
            "encryption_key": "TEXT NOT NULL",
            "dingtalk_webhook": "TEXT",
            "dingtalk_secret": "TEXT",
            "enabled": "INTEGER DEFAULT 1",
            "session_expired": "INTEGER DEFAULT 0",
            "push_count": "INTEGER DEFAULT 0",
            "last_check_at": "INTEGER",
            "created_at": "INTEGER",
            "updated_at": "INTEGER",
        },
        "scores": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "user_account": "TEXT NOT NULL",
            "page_hash": "TEXT NOT NULL",
            "reported_course_ids": 'TEXT DEFAULT "[]"',
            "updated_at": "INTEGER",
        },
    }

    def __init__(self):
        self.conn = None
        self._ensure_db_exists()
        self._ensure_pool()
        self._ensure_migrated()

    def _ensure_db_exists(self):
        """确保数据库文件和目录存在"""
        db_dir = os.path.dirname(self.DB_PATH)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)

    @classmethod
    def _ensure_pool(cls):
        """确保连接池已初始化（单例模式）"""
        if cls._pool is None:
            with cls._pool_lock:
                if cls._pool is None:
                    cls._pool = ConnectionPool(
                        cls.DB_PATH, max_connections=5, timeout=30.0
                    )

    @classmethod
    def _ensure_migrated(cls):
        """确保数据库迁移只执行一次"""
        if cls._migrated:
            return

        with cls._migrate_lock:
            if cls._migrated:
                return

            cls._ensure_pool()
            assert cls._pool is not None  # 类型断言
            conn = cls._pool.get_connection()
            try:
                cursor = conn.cursor()
                conn.execute("BEGIN")

                for table_name, columns in cls.SCHEMA.items():
                    # 检查表是否存在
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                        (table_name,),
                    )
                    if not cursor.fetchone():
                        # 创建表
                        cols = ", ".join(
                            [f"{col} {dtype}" for col, dtype in columns.items()]
                        )
                        cursor.execute(f"CREATE TABLE {table_name} ({cols})")
                    else:
                        # 检查并添加缺失的列
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        existing_cols = {row[1] for row in cursor.fetchall()}

                        for col, dtype in columns.items():
                            if col not in existing_cols:
                                cursor.execute(
                                    f"ALTER TABLE {table_name} ADD COLUMN {col} {dtype}"
                                )

                conn.execute("COMMIT")
                cls._migrated = True
            except Exception:
                conn.execute("ROLLBACK")
                raise
            finally:
                assert cls._pool is not None  # 类型断言
                cls._pool.release_connection(conn)

    def __enter__(self):
        """进入上下文管理器，从连接池获取连接"""
        self._ensure_pool()
        assert self._pool is not None  # 类型断言
        self.conn = self._pool.get_connection()
        self.conn.execute("BEGIN")
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器，归还连接到连接池"""
        if self.conn:
            try:
                if exc_type is None:
                    self.conn.execute("COMMIT")
                else:
                    self.conn.execute("ROLLBACK")
            finally:
                assert self._pool is not None  # 类型断言
                self._pool.release_connection(self.conn)
                self.conn = None
        return False

    @classmethod
    def get_connection(cls):
        """直接获取连接（需要手动释放）"""
        cls._ensure_pool()
        assert cls._pool is not None  # 类型断言
        return cls._pool.get_connection()

    @classmethod
    def release_connection(cls, conn):
        """释放连接回连接池"""
        if cls._pool:
            cls._pool.release_connection(conn)

    @classmethod
    @contextmanager
    def connection(cls):
        """获取连接的上下文管理器（推荐使用）"""
        cls._ensure_pool()
        assert cls._pool is not None  # 类型断言
        conn = cls._pool.get_connection()
        try:
            conn.execute("BEGIN")
            yield conn
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        finally:
            cls._pool.release_connection(conn)

    @classmethod
    def close_pool(cls):
        """关闭连接池（程序退出时调用）"""
        with cls._pool_lock:
            if cls._pool:
                cls._pool.close_all()
                cls._pool = None
                cls._migrated = False


# 初始化数据库
def init_db():
    """初始化数据库（兼容旧代码）"""
    DatabaseManager()
