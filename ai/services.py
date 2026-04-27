import os
from django.conf import settings


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
    """Call AI API with prompt. Returns response or None on error."""
    try:
        import openai
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return None

        openai.api_key = api_key

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
        )

        return response.choices[0].message.content
    except Exception as e:
        return None


def chat_with_student_context(student, message):
    """
    Main chat function: send message with student context.
    Returns dict with 'reply' key.
    """
    if not message or not message.strip():
        return {'reply': 'Please ask me a question!'}

    context = build_student_context(student)

    has_data = (
        context['gpa'] > 0 or
        context['courses'] or
        context['total_xp'] > 0
    )

    if not has_data:
        return {'reply': "Welcome! I don't see any academic data yet. Keep studying and completing assignments, and I'll be able to give you personalized advice based on your progress!"}

    prompt = build_ai_prompt(context, message)

    reply = call_ai_api(prompt)

    if reply is None:
        return {'reply': 'Sorry, I encountered an error processing your request. Please try again later. If the problem persists, please contact support.'}

    return {'reply': reply}