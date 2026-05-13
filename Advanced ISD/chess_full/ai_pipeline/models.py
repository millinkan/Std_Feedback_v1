from django.db import models

from club.models import Member


class Game(models.Model):
    lichess_game_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    player_white = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='lichess_games_as_white')
    player_black = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='lichess_games_as_black')
    pgn = models.TextField(help_text='Portable Game Notation of the full game')
    time_control = models.CharField(max_length=50, blank=True)
    result = models.CharField(max_length=10, help_text='e.g. 1-0, 0-1, 1/2-1/2')
    played_at = models.DateTimeField()
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-played_at']

    def __str__(self):
        return f'{self.player_white} vs {self.player_black} ({self.result})'


class GameAnalysis(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    game = models.OneToOneField(Game, on_delete=models.CASCADE, related_name='analysis')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    depth = models.IntegerField(default=20, help_text='Stockfish search depth used')
    white_avg_centipawn_loss = models.FloatField(null=True, blank=True)
    black_avg_centipawn_loss = models.FloatField(null=True, blank=True)
    white_blunders = models.IntegerField(default=0)
    black_blunders = models.IntegerField(default=0)
    white_mistakes = models.IntegerField(default=0)
    black_mistakes = models.IntegerField(default=0)
    white_inaccuracies = models.IntegerField(default=0)
    black_inaccuracies = models.IntegerField(default=0)
    analysed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Game Analyses'

    def __str__(self):
        return f'Analysis of {self.game} - {self.get_status_display()}'


class MoveEvaluation(models.Model):
    CLASSIFICATION_CHOICES = [
        ('best', 'Best'),
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('inaccuracy', 'Inaccuracy'),
        ('mistake', 'Mistake'),
        ('blunder', 'Blunder'),
    ]

    analysis = models.ForeignKey(GameAnalysis, on_delete=models.CASCADE, related_name='move_evaluations')
    move_number = models.IntegerField()
    is_white = models.BooleanField(help_text='True if this is a white move')
    move_san = models.CharField(max_length=10, help_text='Standard Algebraic Notation, e.g. Nf3')
    best_move_san = models.CharField(max_length=10, blank=True)
    eval_before = models.FloatField(help_text='Centipawn evaluation before the move')
    eval_after = models.FloatField(help_text='Centipawn evaluation after the move')
    centipawn_loss = models.FloatField(default=0)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES, default='good')

    class Meta:
        ordering = ['analysis', 'move_number', '-is_white']

    def __str__(self):
        side = 'W' if self.is_white else 'B'
        return f'Move {self.move_number}{side}: {self.move_san} ({self.classification})'

    @staticmethod
    def format_eval_cp(cp):
        """Human-readable score from stored centipawns (±999 used as mate sentinel in analysis)."""
        if cp is None:
            return '—'
        try:
            v = float(cp)
        except (TypeError, ValueError):
            return '—'
        if v >= 998:
            return 'Mate (+)'
        if v <= -998:
            return 'Mate (−)'
        pawns = v / 100.0
        return f'{pawns:+.2f}'

    @property
    def eval_before_display(self):
        return self.format_eval_cp(self.eval_before)

    @property
    def eval_after_display(self):
        return self.format_eval_cp(self.eval_after)

    @property
    def eval_delta_for_mover_display(self):
        """Signed change from the moving side’s perspective (positive = improved for you)."""
        if self.eval_before is None or self.eval_after is None:
            return '—'
        try:
            before, after = float(self.eval_before), float(self.eval_after)
        except (TypeError, ValueError):
            return '—'
        if self.is_white:
            delta = after - before
        else:
            delta = before - after
        return f'{delta / 100.0:+.2f}'


class PlayerInsight(models.Model):
    CATEGORY_CHOICES = [
        ('opening', 'Opening'),
        ('middlegame', 'Middlegame'),
        ('endgame', 'Endgame'),
        ('tactics', 'Tactics'),
        ('time_management', 'Time Management'),
        ('positional', 'Positional Play'),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='insights')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(help_text='Detailed insight with examples')
    recommendation = models.TextField(help_text='Suggested improvement actions')
    games_analysed = models.IntegerField(default=0)
    avg_centipawn_loss = models.FloatField(null=True, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return f'{self.member} - {self.title}'
