class ContentSecurityPolicyMiddleware:
    """CSP (AC-1-14): только свои ресурсы, без внешних доменов и CDN."""

    POLICY = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'self' blob:; "
        "worker-src 'self'; manifest-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/admin/"):
            response.setdefault("Content-Security-Policy", self.POLICY)
        response.setdefault("Referrer-Policy", "same-origin")
        return response
