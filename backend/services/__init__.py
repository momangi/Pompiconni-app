"""Business logic / use cases.

Services orchestrate one or more repositories and apply domain rules
(visibility flags, decoration of responses, validation). They are the
only layer that ``api/`` routers should call. Repositories should not be
called directly from the route handlers.

Refactor Fase 4B Batch 1 — first three domains: reviews, site_settings,
themes.
"""
