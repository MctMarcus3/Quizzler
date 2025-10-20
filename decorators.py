# decorators.py

from functools import wraps
from flask import session, redirect, url_for, flash

def admin_required(f):
    """Ensures the user is a logged-in admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for('auth.admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def quiz_session_required(f):
    """Ensures a student has started a quiz and provided a name."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'quiz_id' not in session or 'name' not in session:
            flash("Please enter a valid PIN and your name to start a quiz.", "warning")
            return redirect(url_for('student.home'))
        return f(*args, **kwargs)
    return decorated_function