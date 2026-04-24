from django.contrib import admin

from .models import Game, GameAnalysis, MoveEvaluation, PlayerInsight


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('player_white', 'player_black', 'result', 'time_control', 'played_at')
    list_filter = ('result', 'time_control')
    search_fields = ('player_white__display_name', 'player_black__display_name', 'lichess_game_id')


@admin.register(GameAnalysis)
class GameAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        'game',
        'status',
        'depth',
        'white_avg_centipawn_loss',
        'black_avg_centipawn_loss',
        'white_blunders',
        'black_blunders',
        'analysed_at',
    )
    list_filter = ('status',)


@admin.register(MoveEvaluation)
class MoveEvaluationAdmin(admin.ModelAdmin):
    list_display = ('analysis', 'move_number', 'is_white', 'move_san', 'centipawn_loss', 'classification')
    list_filter = ('classification', 'is_white')


@admin.register(PlayerInsight)
class PlayerInsightAdmin(admin.ModelAdmin):
    list_display = ('member', 'category', 'title', 'games_analysed', 'generated_at')
    list_filter = ('category',)
    search_fields = ('member__display_name', 'title')
