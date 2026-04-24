"""
chess_club URL Configuration

The `urlpatterns` list routes URLs to views.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('club.urls')),
    path('ai/', include('ai_pipeline.urls')),
]
