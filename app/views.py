import os

from flask import (abort, flash, jsonify, redirect, render_template, request,
                   send_from_directory, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from flask_socketio import emit
from werkzeug.utils import secure_filename

from . import app, db, socketio
from .forms import ChangeAvatarForm, LoginForm, MessageCreateForm, RegisterForm
from .models import Friendship, FriendshipRequest, Message, User
from .utils import anonymous_required, authenticated_only


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
        user = User.query.filter_by(username=form.data['username']).first()

        if user is None or not user.check_password(form.password.data):
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


@app.route('/update-about', methods=['POST'])
def update_about():
    about = request.get_json().get('about')

    if about is not None:
        current_user.about = about
        db.session.add(current_user)
        db.session.commit()
        return jsonify({'about': about})

    return jsonify({'about': None})


@app.route('/register', methods=['GET', 'POST'])
@anonymous_required
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
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


@app.route('/request-friend/<username>', methods=['POST'])
@login_required
def request_friend(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user in current_user.friends:
        abort(400)

    friend_request = FriendshipRequest(receiving_user_id=user.id)
    current_user.requested_friendships.append(friend_request)

    db.session.add(current_user)
    db.session.commit()

    return redirect(user.get_profile_url())


@app.route('/accept-friend/<username>', methods=['POST'])
@login_required
def accept_friend(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user in current_user.friends:
        abort(400)

    current_user.received_friendships.filter_by(requesting_user=user).delete()
    friendship = Friendship(user1=current_user, user2=user)

    db.session.add(friendship)
    db.session.commit()

    return redirect(current_user.get_profile_url())


@app.route('/refuse-friend/<username>', methods=['POST'])
@login_required
def refuse_friend(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user in current_user.friends:
        abort(400)

    current_user.received_friendships.filter_by(requesting_user=user).delete()

    return redirect(current_user.get_profile_url())


@app.route('/delete-friend/<username>', methods=['POST'])
@login_required
def delete_friend(username):
    user = User.query.filter_by(username=username).first_or_404()

    current_user.friendships1.filter_by(user2=user).delete()
    current_user.friendships2.filter_by(user1=user).delete()

    flash(f'{username} has been deleted from your friends!', 'info')
    return redirect(current_user.get_profile_url())


@app.route('/users')
@login_required
def users():
    username = request.args.get('username',)
    page = request.args.get('page', 1, type=int)

    qs = User.query.filter(User.username != current_user.username)
    if username is not None:
        qs = qs.filter(User.username.contains(username))

    pagination = qs.paginate(page, per_page=10, error_out=False)
    return render_template('users.html', pagination=pagination)


@app.route('/chats')
@login_required
def chats():
    return render_template('chats.html')


@app.route('/chats/<username>', methods=['GET'])
@login_required
def chat(username):
    user = User.query.filter_by(username=username).first_or_404()

    if user not in current_user.friends:
        abort(404)

    form = MessageCreateForm()
    messages = Message.query.filter((Message.sender_id == current_user.id) &
                                    (Message.recipient_id == user.id) |
                                    (Message.recipient_id == current_user.id) &
                                    (Message.sender_id == user.id)).order_by(
                                        Message.created_at).all()

    return render_template('chat.html', user=user, messages=messages, form=form)


@app.route('/messages/<int:message_id>', methods=['DELETE'])
@login_required
def delete_message(message_id):
    Message.query.filter(Message.id == message_id).delete()
    return {}, 204


session_ids = {}


@socketio.on('connect', namespace='/chat')
@authenticated_only
def on_connect():
    session_ids[current_user.username] = request.sid


@socketio.on('disconnect', namespace='/chat')
@authenticated_only
def on_disconnect():
    del session_ids[current_user.username]


@socketio.on('message', namespace='/chat')
@authenticated_only
def on_message(data):
    recipient_username = data.get('recipient', '')
    body = data.get('body', '')

    if recipient_username and body:
        recipient = User.query.filter_by(username=recipient_username).first()

        # Create a new message.
        message = Message(sender_id=current_user.id, recipient_id=recipient.id, body=body)
        db.session.add(message)
        db.session.commit()

        # Create a response.
        response = {
            'type': 'update',
            'data': {
                'sender': {
                    'username': message.sender.username,
                    'imageUrl': message.sender.image_url,
                },
                'recipient': {
                    'username': message.recipient.username,
                    'imageUrl': message.recipient.image_url
                },
                'body': message.body,
                'createdAt': message.formatted_created_at,
                'id': message.id,
            }
        }

        # Emit events.
        emit('message', response)
        if (recipient_room := session_ids.get(recipient.username)) is not None:
            emit('message', response, room=recipient_room)
