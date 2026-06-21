import logging

from django.conf import settings

from ai.models import ChatMessage

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai_mod
except ImportError:
    genai_mod = None

MAX_HISTORY_MESSAGES = 10


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


def _serialize_history_for_prompt(history):
    """Convert ChatMessage queryset into Gemini-style history list."""
    parts = []
    for msg in history:
        parts.append(f"{msg.role}: {msg.message}")
    return "\n".join(parts)


def _get_system_instruction(context):
    """Build the system instruction from student context."""
    courses = ', '.join(context['courses']) if context['courses'] else 'None'
    weak = ', '.join(context['weak_subjects']) if context['weak_subjects'] else 'None'

    return (
        "You are a smart and helpful tutor AI assistant for students. "
        "Keep responses clear, encouraging, and specific to the student's own profile.\n\n"
        "Student Academic Profile:\n"
        f"- GPA: {context['gpa']}\n"
        f"- Enrolled Courses: {courses}\n"
        f"- Weak Subjects: {weak}\n"
        f"- Recent Scores: {context['recent_scores']}\n"
        f"- Study Hours This Week: {context['study_hours']}\n"
        f"- Attendance Rate: {context['attendance_rate']}%\n"
        f"- Total XP: {context['total_xp']}"
    )


def call_ai_api(system_instruction, history_text, message):
    """Call Google Gemini API with system instruction, history, and user message.

    Returns response text or None on error.
    """
    try:
        if genai_mod is None:
            logger.warning("google.generativeai not installed - AI chat unavailable.")
            return None

        api_key = settings.AI_API_KEY
        if not api_key:
            logger.warning("AI_API_KEY not set - AI chat unavailable.")
            return None

        genai_mod.configure(api_key=api_key)
        model = genai_mod.GenerativeModel(
            settings.AI_MODEL_NAME,
            system_instruction=system_instruction,
        )

        full_prompt = history_text + f"\nuser: {message}\nassistant:"
        response = model.generate_content(full_prompt)
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
        return "You're welcome! Keep up the great work!"

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

    system_instruction = _get_system_instruction(context)

    history = ChatMessage.objects.filter(
        student=student.user if hasattr(student, 'user') else student
    ).order_by('-created_at')[:MAX_HISTORY_MESSAGES]

    history = list(reversed(history))
    history_text = _serialize_history_for_prompt(history)

    reply = call_ai_api(system_instruction, history_text, message)

    if reply is None:
        reply = _fallback_reply(message, context)

    ChatMessage.objects.create(
        student=student.user if hasattr(student, 'user') else student,
        role=ChatMessage.Role.USER,
        message=message,
    )
    ChatMessage.objects.create(
        student=student.user if hasattr(student, 'user') else student,
        role=ChatMessage.Role.ASSISTANT,
        message=reply,
    )

    return {'reply': reply}
