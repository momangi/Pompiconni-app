"""Lifecycle package — startup seeding, indexes and migrations (Fase 5/M4).

Centralises everything that previously lived inline in ``server.py``:
seed data constants, the ``init_database`` seeder and the
``ensure_indexes_and_migrations`` startup routine. Modules in this
package access MongoDB via ``core.database`` and configuration via
``core.config.settings`` — they must never import from ``server.py`` to
keep the bootstrap dependency graph linear.
"""
