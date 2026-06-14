import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', '8f9c73a4b1d2e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2')
    DB_PATH = os.path.join(os.path.dirname(__file__), 'monitor.db')
    LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
    EXPORT_DIR = os.path.join(os.path.dirname(__file__), 'exports')
    
    # Master System Initial Records
    DEFAULT_ADMIN_USER = "admin"
    DEFAULT_ADMIN_PASS = "admin123"