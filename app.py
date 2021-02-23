import os

import flask
from flask_login import (LoginManager, current_user, login_required,
                         login_user, logout_user)
from flask_socketio import SocketIO, emit, join_room, send
from werkzeug.utils import secure_filename

from forms import ChangeAvatarForm, LoginForm, MessageCreateForm, RegisterForm
from models import Message, User, db

app = flask.Flask(__name__)

app.config['SECRET_KEY'] = 'nikita is natural'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///social.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'media'
app.config['DEBUG'] = True

socketio = SocketIO(app)

db.app = app
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def home():
    if current_user.is_authenticated:
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))
    return flask.redirect(flask.url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username,
                                    password=password).first()
        if not user:
            flask.flash('Invalid username or password', 'danger')
            return flask.render_template('login.html', form=form)

        login_user(user)
        return flask.redirect(flask.url_for('profile', username=user.username))

    return flask.render_template('login.html', form=form)


@app.route('/users')
@login_required
def users():
    users = User.query.filter(User.username != current_user.username).all()
    return flask.render_template('users.html', users=users)


@app.route('/change-avatar', methods=['GET', 'POST'])
@login_required
def change_avatar():
    form = ChangeAvatarForm()

    if form.validate_on_submit():
        # save file on disk.
        image = form.image.data
        imagename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], imagename))

        # save path to file to db.
        current_user.image = imagename
        db.session.add(current_user)
        db.session.commit()

        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    return flask.render_template('change-avatar.html', form=form)


@app.route('/send-avatar/<string:username>')
@login_required
def send_avatar(username):
    user = User.query.filter_by(username=username).first()

    if not user:
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    return flask.send_from_directory(app.config['UPLOAD_FOLDER'], user.image)


@app.route('/add-friend/<string:username>', methods=['POST'])
@login_required
def add_friend(username):
    user = User.query.filter_by(username=username).first()

    if not user:
        flask.flash('This user does not exist', 'info')
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    if user in current_user.all_friends:
        flask.flash(f'You and {user.username} are already friends!')
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    current_user.friends.append(user)
    db.session.add(current_user)
    db.session.commit()

    flask.flash(f'{user.username} has been added to your friends!')
    return flask.redirect(
        flask.url_for('profile', username=current_user.username))


@app.route('/users/<string:username>')
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()

    if not user:
        flask.flash('This user does not exist', 'info')
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    return flask.render_template('profile.html', user=user)


@app.route('/chats')
@login_required
def chats():
    return flask.render_template('chats.html')


@app.route('/chats/<string:username>', methods=['GET', 'POST'])
@login_required
def chat_with(username):
    user = User.query.filter_by(username=username).first()

    if not user or user not in current_user.all_friends:
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    form = MessageCreateForm()
    if form.validate_on_submit():
        message = Message(recipient_id=user.id, body=form.body.data)

        current_user.sent_messages.append(message)
        db.session.add(current_user)
        db.session.commit()

        # send({'data': 'New message'}) request objects has no attribute namespace
        # socketio.send('LOL')

        return flask.redirect(
            flask.url_for('chat_with', username=user.username))

    messages = Message.query.filter((Message.sender_id == current_user.id)
                                    & (Message.recipient_id == user.id)
                                    | (Message.recipient_id == current_user.id)
                                    & (Message.sender_id == user.id)).order_by(
                                        Message.created_at).all()

    return flask.render_template('chat-with.html',
                                 user=user,
                                 messages=messages,
                                 form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return flask.redirect(
            flask.url_for('profile', username=current_user.username))

    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data,
                    email=form.email.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()

        flask.flash(f'Account for {user.username} has been created.',
                    'success')
        return flask.redirect(flask.url_for('login'))

    return flask.render_template('register.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flask.flash('Logged out!', 'info')
    return flask.redirect(flask.url_for('login'))


# Subscripte to message events.


@socketio.on('connect')
def on_connect():
    data = {'username': current_user.username}
    send(data)


@socketio.on('join')
def on_join(data):
    print(flask.request.args)
    # username = data['with']
    # join_room(current_user.username)


# To run from terminal:
# > python -m pipenv shell
# > python app.py
# > exit
if __name__ == '__main__':
    # app.run(debug=True)
    socketio.run(app)
    db.create_all()
