Swiss imports for Eschen Chess Club
===================================

Put Lichess API exports here (or fetch them automatically):

  info.json — metadata (JSON): GET https://lichess.org/api/swiss/<ID>
            Header: Accept: application/json

  games.ndjson — one game JSON per line: GET https://lichess.org/api/swiss/<ID>/games
            Header: Accept: application/x-ndjson
            Suggested query: pgnInJson=true&tags=true&moves=false&clocks=false&evals=false
            Round numbers are taken from each game’s embedded PGN header [Round].

This directory’s info.json / games.ndjson are listed in .gitignore so large exports are not committed.

Import (from repo root, venv activated):

  python manage.py import_lichess_swiss

Or fetch from Lichess then import:

  python manage.py import_lichess_swiss --fetch <SWISS_ID>

Club members are matched by Member.lichess_username (case-insensitive), then display_name.
Use --create-members to create unmatched players as Members.

Online Swiss mirrors default to not affecting OTB club Elo: pass --counts-for-club-elo only if you
intentionally want pairings mirrored into Match rows for the club Elo engine.
