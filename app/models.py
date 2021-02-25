from datetime import datetime

from flask import url_for
from flask_login import UserMixin
from sqlalchemy.ext.associationproxy import association_proxy

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
    image = db.Column(db.String(128), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    requested_friendships = db.relationship(
        'FriendshipRequest',
        foreign_keys='FriendshipRequest.requesting_user_id',
        backref='requesting_user')

    received_friendships = db.relationship(
        'FriendshipRequest',
        foreign_keys='FriendshipRequest.receiving_user_id',
        backref='receiving_user')

    aspiring_friends = association_proxy('received_friendships', 'requesting_user')
    desired_friends = association_proxy('requested_friendships', 'receiving_user')

    _friendships1 = db.relationship('Friendship',
                                    foreign_keys='Friendship.user1_id',
                                    backref='user1')

    _friendships2 = db.relationship('Friendship',
                                    foreign_keys='Friendship.user2_id',
                                    backref='user2')

    _friends1 = association_proxy('_friendships1', 'user2')
    _friends2 = association_proxy('_friendships2', 'user1')

    sent_messages = db.relationship('Message',
                                    foreign_keys='Message.sender_id',
                                    backref='sender')

    received_messages = db.relationship('Message',
                                        foreign_keys='Message.recipient_id',
                                        backref='recipient')

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
        return self._friendships1 + self._friendships2

    @property
    def friends(self):
        # TODO: BAD!
        return self._friends1 + self._friends2

    def get_friends(self):
        users1 = db.session.query(Friendship.user2).filter(Friendship.user1 == self)
        users2 = db.session.query(Friendship.user1).filter(Friendship.user2 == self)
        return users1.union(users2).all()
