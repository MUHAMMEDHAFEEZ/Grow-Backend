# Grow Project — Implementation Plan

## Project Overview

**Grow** is a multi-role educational platform connecting Students, Parents, and Teachers.  
The system centralizes learning, assignments, grades, and performance tracking in one unified platform.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 6.0 + Django REST Framework |
| Frontend | React 19 + TypeScript + Vite |
| Database | SQLite (dev) / PostgreSQL (production-ready) |
| Auth | JWT (djangorestframework-simplejwt) |
| State | Zustand |
| Styling | TailwindCSS + Bootstrap |
| API Docs | drf-spectacular (OpenAPI/Swagger) |

---

## Architecture

### Type: Modular Monolith

Single deployable Django project with logically separated bounded contexts (apps).  
Cross-app communication via internal event bus only—no direct model imports across domains.

```
┌─────────────────────────────────────┐
│           API Layer                 │  DRF ViewSets + Serializers
│  (views.py / serializers.py)        │  No business logic
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Service Layer               │  services.py
│  (all business rules)               │  Returns domain objects
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Domain Layer                │  models.py + selectors.py
│  (entities, queries)                │  selectors = read-only queries
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Infrastructure Layer           │  Django ORM + SQLite
└─────────────────────────────────────┘
```

---

## Directory Structure

```
Grow-full-master/
├── Grow_backend/grow/
│   ├── accounts/          # User, School, ParentProfile, PasswordResetToken
│   ├── schools/           # Legacy (School now in accounts)
│   ├── students/          # Legacy (Student profile)
│   ├── courses/           # Course, Enrollment, Lesson
│   ├── assignments/       # Assignment
│   ├── submissions/       # Submission
│   ├── grades/            # Grade
│   ├── attendance/       # AttendanceRecord
│   ├── notifications/     # Notification
│   ├── core/              # Event bus, utilities
│   ├── grow/               # Project settings, urls
│   ├── manage.py
│   └── requirements.txt
│
├── Grow_front/
│   ├── src/
│   │   ├── features/
│   │   │   ├── dashboard/      # Student dashboard
│   │   │   ├── parent/        # Parent dashboard, analytics
│   │   │   ├── courses/       # Course listing
│   │   │   ├── tasks/         # Tasks/Assignments board
│   │   │   ├── quiz/          # Quiz module
│   │   │   ├── settings/      # User settings
│   │   │   └── ai/            # AI Tutor
│   │   ├── components/
│   │   │   ├── auth/         # Login/Signup forms
│   │   │   ├── layout/        # Sidebar, Topbar
│   │   │   ├── landing/       # Landing page
│   │   │   └── ui/            # Reusable UI components
│   │   ├── services/          # API services
│   │   ├── store/             # Zustand stores
│   │   ├── hooks/             # Custom hooks
│   │   └── mock/              # Mock data
│   └── package.json
│
└── specs/
    ├── architecture.md
    ├── product.md
    ├── data-model.md
    ├── api.md
    ├── tasks.md
    └── decisions.md
```

---

## Data Models

### User & Accounts

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **User** | role (student/teacher/parent/school_admin), email, phone, avatar | FK → School (nullable) |
| **School** | name, slug, created_by | OneToOne → User (school_admin) |
| **ParentProfile** | parent, child | OneToOne → User (parent), FK → User (student) |
| **PasswordResetToken** | token, expires_at, is_used | FK → User |

### Courses

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **Course** | title, description, teacher | FK → User (teacher) |
| **Enrollment** | enrolled_at | FK → Course, FK → User (student), unique_together (course, student) |
| **Lesson** | title, content, order | FK → Course |

### Assignments & Submissions

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **Assignment** | title, description, due_date | FK → Course, FK → User (created_by) |
| **Submission** | content, status (pending/graded) | FK → Assignment, FK → User (student), unique_together (assignment, student) |

### Grades

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **Grade** | score (0-100), feedback | OneToOne → Submission, FK → User (graded_by) |

### Attendance

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **AttendanceRecord** | date, status (present/absent/late) | FK → Course, FK → User (student), unique_together (course, student, date) |

### Notifications

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **Notification** | title, body, event_type, is_read | FK → User (recipient) |

---

## Event System

Synchronous in-process pub/sub located in `core/events.py`.

| Event | Publisher | Subscribers |
|-------|-----------|-------------|
| `assignment_created` | assignments | notifications |
| `submission_created` | submissions | notifications |
| `submission_graded` | grades | notifications (student + parent) |
| `attendance_marked` | attendance | notifications (parent if absent) |
| `enrollment_created` | courses | notifications |

---

## API Endpoints

**Base URL:** `/api/v1/`

| Module | Endpoints | Methods |
|--------|-----------|---------|
| **Auth** | `/auth/register/`, `/auth/login/`, `/auth/token/refresh/`, `/auth/me/` | POST, GET |
| **Courses** | `/courses/`, `/courses/{id}/`, `/courses/{id}/enroll/`, `/courses/{id}/lessons/` | GET, POST, PUT, DELETE |
| **Assignments** | `/courses/{id}/assignments/`, `/assignments/{id}/` | GET, POST, PUT, DELETE |
| **Submissions** | `/assignments/{id}/submit/`, `/submissions/{id}/`, `/submissions/{id}/grade/` | GET, POST |
| **Grades** | `/grades/` | GET |
| **Attendance** | `/attendance/` | GET, POST |
| **Notifications** | `/notifications/`, `/notifications/{id}/read/` | GET, POST |

---

## Roles & Permissions

| Role | Capabilities |
|------|-------------|
| **Student** | View enrolled courses, submit assignments, view own grades |
| **Teacher** | CRUD courses (owned), create assignments, grade submissions, mark attendance |
| **Parent** | View child's grades, attendance, and notifications |
| **School Admin** | Manage school, view all school data |

---

## Current Implementation Status

### Completed

- Django project structure
- Custom User model with roles
- All core models (Course, Assignment, Submission, Grade, Attendance, Notification)
- Event bus system
- JWT authentication configuration
- REST Framework settings
- API documentation (drf-spectacular)
- Frontend React structure with components

### In Progress

- Service layer completion
- Selector layer for queries
- API ViewSets for all modules
- Frontend-backend integration
- Test coverage

---

## Implementation Roadmap

### Phase 1: Foundation
- [x] Project structure created
- [x] Settings configuration (JWT, CORS, pagination)
- [x] Event bus implementation
- [ ] Complete accounts services/selectors
- [ ] Auth API endpoints refinement

### Phase 2: Courses & Lessons
- [x] Course model
- [x] Lesson model
- [x] Enrollment model
- [ ] Course services (create, enroll, list)
- [ ] Course API ViewSets
- [ ] Event handlers for enrollment

### Phase 3: Assignments & Submissions
- [x] Assignment model
- [x] Submission model
- [ ] Assignment services + API
- [ ] Submission services + API
- [ ] Event handlers for assignment/submission creation

### Phase 4: Grades
- [x] Grade model
- [ ] Grade service (grade_submission, updates submission.status)
- [ ] Grade API endpoints
- [ ] Event handler for graded submissions

### Phase 5: Attendance
- [x] AttendanceRecord model
- [ ] Attendance services (bulk mark, query)
- [ ] Attendance API
- [ ] Event handler for attendance marking

### Phase 6: Notifications
- [x] Notification model
- [ ] Notification services
- [ ] Notification API endpoints
- [ ] Wire all event handlers

### Phase 7: Frontend Integration
- [ ] Connect auth flows
- [ ] Course listing/management
- [ ] Assignment submission
- [ ] Grade viewing
- [ ] Parent dashboard

### Phase 8: Testing
- [ ] Unit tests: accounts
- [ ] Unit tests: courses
- [ ] Unit tests: submissions + grades
- [ ] API tests: auth flow
- [ ] API tests: submit → grade flow

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Modular Monolith | Team size doesn't justify microservices; clean separation for future extraction |
| SQLite (dev) | Zero-config; PostgreSQL ready in settings |
| Synchronous Event Bus | No Celery/Redis for MVP; async upgrade path clear |
| Services Pattern | Business logic isolated; testable without HTTP context |
| Selectors Pattern | Read queries separated; optimized with select_related |
| JWT Auth | Stateless, standard DRF integration |

---

## Performance Guidelines

- Use `select_related` / `prefetch_related` for FK/M2M queries
- Avoid N+1 queries in list endpoints
- Index frequently queried fields:
  - `(assignment, student)` on Submission
  - `(course, student, date)` on AttendanceRecord
  - `(recipient, is_read)` on Notification
- Pagination: 20 items default

---

## Next Steps

1. Complete service layer for each app
2. Implement selectors for optimized queries
3. Build API ViewSets with proper permissions
4. Wire event handlers to notifications
5. Write unit and integration tests
6. Connect frontend to backend APIs
7. Add error handling and validation
8. Performance testing with realistic data

---

## Success Metrics

- Student can submit assignment in < 3 API calls
- Teacher can grade batch submissions efficiently
- Parent receives notification within one request cycle
- All API responses < 200ms (SQLite, 1000 rows/table)
- Test coverage ≥ 80% on service layer