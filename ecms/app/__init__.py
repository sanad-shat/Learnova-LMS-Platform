import os
from pathlib import Path
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from sqlalchemy import text as sql_text

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()


def _ensure_user_profile_columns():
    """Add new profile columns to existing SQLite databases without losing data."""
    columns = {
        'university_id': 'VARCHAR(30)',
        'employee_id': 'VARCHAR(30)',
        'phone': 'VARCHAR(25)',
        'department': 'VARCHAR(100)',
        'level': 'VARCHAR(30)',
        'gender': 'VARCHAR(15)',
        'status': "VARCHAR(20) DEFAULT 'Active'",
        'office_number': 'VARCHAR(30)',
        'academic_rank': 'VARCHAR(60)',
        'visible_password': 'VARCHAR(255)',
    }
    current = {row[1] for row in db.session.execute(sql_text("PRAGMA table_info(user)")).fetchall()}
    for name, sql_type in columns.items():
        if name not in current:
            db.session.execute(sql_text(f"ALTER TABLE user ADD COLUMN {name} {sql_type}"))
    db.session.commit()


def _ensure_forum_columns():
    """Upgrade existing SQLite forum tables without deleting data."""
    upgrades = {
        'topic_type': "VARCHAR(30) DEFAULT 'Discussion'",
        'is_locked': 'BOOLEAN DEFAULT 0',
        'attachment_path': 'VARCHAR(255)',
        'discussion_post': {'attachment_path': 'VARCHAR(255)'},
    }
    for table, columns in upgrades.items():
        if isinstance(columns, dict):
            target_table = table
            cols = columns
        else:
            target_table = 'discussion_topic'
            cols = {table: columns}
        
        try:
            existing = {row[1] for row in db.session.execute(sql_text(f"PRAGMA table_info({target_table})")).fetchall()}
            for name, sql_type in cols.items():
                if name not in existing:
                    db.session.execute(sql_text(f"ALTER TABLE {target_table} ADD COLUMN {name} {sql_type}"))
            db.session.commit()
        except Exception:
            db.session.rollback()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'learnova-development-secret-key')
    app.config['SITE_NAME'] = 'Learnova LMS'

    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # إصلاح توافق صيغة رابط PostgreSQL مع SQLAlchemy
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecms.db'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    login_manager.login_view = 'students.login'
    login_manager.login_message_category = 'info'

    from app.routes.admin import admin_bp
    from app.routes.teachers import teachers_bp
    from app.routes.students import students_bp
    from app.routes.forum import forum_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(forum_bp)

    @app.route('/')
    def home():
        return render_template('choose.html')

    with app.app_context():
        db.create_all()
        # تشغيل الترقية التلقائية فقط في حال استخدام SQLite
        if not database_url:
            try:
                _ensure_user_profile_columns()
                _ensure_forum_columns()
            except Exception:
                pass

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def access_denied(error):
        return render_template('errors/403.html'), 403

    return app
