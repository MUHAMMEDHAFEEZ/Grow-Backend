# grow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-25

## Active Technologies

- Python 3.11 / Django 6.0 + Django REST Framework, drf-spectacular, djangorestframework-simplejwt, core.events.EventBus (001-backend-compliance-audit)
- study_sessions app (StudySession model) + xp app (XPTransaction model) (001-study-session-xp)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11 / Django 6.0: Follow standard conventions

## Recent Changes

- 001-study-session-xp: Added StudySession & XPTransaction models; study_sessions/XP apps implemented (renamed from sessions to avoid conflict); full CRUD; XP calculation 1 XP/min (5 min minimum); clean architecture

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
