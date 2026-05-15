# grow Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-05-16

## Active Technologies

- Python 3.11 / Django 6.0 + Django REST Framework, drf-spectacular, djangorestframework-simplejwt, core.events.EventBus (001-backend-compliance-audit)
- study_sessions app (StudySession model) + xp app (XPTransaction model) (001-study-session-xp)
- dashboard app (DashboardInsight, StudentNote, InterventionRecord models) + WeasyPrint (PDF export) + openpyxl (Excel export) (001-school-management-dashboard)
- google-auth library for Google OAuth token validation + custom Facebook OAuth (Graph API v25.0) for social login (010-auth-parent-flow)
- accounts app extended: student_id field on User, ActiveChildContext model, school selector endpoint (010-auth-parent-flow)
- courses app extended: is_published on Quiz, is_active on Lesson (soft delete) (010-auth-parent-flow)
- notifications app: role-specific event types added (child_grade_changed, quiz_published, etc.); ENROLLMENT_CREATED removed (010-auth-parent-flow)
- parent app extended: add-child, list-children, switch-child, active-dashboard endpoints (010-auth-parent-flow)
- parent role completion: LoginHistory model (dynamic streak), Notification extensions (parent/student FK, reference_id, quiz_deadline/grade_updated events), user.notifications_enabled field, student.parent_access_code field; 5 parent services (gpa, xp, attendance, schedule, report); OAuth signup + login; 15 total parent endpoints (011-parent-role-completion)
- student role backend: 19 endpoints (auth signup/login/OTP/reset/logout, dashboard, courses, quizzes, assignments, tasks, notifications, settings, AI chat); 8 new models (LoginHistory, StudentSession, StudentCourseProgress, LessonCompletion, DailyMasterLog, OTPRecord, RefreshToken, StudentNotification); XPTransaction extended with source_type/source_id + unique constraint; file validation service; rate limiting on auth endpoints; single-session enforcement; students/ as subpackage (services/, serializers/, views/, urls/, tests/) (013-student-role-backend)
- multi-school auth: RegistrationCode model, school field on User (unique email per school), 5 new auth endpoints, seed management command, rate limiting, school-level data isolation (017-multi-school-auth)
- grades API fix: school-scoped GradeListView, deduplication via aggregation, data migration to rename global grades to English "Grade N"; selector layer introduced in schools app (019-fix-grades-api)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd grow-backend; python manage.py test; python -m ruff check .

## Code Style

Python 3.11 / Django 6.0: Follow standard conventions

## Recent Changes

- 001-study-session-xp: Added StudySession & XPTransaction models; study_sessions/XP apps implemented (renamed from sessions to avoid conflict); full CRUD; XP calculation 1 XP/min (5 min minimum); clean architecture

<!-- MANUAL ADDITIONS START -->
- 008-backend-arch-refactor: Enrollment refactor (Enrollment → StudentCourse + lazy creation); grade FK on Course; CourseProgress, LessonActivity, Quiz, QuizAttempt, ActivityLog models; event-driven tracking updates (LESSON_COMPLETED, QUIZ_SUBMITTED, PROGRESS_MILESTONE_REACHED); 1-min rate limit on progress updates; 12-month log retention; analytics aggregation selectors (courses app); attendance composite indexes + analytics selectors; LessonActivityViewSet at /lessons/{id}/track/ and /lessons/{id}/complete/; QuizViewSet at /quizzes/{id}/attempt/ and /quizzes/{id}/attempts/; ActivityLog auto-logged via EventBus handlers in core/handlers.py
- 011-parent-role-completion: Full parent role completion — 15 endpoints (auth signup/login/OAuth, add-student with access code, students list, dashboard, analytics, attendance, report+PDF, notifications, settings); LoginHistory model; Notification extensions (parent/student/reference_id); parent_access_code on Student; notifications_enabled on User; 5 service modules in parent/services/; rate limiting on add-student; PDF caching; OAuth integration
- 012-fix-swagger-schema: drf-spectacular/OpenAPI schema cleanup — eliminated "unable to guess serializer" warnings from 20+ views, fixed path parameter type derivation, resolved operationId collisions; added serializer_class + @extend_schema annotations across accounts, ai, courses, dashboard, parent, study_sessions, xp apps
- 013-student-role-backend: Complete student role backend — 19+ endpoints across auth (signup/login/OTP/reset/logout), dashboard (XP/streak/leaderboard/tasks), courses (list/detail/complete), quizzes (start/submit), assignments (view/submit with file validation), tasks (past due/today/summary), notifications (list/mark read/dedup), settings (profile/aggregates); 8 new models (LoginHistory, StudentSession, StudentCourseProgress, LessonCompletion, DailyMasterLog, OTPRecord, RefreshToken, StudentNotification); XPTransaction extended with source_type/source_id + unique constraint; file validation service (20MB, MIME + extension check); rate limiting on all auth endpoints; single-session enforcement
- 015-async-notification-resilience: transaction.on_commit() isolation for all 6 Celery .delay() calls in teachers/services.py; ensures DB writes commit before async notifications; Redis/Celery failures never crash API
- 017-multi-school-auth: Complete multi-school auth system — RegistrationCode model, school field on User (unique email per school), 5 new auth endpoints (student/teacher signup + login, school login), seed management command for schools/grades/codes, rate limiting, school-level data isolation
- 019-fix-grades-api: Fixed /api/v1/schools/grades/ endpoint — school-scoped queries, deduplication via values+annotate aggregation, data migration 0005 to rename global grades from Arabic to "Grade N", new schools/selectors.py with get_grades_for_school()
<!-- MANUAL ADDITIONS END -->
