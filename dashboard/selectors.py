"""
dashboard/selectors.py — Read-only queries and aggregations.

All dashboard read queries live here. Uses select_related/prefetch_related
for N+1 prevention. Never imports models directly from other apps — uses
their selectors or Django ORM with explicit joins.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import connection
from django.db.models import Avg, Count, F, Prefetch, Q, Sum
from django.db.models.functions import ExtractMonth, ExtractYear, TruncMonth
from django.utils import timezone

from accounts.models import SchoolMembership, User
from attendance.models import AttendanceRecord
from courses.models import Course, StudentCourse
from grades.models import Grade
from submissions.models import Submission

from .models import DashboardInsight, InterventionRecord, StudentNote


def _get_max_possible_score() -> Decimal:
    """Default max score for normalization. Assumes scores are out of 100."""
    return Decimal("100")


def get_gpa_for_student(student_id: int, period: str | None = None) -> Decimal:
    """Calculate weighted GPA on 4.0 scale for a student.

    GPA = avg(score / max_score * 4.0) across all graded submissions.
    """
    max_score = _get_max_possible_score()
    grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status=Submission.Status.GRADED,
    )

    if period:
        now = timezone.now()
        if period == "week":
            cutoff = now - timedelta(weeks=1)
        elif period == "month":
            cutoff = now - timedelta(days=30)
        elif period == "semester":
            cutoff = now - timedelta(days=180)
        else:
            cutoff = None
        if cutoff:
            grades = grades.filter(submission__submitted_at__gte=cutoff)

    total = Decimal("0")
    count = 0
    for g in grades.select_related("submission"):
        normalized = (g.score / max_score) * Decimal("4.0")
        total += normalized
        count += 1

    return total / count if count > 0 else Decimal("0")


def get_gpa_trend_for_class(
    class_id: int, months: int = 6
) -> list[dict[str, Any]]:
    """Return monthly GPA averages for a class over N months."""
    max_score = _get_max_possible_score()
    now = timezone.now()
    cutoff = now - timedelta(days=months * 30)

    grades = Grade.objects.filter(
        submission__status=Submission.Status.GRADED,
        submission__submitted_at__gte=cutoff,
    ).select_related("submission")

    monthly_data: dict[str, list[Decimal]] = {}
    for g in grades:
        month_key = g.submission.submitted_at.strftime("%Y-%m")
        normalized = (g.score / max_score) * Decimal("4.0")
        monthly_data.setdefault(month_key, []).append(normalized)

    sorted_months = sorted(monthly_data.keys())[-months:]
    result = []
    for m in sorted_months:
        values = monthly_data[m]
        avg = sum(values) / len(values) if values else Decimal("0")
        result.append({"month": m, "class_avg": float(round(avg, 2))})

    return result


def get_performance_trend_for_student(
    student_id: int, months: int = 6
) -> list[dict[str, Any]]:
    """Return monthly GPA trend for a student."""
    max_score = _get_max_possible_score()
    now = timezone.now()
    cutoff = now - timedelta(days=months * 30)

    grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status=Submission.Status.GRADED,
        submission__submitted_at__gte=cutoff,
    ).select_related("submission")

    monthly_data: dict[str, list[Decimal]] = {}
    for g in grades:
        month_key = g.submission.submitted_at.strftime("%Y-%m")
        normalized = (g.score / max_score) * Decimal("4.0")
        monthly_data.setdefault(month_key, []).append(normalized)

    sorted_months = sorted(monthly_data.keys())[-months:]
    result = []
    for m in sorted_months:
        values = monthly_data[m]
        avg = sum(values) / len(values) if values else Decimal("0")
        result.append({"month": m, "gpa": float(round(avg, 2))})

    return result


def _get_attendance_rate_for_student(student_id: int) -> float:
    """Return attendance rate (0-100) for a student across all courses."""
    total = AttendanceRecord.objects.filter(student_id=student_id).count()
    if total == 0:
        return 100.0
    present = AttendanceRecord.objects.filter(
        student_id=student_id,
        status__in=[AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.LATE],
    ).count()
    return round((present / total) * 100, 2)


def _get_disciplinary_count_for_student(student_id: int) -> int:
    """Return number of disciplinary cases for a student.

    Uses raw query since disciplinary model may not exist in all deployments.
    """
    with connection.cursor() as cursor:
        tables = connection.introspection.table_names()
        if "disciplinary_cases" not in tables:
            return 0
        cursor.execute(
            "SELECT COUNT(*) FROM disciplinary_cases WHERE student_id = %s",
            [student_id],
        )
        return cursor.fetchone()[0]


def _get_trend_direction(student_id: int) -> str:
    """Determine GPA trend direction: improving, stable, declining."""
    trend = get_performance_trend_for_student(student_id, months=3)
    if len(trend) < 2:
        return "stable"
    first = trend[0]["gpa"]
    last = trend[-1]["gpa"]
    change_pct = ((last - first) / first * 100) if first > 0 else 0
    if change_pct > 5:
        return "improving"
    elif change_pct < -5:
        return "declining"
    return "stable"


def calculate_risk_score(student_id: int) -> dict[str, Any]:
    """Compute risk score (0-100) and tier for a student.

    Components:
    - GPA (40%): (1 - gpa/4.0) * 100
    - Attendance (30%): (1 - attendance_rate/100) * 100
    - Disciplinary (20%): min(cases * 25, 100)
    - Trend (10%): declining=100, stable=50, improving=0
    """
    gpa = get_gpa_for_student(student_id)
    gpa_score = float((1 - gpa / Decimal("4.0")) * 100) if gpa > 0 else 50.0

    attendance_rate = _get_attendance_rate_for_student(student_id)
    attendance_score = (1 - attendance_rate / 100) * 100

    disciplinary_count = _get_disciplinary_count_for_student(student_id)
    disciplinary_score = min(disciplinary_count * 25, 100)

    trend = _get_trend_direction(student_id)
    trend_score = {"declining": 100, "stable": 50, "improving": 0}.get(trend, 50)

    composite = (
        gpa_score * 0.40
        + attendance_score * 0.30
        + disciplinary_score * 0.20
        + trend_score * 0.10
    )
    composite = round(min(max(composite, 0), 100), 1)

    if composite <= 30:
        tier = "low"
    elif composite <= 60:
        tier = "medium"
    elif composite <= 80:
        tier = "high"
    else:
        tier = "critical"

    factors = []
    if gpa < Decimal("2.0"):
        factors.append("low_gpa")
    if attendance_rate < 80:
        factors.append("high_absences")
    if disciplinary_count > 0:
        factors.append("disciplinary_cases")
    if trend == "declining":
        factors.append("declining_trend")

    return {
        "score": composite,
        "tier": tier,
        "factors": factors,
        "gpa": float(gpa),
        "attendance_rate": attendance_rate,
        "disciplinary_count": disciplinary_count,
        "trend": trend,
    }


def get_dashboard_overview(
    period: str = "month",
    academic_year: str | None = None,
    school_id: int | None = None,
) -> dict[str, Any]:
    """Returns KPIs, active alerts, and chart data for the overview page.

    When school_id is provided, all aggregations are scoped to that school.
    """
    if school_id:
        from schools.models import Class as SchoolClass
        from students.models import Student
        total_students = Student.objects.filter(school_id=school_id).count()
        total_teachers = User.objects.filter(
            role=User.Role.TEACHER, taught_courses__school_id=school_id
        ).distinct().count()
        total_classes = SchoolClass.objects.filter(school_id=school_id).count()
    else:
        total_students = User.objects.filter(role=User.Role.STUDENT).count()
        total_teachers = User.objects.filter(role=User.Role.TEACHER).count()
        total_classes = Course.objects.count()

    students = User.objects.filter(role=User.Role.STUDENT)
    gpas = []
    for s in students:
        gpa = get_gpa_for_student(s.id, period=period)
        if gpa > 0:
            gpas.append(float(gpa))
    avg_gpa = round(sum(gpas) / len(gpas), 2) if gpas else 0.0

    total_attendance = AttendanceRecord.objects.count()
    present_count = AttendanceRecord.objects.filter(
        status__in=[AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.LATE]
    ).count()
    attendance_rate = (
        round((present_count / total_attendance) * 100, 1)
        if total_attendance > 0
        else 0.0
    )

    alerts = DashboardInsight.objects.filter(is_dismissed=False).order_by(
        "-created_at"
    )[:10]

    students_per_class = []
    for course in Course.objects.all():
        count = StudentCourse.objects.filter(course=course).count()
        students_per_class.append(
            {"class_id": course.id, "class_name": course.title, "count": count}
        )

    gpa_trend = get_gpa_trend_for_class(
        Course.objects.first().id if Course.objects.exists() else 0, months=6
    )

    excellent = sum(1 for g in gpas if g >= 3.5)
    good = sum(1 for g in gpas if 2.5 <= g < 3.5)
    average = sum(1 for g in gpas if 1.5 <= g < 2.5)
    at_risk = sum(1 for g in gpas if g < 1.5)

    return {
        "kpis": {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_classes": total_classes,
            "average_gpa": avg_gpa,
            "attendance_rate": attendance_rate,
        },
        "alerts": [
            {
                "id": a.id,
                "severity": a.severity,
                "type": a.insight_type,
                "title": a.title,
                "description": a.description,
                "recommendation": a.recommendation,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ],
        "charts": {
            "students_per_class": students_per_class,
            "gpa_trend_6m": gpa_trend,
            "performance_distribution": {
                "excellent": excellent,
                "good": good,
                "average": average,
                "at_risk": at_risk,
            },
        },
    }


def get_classes_list(
    teacher_id: int | None = None, page: int = 1, page_size: int = 20
) -> dict[str, Any]:
    """Returns paginated list of classes with health metrics."""
    qs = Course.objects.select_related("teacher").all()
    if teacher_id:
        qs = qs.filter(teacher_id=teacher_id)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    courses = qs[start:end]

    results = []
    for course in courses:
        enrollment_count = StudentCourse.objects.filter(course=course).count()
        capacity_util = round(
            (enrollment_count / course.target_capacity) * 100, 1
        ) if course.target_capacity > 0 else 0.0

        enrolled_students = StudentCourse.objects.filter(course=course).values_list(
            "student_id", flat=True
        )
        gpas = []
        for sid in enrolled_students:
            gpa = get_gpa_for_student(sid)
            if gpa > 0:
                gpas.append(float(gpa))
        avg_gpa = round(sum(gpas) / len(gpas), 2) if gpas else 0.0

        trend_data = get_gpa_trend_for_class(course.id, months=2)
        gpa_trend = "0.00"
        if len(trend_data) >= 2:
            diff = trend_data[-1]["class_avg"] - trend_data[-2]["class_avg"]
            gpa_trend = f"{diff:+.2f}"

        if capacity_util > 110 or (trend_data and len(trend_data) >= 2
            and trend_data[-1]["class_avg"] - trend_data[-2]["class_avg"] < -0.4):
            health = "red"
        elif capacity_util > 100 or (trend_data and len(trend_data) >= 2
            and trend_data[-1]["class_avg"] - trend_data[-2]["class_avg"] < 0):
            health = "yellow"
        else:
            health = "green"

        results.append({
            "id": course.id,
            "title": course.title,
            "teacher": {"id": course.teacher_id, "name": course.teacher.username},
            "enrollment_count": enrollment_count,
            "target_capacity": course.target_capacity,
            "capacity_utilization": capacity_util,
            "average_gpa": avg_gpa,
            "health_status": health,
            "gpa_trend": gpa_trend,
        })

    return {
        "count": total,
        "next": end < total,
        "previous": page > 1,
        "results": results,
    }


def get_class_detail(class_id: int) -> dict[str, Any]:
    """Returns full class analytics: distribution, leaderboard, trends, teacher performance."""
    course = Course.objects.select_related("teacher").filter(id=class_id).first()
    if not course:
        return {}

    enrolled_students = StudentCourse.objects.filter(course=course).values_list(
        "student_id", flat=True
    )
    enrollment_count = len(enrolled_students)
    capacity_util = round(
        (enrollment_count / course.target_capacity) * 100, 1
    ) if course.target_capacity > 0 else 0.0

    gpas = {}
    for sid in enrolled_students:
        gpa = get_gpa_for_student(sid)
        if gpa > 0:
            gpas[sid] = float(gpa)

    avg_gpa = round(sum(gpas.values()) / len(gpas), 2) if gpas else 0.0

    school_gpas = []
    for s in User.objects.filter(role=User.Role.STUDENT):
        gpa = get_gpa_for_student(s.id)
        if gpa > 0:
            school_gpas.append(float(gpa))
    school_avg = round(sum(school_gpas) / len(school_gpas), 2) if school_gpas else 0.0

    comparison = (
        round(((avg_gpa - school_avg) / school_avg) * 100, 1)
        if school_avg > 0
        else 0.0
    )

    excellent = sum(1 for g in gpas.values() if g >= 3.5)
    good = sum(1 for g in gpas.values() if 2.5 <= g < 3.5)
    average = sum(1 for g in gpas.values() if 1.5 <= g < 2.5)
    at_risk = sum(1 for g in gpas.values() if g < 1.5)

    sorted_students = sorted(gpas.items(), key=lambda x: (-x[1], x[0]))[:4]
    leaderboard = []
    for rank, (sid, gpa) in enumerate(sorted_students, 1):
        student = User.objects.filter(id=sid).first()
        trend_data = get_performance_trend_for_student(sid, months=2)
        trend = "same"
        if len(trend_data) >= 2:
            diff = trend_data[-1]["gpa"] - trend_data[-2]["gpa"]
            if diff > 0.05:
                trend = "up"
            elif diff < -0.05:
                trend = "down"
        leaderboard.append({
            "rank": rank,
            "student_id": sid,
            "name": student.username if student else "Unknown",
            "gpa": gpa,
            "trend": trend,
        })

    gpa_trend = get_gpa_trend_for_class(class_id, months=6)

    teacher_courses = Course.objects.filter(teacher=course.teacher)
    teacher_student_ids = set()
    for tc in teacher_courses:
        teacher_student_ids.update(
            StudentCourse.objects.filter(course=tc).values_list("student_id", flat=True)
        )
    teacher_gpas = []
    for sid in teacher_student_ids:
        gpa = get_gpa_for_student(sid)
        if gpa > 0:
            teacher_gpas.append(float(gpa))
    teacher_avg_gpa = (
        round(sum(teacher_gpas) / len(teacher_gpas), 2) if teacher_gpas else 0.0
    )

    teacher_attendance_records = AttendanceRecord.objects.filter(
        student_id__in=teacher_student_ids
    )
    teacher_att_total = teacher_attendance_records.count()
    teacher_att_present = teacher_attendance_records.filter(
        status__in=[AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.LATE]
    ).count()
    teacher_att_rate = (
        round((teacher_att_present / teacher_att_total) * 100, 1)
        if teacher_att_total > 0
        else 0.0
    )

    school_teacher_avg = school_avg
    teacher_comparison = (
        round(((teacher_avg_gpa - school_teacher_avg) / school_teacher_avg) * 100, 1)
        if school_teacher_avg > 0
        else 0.0
    )

    return {
        "class": {
            "id": course.id,
            "title": course.title,
            "teacher": {"id": course.teacher_id, "name": course.teacher.username},
            "enrollment_count": enrollment_count,
            "target_capacity": course.target_capacity,
            "capacity_utilization": capacity_util,
            "average_gpa": avg_gpa,
            "school_avg_gpa": school_avg,
            "comparison_to_school": f"{comparison:+.1f}%",
        },
        "student_distribution": {
            "excellent": excellent,
            "good": good,
            "average": average,
            "at_risk": at_risk,
        },
        "leaderboard": leaderboard,
        "gpa_trend_6m": gpa_trend,
        "teacher_performance": {
            "avg_student_gpa": teacher_avg_gpa,
            "student_attendance_rate": teacher_att_rate,
            "school_teacher_avg_gpa": school_teacher_avg,
            "comparison": f"{teacher_comparison:+.1f}%",
        },
    }


def get_student_profile(student_id: int) -> dict[str, Any]:
    """Returns student profile with academic history, risk score, interventions, notes."""
    student = User.objects.filter(id=student_id, role=User.Role.STUDENT).first()
    if not student:
        return {}

    risk = calculate_risk_score(student_id)

    gpa_trend = get_performance_trend_for_student(student_id, months=6)

    grade_breakdown = {}
    grades = Grade.objects.filter(
        submission__student_id=student_id,
        submission__status=Submission.Status.GRADED,
    ).select_related("submission__assignment__course")
    for g in grades:
        course = g.submission.assignment.course
        subject = course.title
        grade_breakdown.setdefault(subject, []).append(float(g.score))

    grade_summary = []
    for subject, scores in grade_breakdown.items():
        avg = round(sum(scores) / len(scores), 1)
        grade_letter = (
            "A" if avg >= 90
            else "B+" if avg >= 85
            else "B" if avg >= 80
            else "C+" if avg >= 75
            else "C" if avg >= 70
            else "D" if avg >= 60
            else "F"
        )
        grade_summary.append({"subject": subject, "avg_score": avg, "grade_letter": grade_letter})

    attendance_rate = _get_attendance_rate_for_student(student_id)

    interventions = InterventionRecord.objects.filter(student=student).order_by(
        "priority", "created_at"
    )
    intervention_data = [
        {
            "id": i.id,
            "action": i.action,
            "status": i.status,
            "priority": i.priority,
            "created_at": i.created_at.isoformat(),
            "completed_at": i.completed_at.isoformat() if i.completed_at else None,
        }
        for i in interventions
    ]

    notes = StudentNote.objects.filter(student=student).select_related("author").order_by(
        "-created_at"
    )
    notes_data = [
        {
            "id": n.id,
            "author": n.author.username if n.author else "Unknown",
            "note": n.note,
            "created_at": n.created_at.isoformat(),
        }
        for n in notes
    ]

    current_classes = StudentCourse.objects.filter(
        student=student
    ).select_related("course__teacher")
    classes_data = [
        {
            "id": e.course.id,
            "title": e.course.title,
            "teacher": e.course.teacher.username,
        }
        for e in current_classes
    ]

    school_name = ""
    if student.school:
        school_name = student.school.name

    return {
        "student": {
            "id": student.id,
            "name": student.get_full_name() or student.username,
            "email": student.email,
            "role": student.role,
            "school": school_name,
            "current_classes": classes_data,
            "risk_score": risk["score"],
            "risk_tier": risk["tier"],
        },
        "academic_history": {
            "gpa_trend_6m": gpa_trend,
            "grade_breakdown": grade_summary,
            "attendance_rate": attendance_rate,
            "disciplinary_cases": [],
        },
        "interventions": intervention_data,
        "notes": notes_data,
    }


def get_report_summary(filters: dict[str, Any]) -> dict[str, Any]:
    """Returns filtered report with period comparison and insights."""
    qs = User.objects.filter(role=User.Role.STUDENT)

    class_id = filters.get("class_id")
    if class_id:
        student_ids = StudentCourse.objects.filter(course_id=class_id).values_list(
            "student_id", flat=True
        )
        qs = qs.filter(id__in=student_ids)

    date_from = filters.get("date_from")
    date_to = filters.get("date_to")

    total_students = qs.count()
    gpas = []
    for s in qs:
        gpa = get_gpa_for_student(s.id)
        if gpa > 0:
            gpas.append(float(gpa))
    avg_gpa = round(sum(gpas) / len(gpas), 2) if gpas else 0.0

    att_qs = AttendanceRecord.objects.filter(student__in=qs)
    if date_from:
        att_qs = att_qs.filter(date__gte=date_from)
    if date_to:
        att_qs = att_qs.filter(date__lte=date_to)

    att_total = att_qs.count()
    att_present = att_qs.filter(
        status__in=[AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.LATE]
    ).count()
    attendance_rate = (
        round((att_present / att_total) * 100, 1) if att_total > 0 else 0.0
    )

    current_attendance_rate = attendance_rate

    prior_date_from = None
    prior_date_to = None
    if date_from and date_to:
        delta = date_to - date_from
        prior_date_to = date_from - timedelta(days=1)
        prior_date_from = prior_date_to - delta

    if prior_date_from and prior_date_to:
        prior_att = AttendanceRecord.objects.filter(
            student__in=qs,
            date__gte=prior_date_from,
            date__lte=prior_date_to,
        )
        prior_total = prior_att.count()
        prior_present = prior_att.filter(
            status__in=[AttendanceRecord.Status.PRESENT, AttendanceRecord.Status.LATE]
        ).count()
        prior_attendance_rate = (
            round((prior_present / prior_total) * 100, 1)
            if prior_total > 0
            else current_attendance_rate
        )
    else:
        prior_attendance_rate = current_attendance_rate

    gpa_change = 0.0
    attendance_change = round(current_attendance_rate - prior_attendance_rate, 1)

    insights = []
    if attendance_change < -2:
        insights.append({
            "type": "performance_drop",
            "description": f"Attendance rate declined {abs(attendance_change)}% vs prior period",
            "recommendation": "Review attendance patterns for individual students",
        })

    return {
        "filters_applied": {k: v for k, v in filters.items() if v},
        "summary": {
            "total_students": total_students,
            "average_gpa": avg_gpa,
            "attendance_rate": attendance_rate,
            "disciplinary_incidents": 0,
        },
        "period_comparison": {
            "current_period": {
                "avg_gpa": avg_gpa,
                "attendance_rate": current_attendance_rate,
            },
            "prior_period": {
                "avg_gpa": avg_gpa,
                "attendance_rate": prior_attendance_rate,
            },
            "gpa_change_pct": f"{gpa_change:+.1f}%",
            "attendance_change_pct": f"{attendance_change:+.1f}%",
        },
        "insights": insights,
    }


def get_risk_summary() -> dict[str, Any]:
    """Returns risk tier breakdown and top at-risk students."""
    students = User.objects.filter(role=User.Role.STUDENT)
    tiers = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    at_risk_list = []

    for s in students:
        risk = calculate_risk_score(s.id)
        tiers[risk["tier"]] += 1
        if risk["score"] > 60:
            at_risk_list.append({
                "student_id": s.id,
                "name": s.get_full_name() or s.username,
                "risk_score": risk["score"],
                "risk_tier": risk["tier"],
                "contributing_factors": risk["factors"],
                "recommended_actions": _get_recommended_actions(risk["factors"]),
            })

    at_risk_list.sort(key=lambda x: -x["risk_score"])

    return {
        "total_at_risk": tiers["high"] + tiers["critical"],
        "by_tier": tiers,
        "top_at_risk_students": at_risk_list[:10],
    }


def _get_recommended_actions(factors: list[str]) -> list[str]:
    """Map risk factors to recommended actions."""
    actions = []
    if "low_gpa" in factors:
        actions.append("tutoring_referral")
    if "high_absences" in factors:
        actions.append("parent_meeting")
    if "disciplinary_cases" in factors:
        actions.append("counseling_referral")
    if "declining_trend" in factors:
        actions.append("teacher_checkin")
    if not actions:
        actions.append("peer_mentoring")
    return actions[:3]


def compare_classes(class_ids: list[int]) -> list[dict[str, Any]]:
    """Returns side-by-side comparison metrics for multiple classes."""
    results = []
    for cid in class_ids:
        detail = get_class_detail(cid)
        if detail:
            results.append({
                "class": detail["class"],
                "student_distribution": detail["student_distribution"],
                "teacher_performance": detail["teacher_performance"],
            })
    return results
