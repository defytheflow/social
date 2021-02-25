import os

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.utils import secure_filename

from . import app, db
from .forms import ChangeAvatarForm, LoginForm, MessageCreateForm, RegisterForm
from .models import Friendship, Message, User
from .utils import anonymous_required


@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(error):
    return render_template('500.html'), 500


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


@app.route('/check-unique')
def check_unique():
    username = request.args.get('username')

    if username is not None:
        if User.query.filter_by(username=username).first() is None:
            return jsonify({'username': True})

        return jsonify({'username': False})


@app.route('/register', methods=['GET', 'POST'])
@anonymous_required
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        user = User(username=form.username.data, password=form.password.data)
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


@app.route('/users/<username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user=user)


@app.route('/change-avatar', methods=['GET', 'POST'])
@login_required
def change_avatar():
    form = ChangeAvatarForm()

    if form.validate_on_submit():
        # save file on disk.
        image = form.image.data
        image_name = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))

        # save path to file to db.
        current_user.image = image_name
        db.session.add(current_user)
        db.session.commit()

        return redirect(current_user.get_profile_url())

    return render_template('change-avatar.html', form=form)


@app.route('/send-avatar/<username>')
@login_required
def send_avatar(username):
    user = User.query.filter_by(username=username).first_or_404()
    return send_from_directory(app.config['UPLOAD_FOLDER'], user.image)


@app.route('/add-friend/<username>', methods=['POST'])
@login_required
def add_friend(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user in current_user.friends:
        flash(f'You and {user.username} are already friends!', 'info')
        return redirect(current_user.get_profile_url())

    friendship = Friendship(user1_id=current_user.id, user2_id=user.id)
    db.session.add(friendship)
    db.session.commit()

    flash(f'{username} has been added to your friends!', 'info')
    return redirect(current_user.get_profile_url())


@app.route('/delete-friend/<username>', methods=['POST'])
@login_required
def delete_friend(username):
    user = User.query.filter_by(username=username).first_or_404()

    Friendship.query.filter((Friendship.user1_id == current_user.id) &
                            (Friendship.user2_id == user.id) |
                            (Friendship.user2_id == current_user.id) &
                            (Friendship.user1_id == user.id)).delete()

    flash(f'{username} has been deleted from your friends!', 'info')
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


@app.route('/chats/<username>', methods=['GET', 'POST'])
@login_required
def chat_with(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user not in current_user.friends:
        abort(404)

    form = MessageCreateForm()

    if form.validate_on_submit():
        message = Message(recipient_id=user.id, body=form.body.data)
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
