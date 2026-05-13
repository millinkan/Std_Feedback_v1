"""Staff-only admin view for tailing rotating application logs (settings.LOGGING file handler)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import render
from django.utils import timezone

SAFE_LOG_BASENAME = re.compile(r'^application\.log(?:\.[0-9]+)?$')


def _can_view_logs(user) -> bool:
    if not user.is_active or not user.is_staff:
        return False
    if getattr(settings, 'APP_LOG_ADMIN_SUPERUSER_ONLY', True):
        return user.is_superuser
    return True


def _allowed_log_files(logs_dir: Path) -> list[Path]:
    if not logs_dir.is_dir():
        return []
    out: list[Path] = []
    for p in logs_dir.iterdir():
        if p.is_file() and SAFE_LOG_BASENAME.match(p.name):
            out.append(p)

    def sort_key(path: Path) -> tuple[int, int]:
        name = path.name
        if name == 'application.log':
            return (0, 0)
        suffix = name.removeprefix('application.log.')
        try:
            return (1, int(suffix))
        except ValueError:
            return (2, 0)

    return sorted(out, key=sort_key, reverse=True)


def _resolve_log_path(logs_dir: Path, basename: str) -> Path:
    if not SAFE_LOG_BASENAME.match(basename):
        raise Http404('Invalid log file name.')
    candidate = (logs_dir / basename).resolve()
    try:
        candidate.relative_to(logs_dir.resolve())
    except ValueError as exc:
        raise Http404('Invalid log path.') from exc
    return candidate


def _read_tail_lines(path: Path, *, max_lines: int, max_bytes: int) -> list[str]:
    if not path.is_file():
        return []
    size = path.stat().st_size
    with path.open('rb') as fh:
        if size <= max_bytes:
            raw = fh.read()
        else:
            fh.seek(-max_bytes, 2)
            raw = fh.read()
    text = raw.decode('utf-8', errors='replace')
    lines = text.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return lines


def _line_level_class(line: str) -> str:
    token = line.split(None, 1)[0] if line.strip() else ''
    if token in ('ERROR', 'CRITICAL'):
        return 'log-line--error'
    if token == 'WARNING':
        return 'log-line--warning'
    if token == 'INFO':
        return 'log-line--info'
    if token == 'DEBUG':
        return 'log-line--debug'
    return 'log-line--plain'


def application_log_view(request):
    if not _can_view_logs(request.user):
        raise PermissionDenied('You do not have permission to view application logs.')

    logs_dir = Path(getattr(settings, 'LOGS_DIR', settings.BASE_DIR / 'logs')).resolve()
    max_lines_cap = max(50, int(getattr(settings, 'APP_LOG_ADMIN_MAX_LINES', 5000)))
    default_lines = min(500, max_lines_cap)
    line_presets = tuple(n for n in (200, 500, 1000, 2000, 5000) if n <= max_lines_cap)
    if not line_presets:
        line_presets = (max_lines_cap,)

    try:
        lines_param = int(request.GET.get('lines', default_lines))
    except (TypeError, ValueError):
        lines_param = default_lines
    lines_param = max(50, min(lines_param, max_lines_cap))

    line_choices = sorted(set(line_presets) | {lines_param})

    level_filter = (request.GET.get('level') or 'ALL').upper()
    if level_filter not in ('ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
        level_filter = 'ALL'

    refresh_sec = request.GET.get('refresh', '').strip()
    try:
        refresh_interval = int(refresh_sec) if refresh_sec else 0
    except ValueError:
        refresh_interval = 0
    refresh_interval = max(0, min(refresh_interval, 300))

    basename = request.GET.get('file') or 'application.log'
    log_path = _resolve_log_path(logs_dir, basename)

    if request.GET.get('download'):
        if not log_path.is_file():
            raise Http404('Log file not found.')
        return FileResponse(
            log_path.open('rb'),
            as_attachment=True,
            filename=log_path.name,
            content_type='text/plain; charset=utf-8',
        )

    max_read = int(getattr(settings, 'APP_LOG_ADMIN_TAIL_BYTES', 512 * 1024))
    raw_lines = _read_tail_lines(log_path, max_lines=lines_param, max_bytes=max_read)

    if level_filter != 'ALL':
        prefix = level_filter + ' '
        raw_lines = [ln for ln in raw_lines if ln.startswith(prefix) or ln.startswith(level_filter + '\t')]

    annotated = [{'text': ln, 'level_class': _line_level_class(ln)} for ln in raw_lines]

    stat = None
    if log_path.is_file():
        st = log_path.stat()
        stat = {
            'size_bytes': st.st_size,
            'modified': datetime.fromtimestamp(st.st_mtime, tz=timezone.utc),
        }

    log_files = _allowed_log_files(logs_dir)
    if not log_files and not log_path.is_file():
        messages.info(
            request,
            'No log file yet. It is created when the app first writes to the rotating file handler.',
        )

    context = {
        'title': 'Application logs',
        'log_path': str(log_path),
        'log_basename': log_path.name,
        'log_exists': log_path.is_file(),
        'log_stat': stat,
        'lines': annotated,
        'line_count': len(annotated),
        'lines_param': lines_param,
        'level_filter': level_filter,
        'log_files': log_files,
        'max_lines_cap': max_lines_cap,
        'line_presets': line_choices,
        'refresh_interval': refresh_interval,
        'logs_dir': str(logs_dir),
    }
    return render(request, 'admin/club/application_logs.html', context)
