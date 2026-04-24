# Eschen Chess Club

A web application for the Eschen Chess Club (Liechtenstein) built with Django. The system manages club members, tracks matches, calculates ELO ratings, and publishes announcements.

## Tech Stack 

| Layer        | Technology                             |
|--------------|----------------------------------------|
| Backend      | Python 3, Django 5                     |
| Frontend     | Bootstrap 5, Chart.js, Bootstrap Icons |
| Database     | SQLite (development)                   |
| Forms        | django-crispy-forms + crispy-bootstrap5|
| Images       | Pillow                                 |
| Static Files | WhiteNoise                             |

## Development Plan

The project is built incrementally across the following phases. Each phase is a separate branch merged into `develop` via pull request, and then into `main` for release.

### Phase 1 — Project Setup & Skeleton

> Branch: `main` (current state)

- [x] Create Django project (`chess_club`)
- [x] Create `club` app
- [x] Configure `settings.py` (database, static files, media, templates)
- [x] Set up `requirements.txt` with core dependencies
- [x] Add `.gitignore`
- [x] Initialize Git repository with `main` and `develop` branches

### Phase 2 — Data Models & Migrations

> Branch: `feature/models`

- [ ] Define `Member` model (linked to Django `User`, ELO rating, avatar, win/loss/draw stats)
- [ ] Define `Match` model (white player, black player, status, result, venue, scheduled date)
- [ ] Define `EloHistory` model (tracks rating changes per match)
- [ ] Define `Announcement` model (title, body, published date, author)
- [ ] Generate and apply migrations
- [ ] Register models in the admin site (basic)

### Phase 3 — ELO Rating Engine

> Branch: `feature/elo-engine`

- [ ] Implement `calculate_elo()` using the FIDE formula
- [ ] Implement adaptive K-factor logic (K=40 new players, K=20 standard, K=10 elite)
- [ ] Integrate ELO updates into match result saving (admin `save_model` override)
- [ ] Create `EloHistory` records automatically on match completion
- [ ] Add admin action to recalculate all ELO ratings from match history

### Phase 4 — Admin Panel Configuration

> Branch: `feature/admin-panel`

- [ ] Customize `MemberAdmin` (list display, filters, search)
- [ ] Customize `MatchAdmin` (list display, filters, auto ELO on save)
- [ ] Customize `EloHistoryAdmin` and `AnnouncementAdmin`
- [ ] Test admin workflows (create member, schedule match, record result)

### Phase 5 — Views & URL Routing

> Branch: `feature/views`

- [ ] Home page view (top 5 players, upcoming matches, announcements)
- [ ] Leaderboard view (sortable by ELO or win percentage)
- [ ] Matches view (tabbed: upcoming vs completed results)
- [ ] Match detail view
- [ ] Member profile view (stats, ELO history chart data, recent matches)
- [ ] About page view with contact form
- [ ] Wire up all URL routes in `club/urls.py`
- [ ] Include club URLs in the project `urls.py`

### Phase 6 — Templates & Frontend

> Branch: `feature/templates`

- [ ] Create base template (`base.html`) with navbar, footer, Bootstrap 5
- [ ] Home page template (hero section, player cards, match schedule, announcements)
- [ ] Leaderboard template (ranking table with sort toggles)
- [ ] Matches template (tabbed layout for upcoming/results)
- [ ] Match detail template
- [ ] Member profile template (stat cards, Chart.js ELO graph, match history table)
- [ ] About page template (club info, contact form with crispy-forms)
- [ ] Add custom CSS (`style.css`) and JavaScript (`app.js`)
- [ ] Add `django-crispy-forms` and `crispy-bootstrap5` to requirements and settings

### Phase 7 — Sample Data & Polish

> Branch: `feature/sample-data`

- [ ] Write `create_sample_data.py` script (members, matches, ELO history, announcements)
- [ ] Add fixture files for reproducible data loading
- [ ] Configure `WhiteNoise` for static file serving
- [ ] Add `python-decouple` for environment variable management
- [ ] Final testing of all pages and workflows
- [ ] Update README with full installation and usage instructions

## Git Workflow

```
main            ← stable releases
  └── develop   ← integration branch
        ├── feature/models
        ├── feature/elo-engine
        ├── feature/admin-panel
        ├── feature/views
        ├── feature/templates
        └── feature/sample-data
```

Each feature branch is created from `develop`, worked on, and merged back into `develop` via pull request. When a set of features is stable, `develop` is merged into `main`.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Amani-ojo/-Chess-Club.git
   cd -Chess-Club
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv

   # Windows
   venv\Scripts\activate

   # macOS / Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply database migrations**
   ```bash
   python manage.py migrate
   ```

5. **Run the development server**
   ```bash
   python manage.py runserver
   ```

6. Open your browser and visit `http://127.0.0.1:8000/`

## AI Pipeline Integration

The project now includes a full AI analysis pipeline integrated into the same Django app:

- Lichess import tasks
- Stockfish game analysis
- Move-by-move evaluations
- Player insight generation

### Environment Variables (optional but recommended)

Set these before running:

- `LICHESS_API_TOKEN` for authenticated Lichess API usage
- `STOCKFISH_PATH` to your local Stockfish executable (defaults to the bundled binary path)
- `CELERY_BROKER_URL` (default `redis://localhost:6379/0`)

### Running Locally with Pipeline

1. Start Redis.
2. Run Django:
   - `python manage.py migrate`
   - `python manage.py runserver`
3. In another terminal, run Celery worker:
   - `celery -A chess_club worker -l info`

Use `/admin/` to add members and games, then trigger task functions from the shell or admin workflows.

## Contributors

- Amani Ojo

## License

This project is for educational purposes as part of an ISD course.
