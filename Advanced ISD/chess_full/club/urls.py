from django.urls import path

from . import views

app_name = 'club'

urlpatterns = [
    path('', views.home, name='home'),
    path('member/<int:member_id>/', views.member_detail, name='member_detail'),
]
