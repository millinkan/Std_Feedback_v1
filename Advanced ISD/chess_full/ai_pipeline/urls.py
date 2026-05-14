from django.urls import path

from . import views

app_name = 'ai_pipeline'

urlpatterns = [
    path('game/<str:game_id>/embed/', views.game_embed, name='game_embed'),
    path(
        'game/<str:game_id>/analysis/visual/',
        views.game_analysis_visual_view,
        name='game_analysis_visual',
    ),
    path('game/<str:game_id>/analysis/', views.game_analysis_view, name='game_analysis'),
    path('game/<str:game_id>/analysis/export/<str:fmt>/', views.export_game_analysis, name='export_game_analysis'),
    path('member/<int:member_id>/insights/', views.player_insights_view, name='player_insights'),
]
