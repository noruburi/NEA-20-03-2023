from . import db
from flask_login import UserMixin
from datetime import datetime, timedelta
import random
import string

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(25), unique=True)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, index=True)
    password = db.Column(db.String(255))
    first_name = db.Column(db.String(25))
    last_name = db.Column(db.String(25))
    user_name = db.Column(db.String(25))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'))
    role = db.relationship('Role', backref=db.backref('users', lazy=True))
    role_approved = db.Column(db.Boolean, default=False)
    role_request = db.Column(db.Boolean, default=False)
    role_requested_on = db.Column(db.DateTime)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    account = db.relationship('Account', backref='owner', lazy=True, uselist=False, foreign_keys=[account_id])
    weekly_point_limit = db.Column(db.Integer, default=100)
    last_award_date = db.Column(db.Date)
    points_awarded_this_week = db.Column(db.Integer, default=0)


    @property
    def remaining_points(self):
        today = datetime.utcnow().date()
        if self.last_award_date and self.last_award_date.isocalendar()[1] == today.isocalendar()[1]:
            return max(self.weekly_point_limit - self.points_awarded_this_week, 0)
        else:
            return self.weekly_point_limit

    @property
    def points_awarded_percentage(self):
        return int(self.points_awarded_this_week / self.weekly_point_limit * 100)

    @property
    def remaining_point_percentage(self):
        return int(self.remaining_points / self.weekly_point_limit * 100)

    def is_admin(self):
        return self.role.name == 'admin'
    
    def is_teacher(self):
        return self.role.name == 'teacher'

class Account(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('account_ref', lazy=True), uselist=False)
    balance = db.Column(db.Integer)
    points_awarded = db.Column(db.Integer, default=0)
    transactions = db.relationship('Transactions', backref='account', lazy=True)

class Transactions(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    sequence = db.Column(db.Integer)
    from_account_id = db.Column(db.Integer)
    dateTime = db.Column(db.DateTime)
    to_account_id = db.Column(db.Integer)
    amount = db.Column(db.Integer)
    code = db.Column(db.String(8), nullable=True)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupon.id'))
    coupon = db.relationship('Coupon', backref=db.backref('transactions', lazy=True))
    date_redeemed = db.Column(db.DateTime)
    
class TeacherRequestHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('teacher_requests_history', lazy=True))
    status = db.Column(db.String(20), nullable=False)
    date_resolved = db.Column(db.DateTime)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    resolved_by = db.relationship('User', foreign_keys=[resolved_by_id])

    def __repr__(self):
        return f"<TeacherRequestHistory {self.id}>"

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

student_class = db.Table('student_class',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('class_id', db.Integer, db.ForeignKey('class.id'), primary_key=True)
)

class Class(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'))
    subject = db.relationship('Subject', backref=db.backref('classes', lazy=True))
    year_group = db.Column(db.Integer)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    teacher = db.relationship('User', backref=db.backref('classes', lazy=True))
    students = db.relationship('User', secondary=student_class, lazy='subquery',backref=db.backref('enrolled_classes', lazy=True))
    
    def class_name(self):
        subject_initial = self.subject.name[0].upper() if self.subject.name else ''
        teacher_first_name_initial = self.teacher.first_name[0].upper() if self.teacher.first_name else ''
        teacher_last_name_initial = self.teacher.last_name[0].upper() if self.teacher.last_name else ''
        return f"{self.year_group}{subject_initial}{teacher_first_name_initial}{teacher_last_name_initial}"
    


class JoinRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student = db.relationship('User', backref=db.backref('join_requests', lazy=True))
    class_id = db.Column(db.Integer, db.ForeignKey('class.id'), nullable=False)
    class_ = db.relationship('Class', backref=db.backref('join_requests', lazy=True))
    status = db.Column(db.String(20), nullable=False)
    __table_args__ = (db.UniqueConstraint('student_id', 'class_id'),)

class Coupon(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student = db.relationship('User', backref=db.backref('coupons', lazy=True))
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    points_cost = db.Column(db.Integer, nullable=False)
    code = db.Column(db.String(8), nullable=True, unique=True)
    redeemed = db.Column(db.Boolean, nullable=False, default=False)
    redeem_date = db.Column(db.DateTime)


    def __init__(self, student_id, name, description, points_cost, code=None, redeemed=False, redeem_date=None):
        self.student_id = student_id
        self.name = name
        self.description = description
        self.points_cost = points_cost
        self.code = code or self.generate_code()
        self.redeemed = redeemed
        self.redeem_date = redeem_date

    def generate_code(self):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        while Coupon.query.filter_by(code=code).first() is not None:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return code

    def redeem(self):
        self.redeemed = True
        self.redeem_date = datetime.utcnow()

    @property
    def is_expired(self):
        if self.redeem_date is None:
            return False
        return (datetime.utcnow() - self.redeem_date) > timedelta(days=2)

    def __repr__(self):
        return f'<Coupon {self.name}>'