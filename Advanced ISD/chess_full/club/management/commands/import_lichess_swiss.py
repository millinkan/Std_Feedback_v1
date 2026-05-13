from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from club.services.lichess_swiss_import import fetch_swiss_files, import_swiss_from_dir


class Command(BaseCommand):
    help = (
        'Import a Lichess Swiss tournament from lichess_API/info.json + games.ndjson '
        '(or download them with --fetch).'
    )

    def add_arguments(self, parser):
        default_dir = Path(settings.BASE_DIR) / 'lichess_API'
        parser.add_argument(
            '--dir',
            type=Path,
            default=default_dir,
            help=f'Directory holding info.json and games.ndjson (default: {default_dir})',
        )
        parser.add_argument(
            '--fetch',
            metavar='SWISS_ID',
            help='Download info.json + games.ndjson from Lichess into --dir, then import',
        )
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Delete existing club Swiss with slug lichess-<id> before importing',
        )
        parser.add_argument(
            '--create-members',
            action='store_true',
            help='Create Member rows when no lichess_username / display_name match exists',
        )
        parser.add_argument(
            '--counts-for-club-elo',
            action='store_true',
            help='Set counts_for_club_elo on the Swiss (creates OTB Match rows; usually off for online Lichess)',
        )

    def handle(self, *args, **options):
        dir_path = Path(options['dir']).resolve()
        if options['fetch']:
            sid = options['fetch'].strip()
            if not sid:
                raise CommandError('Swiss ID must not be empty')
            self.stdout.write(f'Downloading Lichess Swiss {sid!r} into {dir_path} …')
            fetch_swiss_files(sid, dir_path)
            self.stdout.write(self.style.SUCCESS('Download complete'))

        try:
            t = import_swiss_from_dir(
                dir_path,
                create_members=options['create_members'],
                counts_for_club_elo=options['counts_for_club_elo'],
                replace=options['replace'],
            )
        except (FileNotFoundError, LookupError, ValueError) as e:
            raise CommandError(str(e)) from e

        self.stdout.write(
            self.style.SUCCESS(f'Imported {t.name} as slug={t.slug} (counts_for_club_elo={t.counts_for_club_elo}).')
        )
