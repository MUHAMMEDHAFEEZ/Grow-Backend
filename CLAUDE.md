# grow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-12

## Active Technologies

- Python 3.11 / Django 6.0 + Django REST Framework, drf-spectacular, djangorestframework-simplejwt, core.events.EventBus (001-backend-compliance-audit)

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

- 001-backend-compliance-audit: Added Python 3.11 / Django 6.0 + Django REST Framework, drf-spectacular, djangorestframework-simplejwt, core.events.EventBus
- 002-school-enrollment-codes: Added EnrollmentCode, SchoolMembership, EnrollmentRateLimit, EnrollmentCodeEvent models in accounts app; new event Events.SCHOOL_MEMBER_ADDED; DB-based rate limiting (no Redis); uuid.uuid4 single-use tokens

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
