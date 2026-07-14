from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))

    health_records = db.relationship('HealthRecord', back_populates='user', lazy='dynamic')


class HealthRecord(db.Model):
    __tablename__ = 'health_records'
    id = db.Column(db.Integer, primary_key=True)

    # Link to user (optional but recommended)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', back_populates='health_records')

    # Personal Information
    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(20), nullable=False)
    city = db.Column(db.String(120))

    # Vitals
    systolic_bp = db.Column(db.Integer)
    diastolic_bp = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    temperature = db.Column(db.Float)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    sugar = db.Column(db.Float)

    # Medical Details
    symptoms = db.Column(db.Text, nullable=False)
    history = db.Column(db.Text)
    medications = db.Column(db.Text)
    allergies = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<HealthRecord id={self.id} name={self.name} age={self.age}>"
