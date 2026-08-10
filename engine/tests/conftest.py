"""Shared test environment defaults.

Runs before any test module is imported, so the first module to ``import app``
sees a consistent, test-only environment regardless of collection order.

Since AR-SEC-REC-001 removed the committed credential-bearing default
DATABASE_URL, ``scripts/db/config.py::database_url()`` fails fast when nothing
is configured, and the development-only ``/dev/login`` gate in
``scripts/api/app.py`` resolves DATABASE_URL at import time. These defaults
supply a local, credential-free URL so tests do not depend on import ordering
or on a committed default. They are test-only and are never an operational
default; the API's real connection path is stubbed in the tests that exercise
it, so no live connection is ever opened.
"""
import os

os.environ.setdefault('APP_SECRET', 'test-secret')
os.environ.setdefault('APP_ENV', 'development')
os.environ.setdefault('DATABASE_URL', 'postgresql://localhost:5432/argument_recipes')
