from datetime import datetime
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app
from app import db, login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    posts = db.relationship('Post', backref='author', lazy=True)
    comments = db.relationship('Comment', backref='comment_author', lazy=True)
    likes = db.relationship('Like', backref='like_author', lazy='dynamic')
    dislikes = db.relationship('Dislike', backref='dislike_author', lazy='dynamic')
    age = db.Column(db.Integer, nullable=True)
    my_past = db.Column(db.String(100), nullable=True)
    is_moderator = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)  # Yeni alan

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod
    def verify_reset_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def is_liking(self, post):
        return Like.query.filter_by(user_id=self.id, post_id=post.id).count() > 0

    def is_disliking(self, post):
        return Dislike.query.filter_by(user_id=self.id, post_id=post.id).count() > 0

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='post', lazy=True, cascade="all, delete-orphan")
    likes = db.relationship('Like', backref='post', lazy=True, cascade="all, delete-orphan")
    dislikes = db.relationship('Dislike', backref='post', lazy=True, cascade="all, delete-orphan")
    is_moderator_post = db.Column(db.Boolean, default=False)  # Yeni alan
    image_file = db.Column(db.String(20), nullable=True)  # Yeni alan
    is_approved = db.Column(db.Boolean, default=False)  # Yeni alan

    @property
    def like_count(self):
        return len(self.likes)

    @property
    def dislike_count(self):
        return len(self.dislikes)

    @property
    def net_likes(self):
        return self.like_count - self.dislike_count

    def is_liked_by(self, user):
        return Like.query.filter(Like.user_id == user.id, Like.post_id == self.id).count() > 0

    def is_disliked_by(self, user):
        return Dislike.query.filter(Dislike.user_id == user.id, Dislike.post_id == self.id).count() > 0

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

    def __repr__(self):
        return f"Comment('{self.content}', '{self.date_posted}')"

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)

class Dislike(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
