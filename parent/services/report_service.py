from datetime import date, datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Avg, Sum
from django.template.loader import render_to_string

from grades.models import Grade
from submissions.models import Submission
from xp.models import XPTransaction


def _cache_key(student_id: int, year_month: str) -> str:
    return f"parent_report_{student_id}_{year_month}"


def get_cached_report(student_id: int, year_month: str) -> bytes | None:
    return cache.get(_cache_key(student_id, year_month))


def invalidate_report_cache(student_id: int, year_month: str) -> None:
    cache.delete(_cache_key(student_id, year_month))


def get_monthly_report(student_id: int, year_month: str) -> dict:
    from attendance.models import AttendanceRecord
    from assignments.models import Assignment
    from courses.models import Course
    from students.models import Student as StudentProfile
    from study_sessions.models import LoginHistory

    year, month = _parse_year_month(year_month)

    grades_qs = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded",
        graded_at__year=year,
        graded_at__month=month,
    )
    overall_avg = grades_qs.aggregate(avg=Avg("score"))["avg"] or 0.0

    past_month = month - 1 or 12
    past_year = year if month > 1 else year - 1
    past_avg = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded",
        graded_at__year=past_year,
        graded_at__month=past_month,
    ).aggregate(avg=Avg("score"))["avg"] or 0.0

    def _grade_label(avg):
        if avg >= 90:
            return "A"
        if avg >= 80:
            return "B"
        if avg >= 70:
            return "C"
        return "D"

    total_assignments = Assignment.objects.filter(
        course__student_courses__student_id=student_id,
        due_date__year=year,
        due_date__month=month,
    ).distinct().count()
    submitted = Submission.objects.filter(
        student_id=student_id,
        submitted_at__year=year,
        submitted_at__month=month,
    ).count()
    missing = max(0, total_assignments - submitted)

    xp_total = (
        XPTransaction.objects.filter(
            student_id=student_id,
            created_at__year=year,
            created_at__month=month,
        ).aggregate(total=Sum("xp_amount"))["total"]
        or 0
    )

    subject_grades = {}
    for g in grades_qs.select_related("submission__assignment__course"):
        course = g.submission.assignment.course
        course_name = course.title
        if course_name not in subject_grades:
            subject_grades[course_name] = {"scores": [], "total": 0}
        subject_grades[course_name]["scores"].append(float(g.score))
        subject_grades[course_name]["total"] += 1

    profile = StudentProfile.objects.filter(user_id=student_id).first()
    course_list = Course.objects.none()
    if profile and profile.school_id:
        course_list = Course.objects.filter(
            school_id=profile.school_id, grade_id=profile.grade_id,
        )

    subject_performance = []
    for course in course_list:
        data = subject_grades.get(course.title, {"scores": [], "total": 0})
        avg = round(sum(data["scores"]) / len(data["scores"]), 1) if data["scores"] else 0

        current_submissions_count = Submission.objects.filter(
            student_id=student_id,
            assignment__course=course,
            submitted_at__year=year,
            submitted_at__month=month,
        ).count()

        total_course_assignments = Assignment.objects.filter(
            course=course, due_date__year=year, due_date__month=month,
        ).count()
        submissions_str = f"{current_submissions_count}/{total_course_assignments or 1}"

        subject_performance.append({
            "name": course.title,
            "total_percent": avg,
            "change": round(avg - past_avg, 1),
            "grade": _grade_label(avg) if data["scores"] else "N/A",
            "submissions": submissions_str,
        })

    sun_thu = 0
    for d in range(1, 32):
        try:
            dd = date(year, month, d)
            if dd.weekday() < 5:
                sun_thu += 1
        except ValueError:
            break
    present = AttendanceRecord.objects.filter(
        student_id=student_id, date__year=year, date__month=month,
        status__in=["present", "late"],
    ).count()
    attendance_rate = round((present / sun_thu) * 100, 1) if sun_thu else 0.0

    login_dates = set(
        LoginHistory.objects.filter(student_id=student_id)
        .values_list("login_date", flat=True)
    )
    streak = 0
    today = date.today()
    for i in range(365):
        if today - timedelta(days=i) in login_dates:
            streak += 1
        else:
            break

    return {
        "month": year_month,
        "overall_average": {
            "total": round(float(overall_avg), 1),
            "grade": _grade_label(float(overall_avg)),
            "change": round(float(overall_avg) - float(past_avg), 1),
        },
        "attendance": {
            "total": attendance_rate,
            "streak": streak,
        },
        "assignment_summary": {
            "total": total_assignments,
            "submitted": submitted,
            "missing": missing,
        },
        "total_xp": xp_total,
        "subject_performance": subject_performance,
    }


def generate_pdf_report(student_id: int, year_month: str) -> bytes:
    cached = get_cached_report(student_id, year_month)
    if cached:
        return cached

    report = get_monthly_report(student_id, year_month)

    try:
        from weasyprint import HTML

        html = render_to_string("parent/report_pdf.html", {"report": report})
        pdf = HTML(string=html).write_pdf()

        cache_timeout = getattr(settings, "PARENT_REPORT_CACHE_TIMEOUT", 3600)
        cache.set(_cache_key(student_id, year_month), pdf, cache_timeout)

        return pdf
    except Exception:
        return None


def _parse_year_month(year_month: str) -> tuple:
    try:
        dt = datetime.strptime(year_month, "%Y-%m")
        return dt.year, dt.month
    except (ValueError, TypeError):
        raise ValueError("Invalid month format. Use YYYY-MM.")
