# Grow Educational Platform — API Documentation

**Base URL:** `https://edugrow.pythonanywhere.com/api/v1/`  
**Local:** `http://localhost:8000/api/v1/`  
**Auth:** JWT Bearer Token (60 min access / 7 day refresh)  
**Swagger UI:** `/api/docs/` | **ReDoc:** `/api/redoc/` | **Schema:** `/api/schema/`

---

## Authentication

All endpoints require `Authorization: Bearer <access_token>` unless noted.

### Flow
1. `POST /auth/register/` — Create account
2. `POST /auth/login/` — Get `access` + `refresh` tokens
3. Attach `Authorization: Bearer <access_token>` to every request
4. When access expires (401), call `POST /auth/token/refresh/` with `{ "refresh": "<refresh_token>" }`

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register/` | — | Register a new user |
| POST | `/auth/login/` | — | Login, get JWT tokens |
| POST | `/auth/logout/` | Required | Logout, blacklist refresh token |
| POST | `/auth/token/refresh/` | — | Refresh access token |
| POST | `/auth/forgot-password/` | — | Request password reset |
| POST | `/auth/reset-password/` | — | Reset password with token |
| POST | `/auth/change-password/` | Required | Change password |
| GET | `/auth/profile/` | Required | Get user profile |
| PUT | `/auth/profile/` | Required | Update profile |
| GET | `/auth/me/` | Required | Get current user |
| POST | `/auth/parent-profile/` | Parent | Link parent to student |
| GET | `/auth/school/` | SchoolAdmin | Get my school |
| POST | `/auth/school/` | SchoolAdmin | Create school |

### Register
```
POST /auth/register/
{
  "username": "john",
  "email": "john@example.com",
  "password": "securePass123",
  "role": "student"        // student | teacher | parent | school_admin
}
→ 201 { "id": 1, "username": "john", "email": "john@example.com", "role": "student", ... }
```

### Login
```
POST /auth/login/
{
  "email": "john@example.com",
  "password": "securePass123"
}
→ 200 { "access": "<jwt>", "refresh": "<jwt>", "user": { ... } }
```

### Refresh Token
```
POST /auth/token/refresh/
{ "refresh": "<refresh_token>" }
→ 200 { "access": "<new_access>", "refresh": "<new_refresh>" }
```

### Logout
```
POST /auth/logout/
Authorization: Bearer <access_token>
{ "refresh": "<refresh_token>" }
→ 204 No Content
```

---

## User Roles

| Role | Description |
|------|-------------|
| `student` | Enrolled in courses, submits work, takes quizzes |
| `teacher` | Creates courses, lessons, assignments, grades |
| `parent` | Links to a student, views dashboard |
| `school_admin` | Manages school, enrollment codes, reports |

---

## Enrollment Codes

School admins generate codes that students use to join the school.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/enrollment-codes/use/` | Required | Use a code to join a school |
| GET | `/auth/schools/{school_id}/enrollment-codes/` | SchoolAdmin | List codes |
| POST | `/auth/schools/{school_id}/enrollment-codes/generate/` | SchoolAdmin | Generate codes |
| POST | `/auth/schools/{school_id}/enrollment-codes/{code_id}/revoke/` | SchoolAdmin | Revoke a code |

### Use Code
```
POST /auth/enrollment-codes/use/
{ "code": "550e8400-e29b-41d4-a716-446655440000" }
→ 201 { "school": { "id": 1, "name": "My School", "slug": "my-school" }, "role": "student", "joined_at": "..." }
```

### Generate Codes
```
POST /auth/schools/1/enrollment-codes/generate/
{ "quantity": 10 }
→ 201 { "codes": ["uuid1", "uuid2", ...] }
```

---

## Courses

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/courses/` | Required | List courses (scoped by role) |
| GET | `/courses/{id}/` | Required | Course details |
| POST | `/courses/` | Required | Create course |
| PUT | `/courses/{id}/` | Required | Update course |
| DELETE | `/courses/{id}/` | Required | Delete course |
| POST | `/courses/{id}/enroll/` | Student | Enroll in a course |
| GET | `/courses/{id}/students/` | Teacher | List enrolled students |
| POST | `/courses/{id}/set_grade/` | Teacher | Set course grade level |
| GET | `/courses/{id}/progress/` | Teacher | All students' progress |
| GET | `/courses/{id}/progress_me/` | Required | My progress in course |
| GET | `/courses/{id}/lessons/` | Required | List course lessons |
| POST | `/courses/{id}/lessons/` | Teacher | Create lesson in course |
| POST | `/courses/{id}/join/` | Student | Join lesson (auto-attendance) |
| GET | `/courses/{id}/attendance/` | Teacher | Lesson attendance summary |

### Create Course
```
POST /courses/
Authorization: Bearer <token>
{ "title": "Math 101", "description": "Intro to Algebra" }
→ 201 { "id": 1, "title": "Math 101", "description": "...", "teacher": { ... }, "created_at": "..." }
```

### Enroll in Course
```
POST /courses/1/enroll/
Authorization: Bearer <token>
→ 201 { "id": 1, "student": { ... }, "is_active": true, "enrolled_at": "..." }
```

### Course Progress (Teacher)
```
GET /courses/1/progress/
→ 200 [
  { "student_id": 1, "student_name": "John", "progress_percentage": 75.00, "study_time_seconds": 3600, "study_time_formatted": "1h 0m", "last_activity": "...", "completion_status": "in_progress" }
]
```

---

## Lessons

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/lessons/{id}/track/` | Student | Track watch time |
| POST | `/lessons/{id}/complete/` | Student | Mark lesson complete |
| POST | `/lessons/{id}/join/` | Student | Join lesson (auto-attendance) |
| GET | `/lessons/{id}/attendance/` | Teacher | Lesson attendance summary |

### Track Lesson Progress
```
POST /lessons/1/track/
{ "watch_duration_seconds": 300, "completed": false }
→ 200 { "id": 1, "lesson_id": 1, "lesson_title": "Intro", "watch_duration_seconds": 300, "completed": false, "last_opened_at": "..." }
```

### Complete Lesson
```
POST /lessons/1/complete/
→ 200 { "id": 1, ..., "completed": true, ... }
```

### Join Lesson (Auto Attendance)
```
POST /lessons/1/join/
→ 200 { "status": "present"|"late"|"absent", "date": "2026-05-09", "is_new": true }
```
Attendance is calculated automatically based on server time vs. lesson schedule (10 min grace period).

---

## Quizzes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/quizzes/` | Required | List quizzes (?course=1 to filter) |
| GET | `/quizzes/{id}/` | Required | Quiz details |
| POST | `/quizzes/` | Required | Create quiz |
| POST | `/quizzes/{id}/attempt/` | Student | Submit quiz attempt |
| GET | `/quizzes/{id}/attempts/` | Required | List attempts |

### Create Quiz
```
POST /quizzes/
{ "course_id": 1, "lesson_id": 1, "title": "Quiz 1", "max_score": 100 }
→ 201 { "id": 1, "course_id": 1, "lesson_id": 1, "title": "Quiz 1", "max_score": "100.00", "created_at": "..." }
```

### Submit Quiz Attempt
```
POST /quizzes/1/attempt/
{ "score": 85.5 }
→ 201 { "id": 1, "attempt_number": 1, "score": "85.50", "submitted_at": "..." }
```

---

## Assignments

Nested under courses: `/courses/{course_pk}/assignments/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/courses/{course_pk}/assignments/` | Required | List assignments |
| GET | `/courses/{course_pk}/assignments/{id}/` | Required | Assignment details |
| POST | `/courses/{course_pk}/assignments/` | Required | Create assignment |
| PUT | `/courses/{course_pk}/assignments/{id}/` | Required | Update assignment |
| DELETE | `/courses/{course_pk}/assignments/{id}/` | Required | Delete assignment |

### Create Assignment
```
POST /courses/1/assignments/
{ "title": "Homework 1", "description": "Solve problems 1-10", "due_date": "2026-05-16T23:59:00Z" }
→ 201 { "id": 1, "course": 1, "title": "...", "description": "...", "due_date": "...", "created_by": 2, "created_at": "..." }
```

---

## Submissions

Nested under assignments: `/courses/{course_pk}/assignments/{assignment_pk}/submissions/`

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/courses/{course_pk}/assignments/{assignment_pk}/submissions/` | Teacher | List submissions |
| GET | `/courses/{course_pk}/assignments/{assignment_pk}/submissions/{id}/` | Required | Get submission |
| POST | `/courses/{course_pk}/assignments/{assignment_pk}/submissions/submit/` | Required | Submit work |
| POST | `/courses/{course_pk}/assignments/{assignment_pk}/submissions/{id}/grade/` | Required | Grade submission |

### Submit Work
```
POST /courses/1/assignments/1/submissions/submit/
{ "content": "My answer to the assignment..." }
→ 201 { "id": 1, "assignment": 1, "student": 3, "content": "...", "status": "pending", "submitted_at": "..." }
```

---

## Grades

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/grades/` | Required | List grades (scoped by role) |
| GET | `/grades/student/{student_id}/gpa/` | Required | Student GPA |
| POST | `/submissions/{submission_pk}/grade/` | Teacher | Grade a submission |

### Grade Submission
```
POST /submissions/1/grade/
{ "score": 92, "feedback": "Great work!" }
→ 201 { "id": 1, "submission": 1, "score": "92.00", "feedback": "Great work!", "graded_by": 2, "graded_at": "..." }
```

### Get GPA
```
GET /grades/student/3/gpa/
→ 200 { "student_id": 3, "gpa": 3.5, "graded_count": 8 }
```

---

## Attendance

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/attendance/` | Required | List attendance records |
| POST | `/attendance/` | Required | Mark attendance |

### Mark Attendance
```
POST /attendance/
{
  "course": 1,
  "date": "2026-05-09",
  "records": [
    { "student_id": 3, "status": "present" },
    { "student_id": 4, "status": "absent" }
  ]
}
→ 201 [ { "id": 1, "course": 1, "student": 3, "date": "2026-05-09", "status": "present", "marked_by": 2 }, ... ]
```

---

## Notifications

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/notifications/` | Required | List notifications |
| POST | `/notifications/{id}/read/` | Required | Mark one as read |
| POST | `/notifications/read-all/` | Required | Mark all as read |

### List Notifications
```
GET /notifications/
→ 200 {
  "unread_count": 3,
  "results": [
    { "id": 1, "title": "New Assignment", "body": "Homework 1 posted", "event_type": "assignment_created", "is_read": false, "created_at": "...", "related_course": 1, "related_content_id": 5 }
  ]
}
```

**Event types:** `assignment_created`, `submission_created`, `submission_graded`, `attendance_marked`, `enrollment_created`, `lesson_created`, `quiz_created`

---

## Study Sessions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/sessions/start/` | Required | Start a study session |
| POST | `/sessions/end/` | Required | End current session |
| GET | `/sessions/active/` | Required | Get active session |
| GET | `/sessions/total/` | Required | Total study time |
| GET | `/sessions/` | Required | List all sessions |

### Start Session
```
POST /sessions/start/
→ 201 { "id": 1, "student": 3, "started_at": "...", "ended_at": null, "duration": null, "xp_earned": null }
```
XP is calculated at 1 XP per minute (5 min minimum) when session ends.

### End Session
```
POST /sessions/end/
→ 200 { "id": 1, "student": 3, "started_at": "...", "ended_at": "...", "duration": 1800, "xp_earned": 30 }
```

### Total Study Time
```
GET /sessions/total/
→ 200 { "total_duration_seconds": 7200, "total_duration_formatted": "2h 0m", "session_count": 5 }
```

---

## XP System

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/xp/add/` | Required | Add XP |
| GET | `/xp/total/` | Required | Total XP + breakdown |
| GET | `/xp/history/` | Required | XP transaction history |

### Add XP
```
POST /xp/add/
{ "xp": 50, "source": "assignment" }
→ 201 { "id": 1, "student": 3, "xp": 50, "source": "assignment", "created_at": "..." }
```
**Sources:** `study`, `assignment`, `quiz`, `attendance`

### Get XP Total
```
GET /xp/total/
→ 200 { "total_xp": 1500, "transaction_count": 12, "breakdown": { "study": 800, "assignment": 400, "quiz": 200, "attendance": 100 } }
```

---

## Tasks (Auto-generated To-Do List)

When lessons, quizzes, or assignments are created, tasks are auto-generated for enrolled students. They auto-complete when the student does the action.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/tasks/` | Required | List all tasks |
| GET | `/tasks/pending/` | Student | List pending tasks |
| PATCH | `/tasks/{id}/complete/` | Student | Manually mark complete |
| GET | `/courses/{course_id}/task-summary/` | Teacher | Course task overview |

---

## Dashboard (School Admin / Teacher)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/dashboard/overview/` | Teacher/SchoolAdmin | Overview with period filter |
| GET | `/dashboard/classes/` | Teacher/SchoolAdmin | List classes |
| GET | `/dashboard/classes/{class_id}/` | Teacher/SchoolAdmin | Class detail |
| GET | `/dashboard/students/{student_id}/` | Required | Student profile |
| POST | `/dashboard/students/{student_id}/notes/` | Required | Add student note |
| GET | `/dashboard/reports/` | SchoolAdmin | Report summary |
| GET | `/dashboard/reports/export/?format=pdf` | SchoolAdmin | Export PDF report |
| GET | `/dashboard/reports/export/?format=xlsx` | SchoolAdmin | Export Excel report |
| GET | `/dashboard/risk-summary/` | Teacher/SchoolAdmin | At-risk students |
| POST | `/dashboard/insights/{insight_id}/dismiss/` | Teacher/SchoolAdmin | Dismiss insight |

### Add Student Note
```
POST /dashboard/students/3/notes/
{ "note": "John has been doing well this semester." }
→ 201 { "id": 1, "author": "Teacher Smith", "note": "...", "created_at": "...", "updated_at": "..." }
```

---

## Parent Dashboard

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/parent/dashboard/{student_id}/` | Parent | Child's learning dashboard |

```
GET /parent/dashboard/3/
→ 200 { "gpa": {...}, "study_hours": {...}, "engagement": 85, "subjects": [...], "recent_activity": [...] }
```

---

## Teacher Dashboard

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/dashboard/teacher/dashboard/` | Required | Teacher stats |

```
GET /dashboard/teacher/dashboard/
→ 200 { "total_students": 30, "total_courses": 3, "assignments_created": 8, "active_assignments": 2, "recent_activity": [...] }
```

---

## AI Chat Assistant

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/ai/chat/` | Required | Chat with AI assistant |

```
POST /ai/chat/
{ "message": "What is the quadratic formula?" }
→ 200 { "reply": "The quadratic formula is x = (-b ± √(b² - 4ac)) / 2a..." }
```

---

## Common Error Responses

```json
// Validation Error (400)
{ "field_name": ["This field is required."] }

// Unauthorized (401)
{ "detail": "Authentication credentials were not provided." }

// Permission Denied (403)
{ "detail": "You do not have permission to perform this action." }

// Not Found (404)
{ "detail": "Not found." }
```

---

## Pagination

All list endpoints use page-based pagination (20 items per page).

```
GET /courses/?page=1
→ 200 {
  "count": 45,
  "next": "https://.../api/v1/courses/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

Change page size: `?page=1&page_size=50` (not recommended — respect server limits).

---

## Filtering & Ordering

List endpoints support:
- **Filtering:** `?course=1`, `?status=pending`, `?student_id=3`
- **Search:** `?search=math` (searches title/name fields)
- **Ordering:** `?ordering=-created_at`, `?ordering=title`

---

## Data Models Summary (Key Entities)

| Entity | Key Fields | Notes |
|--------|-----------|-------|
| **User** | id, username, email, role, phone, avatar, school | 4 roles: student, teacher, parent, school_admin |
| **School** | id, name, slug | Created by school_admin |
| **Course** | id, title, description, teacher, grade, target_capacity | teacher FK → User (role=teacher) |
| **StudentCourse** | course, student, is_active | Junction table, replaces Enrollment |
| **Lesson** | id, title, content, order, start_time, end_time, course | Has auto-attendance on join |
| **LessonActivity** | student, lesson, watch_duration_seconds, completed | Per-student tracking |
| **Quiz** | id, title, max_score, course, lesson | Optional lesson FK |
| **QuizAttempt** | student, quiz, score, attempt_number | Rate-limited: 10 per 5 min |
| **Assignment** | id, title, description, due_date, course, created_by | |
| **Submission** | id, content, status (pending/graded), assignment, student | |
| **Grade** | submission, score, feedback, graded_by | Linked to submission |
| **AttendanceRecord** | course, student, date, status (present/absent/late) | |
| **StudySession** | student, started_at, ended_at, duration, xp_earned | XP = 1/min, min 5 min |
| **XPTransaction** | student, xp, source | Sources: study, assignment, quiz, attendance |
| **StudentTask** | student, course, content_type, content_id, status | Auto-generated / auto-completed |
| **Notification** | recipient, title, body, event_type, is_read | Events: assignment_created, etc. |
| **DashboardInsight** | title, severity, insight_type, recommendation | Types: overcrowded_class, at_risk_student, etc. |
| **InterventionRecord** | student, action, priority, status | Actions: parent_meeting, tutoring_referral, etc. |

---

## Event-Driven Behavior

Certain actions trigger automatic side effects:

| Action | Side Effects |
|--------|-------------|
| Lesson completed | ActivityLog logged, StudentTask auto-completed |
| Quiz submitted | ActivityLog logged, StudentTask auto-completed |
| Attendance marked | ActivityLog logged, risk score updated, notification sent (if absent) |
| Submission graded | Student + parent notified, risk score updated |
| Assignment/Lesson/Quiz created | Auto-creates StudentTask for all enrolled students |
| Lesson joined | Attendance auto-calculated (present/late/absent based on time) |
| Course progress > 25/50/75/100% | Milestone event published |
| Session ended | XP auto-awarded at 1 XP per minute (min 5 min) |

---

## Authentication Flow Diagram

```
Frontend                          Backend
   │                                │
   │  POST /auth/login/             │
   │───────────────────────────────>│
   │  { email, password }           │
   │<───────────────────────────────│
   │  { access, refresh, user }     │
   │                                │
   │  Store tokens (localStorage)   │
   │                                │
   │  GET /courses/                 │
   │  Authorization: Bearer access  │
   │───────────────────────────────>│
   │<───────────────────────────────│
   │  200 { results: [...] }        │
   │                                │
   │  [If 401 — token expired]      │
   │  POST /auth/token/refresh/     │
   │  { refresh }                   │
   │───────────────────────────────>│
   │<───────────────────────────────│
   │  { access, refresh }           │
   │                                │
   │  Retry original request        │
   │                                │
   │  POST /auth/logout/            │
   │  Authorization: Bearer access  │
   │  { refresh }                   │
   │───────────────────────────────>│
   │  204 No Content                │
   │                                │
   │  Clear tokens                  │
```
