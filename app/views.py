import os

from flask import (flash, redirect, render_template, send_from_directory, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from . import app, db
from .forms import ChangeAvatarForm, LoginForm, MessageCreateForm, RegisterForm
from .models import Friendship, Message, User
from .utils import anonymous_required


@app.route('/')
@anonymous_required
def home():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
@anonymous_required
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.data['username'],
                                    password=form.data['password']).first()

        if user is None:
            flash('Invalid username or/and password.', 'danger')
            return render_template('login.html', form=form)

        login_user(user)
        return redirect(user.get_profile_url())

    return render_template('login.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
@anonymous_required
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        user = User(username=form.data['username'],
                    email=form.data['email'],
                    password=form.data['password'])
        db.session.add(user)
        db.session.commit()

        flash(f'Account for {user.username} has been created.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out!', 'info')
    return redirect(url_for('login'))


@app.route('/users/<string:username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User with username '{username}' does not exist!")
        return redirect(current_user.get_profile_url())

    return render_template('profile.html', user=user)


@app.route('/change-avatar', methods=['GET', 'POST'])
@login_required
def change_avatar():
    form = ChangeAvatarForm()

    if form.validate_on_submit():
        # save file on disk.
        image = form.data['image']
        image_name = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))

        # save path to file to db.
        current_user.image = image_name
        db.session.add(current_user)
        db.session.commit()

        return redirect(current_user.get_profile_url())

    return render_template('change-avatar.html', form=form)


@app.route('/send-avatar/<string:username>')
@login_required
def send_avatar(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        return redirect(current_user.get_profile_url())

    return send_from_directory(app.config['UPLOAD_FOLDER'], user.image)


@app.route('/add-friend/<string:username>', methods=['POST'])
@login_required
def add_friend(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User with username '{username}' does not exist!")
        return redirect(current_user.get_profile_url())

    if user in current_user.friends:
        flash(f"You and '{user.username}' are already friends!")
        return redirect(current_user.get_profile_url())

    new_friendship = Friendship(user1_id=current_user.id, user2_id=user.id)
    db.session.add(new_friendship)
    db.session.commit()

    flash(f"'{user.username}' has been added to your friends!")
    return redirect(current_user.get_profile_url())


@app.route('/delete-friend/<string:username>', methods=['POST'])
@login_required
def delete_friend(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User with username '{username}' does not exist!")
        return redirect(current_user.get_profile_url())

    Friendship.query.filter((Friendship.user1_id == current_user.id) &
                            (Friendship.user2_id == user.id) |
                            (Friendship.user2_id == current_user.id) &
                            (Friendship.user1_id == user.id)).delete()

    flash(f'Friend {username} has been deleted!', 'info')
    return redirect(current_user.get_profile_url())


@app.route('/users')
@login_required
def users():
    users = User.query.filter(User.username != current_user.username).all()
    return render_template('users.html', users=users)


@app.route('/chats')
@login_required
def chats():
    return render_template('chats.html')


@app.route('/chats/<string:username>', methods=['GET', 'POST'])
@login_required
def chat_with(username):
    user = User.query.filter_by(username=username).first()

    if user is None:
        flash("User with username '{username}' does not exist!")
        return redirect(current_user.get_profile_url())

    if user not in current_user.friends:
        flash(f'You must be friends with {user.username} to have a chat!', 'info')
        return redirect(current_user.get_profile_url())

    form = MessageCreateForm()

    if form.validate_on_submit():
        message = Message(recipient_id=user.id, body=form.data['body'])

        current_user.sent_messages.append(message)
        db.session.add(current_user)
        db.session.commit()

        return redirect(url_for('chat_with', username=user.username))

    messages = Message.query.filter((Message.sender_id == current_user.id) &
                                    (Message.recipient_id == user.id) |
                                    (Message.recipient_id == current_user.id) &
                                    (Message.sender_id == user.id)).order_by(
                                        Message.created_at).all()

    return render_template('chat-with.html', user=user, messages=messages, form=form)
