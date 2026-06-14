import hashlib
from flask import session, redirect, url_for, flash
from functools import wraps
from database import db_pool

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_user(username, password) -> bool:
    phash = hash_password(password)
    with db_pool.acquire() as cursor:
        cursor.execute("SELECT id FROM admins WHERE username = ? AND password_hash = ?", (username, phash))
        return cursor.fetchone() is not None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Access token signature required. Please verify profile parameters.', 'danger')
            return redirect(url_for('login_route'))
        return f(*args, **kwargs)
    return decorated_function