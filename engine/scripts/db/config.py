"""Database configuration for local development.

Stdlib-only and import-safe: importing this module never opens a connection and
never requires a driver, so the test suite runs without a database.

Phase 1 targets local Postgres (see docker-compose.yml). Supabase and any
production service are out of scope.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / 'db' / 'migrations'

# Governance validation runs entirely against throwaway databases. Disposable
# databases carry this prefix; the local maintenance database is only used to
# create and drop them. The operational database is never a valid target.
VALIDATION_DATABASE_PREFIX = 'argument_recipes_test_provenance_'
MAINTENANCE_DATABASE = 'postgres'


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader. Does not override already-set environment vars."""
    if not path.exists():
        return
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        os.environ.setdefault(key.strip(), value.strip())


def database_url() -> str:
    """Resolve DATABASE_URL from the environment, then a local .env file.

    There is deliberately no committed credential fallback: operational database
    access must never silently default to a tracked username/password URL. If no
    DATABASE_URL is configured, fail loudly so the operator supplies one.
    """
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    _load_dotenv(ROOT / '.env')
    url = os.environ.get('DATABASE_URL')
    if not url:
        raise RuntimeError(
            'DATABASE_URL is not configured. Set it in the environment or in a '
            'local, untracked .env file (copy .env.example and set a strong '
            'password). Phase 1 uses local Postgres only; no credential-bearing '
            'default is committed.'
        )
    return url


def assert_not_production(url: str | None = None) -> str:
    """Guard: refuse to operate against anything that looks non-local.

    Phase 1 is local-Postgres-only. This is a safety rail, not a security
    control -- it exists so an agent cannot accidentally point a loader at a
    hosted database.
    """
    url = url or database_url()
    host = (urlparse(url).hostname or '').lower()
    if host not in ('localhost', '127.0.0.1', '::1', 'db'):
        raise RuntimeError(
            f'Refusing to operate against non-local database host {host!r}. '
            'Phase 1 uses local Postgres only (docker-compose.yml). '
            'Supabase and production services are out of scope.'
        )
    if 'supabase' in url.lower():
        raise RuntimeError('Refusing to operate against Supabase (out of scope for Phase 1).')
    return url


def operational_database_name(url: str | None = None) -> str:
    """The operational database name that governance validation must not touch."""
    path = urlparse(url or database_url()).path.lstrip('/')
    return path or 'argument_recipes'


def assert_validation_database(name: str | None) -> str:
    """Fail-fast guard for governance validation database targets.

    Validation may connect only to the local maintenance database (needed to
    create and drop disposable databases) or to an approved disposable database
    (``argument_recipes_test_provenance_*``). It must never resolve to the
    operational database, and it must not require that database to exist or be
    migrated. Raising here aborts before any connection is opened.
    """
    if name == MAINTENANCE_DATABASE:
        return name
    if not isinstance(name, str) or not re.fullmatch(
            rf'{re.escape(VALIDATION_DATABASE_PREFIX)}[a-z0-9_]+', name):
        raise RuntimeError(
            f'refusing non-disposable validation database target: {name!r}. '
            'Governance validation must use an approved disposable database '
            f'({VALIDATION_DATABASE_PREFIX}*) or the local maintenance database, '
            'never the operational database.')
    return name


def migration_paths() -> list[Path]:
    """Migration files in lexicographic (= applied) order."""
    return sorted(MIGRATIONS_DIR.glob('*.sql'))
