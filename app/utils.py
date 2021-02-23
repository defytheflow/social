import functools

from flask import redirect
from flask_login import current_user


def anonymous_required(view_func):

    @functools.wraps(view_func)
    def actual_decorator(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(current_user.get_profile_url())
        return view_func(*args, **kwargs)

    return actual_decorator
