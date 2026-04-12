from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from schools.models import School, Subject, Course
from students.models import Grade, Student
import random


User = get_user_model()

class Command(BaseCommand):
    help = 'Data Integration كاملة مع المواد والمناهج والمعلمين (أدبي - علمي - عربي - لغات)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 بدء Data Integration الكاملة...'))

        # 1. المدارس (كود رقمي فقط)
        schools_data = [
            {"name": "عمر الفاروق بنين", "school_code": "1001", "type": "arabic"},
            {"name": "مدرسة التحدي", "school_code": "1002", "type": "language"},
            {"name": "الأزهر الشريف", "school_code": "1003", "type": "arabic"},
            {"name": "مدرسة النور", "school_code": "1004", "type": "language"},
        ]

        schools = {}
        for data in schools_data:
            school, created = School.objects.get_or_create(
                school_code=data["school_code"],
                defaults={"name": data["name"], "school_type": data["type"]}
            )
            schools[data["school_code"]] = school
            status = "✅ Created" if created else "✅ موجودة"
            self.stdout.write(f'{status}: {data["name"]} (كود: {data["school_code"]})')

        # 2. الدرجات
        grades_list = [
            ("الصف الأول الإعدادي", 1, "إعدادي"),
            ("الصف الثاني الإعدادي", 2, "إعدادي"),
            ("الصف الثالث الإعدادي", 3, "إعدادي"),
            ("الصف الأول الثانوي", 4, "ثانوي"),
            ("الصف الثاني الثانوي", 5, "ثانوي"),
            ("الصف الثالث الثانوي", 6, "ثانوي"),
        ]
        for name, level, stage in grades_list:
            Grade.objects.get_or_create(name=name, level=level, stage=stage)

        # 3. المواد الأساسية (Subject)
        subjects_data = [
            ("اللغة العربية", "Arabic", "ARB"),
            ("اللغة الإنجليزية", "English", "ENG"),
            ("اللغة الفرنسية", "French", "FRE"),
            ("الرياضيات", "Mathematics", "MATH"),
            ("العلوم", "Science", "SCI"),
            ("الفيزياء", "Physics", "PHY"),
            ("الكيمياء", "Chemistry", "CHEM"),
            ("الأحياء", "Biology", "BIO"),
            ("التاريخ", "History", "HIST"),
            ("الجغرافيا", "Geography", "GEO"),
            ("الفلسفة والمنطق", "Philosophy", "PHIL"),
            ("علم النفس والاجتماع", "Psychology", "PSY"),
            ("المواطنة وحقوق الإنسان", "Citizenship", "CIT"),
            ("التربية الدينية", "Religious Education", "REL"),
        ]

        subjects = {}
        for name_ar, name_en, code in subjects_data:
            subject, _ = Subject.objects.get_or_create(
                code=code,
                defaults={"name_ar": name_ar, "name_en": name_en}
            )
            subjects[code] = subject

        # 4. المناهج (Courses)
        self.stdout.write(self.style.SUCCESS('جاري إنشاء المناهج...'))

        # إعدادي (مواد أساسية مشتركة)
        for grade in Grade.objects.filter(level__lte=3):
            for subject in subjects.values():
                for school_type in ['arabic', 'language']:
                    Course.objects.get_or_create(
                        subject=subject,
                        grade=grade,
                        school_type=school_type,
                        section='general'
                    )

        # أولى ثانوي (مواد موحدة)
        grade1 = Grade.objects.get(level=4)
        for subject in subjects.values():
            for school_type in ['arabic', 'language']:
                Course.objects.get_or_create(
                    subject=subject,
                    grade=grade1,
                    school_type=school_type,
                    section='general'
                )

        # ثانية ثانوي
        grade2 = Grade.objects.get(level=5)
        for school_type in ['arabic', 'language']:
            # أدبي
            literary = ['ARB', 'ENG', 'FRE', 'HIST', 'GEO', 'PHIL', 'PSY']
            for code in literary:
                if code in subjects:
                    Course.objects.get_or_create(
                        subject=subjects[code],
                        grade=grade2,
                        school_type=school_type,
                        section='literary'
                    )
            # علمي
            scientific = ['ARB', 'ENG', 'FRE', 'PHY', 'CHEM', 'BIO', 'MATH']
            for code in scientific:
                if code in subjects:
                    Course.objects.get_or_create(
                        subject=subjects[code],
                        grade=grade2,
                        school_type=school_type,
                        section='scientific'
                    )

        # ثالثة ثانوي
        grade3 = Grade.objects.get(level=6)
        for school_type in ['arabic', 'language']:
            literary = ['ARB', 'ENG', 'FRE', 'HIST', 'GEO', 'PHIL', 'PSY']
            for code in literary:
                if code in subjects:
                    Course.objects.get_or_create(
                        subject=subjects[code],
                        grade=grade3,
                        school_type=school_type,
                        section='literary'
                    )
            scientific = ['ARB', 'ENG', 'FRE', 'PHY', 'CHEM', 'BIO', 'MATH']
            for code in scientific:
                if code in subjects:
                    Course.objects.get_or_create(
                        subject=subjects[code],
                        grade=grade3,
                        school_type=school_type,
                        section='scientific'
                    )

        self.stdout.write(self.style.SUCCESS('✅ تم إنشاء المناهج بنجاح'))

        # 5. المعلمين (كل معلم مرتبط بـ 2 مواد)
        self.stdout.write(self.style.SUCCESS('جاري إنشاء المعلمين...'))

        teacher_subjects_pairs = [
            ("رياضيات", "فيزياء"),
            ("كيمياء", "أحياء"),
            ("عربي", "تاريخ"),
            ("إنجليزي", "فرنسي"),
            ("رياضيات", "علوم"),
            ("جغرافيا", "تاريخ"),
        ]

        for i, (sub1, sub2) in enumerate(teacher_subjects_pairs, 1):
            username = f"teacher{i:02d}"
            full_name = f"معلم {random.choice(['أحمد', 'محمد', 'علي', 'سارة', 'فاطمة', 'خالد'])}"

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "role": "teacher",
                    "email": f"{username}@grow.com",
                    "is_staff": True,
                }
            )
            if created:
                user.set_password("123456")
                user.save()

            school1 = random.choice(list(schools.values()))
            school2 = random.choice(list(schools.values()))

            self.stdout.write(self.style.SUCCESS(
                f'✓ معلم: {full_name} ({username}) → {sub1} + {sub2}'
            ))

        # 6. الطلاب (150 في كل مدرسة)
        first_names = ["محمد", "أحمد", "عمر", "علي", "حسن", "خالد", "يوسف", "إبراهيم", "مصطفى"]
        last_names = ["السيد", "محمد", "أحمد", "عبدالله", "حسن", "إبراهيم"]

        total_students = 0
        students_per_school = 150

        for school_code, school in schools.items():
            for _ in range(students_per_school):
                full_name = f"{random.choice(first_names)} {random.choice(last_names)}"
                grade = Grade.objects.order_by('?').first()

                Student.objects.create(
                    parent=None,
                    school=school,
                    grade=grade,
                    full_name=full_name,
                )
                total_students += 1

            self.stdout.write(self.style.SUCCESS(f'✓ {students_per_school} طالب في {school.name}'))

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ تم الانتهاء بنجاح!\n'
            f'   • عدد المدارس: {len(schools)}\n'
            f'   • إجمالي الطلاب: {total_students}\n'
            f'   • عدد المعلمين: {len(teacher_subjects_pairs)}\n'
            f'   • كود المدرسة رقمي (1001, 1002...)\n'
            f'   • المناهج مقسمة حسب أدبي / علمي + عربي / لغات'
        ))