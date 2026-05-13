from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from club.models import Member

from .models import Game
from .tasks import analyse_game_task, fetch_lichess_games_task, generate_insights_task


class GameActionSerializer(serializers.Serializer):
    game_id = serializers.CharField()


class MemberActionSerializer(serializers.Serializer):
    member_id = serializers.IntegerField(required=False)


class ImportGamesSerializer(serializers.Serializer):
    lichess_username = serializers.CharField(required=False, allow_blank=False)


class ImportGamesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ImportGamesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = getattr(request.user, 'profile', None)
        if profile is None:
            return Response({'detail': 'User profile not configured.'}, status=status.HTTP_400_BAD_REQUEST)
        lichess_username = serializer.validated_data.get('lichess_username') or profile.lichess_username
        if not lichess_username:
            return Response({'detail': 'No lichess_username provided.'}, status=status.HTTP_400_BAD_REQUEST)

        member, _ = Member.objects.get_or_create(
            display_name=request.user.username,
            defaults={'lichess_username': lichess_username},
        )
        member.lichess_username = lichess_username
        member.save(update_fields=['lichess_username'])
        fetch_lichess_games_task.delay(lichess_username, member.id, profile.lichess_api_key)
        return Response({'status': 'queued', 'task': 'fetch_lichess_games', 'member_id': member.id})


class AnalyseGameAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GameActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game_ref = serializer.validated_data['game_id'].strip()
        game = Game.objects.filter(lichess_game_id=game_ref).first()
        if not game and game_ref.isdigit():
            game = Game.objects.filter(pk=int(game_ref)).first()
        if not game:
            return Response({'detail': 'Game not found for provided game_id.'}, status=status.HTTP_404_NOT_FOUND)

        analyse_game_task.delay(game.id)
        return Response({'status': 'queued', 'task': 'analyse_game', 'game_id': game.id, 'lichess_game_id': game.lichess_game_id})


class GenerateInsightsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MemberActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        member_id = serializer.validated_data.get('member_id')
        if not member_id:
            profile = getattr(request.user, 'profile', None)
            if profile is None:
                return Response({'detail': 'User profile not configured.'}, status=status.HTTP_400_BAD_REQUEST)
            member = Member.objects.filter(lichess_username=profile.lichess_username).first()
            if not member:
                return Response({'detail': 'No member found for current user.'}, status=status.HTTP_400_BAD_REQUEST)
            member_id = member.id
        generate_insights_task.delay(member_id)
        return Response({'status': 'queued', 'task': 'generate_insights', 'member_id': member_id})


class GameAnalysisAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, game_id):
        game_ref = game_id.strip()
        game = Game.objects.filter(lichess_game_id=game_ref).select_related('analysis').first()
        if not game and game_ref.isdigit():
            game = Game.objects.filter(pk=int(game_ref)).select_related('analysis').first()
        if not game:
            return Response({'detail': 'Game not found.'}, status=status.HTTP_404_NOT_FOUND)
        analysis = getattr(game, 'analysis', None)
        moves = []
        if analysis:
            moves = list(
                analysis.move_evaluations.values(
                    'move_number',
                    'is_white',
                    'move_san',
                    'best_move_san',
                    'centipawn_loss',
                    'classification',
                )
            )
        return Response(
            {
                'game': {
                    'id': game.id,
                    'lichess_game_id': game.lichess_game_id,
                    'result': game.result,
                    'time_control': game.time_control,
                },
                'analysis': {
                    'status': analysis.status,
                    'white_avg_centipawn_loss': analysis.white_avg_centipawn_loss,
                    'black_avg_centipawn_loss': analysis.black_avg_centipawn_loss,
                }
                if analysis
                else None,
                'moves': moves,
            }
        )


class MemberInsightsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, member_id):
        member = Member.objects.filter(pk=member_id).first()
        if not member:
            return Response({'detail': 'Member not found.'}, status=status.HTTP_404_NOT_FOUND)
        insights = list(
            member.insights.values('category', 'title', 'description', 'recommendation', 'games_analysed', 'avg_centipawn_loss')
        )
        return Response({'member_id': member.id, 'member': member.display_name, 'insights': insights})
