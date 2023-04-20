# Import Flask and related libraries
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from os import path
from flask_login import LoginManager, login_user
from werkzeug.security import generate_password_hash
import secrets

# Initialize SQLAlchemy
db = SQLAlchemy()

# Define the name of the database
DB_NAME = "database.db"

# Generate CSRF token for secure forms
def generate_csrf_token():
    # If token doesn't exist in session, generate a new one and save it in session
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    # Return the token from session
    return session['_csrf_token']

# Create a Flask application instance
def create_app():
    app = Flask(__name__)

    # Set application configuration
    app.config['SECRET_KEY'] = 'hjshjhdjah kjshkjdhjs'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_NAME  #store database inside the directory of the init.py file

    # Initialize database
    db.init_app(app)

    # Make the CSRF token generator available in templates
    app.jinja_env.globals['csrf_token'] = generate_csrf_token

    # Initialize login manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    login_manager.login_message_category = 'info'

    # Load user data from database for user authentication
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))

    # Create admin, teacher, and student users with corresponding roles and accounts
    @app.before_first_request
    def create_admin_user():
        # Create the admin role if it doesn't exist
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            db.session.commit()

        # Create the teacher role if it doesn't exist
        teacher_role = Role.query.filter_by(name='teacher').first()
        if not teacher_role:
            teacher_role = Role(name='teacher')
            db.session.add(teacher_role)
            db.session.commit()

        # Create the student role if it doesn't exist
        student_role = Role.query.filter_by(name='student').first()
        if not student_role:
            student_role = Role(name='student')
            db.session.add(student_role)
            db.session.commit()

        # Create the admin user if it doesn't exist
        admin = User.query.filter_by(email='admin@Kimberley.com').first()
        if not admin:
            admin = User(email='admin@Kimberley.com', password=generate_password_hash('secret', method='sha256'), first_name='Admin', role_id=admin_role.id)
            db.session.add(admin)
            db.session.commit()

        # Create the teacher user if it doesn't exist
        teacher = User.query.filter_by(email='teacher@Kimberley.com').first()
        if not teacher:
            teacher = User(email='teacher@Kimberley.com', password=generate_password_hash('secret', method='sha256'), first_name='Teacher', last_name='LastName', role_id=teacher_role.id)
            teacher.user_name = generate_username(teacher.first_name, teacher.last_name)
            db.session.add(teacher)
            db.session.commit()

        # Create the teacher account if it doesn't exist
        teacher_account = Account.query.filter_by(user_id=teacher.id).first()
        if not teacher_account:
            teacher_account = Account(user=teacher, balance=0)
            db.session.add(teacher_account)
            db.session.commit()

        # Check if a user with email 'student@Kimberley.com' exists, and create one if not
        student = User.query.filter_by(email='student@Kimberley.com').first()
        if not student:
            student = User(email='student@Kimberley.com', password=generate_password_hash('secret', method='sha256'), first_name='Student', last_name='LastName', role_id=student_role.id)
            student.user_name = generate_username(student.first_name, student.last_name)
            db.session.add(student)
            db.session.commit()
        
        # Check if a corresponding account for the student exists, and create one if not
        student_account = Account.query.filter_by(user_id=student.id).first()
        if not student_account:
            student_account = Account(user=student, balance=0)
            db.session.add(student_account)
            db.session.commit()


        # Set the appropriate properties for the teacher and student accounts and commit changes to the database
        teacher.role_approved = True
        teacher.account_id = teacher_account.id
        student.account_id = student_account.id
        db.session.commit()
    
        # Create the Subject records for the default list of subjects if they don't exist
        subjects_list = ['Math', 'English', 'Science', 'History', 'Geography', 'Art', 'Physical Education', 'Music']
        for subject_name in subjects_list:
            subject = Subject.query.filter_by(name=subject_name).first()
            if not subject:
                new_subject = Subject(name=subject_name)
                db.session.add(new_subject)
                db.session.commit()

    # Import necessary models and blueprints inside of the function to avoid calling databases before they have been made 
    from .models import User, Role, Subject, Account   
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint)
    from .auth import generate_username
    from .views import views as views_blueprint
    app.register_blueprint(views_blueprint)
        
    # Create all necessary tables in the database
    with app.app_context():
        db.create_all()

    return app

# Define a function to create the database if it doesn't exist
def create_database(app):
    with app.app_context():
        if not path.exists('website/' + DB_NAME):
            db.create_all()
            print('create_database')

# Define a function to drop and recreate the database
def recreate_database(app):
    with app.app_context():
        db.drop_all()
        db.create_all()
        print('Database recreated')

