from django.shortcuts import get_object_or_404, render

from ai_pipeline.models import Game

from .models import Member


def home(request):
    members = Member.objects.all()[:10]
    recent_games = Game.objects.select_related('player_white', 'player_black')[:10]
    return render(
        request,
        'club/home.html',
        {
            'members': members,
            'recent_games': recent_games,
        },
    )


def member_detail(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    games = Game.objects.filter(player_white=member) | Game.objects.filter(player_black=member)
    games = games.select_related('player_white', 'player_black').distinct()[:20]
    return render(
        request,
        'club/member_detail.html',
        {
            'member': member,
            'games': games,
        },
    )
