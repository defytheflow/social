from datetime import datetime

from flask import url_for, send_from_directory
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

friends = db.Table(
    'friends',
    db.Column(
        'user_id',
        db.Integer,
        db.ForeignKey('user.id',
                      ondelete='cascade'),
        nullable=False
    ),
    db.Column(
        'friend_id',
        db.Integer,
        db.ForeignKey('user.id',
                      ondelete='cascade'),
        nullable=False
    ),
    db.Column('created_at',
              db.DateTime,
              nullable=False,
              default=datetime.utcnow),
)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='cascade'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='cascade'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    body = db.Column(db.Text(), nullable=False)

    @property
    def formatted_created_at(self):
        return self.created_at.strftime("%m/%d/%Y %H:%M:%S")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    image = db.Column(db.String(128), nullable=True)

    friends = db.relationship(
        'User',
        secondary=friends,
        primaryjoin=friends.c.user_id == id,
        secondaryjoin=friends.c.friend_id == id,
        backref=db.backref('_friends',
                           lazy='dynamic'),
        lazy='dynamic'
    )

    sent_messages = db.relationship('Message', backref='sender', lazy='dynamic', foreign_keys=[Message.sender_id])
    received_messages = db.relationship('Message', backref='recipient', lazy='dynamic', foreign_keys=[Message.recipient_id])

    @property
    def all_friends(self):
         # TODO: sort them in alphabetical order.
        return self.friends.all() + self._friends.all()

    def __repr__(self):
        return f'User({self.username})'

    def get_absolute_url(self):
        return url_for('profile', username=self.username)

    @property
    def image_url(self):
        if self.image:
            return url_for('send_avatar', username=self.username)

        return url_for('static', filename='images/default-avatar.png')
