from django.urls import path

from .api import (
    AnalyseGameAPIView,
    GameAnalysisAPIView,
    GenerateInsightsAPIView,
    ImportGamesAPIView,
    MemberInsightsAPIView,
)

urlpatterns = [
    path('import-games/', ImportGamesAPIView.as_view(), name='api-import-games'),
    path('analyse-game/', AnalyseGameAPIView.as_view(), name='api-analyse-game'),
    path('generate-insights/', GenerateInsightsAPIView.as_view(), name='api-generate-insights'),
    path('games/<str:game_id>/analysis/', GameAnalysisAPIView.as_view(), name='api-game-analysis'),
    path('members/<int:member_id>/insights/', MemberInsightsAPIView.as_view(), name='api-member-insights'),
]
