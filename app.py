# app.py

from flask import Flask
from config import SECRET_KEY

def create_app():
    """Application factory function."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_FORM_FIELDS'] = 100000 
    
    # Import and register blueprints
    from views.auth import auth_bp
    from views.admin import admin_bp
    from views.student import student_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)