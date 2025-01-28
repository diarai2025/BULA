
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    spend = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    end_date = db.Column(db.DateTime)
    daily_stats = db.relationship('DailyStat', backref='campaign', lazy=True)
    
    # Campaign goals
    impression_goal = db.Column(db.Integer, default=0)
    click_goal = db.Column(db.Integer, default=0)
    conversion_goal = db.Column(db.Integer, default=0)
    roi_goal = db.Column(db.Float, default=0.0)

class DailyStat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'))
    date = db.Column(db.Date, nullable=False)
    impressions = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    conversions = db.Column(db.Integer, default=0)
    spend = db.Column(db.Float, default=0.0)
    platform = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    ad_text = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    budget = db.Column(db.Integer)
    location = db.Column(db.String(100))
    platforms = db.Column(db.String(200))
    style = db.Column(db.String(50))

class SubscriptionPlan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    campaign_limit = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True, default='')
    features = db.Column(db.Text, nullable=True, default='')
    
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # budget, performance, goal
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_read = db.Column(db.Boolean, default=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    notifications = db.relationship('Notification', backref='user', lazy=True)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    subscription_id = db.Column(db.Integer, db.ForeignKey('subscription_plan.id'))
    subscription_active = db.Column(db.Boolean, default=False)
    campaigns = db.relationship('Campaign', backref='user', lazy=True)
    subscription = db.relationship('SubscriptionPlan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
