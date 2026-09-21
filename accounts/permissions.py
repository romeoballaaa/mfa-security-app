from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from audit.models import SecurityEvent
from audit.services import record_event


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if not request.user.is_app_admin:
            record_event(
                SecurityEvent.EventType.UNAUTHORIZED_ACCESS,
                request=request,
                success=False,
                metadata={"reason": "not_admin", "path": request.path},
            )
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return _wrapped