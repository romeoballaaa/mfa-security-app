from django.conf import settings


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)

        if settings.DEBUG and response.status_code >= 400:
            return response
        if request.path.startswith("/admin/"):
            return response

        response.setdefault("Content-Security-Policy", settings.CSP_POLICY)
        return response