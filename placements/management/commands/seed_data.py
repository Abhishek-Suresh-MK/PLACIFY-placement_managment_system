"""Create a complete, repeatable PLACIFY demonstration dataset.

Run with:
    python manage.py seed_data

Demo credentials are for local development only. Never reuse them in production.
The command updates records it owns by stable email/name keys and can be run repeatedly.
"""
import os
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from accounts.models import Role, User
from placements.models import (
    Announcement, AnnouncementAudience, AnnouncementStatus, Application,
    ApplicationStatus, College, Company, Department, EmploymentType, Gallery,
    PlacementDrive, PlacementDriveStatus, PlacementHistory, PlacementHistoryStatus,
    PlacementType, RecruiterProfile, Result, Skill, StageStatus, StudentProfile,
    StudyMaterial,
)


class Command(BaseCommand):
    help = "Seed a complete, idempotent local PLACIFY demo dataset."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        admin = self._user(
            os.getenv("SEED_ADMIN_EMAIL", "admin@placify.local"),
            os.getenv("SEED_ADMIN_PASSWORD", "AdminPass123!"),
            "PLACIFY Administrator", Role.ADMIN, staff=True, superuser=True,
        )

        # Colleges and departments: CEM is the primary operating institution.
        cem = self._college("College of Engineering Munnar", "CEM", "Munnar, Kerala")
        gect = self._college("Government Engineering College Thrissur", "GECT", "Thrissur, Kerala")
        rset = self._college("Rajagiri School of Engineering & Technology", "RSET", "Kakkanad, Kerala")
        colleges = [cem, gect, rset]

        department_rows = [
            ("Computer Science and Engineering", "CSE"),
            ("Electronics and Communication Engineering", "ECE"),
            ("Electrical and Electronics Engineering", "EEE"),
            ("Mechanical Engineering", "ME"),
            ("Civil Engineering", "CE"),
            ("Information Technology", "IT"),
        ]
        departments = {}
        for name, code in department_rows:
            obj, _ = Department.objects.update_or_create(
                code=code, defaults={"name": name, "is_active": True}
            )
            departments[code] = obj

        skill_rows = {
            "Python": "PROGRAMMING", "C": "PROGRAMMING", "C++": "PROGRAMMING",
            "Java": "PROGRAMMING", "JavaScript": "PROGRAMMING",
            "Django": "FRAMEWORK", "Django REST Framework": "FRAMEWORK",
            "Flask": "FRAMEWORK", "React": "FRONTEND",
            "PostgreSQL": "DATABASE", "MySQL": "DATABASE", "SQL": "DATABASE",
            "AWS": "CLOUD", "Linux": "DEVOPS", "Docker": "DEVOPS",
            "Git": "TOOL", "GitHub": "TOOL", "Machine Learning": "AI_ML",
            "Data Analysis": "OTHER", "Communication": "OTHER",
        }
        skills = {}
        for name, category in skill_rows.items():
            obj, _ = Skill.objects.update_or_create(
                name=name, defaults={"category": category, "is_active": True}
            )
            skills[name] = obj

        company_rows = [
            ("Tata Consultancy Services", "IT services, consulting and business solutions.", "https://www.tcs.com", "Kochi, Kerala", "Campus Hiring Team", "campus.demo@tcs.example"),
            ("Infosys", "Digital services and consulting roles for early-career engineers.", "https://www.infosys.com", "Thiruvananthapuram, Kerala", "Early Careers Team", "careers.demo@infosys.example"),
            ("UST", "Digital transformation, engineering and technology services.", "https://www.ust.com", "Kochi, Kerala", "University Relations", "campus.demo@ust.example"),
            ("Federal Bank", "Technology, analytics and digital banking opportunities.", "https://www.federalbank.co.in", "Aluva, Kerala", "Talent Acquisition", "campus.demo@federalbank.example"),
            ("IBM", "Software, cloud, data and infrastructure technology.", "https://www.ibm.com", "Bengaluru, Karnataka", "Campus Recruiting", "campus.demo@ibm.example"),
            ("Zoho", "Product engineering and business software.", "https://www.zoho.com", "Chennai, Tamil Nadu", "University Hiring", "campus.demo@zoho.example"),
        ]
        companies = {}
        for name, description, website, location, contact, email in company_rows:
            obj, _ = Company.objects.update_or_create(
                name=name,
                defaults={
                    "description": description, "website": website, "location": location,
                    "contact_name": contact, "contact_email": email, "is_active": True,
                },
            )
            companies[name] = obj

        recruiter = self._user(
            os.getenv("SEED_RECRUITER_EMAIL", "recruiter@placify.local"),
            os.getenv("SEED_RECRUITER_PASSWORD", "RecruiterPass123!"),
            "Aarav Menon — TCS Recruiter", Role.RECRUITER,
        )
        recruiter_profile, _ = RecruiterProfile.objects.update_or_create(
            user=recruiter,
            defaults={"company": companies["Tata Consultancy Services"], "phone": "+91-90000-10001"},
        )

        # Exactly two named student demo accounts, with deliberately varied profiles.
        student_specs = [
            {
                "email": "student01@placify.local", "password": os.getenv("SEED_STUDENT_PASSWORD", "StudentPass123!"),
                "name": "Ananya Nair", "phone": "+91-90000-20001", "university_no": "CEM2026CSE001",
                "address": "Munnar, Idukki, Kerala", "age": 22, "dept": "CSE", "cgpa": "8.42",
                "backlogs": 0, "passout": now.year, "skill_names": ["Python", "Django", "SQL", "PostgreSQL", "Git", "GitHub", "Communication"],
            },
            {
                "email": "student02@placify.local", "password": os.getenv("SEED_STUDENT_PASSWORD", "StudentPass123!"),
                "name": "Nikhil Raj", "phone": "+91-90000-20002", "university_no": "CEM2026ECE002",
                "address": "Payyannur, Kannur, Kerala", "age": 22, "dept": "ECE", "cgpa": "7.18",
                "backlogs": 1, "passout": now.year, "skill_names": ["C", "C++", "Python", "Linux", "AWS", "Communication"],
            },
        ]
        students = {}
        for spec in student_specs:
            user = self._user(spec["email"], spec["password"], spec["name"], Role.STUDENT)
            profile, _ = StudentProfile.objects.update_or_create(
                user=user,
                defaults={
                    "phone": spec["phone"], "college": cem,
                    "university_no": spec["university_no"], "address": spec["address"],
                    "age": spec["age"], "department": departments[spec["dept"]],
                    "current_year": 4, "cgpa": Decimal(spec["cgpa"]),
                    "backlogs": spec["backlogs"], "passout_year": spec["passout"],
                    "is_active": True,
                },
            )
            profile.skills.set([skills[s] for s in spec["skill_names"]])
            students[spec["email"]] = profile

        # Drives include a mix of open, draft, closed and cancelled states for UI/testing.
        # Every drive includes CEM. Only one explicitly cross-college drive includes others.
        start_past = now - timedelta(days=10)
        deadline_future = now + timedelta(days=14)
        drive_specs = [
            ("TCS — Assistant System Engineer", "Tata Consultancy Services", "Assistant System Engineer", "FULL_TIME", "4.20", "7.00", 1, ["CSE", "IT", "ECE"], ["Python", "SQL"], "OPEN", -5, 14, 12, [cem]),
            ("Infosys — Systems Engineer", "Infosys", "Systems Engineer", "FULL_TIME", "3.60", "6.50", 0, ["CSE", "IT", "ECE", "EEE"], ["Python", "SQL"], "OPEN", -3, 10, 18, [cem]),
            ("UST — Python Developer Intern", "UST", "Python Developer Intern", "INTERNSHIP", "0.60", "6.50", 0, ["CSE", "IT"], ["Python", "Django"], "OPEN", -2, 8, 20, [cem]),
            ("Federal Bank — Data Analyst Trainee", "Federal Bank", "Data Analyst Trainee", "FULL_TIME", "5.50", "7.00", 0, ["CSE", "IT", "ECE"], ["SQL", "Data Analysis"], "OPEN", -1, 7, 24, [cem, gect, rset]),
            ("IBM — Associate Technical Engineer", "IBM", "Associate Technical Engineer", "FULL_TIME", "6.00", "7.50", 0, ["CSE", "IT", "ECE"], ["Python", "Linux", "AWS"], "DRAFT", 2, 20, 30, [cem]),
            ("Zoho — Software Developer", "Zoho", "Software Developer", "FULL_TIME", "8.00", "8.00", 0, ["CSE", "IT"], ["C", "C++", "SQL"], "OPEN", -4, 5, 16, [cem]),
            ("TCS — Graduate Trainee (Closed)", "Tata Consultancy Services", "Graduate Trainee", "FULL_TIME", "3.80", "6.00", 0, ["CSE", "ECE", "EEE", "ME", "CE", "IT"], [], "CLOSED", -45, -10, -5, [cem]),
            ("UST — Cloud Support Associate (Cancelled)", "UST", "Cloud Support Associate", "FULL_TIME", "5.00", "6.00", 0, ["CSE", "IT", "ECE"], ["Linux", "AWS"], "CANCELLED", -30, -15, -8, [cem]),
        ]
        drives = {}
        for title, company_name, role_title, emp_type, package, min_cgpa, max_backlogs, dept_codes, skill_names, status, start_delta, deadline_delta, drive_delta, allowed in drive_specs:
            drive, _ = PlacementDrive.objects.update_or_create(
                company=companies[company_name], title=title,
                defaults={
                    "description": f"Demonstration recruitment drive for {role_title}. Review eligibility, submit an application, and track each recruitment stage in PLACIFY.",
                    "job_role": role_title, "location": companies[company_name].location,
                    "employment_type": emp_type, "salary_package": Decimal(package),
                    "eligibility_description": f"Minimum CGPA {min_cgpa}; maximum {max_backlogs} active backlogs. Eligible departments: {', '.join(dept_codes)}.",
                    "minimum_cgpa": Decimal(min_cgpa), "maximum_backlogs": max_backlogs,
                    "allowed_graduation_years": [now.year],
                    "application_start": now + timedelta(days=start_delta),
                    "application_deadline": now + timedelta(days=deadline_delta),
                    "drive_date": now + timedelta(days=drive_delta),
                    "status": status,
                },
            )
            drive.allowed_colleges.set(allowed)
            drive.allowed_departments.set([departments[c] for c in dept_codes])
            drive.required_skills.set([skills[s] for s in skill_names])
            drive.recruiters.set([recruiter_profile] if company_name == "Tata Consultancy Services" else [])
            drives[title] = drive

        # Application matrix covers every major status and includes separate stage results.
        application_specs = [
            ("student01@placify.local", "TCS — Assistant System Engineer", "SHORTLISTED", ("PASSED", "PENDING", "PENDING", "PENDING"), "Shortlisted for the next recruitment stage."),
            ("student01@placify.local", "TCS — Graduate Trainee (Closed)", "SELECTED", ("PASSED", "PASSED", "PASSED", "PASSED"), "Selected — historical demo record."),
            ("student02@placify.local", "TCS — Assistant System Engineer", "UNDER_REVIEW", ("PENDING", "PENDING", "PENDING", "PENDING"), "Application is being reviewed."),
            ("student01@placify.local", "Infosys — Systems Engineer", "ASSESSMENT", ("PASSED", "PENDING", "PENDING", "PENDING"), "Online assessment scheduled."),
            
            ("student01@placify.local", "UST — Python Developer Intern", "INTERVIEW", ("PASSED", "PASSED", "PASSED", "PENDING"), "Technical interview passed; HR interview pending."),
            
            ("student01@placify.local", "Federal Bank — Data Analyst Trainee", "APPLIED", ("PENDING", "PENDING", "PENDING", "PENDING"), "Application submitted to a cross-college drive explicitly enabled by admin."),
            ("student01@placify.local", "Zoho — Software Developer", "WITHDRAWN", ("PENDING", "PENDING", "PENDING", "PENDING"), "Withdrawn by student in demo data."),
        ]
        applications = {}
        for email, drive_title, status, stage_values, remarks in application_specs:
            app, _ = Application.objects.update_or_create(
                student=students[email], placement_drive=drives[drive_title],
                defaults={"status": status, "remarks": remarks},
            )
            result, _ = Result.objects.update_or_create(
                application=app,
                defaults={
                    "test": stage_values[0], "gd": stage_values[1],
                    "technical_interview": stage_values[2], "hr_interview": stage_values[3],
                },
            )
            applications[(email, drive_title)] = app

        # On-campus placement history only; every record is tied to a selected drive.
        for email, drive_title, role_title, package, days_ago in [
            ("student01@placify.local", "TCS — Graduate Trainee (Closed)", "Graduate Trainee", "4.20", 4),
        ]:
            PlacementHistory.objects.update_or_create(
                student=students[email], placement_drive=drives[drive_title],
                defaults={
                    "company": drives[drive_title].company, "job_role": role_title,
                    "package": Decimal(package), "placement_date": (now - timedelta(days=days_ago)).date(),
                    "placement_type": PlacementType.ON_CAMPUS,
                    "status": PlacementHistoryStatus.PLACED,
                    "remarks": "Demonstration placement record. Not a real student outcome.",
                    "created_by": admin,
                },
            )

        # Public/global, college-targeted, drive-targeted and draft examples.
        self._announcement(
            "PLACIFY demo environment is ready",
            "This is demonstration content. Use the seeded student accounts to explore drive eligibility, applications and results.",
            AnnouncementAudience.GLOBAL, AnnouncementStatus.PUBLISHED,
        )
        ann = self._announcement(
            "CEM placement orientation",
            "Placement orientation for final-year students: review your profile, verify your resume and check each drive's deadline.",
            AnnouncementAudience.COLLEGE, AnnouncementStatus.PUBLISHED,
        )
        ann.colleges.set([cem])
        ann = self._announcement(
            "TCS recruitment update",
            "Shortlisted applicants should monitor their application status and check the recruiter instructions.",
            AnnouncementAudience.DRIVE, AnnouncementStatus.PUBLISHED,
            drive=drives["TCS — Assistant System Engineer"], drive_date=(now + timedelta(days=12)).date(),
        )
        ann = self._announcement(
            "Draft: placement committee review",
            "This draft should not appear in public student-facing announcement lists.",
            AnnouncementAudience.GLOBAL, AnnouncementStatus.DRAFT,
        )
        targeted = self._announcement(
            "Personal profile reminder",
            "Please ensure your contact details and skills are current before applying.",
            AnnouncementAudience.STUDENT, AnnouncementStatus.PUBLISHED,
        )
        targeted.students.set([students["student02@placify.local"]])

        materials = [
            ("Aptitude practice set", "Quantitative aptitude and logical reasoning practice for campus assessments.", "Aptitude", "https://www.indiabix.com/"),
            ("Python interview revision", "Review Python collections, functions, exceptions, OOP and common coding patterns.", "Programming", "https://docs.python.org/3/tutorial/"),
            ("SQL interview practice", "Practice joins, aggregation, subqueries and window functions.", "Database", "https://www.postgresql.org/docs/"),
            ("Resume and interview checklist", "A concise checklist for preparing a clear, role-relevant resume and interview examples.", "Career Preparation", "https://www.ncs.gov.in/"),
            ("TCS drive preparation", "Preparation resource associated with the seeded TCS drive.", "Company Preparation", "https://www.tcs.com/careers"),
            ("Draft: internal placement notes", "Unpublished sample material for testing publication filters.", "Internal", "https://example.com/placify-draft"),
        ]
        for title, description, category, url in materials:
            StudyMaterial.objects.update_or_create(
                title=title,
                defaults={
                    "description": description, "category": category,
                    "external_url": url, "drive_link": url,
                    "uploaded_by": admin,
                    "company": companies["Tata Consultancy Services"] if "TCS" in title else None,
                    "placement_drive": drives["TCS — Assistant System Engineer"] if "TCS" in title else None,
                    "is_published": not title.startswith("Draft:"),
                },
            )

        self._seed_gallery(companies)
        self.stdout.write(self.style.SUCCESS("PLACIFY demo seed completed (safe to rerun)."))
        self.stdout.write("Demo logins (local development only):")
        self.stdout.write(f"  Admin:     {admin.email} / {os.getenv('SEED_ADMIN_PASSWORD', 'AdminPass123!')}")
        self.stdout.write(f"  Recruiter: {recruiter.email} / {os.getenv('SEED_RECRUITER_PASSWORD', 'RecruiterPass123!')}")
        self.stdout.write("  Student 1: student01@placify.local / " + os.getenv("SEED_STUDENT_PASSWORD", "StudentPass123!"))
        self.stdout.write("  Student 2: student02@placify.local / " + os.getenv("SEED_STUDENT_PASSWORD", "StudentPass123!"))
        self.stdout.write("Seeded: 3 colleges, 6 departments, 20 skills, 6 companies, 8 drives, 2 students, 7 applications, 7 stage-result records, announcements, study materials and gallery entries.")
        self.stdout.write(self.style.WARNING("All listed people, outcomes and contact details are synthetic demo data."))

    def _user(self, email, password, name, role, staff=False, superuser=False):
        user, _ = User.objects.get_or_create(email=email, defaults={"name": name, "role": role})
        user.name = name
        user.role = role
        user.is_staff = staff
        user.is_superuser = superuser
        user.is_active = True
        user.set_password(password)
        user.save()
        return user

    def _college(self, name, short_name, location):
        college, _ = College.objects.update_or_create(
            name=name, defaults={"short_name": short_name, "location": location, "is_active": True}
        )
        return college

    def _announcement(self, title, content, audience, status, drive=None, drive_date=None):
        published_at = timezone.now() if status == AnnouncementStatus.PUBLISHED else None
        announcement, _ = Announcement.objects.update_or_create(
            title=title,
            defaults={
                "content": content, "audience": audience, "status": status,
                "placement_drive": drive, "drive_date": drive_date,
                "published_at": published_at,
            },
        )
        return announcement

    def _seed_gallery(self, companies):
        # Generate real, local PNG assets so the gallery renders without remote dependencies.
        gallery_rows = [
            ("Placement Drive Orientation", "Students attending a campus placement orientation.", None),
            ("Recruitment Day", "Campus recruitment day demonstration image.", companies["Tata Consultancy Services"]),
            ("Career Preparation Workshop", "Resume and interview preparation workshop.", None),
        ]
        for index, (title, description, company) in enumerate(gallery_rows, start=1):
            image = self._placeholder_png(title, index)
            entry, created = Gallery.objects.get_or_create(title=title)
            entry.description = description
            entry.company = company
            entry.year = timezone.now().year
            entry.display_order = index
            entry.is_published = True
            # Always ensure a valid local image exists; do not overwrite a manually uploaded image.
            if created or not entry.image or not entry.image.storage.exists(entry.image.name):
                entry.image.save(f"placify-demo-{index}.png", image, save=False)
            entry.save()

    def _placeholder_png(self, title, index):
        image = Image.new("RGB", (1200, 675), color=(20 + index * 10, 45, 75 + index * 8))
        draw = ImageDraw.Draw(image)
        draw.rectangle((48, 48, 1152, 627), outline=(95, 180, 220), width=4)
        draw.text((85, 240), "PLACIFY", fill=(255, 255, 255))
        draw.text((85, 300), title, fill=(220, 235, 245))
        draw.text((85, 355), "DEMO CONTENT • NOT A REAL EVENT PHOTO", fill=(180, 205, 220))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return ContentFile(buffer.getvalue())
