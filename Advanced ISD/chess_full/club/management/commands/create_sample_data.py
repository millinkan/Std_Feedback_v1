"""Seed OTB matches, announcements, members, and teams for staging (e.g. Codespaces)."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from club.constants import CLUB_PRIMARY_VENUE
from club.models import Announcement, Match, Member, Team, TeamMembership

User = get_user_model()

# Members identifiable for --purge-seed (and legacy handles from older seeds).
MEMBER_SPECS = [
    ('Marie Weber', 'mweber_eschen'),
    ('Luca Büchel', 'lbuechel_eschen'),
    ('Nina Klaus', 'nklaus_eschen'),
    ('Jonas Quaderer', 'jquaderer_eschen'),
    ('Sophie Meier', 'smeier_eschen'),
    ('Markus Schädler', 'mschaedler_eschen'),
    ('Elena Beck', 'ebeck_eschen'),
    ('Bruno Marxer', 'bmarxer_eschen'),
    ('Alice Winter', 'awinter_eschen'),
    ('Bob Feger', 'bfeger_eschen'),
]

SEED_MEMBER_LICHESS = frozenset(spec[1] for spec in MEMBER_SPECS)

LEGACY_MEMBER_LICHESS = frozenset(
    {
        'marie_eschen_demo',
        'luca_eschen_demo',
        'nina_eschen_demo',
        'jonas_eschen_demo',
        'sophie_eschen_demo',
        'markus_eschen_demo',
        'elena_eschen_demo',
        'bruno_eschen_demo',
        'alice_club_demo',
        'bob_club_demo',
    }
)

CLUB_DEFAULT_VENUE = CLUB_PRIMARY_VENUE

ANNOUNCEMENTS = [
    (
        'Herbst-Schnellschach: erste Runden ab 15. Oktober',
        'Wir starten wieder mit einer kleinen Rundenturnier-Gruppe am Vereinsabend. Anmeldung bis eine Woche vorher beim Vorstand.',
    ),
    (
        'Parkplatz Gemeindehaus Eschen — kurze Hinweise',
        'Am Donnerstagabend oft parallel Veranstaltung: kurzzeitig Parkfelder nördlich des Platzes oder öV (Bus Richtung Eschen/Zentrum) bevorzugen.',
    ),
    (
        'Jugendstunde Sundays, Schulhaus Eschen',
        'Einsteiger:innen von 09:45 Uhr mit kurzen Unterrichtseinheiten plus freies Spielen. Betreuung wechselt zwischen Luca und Nora.',
    ),
    (
        'Zeitkontrollen nach FIDE-Anhang für Club-Opens',
        'Für offene Vereinsranglisten gelten wieder die gleichen Standards wie in den Landesmeisterschaften des Fürstentums (90+30 klassisch wo ausgeschrieben).',
    ),
    (
        'Willkommen am öffentlichen Vereinsportal',
        'Über diese Seite erscheinen Spieltermine und interne Rundschreiben. Persönliche Lichess-Spiele können nach Login ergänzend importiert werden.',
    ),
]


class Command(BaseCommand):
    help = (
        'Seed Eschen-themed sample members, announcements, matches, and teams. '
        'Use --purge-seed before re-running to remove prior seed rows; --purge-demo is a deprecated alias.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-club-stats',
            action='store_true',
            help='Clear all OTB matches and ELO history, reset member club ratings.',
        )
        parser.add_argument(
            '--purge-seed',
            action='store_true',
            help=(
                'Remove seed members (current + legacy handles), seed announcements '
                '(by title match), then re-run a clean import.'
            ),
        )
        parser.add_argument(
            '--purge-demo',
            action='store_true',
            help='Deprecated: same as --purge-seed.',
        )

    def handle(self, *args, **options):
        from club.models import EloHistory
        from club.services.match_elo import recalculate_all_club_elo

        if options['purge_seed'] or options['purge_demo']:
            self._purge_seed()

        if options['reset_club_stats']:
            Match.objects.all().delete()
            EloHistory.objects.all().delete()
            Member.objects.all().update(elo_rating=1500.0, wins=0, losses=0, draws=0)
            self.stdout.write(self.style.WARNING('Cleared OTB matches, ELO history, and reset club ratings.'))

        with transaction.atomic():
            admin_user, created = User.objects.get_or_create(
                username='admin',
                defaults={'email': 'admin@example.com', 'is_staff': True, 'is_superuser': True},
            )
            if created:
                admin_user.set_password('admin')
                admin_user.save()

            members = []
            for display_name, lichess in MEMBER_SPECS:
                m, _ = Member.objects.get_or_create(
                    lichess_username=lichess,
                    defaults={'display_name': display_name},
                )
                if m.display_name != display_name:
                    m.display_name = display_name
                    m.save(update_fields=['display_name'])
                members.append(m)

            by_lichess = {m.lichess_username: m for m in members}
            now = timezone.now()

            upcoming_specs = [
                (by_lichess['mweber_eschen'], by_lichess['lbuechel_eschen'], now + timedelta(days=2, hours=18)),
                (by_lichess['nklaus_eschen'], by_lichess['jquaderer_eschen'], now + timedelta(days=5, hours=17, minutes=30)),
                (by_lichess['smeier_eschen'], by_lichess['mschaedler_eschen'], now + timedelta(days=9, hours=14)),
                (by_lichess['ebeck_eschen'], by_lichess['bmarxer_eschen'], now + timedelta(days=12, hours=19)),
                (by_lichess['awinter_eschen'], by_lichess['bfeger_eschen'], now + timedelta(days=14, hours=16)),
            ]
            for white, black, start in upcoming_specs:
                if not Match.objects.filter(
                    white_player=white,
                    black_player=black,
                    scheduled_at=start,
                ).exists():
                    Match.objects.create(
                        white_player=white,
                        black_player=black,
                        status=Match.STATUS_SCHEDULED,
                        venue=CLUB_DEFAULT_VENUE,
                        scheduled_at=start,
                    )

            base = now - timedelta(days=120)
            completed_rows = [
                (by_lichess['mweber_eschen'], by_lichess['lbuechel_eschen'], Match.RESULT_WHITE, base),
                (by_lichess['nklaus_eschen'], by_lichess['smeier_eschen'], Match.RESULT_BLACK, base + timedelta(days=7)),
                (by_lichess['mschaedler_eschen'], by_lichess['mweber_eschen'], Match.RESULT_DRAW, base + timedelta(days=14)),
                (by_lichess['lbuechel_eschen'], by_lichess['jquaderer_eschen'], Match.RESULT_WHITE, base + timedelta(days=21)),
                (by_lichess['bmarxer_eschen'], by_lichess['ebeck_eschen'], Match.RESULT_WHITE, base + timedelta(days=28)),
                (by_lichess['awinter_eschen'], by_lichess['bfeger_eschen'], Match.RESULT_WHITE, base + timedelta(days=35)),
                (by_lichess['bfeger_eschen'], by_lichess['awinter_eschen'], Match.RESULT_DRAW, base + timedelta(days=42)),
                (by_lichess['smeier_eschen'], by_lichess['nklaus_eschen'], Match.RESULT_WHITE, base + timedelta(days=49)),
                (by_lichess['jquaderer_eschen'], by_lichess['mschaedler_eschen'], Match.RESULT_BLACK, base + timedelta(days=56)),
                (by_lichess['ebeck_eschen'], by_lichess['mweber_eschen'], Match.RESULT_BLACK, base + timedelta(days=63)),
                (by_lichess['mweber_eschen'], by_lichess['bmarxer_eschen'], Match.RESULT_WHITE, base + timedelta(days=70)),
                (by_lichess['mschaedler_eschen'], by_lichess['lbuechel_eschen'], Match.RESULT_DRAW, base + timedelta(days=77)),
            ]
            for white, black, result, scheduled in completed_rows:
                completed_at = scheduled + timedelta(hours=3)
                if Match.objects.filter(white_player=white, black_player=black, scheduled_at=scheduled).exists():
                    continue
                Match.objects.create(
                    white_player=white,
                    black_player=black,
                    status=Match.STATUS_COMPLETED,
                    result=result,
                    venue=CLUB_DEFAULT_VENUE,
                    scheduled_at=scheduled,
                    completed_at=completed_at,
                )

            for idx, (title, body) in enumerate(ANNOUNCEMENTS):
                published = now - timedelta(days=idx * 4 + 1)
                ann, created_ann = Announcement.objects.get_or_create(
                    title=title,
                    defaults={'body': body, 'published_at': published, 'author': admin_user},
                )
                if not created_ann:
                    ann.body = body
                    ann.published_at = published
                    ann.author = admin_user
                    ann.save()

            team, _ = Team.objects.get_or_create(
                name='Eschen Schnellschach Squad',
                defaults={'description': 'Wöchentliche OTB Rapid-Runden im Vereinsbetrieb Eschen.'},
            )
            for m in members[:8]:
                TeamMembership.objects.get_or_create(team=team, member=m, defaults={'role': TeamMembership.ROLE_MEMBER})

        n = recalculate_all_club_elo()
        self.stdout.write(self.style.SUCCESS(f'Sample data seeded; replayed {n} completed OTB matches for ratings.'))

    def _purge_seed(self):
        """Drop seed-labelled members plus legacy *_demo aliases; related matches/history cascade."""
        to_delete = LEGACY_MEMBER_LICHESS | SEED_MEMBER_LICHESS
        qs_members = Member.objects.filter(lichess_username__in=to_delete)
        total_deleted, _by_model = qs_members.delete()
        self.stdout.write(
            self.style.WARNING(
                f'Removed prior seed footprint ({total_deleted} database rows, including cascading matches/ELO rows).'
            )
        )

        seed_titles = [t for t, _ in ANNOUNCEMENTS]
        Announcement.objects.filter(title__in=seed_titles).delete()
        Announcement.objects.filter(title__startswith='[Demo]').delete()

        Team.objects.filter(
            name__in=('Eschen Rapid Squad', 'Eschen Schnellschach Squad'),
        ).delete()
