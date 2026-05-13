from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'club'

urlpatterns = [
    path('', views.home, name='home'),
    path('member/<int:member_id>/', views.member_detail, name='member_detail'),
    path(
        'member/<int:member_id>/edit/',
        views.member_profile_edit_view,
        name='member_profile_edit',
    ),
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('matches/', views.matches_view, name='matches'),
    path('matches/<int:match_id>/', views.match_detail_view, name='match_detail'),
    path('teams/', views.teams_list_view, name='teams_list'),
    path('teams/<slug:slug>/', views.team_detail_view, name='team_detail'),
    path('tournaments/', views.tournament_list_view, name='tournament_list'),
    path('tournaments/<slug:slug>/', views.tournament_detail_view, name='tournament_detail'),
    path('about/', views.about_view, name='about'),
    path('register/', views.register_view, name='register'),
    path('login/', views.ClubLoginView.as_view(), name='login'),
    path('login/otp/', views.otp_verify_view, name='otp_verify'),
    path('account/totp/', views.totp_manage_view, name='totp_manage'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(template_name='registration/password_reset_form.html'),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
        name='password_reset_done',
    ),
    path(
        'password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html'
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard/metrics/', views.dashboard_metrics_api, name='dashboard_metrics'),
]
