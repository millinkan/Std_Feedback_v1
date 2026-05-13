from django.conf import settings


def user_theme(request):
    """Club UI uses one palette site-wide (see static/css/theme.css)."""
    return {'ui_theme': 'classic'}


def admin_log_nav(request):
    """Expose log-viewer policy to admin templates (nav link visibility)."""
    return {
        'app_log_admin_superuser_only': getattr(settings, 'APP_LOG_ADMIN_SUPERUSER_ONLY', True),
    }


def oauth_public_base(request):
    """Base URL for OAuth redirect URI hints on register/login (production vs dev)."""
    configured = getattr(settings, 'PUBLIC_BASE_URL', '').strip().rstrip('/')
    if configured:
        base = configured
    elif request.get_host():
        scheme = 'https' if request.is_secure() else 'http'
        base = f'{scheme}://{request.get_host()}'
    else:
        base = ''
    return {'oauth_public_base': base}
