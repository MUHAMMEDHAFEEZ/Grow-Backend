# grow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-06

## Active Technologies

- Python 3.11 / Django 6.0 + Django REST Framework, drf-spectacular, djangorestframework-simplejwt, core.events.EventBus (001-backend-compliance-audit)
- study_sessions app (StudySession model) + xp app (XPTransaction model) (001-study-session-xp)
- dashboard app (DashboardInsight, StudentNote, InterventionRecord models) + WeasyPrint (PDF export) + openpyxl (Excel export) (001-school-management-dashboard)

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
- 008-backend-arch-refactor: Enrollment refactor (Enrollment → StudentCourse + lazy creation); grade FK on Course; CourseProgress, LessonActivity, Quiz, QuizAttempt, ActivityLog models; event-driven tracking updates (LESSON_COMPLETED, QUIZ_SUBMITTED, PROGRESS_MILESTONE_REACHED); 1-min rate limit on progress updates; 12-month log retention; analytics aggregation selectors (courses app); attendance composite indexes + analytics selectors; LessonActivityViewSet at /lessons/{id}/track/ and /lessons/{id}/complete/; QuizViewSet at /quizzes/{id}/attempt/ and /quizzes/{id}/attempts/; ActivityLog auto-logged via EventBus handlers in core/handlers.py
<!-- MANUAL ADDITIONS END -->
