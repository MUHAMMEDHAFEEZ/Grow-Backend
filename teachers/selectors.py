from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from assignments.models import Assignment
from attendance.models import AttendanceRecord
from courses.models import (
    Course,
    Lesson,
    Quiz,
    StudentCourse,
)
from submissions.models import Submission
from xp.models import XPTransaction

from .models import TeacherProfile

User = get_user_model()


def get_teacher_profile(user: User) -> TeacherProfile | None:
    return TeacherProfile.objects.select_related("user", "school").filter(user=user).first()


def get_teacher_courses(teacher: User) -> list[Course]:
    return (
        Course.objects.filter(teacher=teacher)
        .select_related("grade")
        .annotate(
            _lesson_count=Count("lessons", distinct=True),
            _enrolled_count=Count("student_courses", distinct=True),
            _total_xp=Coalesce(
                Sum(
                    "lessons__xp_reward",
                    filter=Q(lessons__status=Lesson.Status.PUBLISHED),
                ),
                Value(0),
            ),
        )
        .order_by("-created_at")
    )


def get_teacher_course_detail(teacher: User, course_id: int) -> Course | None:
    return get_teacher_courses(teacher).filter(pk=course_id).first()


def get_course_lessons(course_id: int) -> list[Lesson]:
    return Lesson.objects.filter(course_id=course_id).order_by("order")


def get_lesson(lesson_id: int) -> Lesson | None:
    return Lesson.objects.select_related("course").filter(pk=lesson_id).first()


def get_teacher_assignments(teacher: User, course_id: int | None = None) -> list[Assignment]:
    qs = Assignment.objects.filter(course__teacher=teacher).select_related("course")
    if course_id:
        qs = qs.filter(course_id=course_id)
    return qs.order_by("due_date")


def get_assignment_detail(assignment_id: int) -> Assignment | None:
    return Assignment.objects.select_related("course").filter(pk=assignment_id).first()


def get_submissions_for_assignment(assignment_id: int) -> list[Submission]:
    return Submission.objects.filter(assignment_id=assignment_id).select_related("student").order_by("-submitted_at")


def get_submission(submission_id: int) -> Submission | None:
    return Submission.objects.select_related("student", "assignment__course").filter(pk=submission_id).first()


def get_assignment_review_summary(assignment: Assignment) -> dict:
    subs = Submission.objects.filter(assignment=assignment)
    total = subs.count()
    graded = subs.filter(is_graded=True).count()
    submitted = subs.exclude(content="", file="").count()
    missing = StudentCourse.objects.filter(
        course=assignment.course, is_active=True
    ).exclude(
        student__in=subs.values("student")
    ).count()
    return {
        "total_students": total + missing,
        "submitted": submitted,
        "scored": graded,
        "missing": missing,
    }


def get_teacher_quizzes(teacher: User, course_id: int | None = None) -> list[Quiz]:
    qs = Quiz.objects.filter(teacher=teacher).select_related("course")
    if course_id:
        qs = qs.filter(course_id=course_id)
    return qs.order_by("-created_at")


def get_quiz_detail(quiz_id: int) -> Quiz | None:
    return Quiz.objects.select_related("course").prefetch_related(
        "questions__options"
    ).filter(pk=quiz_id).first()


def get_quiz_results(quiz: Quiz) -> list[dict]:
    from courses.models import QuizAttempt
    from xp.models import XPTransaction

    attempts = (
        QuizAttempt.objects.filter(quiz=quiz)
        .select_related("student")
        .order_by("-submitted_at")
    )
    results = []
    for attempt in attempts:
        max_score = float(quiz.max_score)
        score = float(attempt.score)
        normalized = round((score / max_score) * 100, 2) if max_score > 0 else 0
        xp_row = XPTransaction.objects.filter(
            student=attempt.student,
            source_type=XPTransaction.SourceType.QUIZ.value,
            source_id=quiz.id,
        ).first()
        xp_earned = xp_row.xp_amount if xp_row else 0
        results.append({
            "student_id": attempt.student_id,
            "student_name": attempt.student.get_full_name() or attempt.student.username,
            "raw_score": attempt.score,
            "max_score": quiz.max_score,
            "normalized_score": normalized,
            "xp_earned": xp_earned,
            "status": "completed",
        })
    return results


def get_dashboard_stats(teacher: User) -> dict:
    from students.models import Student

    course_ids = Course.objects.filter(teacher=teacher).values_list("id", flat=True)
    grade_ids = Course.objects.filter(teacher=teacher).values_list("grade_id", flat=True).distinct()

    total_students = (
        Student.objects.filter(grade_id__in=grade_ids)
        .values("user_id")
        .distinct()
        .count()
    )
    total_courses = len(course_ids)

    now = timezone.now()
    assignments_created = Assignment.objects.filter(course__teacher=teacher).count()
    active_quizzes = Quiz.objects.filter(
        teacher=teacher, is_locked=False,
        end_time__gte=now,
    ).count()

    enrolled_students = (
        Student.objects.filter(grade_id__in=grade_ids)
        .values_list("user_id", flat=True)
        .distinct()
    )[:20]

    student_scores = []
    for sid in enrolled_students:
        subs = Submission.objects.filter(
            student_id=sid, assignment__course_id__in=course_ids, is_graded=True
        )
        if subs.exists():
            avg = subs.aggregate(avg_score=Avg("normalized_score"))["avg_score"] or 0
            student_scores.append((sid, float(avg)))

    student_scores.sort(key=lambda x: x[1], reverse=True)

    top_perf_ids = [s[0] for s in student_scores[:3]]
    bottom_ids = [s[0] for s in student_scores[-3:]] if len(student_scores) >= 3 else [s[0] for s in student_scores]

    top_performance = _format_student_list(top_perf_ids)
    need_review = _format_student_list(bottom_ids)

    recent_activity = list(
        Submission.objects.filter(assignment__course_id__in=course_ids)
        .select_related("student", "assignment")
        .order_by("-submitted_at")[:10]
        .values("student__username", "assignment__title", "status", "raw_score", "submitted_at")
    )

    return {
        "total_students": total_students,
        "total_courses": total_courses,
        "assignments_created": assignments_created,
        "active_quizzes": active_quizzes,
        "top_performance": top_performance,
        "need_review": need_review,
        "recent_student_activity": recent_activity,
    }


def _format_student_list(student_ids: list) -> list[dict]:
    users = User.objects.filter(id__in=student_ids).only("id", "username")
    result = []
    for uid in student_ids:
        user = next((u for u in users if u.id == uid), None)
        if user:
            result.append({"student_id": user.id, "student_name": user.username})
    return result


def get_teacher_students(teacher: User, grade: int | None = None, search: str | None = None) -> list[dict]:
    course_ids = Course.objects.filter(teacher=teacher).values_list("id", flat=True)
    student_ids = (
        StudentCourse.objects.filter(course_id__in=course_ids, is_active=True)
        .values_list("student_id", flat=True)
        .distinct()
    )
    students = User.objects.filter(id__in=student_ids)

    if search:
        students = students.filter(
            Q(username__icontains=search) | Q(first_name__icontains=search) | Q(last_name__icontains=search)
        )

    result = []
    for student in students:
        subs = Submission.objects.filter(
            student=student, assignment__course_id__in=course_ids, is_graded=True
        )
        avg_score = subs.aggregate(avg=Avg("normalized_score"))["avg"] or 0

        attendance_records = AttendanceRecord.objects.filter(
            student=student, course_id__in=course_ids
        )
        total_att = attendance_records.count()
        present_att = attendance_records.filter(
            Q(status="present") | Q(status="late")
        ).count()
        att_rate = (present_att / total_att * 100) if total_att > 0 else 0

        total_xp = (
            XPTransaction.objects.filter(student=student)
            .aggregate(total=Sum("xp_amount"))["total"] or 0
        )

        avg_score_pct = float(avg_score)
        student_status = _calculate_student_status(avg_score_pct, att_rate, student.id)

        result.append({
            "student_id": student.id,
            "student_name": student.get_full_name() or student.username,
            "avg_score_pct": round(avg_score_pct, 2),
            "attendance_rate": round(att_rate, 2),
            "total_xp": total_xp,
            "status": student_status,
        })

    return result


def _calculate_student_status(avg_score: float, attendance_rate: float, student_id: int) -> str:
    if avg_score >= 85 and attendance_rate >= 85:
        return "excellent"
    if avg_score >= 60:
        return "average"
    from assignments.models import Assignment
    overdue = Assignment.objects.filter(
        course__student_courses__student_id=student_id,
        due_date__lt=timezone.now(),
    ).exclude(
        submissions__student_id=student_id
    ).exists()
    if avg_score < 60 or attendance_rate < 70 or overdue:
        return "needs_attention"
    return "average"
