from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

from .models import User


class LoginForm(FlaskForm):

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log in')


class RegisterForm(FlaskForm):

    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password',
                             validators=[DataRequired(),
                                         Length(min=8, max=128)])
    password2 = PasswordField('Confirm Password',
                              validators=[
                                  DataRequired(),
                                  EqualTo('password', message='Passwords do not match.')
                              ])
    submit = SubmitField('Create account')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first() is not None:
            raise ValidationError('User with this username already exists.')


class MessageCreateForm(FlaskForm):

    body = StringField('Body', validators=[DataRequired()])
    submit = SubmitField('Send message')


class ChangeAvatarForm(FlaskForm):

    image = FileField(
        validators=[FileRequired(),
                    FileAllowed(['png', 'jpg', 'jpeg'], 'Images only!')])
    submit = SubmitField('Save')
