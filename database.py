import sqlite3
import hashlib
import queue
import os
import threading
from config import Config

class ThreadSafeDatabasePool:
    """Thread-safe SQLite connection pool executor enforcing Write-Ahead Logging (WAL)."""
    def __init__(self, db_path=Config.DB_PATH, max_connections=12):
        self.db_path = db_path
        self.max_connections = max_connections
        self.pool = queue.Queue(maxsize=max_connections)
        self._lock = threading.Lock()
        self._allocated = 0

    def _get_connection(self):
        with self._lock:
            if self.pool.empty() and self._allocated < self.max_connections:
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
                self._allocated += 1
                return conn
        return self.pool.get(block=True, timeout=5)

    def _return_connection(self, conn):
        try:
            self.pool.put(conn, block=False)
        except queue.Full:
            conn.close()
            with self._lock:
                self._allocated -= 1

    class ConnectionContext:
        def __init__(self, pool_instance):
            self.pool_instance = pool_instance
            self.conn = None
            self.cursor = None

        def __enter__(self):
            self.conn = self.pool_instance._get_connection()
            self.cursor = self.conn.cursor()
            return self.cursor

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.pool_instance._return_connection(self.conn)

    def acquire(self):
        return self.ConnectionContext(self)

db_pool = ThreadSafeDatabasePool()

def init_database():
    """Build transactional matrix tracking fields and write configurations."""
    with db_pool.acquire() as cursor:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS apis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'GET',
                headers TEXT,
                timeout INTEGER DEFAULT 10,
                interval_seconds INTEGER DEFAULT 60,
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_id INTEGER,
                status_code INTEGER,
                response_time_ms REAL,
                is_success INTEGER,
                is_anomaly INTEGER DEFAULT 0,
                error_message TEXT,
                checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(api_id) REFERENCES apis(id) ON DELETE CASCADE
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_checks_composite ON api_checks(api_id, checked_at DESC);')
        
        cursor.execute("SELECT id FROM admins WHERE username = ?", (Config.DEFAULT_ADMIN_USER,))
        if not cursor.fetchone():
            hashed = hashlib.sha256(Config.DEFAULT_ADMIN_PASS.encode('utf-8')).hexdigest()
            cursor.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)", 
                           (Config.DEFAULT_ADMIN_USER, hashed))