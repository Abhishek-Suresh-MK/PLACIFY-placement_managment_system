from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import Role


def role_required(*roles):
    """
    Restricts a view to authenticated users whose `role` is in `roles`
    (superusers always pass). Unauthenticated users are sent to the login
    page (django's default `login_required` behavior); authenticated users
    with the wrong role are redirected to the homepage instead of getting a
    raw 403, matching the legacy app's `header("Location: index.php")`
    pattern used by admin.php/recruiters.php for unauthorized access.
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if user.is_superuser or user.role in roles:
                return view_func(request, *args, **kwargs)
            return redirect("placements:index")

        return wrapped

    return decorator


admin_required = role_required(Role.ADMIN)
recruiter_required = role_required(Role.RECRUITER)
student_required = role_required(Role.STUDENT)
