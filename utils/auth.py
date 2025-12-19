from functools import wraps
from flask import abort
from flask_login import current_user

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return abort(401)
            
            # Use the new helper method which also handles 'admin' as superuser
            if not current_user.has_any_role(roles):
                return abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
