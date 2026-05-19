import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def build_student_context(student):
    """Build comprehensive student context for AI prompts."""
    from ai import selectors

    courses = selectors.get_student_courses(student)
    grades = selectors.get_student_grades(student)
    sessions = selectors.get_student_sessions(student)
    attendance = selectors.get_student_attendance(student)
    xp_data = selectors.get_student_xp(student)
    gpa = selectors.compute_gpa(student)
    weak_subjects = selectors.identify_weak_subjects(student)

    recent_scores = [g['score'] for g in grades[:5]]

    return {
        'gpa': gpa,
        'courses': [c['name'] for c in courses],
        'weak_subjects': weak_subjects,
        'recent_scores': recent_scores,
        'study_hours': sessions['this_week_hours'],
        'attendance_rate': attendance['rate'],
        'total_xp': xp_data['total_xp'],
    }


def build_ai_prompt(context, message):
    """Build AI prompt with student context."""
    prompt = f"""You are a smart and helpful tutor AI assistant for students.

Student Academic Profile:
- GPA: {context['gpa']}
- Enrolled Courses: {', '.join(context['courses']) if context['courses'] else 'None'}
- Weak Subjects: {', '.join(context['weak_subjects']) if context['weak_subjects'] else 'None'}
- Recent Scores: {context['recent_scores']}
- Study Hours This Week: {context['study_hours']}
- Attendance Rate: {context['attendance_rate']}%
- Total XP: {context['total_xp']}

Student Question: {message}

Provide helpful, personalized advice based on the student's academic profile. Be encouraging but specific."""
    return prompt


def call_ai_api(prompt):
    """Call Google Gemini API with prompt. Returns response or None on error."""
    try:
        import google.generativeai as genai

        api_key = settings.AI_API_KEY
        if not api_key:
            logger.warning("AI_API_KEY not set — AI chat unavailable.")
            return None

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as exc:
        logger.error("Gemini API call failed: %s", exc, exc_info=True)
        return None


def _fallback_reply(message: str, context: dict) -> str:
    """Simple fallback response when AI API is unavailable."""
    message_lower = message.lower().strip()

    greetings = ["hi", "hello", "hey", "hi there", "hello there", "good morning", "good afternoon"]
    if message_lower in greetings or message_lower.startswith(tuple(g.strip() for g in ["hi", "hello", "hey"])):
        name_part = context.get("full_name", "")
        greeting = f"Hello {name_part}!" if name_part else "Hello!"
        if context["courses"]:
            return f"{greeting} I see you're enrolled in {', '.join(context['courses'][:3])}. How can I help you with your studies today?"
        return f"{greeting} How can I help you with your studies today?"

    thanks = ["thank", "thanks", "thx", "thank you"]
    if any(t in message_lower for t in thanks):
        return "You're welcome! Keep up the great work! 😊"

    return "I'm here to help with your studies! You can ask me about your courses, grades, study tips, or anything academic."


def _get_full_name(student) -> str:
    try:
        return student.get_full_name() or ""
    except Exception:
        return ""


def chat_with_student_context(student, message):
    if not message or not message.strip():
        return {'reply': 'Please ask me a question!'}

    context = build_student_context(student)
    context["full_name"] = _get_full_name(student)

    prompt = build_ai_prompt(context, message)

    reply = call_ai_api(prompt)

    if reply is None:
        reply = _fallback_reply(message, context)

    return {'reply': reply}