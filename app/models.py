from datetime import datetime

from flask import url_for
from flask_login import UserMixin
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.associationproxy import association_proxy
from werkzeug.security import check_password_hash, generate_password_hash

from . import db


class Message(db.Model):

    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)

    sender_id = db.Column(db.Integer,
                          db.ForeignKey('users.id', ondelete='cascade'),
                          nullable=False)

    recipient_id = db.Column(db.Integer,
                             db.ForeignKey('users.id', ondelete='cascade'),
                             nullable=False)

    body = db.Column(db.Text(), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Message {self.body[:30]}'

    @property
    def formatted_created_at(self):
        return self.created_at.strftime('%m/%d/%Y %H:%M:%S')


class FriendshipRequest(db.Model):

    __tablename__ = 'friendship_requests'

    requesting_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        primary_key=True,
    )

    receiving_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        primary_key=True,
    )


class Friendship(db.Model):

    user1_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        primary_key=True,
    )

    user2_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='cascade'),
        primary_key=True,
    )

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Friendship {self.user1} -> {self.user2}>'


class User(UserMixin, db.Model):

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    about = db.Column(db.String(140), nullable=False, default='')
    image = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    requested_friendships = db.relationship(
        'FriendshipRequest',
        foreign_keys='FriendshipRequest.requesting_user_id',
        backref='requesting_user',
        lazy='dynamic')

    received_friendships = db.relationship(
        'FriendshipRequest',
        foreign_keys='FriendshipRequest.receiving_user_id',
        backref='receiving_user',
        lazy='dynamic')

    aspiring_friends = association_proxy('received_friendships', 'requesting_user')
    desired_friends = association_proxy('requested_friendships', 'receiving_user')

    friendships1 = db.relationship('Friendship',
                                   foreign_keys='Friendship.user1_id',
                                   backref='user1',
                                   lazy='dynamic')

    friendships2 = db.relationship('Friendship',
                                   foreign_keys='Friendship.user2_id',
                                   backref='user2',
                                   lazy='dynamic')

    friends1 = association_proxy('friendships1', 'user2')
    friends2 = association_proxy('friendships2', 'user1')

    sent_messages = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='sender',
                                    lazy='dynamic')

    received_messages = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient',
                                        lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def get_profile_url(self):
        return url_for('profile', username=self.username)

    @property
    def image_url(self):
        if self.image:
            return url_for('send_avatar', username=self.username)
        return url_for('static', filename='images/default-avatar.png')

    @property
    def friendships(self):
        # TODO: BAD!
        return self.friendships1.all() + self.friendships2.all()

    @property
    def friends(self):
        # TODO: BAD!
        return self.friends1 + self.friends2

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    # def get_friends(self):
    #     users1 = db.session.query(Friendship.user2).filter(Friendship.user1 == self)
    #     users2 = db.session.query(Friendship.user1).filter(Friendship.user2 == self)
    #     return users1.union(users2).all()

    @classmethod
    def generate_fake(cls, count=100):
        from faker import Faker
        fake = Faker()

        for i in range(count):
            user = cls(username=fake.user_name(), about=fake.paragraph())
            user.set_password('pass')
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
