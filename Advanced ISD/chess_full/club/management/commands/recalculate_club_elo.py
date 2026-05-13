from django.core.management.base import BaseCommand

from club.services.match_elo import recalculate_all_club_elo


class Command(BaseCommand):
    help = 'Rebuild Club ELO from all completed OTB matches (see README Phase 3).'

    def handle(self, *args, **options):
        n = recalculate_all_club_elo()
        self.stdout.write(self.style.SUCCESS(f'Replayed {n} completed matches.'))
