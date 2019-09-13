def DisableCSRFMiddleware(get_response):
    def middleware(request):
        setattr(request, '_dont_enforce_csrf_checks', True)
        return get_response(request)

    return middleware
