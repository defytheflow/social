from functools import wraps

from flask import redirect
from flask_login import current_user
from flask_socketio import disconnect


def anonymous_required(f):

    @wraps(f)
    def actual_decorator(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(current_user.get_profile_url())
        return f(*args, **kwargs)

    return actual_decorator


def authenticated_only(f):

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)

    return wrapped
