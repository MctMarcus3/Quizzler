# views/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from data_manager import load_users, save_users # Import save_users

auth_bp = Blueprint('auth', __name__, url_prefix='/admin')

@auth_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users()
        
        user = users.get(username)
        if user and check_password_hash(user['password'], password) and user['role'] == 'admin':
            # If this is the first login and users.json doesn't exist, save it.
            # This ensures the default admin is persisted.
            import os
            from config import USER_DATA_FILE
            if not os.path.exists(USER_DATA_FILE):
                save_users(users)

            session['user'] = username
            session['role'] = user['role']
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Invalid admin credentials.')
            
    return render_template('admin_login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('student.home'))