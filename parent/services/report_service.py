from datetime import datetime

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
    year, month = _parse_year_month(year_month)

    grades_qs = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status="graded",
        graded_at__year=year,
        graded_at__month=month,
    )
    overall_avg = grades_qs.aggregate(avg=Avg("score"))["avg"] or 0.0

    from assignments.models import Assignment
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

    subject_performance = [
        {
            "name": name,
            "average": round(sum(d["scores"]) / len(d["scores"]), 1),
            "completed": d["total"],
        }
        for name, d in subject_grades.items()
    ]

    return {
        "month": year_month,
        "overall_average": round(float(overall_avg), 1),
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
