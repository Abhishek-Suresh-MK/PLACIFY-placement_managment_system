import os

from django.core.management.base import BaseCommand

from accounts.models import Role, User
from placements.models import College, Company, Department, RecruiterProfile, Skill


class Command(BaseCommand):
    help = "Create safe local PLACIFY seed data using email-based accounts."

    def handle(self, *args, **options):
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@placify.local")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "AdminPass123!")
        admin, _ = User.objects.get_or_create(email=admin_email, defaults={"name": "Placify Admin", "role": Role.ADMIN, "is_staff": True, "is_superuser": True})
        admin.name = "Placify Admin"
        admin.role = Role.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password(admin_password)
        admin.save()

        College.objects.get_or_create(name="College of Engineering Munnar", defaults={"short_name": "CEM", "location": "Munnar, Kerala"})
        departments = [
            ("Computer Science and Engineering", "CSE"),
            ("Electronics and Communication Engineering", "ECE"),
            ("Electrical and Electronics Engineering", "EEE"),
            ("Mechanical Engineering", "ME"),
            ("Civil Engineering", "CE"),
            ("Information Technology", "IT"),
        ]
        for name, code in departments:
            Department.objects.get_or_create(code=code, defaults={"name": name})

        skills = [
            ("Python", "PROGRAMMING"), ("C", "PROGRAMMING"), ("C++", "PROGRAMMING"), ("Java", "PROGRAMMING"),
            ("JavaScript", "PROGRAMMING"), ("Django", "FRAMEWORK"), ("Flask", "FRAMEWORK"), ("FastAPI", "FRAMEWORK"),
            ("SQL", "DATABASE"), ("PostgreSQL", "DATABASE"), ("MySQL", "DATABASE"), ("AWS", "CLOUD"),
            ("Docker", "DEVOPS"), ("Linux", "DEVOPS"), ("Git", "TOOL"), ("Machine Learning", "AI_ML"),
            ("Deep Learning", "AI_ML"), ("React", "FRONTEND"),
        ]
        for name, category in skills:
            Skill.objects.get_or_create(name=name, defaults={"category": category})

        company, _ = Company.objects.get_or_create(name="Placify Demo Technologies", defaults={"location": "Bangalore"})
        recruiter_email = os.getenv("SEED_RECRUITER_EMAIL", "recruiter@placify.local")
        recruiter_password = os.getenv("SEED_RECRUITER_PASSWORD", "RecruiterPass123!")
        recruiter, _ = User.objects.get_or_create(email=recruiter_email, defaults={"name": "Demo Recruiter", "role": Role.RECRUITER})
        recruiter.name = "Demo Recruiter"
        recruiter.role = Role.RECRUITER
        recruiter.set_password(recruiter_password)
        recruiter.save()
        RecruiterProfile.objects.get_or_create(user=recruiter, defaults={"company": company, "phone": ""})

        self.stdout.write(self.style.SUCCESS("PLACIFY seed data created."))
        self.stdout.write(f"Admin: {admin_email}")
        self.stdout.write(f"Recruiter: {recruiter_email}")
