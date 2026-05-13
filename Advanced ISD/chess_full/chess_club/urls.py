"""
chess_club URL Configuration

The `urlpatterns` list routes URLs to views.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from club.admin_log_view import application_log_view

urlpatterns = [
    path(
        'admin/diagnostics/application-logs/',
        admin.site.admin_view(application_log_view),
        name='admin_application_logs',
    ),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('club.urls')),
    path('ai/', include('ai_pipeline.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='api-schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='api-schema'), name='api-docs'),
    path('api/', include('ai_pipeline.api_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
