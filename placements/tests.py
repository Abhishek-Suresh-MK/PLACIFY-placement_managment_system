import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Role, User
from .models import (
    Announcement, AnnouncementAudience, AnnouncementStatus, Application, ApplicationStatus,
    College, Company, Department, PlacementDrive, PlacementHistory, PlacementType, RecruiterProfile,
    Result, Skill, StageStatus, StudentProfile,
)


def make_base():
    college = College.objects.create(name="College of Engineering Munnar", short_name="CEM")
    department = Department.objects.create(name="Computer Science and Engineering", code="CSE")
    python = Skill.objects.create(name="Python", category="PROGRAMMING")
    django = Skill.objects.create(name="Django", category="FRAMEWORK")
    company = Company.objects.create(name="Example Technologies")
    return college, department, python, django, company


def make_student(email="student@example.com", name="Student", cgpa="8.00", skills=()):
    college, department, python, django, company = make_base()
    user = User.objects.create_user(email=email, name=name, password="Pass1234!abc", role=Role.STUDENT)
    profile = StudentProfile.objects.create(user=user, phone="9999999999", college=college, university_no=f"U-{user.pk}", address="Addr", age=21, department=department, current_year=4, cgpa=cgpa, backlogs=0, passout_year=2026)
    profile.skills.set(skills)
    return profile, company, python, django


class RegistrationTests(TestCase):
    def setUp(self):
        self.college, self.department, self.python, _, _ = make_base()

    def test_student_registration_uses_master_data(self):
        response = self.client.post(reverse("accounts:register"), {
            "name": "New Student", "email": "new@example.com", "password": "Pass1234!abc", "password2": "Pass1234!abc",
            "phone": "9999999999", "college": self.college.pk, "university_no": "U1", "address": "A", "age": 21,
            "department": self.department.pk, "current_year": 4, "cgpa": "8.50", "backlogs": 0, "passout_year": 2026,
            "skills": [self.python.pk],
        })
        self.assertRedirects(response, reverse("placements:index") + "?registered=1")
        profile = StudentProfile.objects.get(user__email="new@example.com")
        self.assertEqual(profile.college, self.college)
        self.assertEqual(profile.department, self.department)
        self.assertEqual(list(profile.skills.values_list("name", flat=True)), ["Python"])


class StudentPlacementFlowTests(TestCase):
    def setUp(self):
        self.college, self.department, self.python, self.django, self.company = make_base()
        self.user = User.objects.create_user(email="student@example.com", name="Student", password="Pass1234!abc", role=Role.STUDENT)
        self.profile = StudentProfile.objects.create(user=self.user, phone="1", college=self.college, university_no="U1", address="A", age=21, department=self.department, current_year=4, cgpa="8.50", backlogs=0, passout_year=2026)
        self.profile.skills.set([self.python, self.django])
        self.client.login(email=self.user.email, password="Pass1234!abc")
        start = timezone.now() - datetime.timedelta(hours=1)
        self.drive = PlacementDrive.objects.create(company=self.company, title="Backend Hiring", job_role="Python Developer", application_start=start, application_deadline=start + datetime.timedelta(days=5), status="OPEN", minimum_cgpa="7.00", maximum_backlogs=0)
        self.drive.allowed_colleges.add(self.college)
        self.drive.allowed_departments.add(self.department)
        self.drive.required_skills.add(self.python)

    def test_student_can_apply_and_result_is_created(self):
        response = self.client.post(reverse("placements:apply_drive", args=[self.drive.pk]))
        self.assertRedirects(response, reverse("placements:applications"))
        app = Application.objects.get(student=self.profile, placement_drive=self.drive)
        self.assertEqual(app.status, ApplicationStatus.APPLIED)
        self.assertTrue(Result.objects.filter(application=app).exists())

    def test_student_cannot_apply_if_missing_skill(self):
        other = Skill.objects.create(name="AWS", category="CLOUD")
        self.drive.required_skills.add(other)
        response = self.client.post(reverse("placements:apply_drive", args=[self.drive.pk]))
        self.assertRedirects(response, reverse("placements:drive_detail", args=[self.drive.pk]))
        self.assertFalse(Application.objects.filter(student=self.profile, placement_drive=self.drive).exists())


class RecruiterWorkflowTests(TestCase):
    def setUp(self):
        self.college, self.department, self.python, self.django, self.company = make_base()
        student_user = User.objects.create_user(email="student@example.com", name="Candidate", password="Pass1234!abc", role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=student_user, phone="1", college=self.college, university_no="U1", address="A", age=21, department=self.department, current_year=4, cgpa="9.20", backlogs=0, passout_year=2026)
        self.student.skills.set([self.python, self.django])
        recruiter_user = User.objects.create_user(email="recruiter@example.com", name="Recruiter", password="Pass1234!abc", role=Role.RECRUITER)
        self.recruiter = RecruiterProfile.objects.create(user=recruiter_user, company=self.company)
        start = timezone.now() - datetime.timedelta(hours=1)
        self.drive = PlacementDrive.objects.create(company=self.company, title="Python Hiring", job_role="Developer", application_start=start, application_deadline=start + datetime.timedelta(days=5), status="OPEN")
        self.drive.recruiters.add(self.recruiter)
        app = Application.objects.create(student=self.student, placement_drive=self.drive)
        Result.objects.create(application=app)
        self.app = app
        self.client.login(email="recruiter@example.com", password="Pass1234!abc")

    def test_recruiter_sees_assigned_application(self):
        response = self.client.get(reverse("placements:recruiter_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Candidate")

    def test_recruiter_can_filter_multiple_skills(self):
        response = self.client.get(reverse("placements:recruiter_dashboard"), {"skills": [str(self.python.pk), str(self.django.pk)], "skill_mode": "all"})
        self.assertContains(response, "Candidate")

    def test_recruiter_can_update_status_but_not_result(self):
        response = self.client.post(reverse("placements:recruiter_update_application", args=[self.app.pk]), {"status": "SHORTLISTED", "remarks": "Good profile"})
        self.assertRedirects(response, reverse("placements:recruiter_dashboard"))
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, ApplicationStatus.SHORTLISTED)
        result = self.app.result
        response = self.client.post(reverse("placements:admin_result_update", args=[self.app.pk]), {"test": "PASSED", "gd": "PENDING", "technical_interview": "PENDING", "hr_interview": "PENDING"})
        self.assertEqual(response.status_code, 302)
        result.refresh_from_db()
        self.assertEqual(result.test, StageStatus.PENDING)


class AdminWorkflowTests(TestCase):
    def setUp(self):
        self.college, self.department, self.python, _, self.company = make_base()
        self.admin = User.objects.create_superuser(email="admin@example.com", password="Pass1234!abc", name="Admin")
        self.student_user = User.objects.create_user(email="student@example.com", name="Student", password="Pass1234!abc", role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=self.student_user, phone="1", college=self.college, university_no="U1", address="A", age=21, department=self.department, current_year=4, cgpa="8.0", backlogs=0, passout_year=2026)
        self.client.login(email="admin@example.com", password="Pass1234!abc")

    def test_admin_dashboard_is_useful(self):
        response = self.client.get(reverse("placements:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Master data")
        self.assertContains(response, "Applications & Results")

    def test_admin_can_create_off_campus_history(self):
        response = self.client.post(reverse("placements:admin_resource", args=["history"]), {
            "student": self.student.pk, "company": self.company.pk, "placement_drive": "", "job_role": "Software Engineer",
            "package": "12.00", "placement_date": "2026-09-01", "placement_type": "OFF_CAMPUS", "status": "PLACED", "remarks": "External offer",
        })
        self.assertRedirects(response, reverse("placements:admin_resource", args=["history"]))
        record = PlacementHistory.objects.get(student=self.student)
        self.assertEqual(record.placement_type, PlacementType.OFF_CAMPUS)
        self.assertIsNone(record.placement_drive)

    def test_admin_can_edit_results(self):
        drive = PlacementDrive.objects.create(company=self.company, title="Drive", job_role="SWE", application_start=timezone.now(), application_deadline=timezone.now() + datetime.timedelta(days=1))
        app = Application.objects.create(student=self.student, placement_drive=drive)
        Result.objects.create(application=app)
        response = self.client.post(reverse("placements:admin_result_update", args=[app.pk]), {"test": "PASSED", "gd": "PENDING", "technical_interview": "PENDING", "hr_interview": "FAILED"})
        self.assertRedirects(response, reverse("placements:admin_applications"))
        result = app.result
        result.refresh_from_db()
        self.assertEqual(result.test, StageStatus.PASSED)
        self.assertEqual(result.hr_interview, StageStatus.FAILED)


class AnnouncementTargetingTests(TestCase):
    def setUp(self):
        self.college, self.department, _, _, _ = make_base()
        user = User.objects.create_user(email="student@example.com", name="Student", password="Pass1234!abc", role=Role.STUDENT)
        self.profile = StudentProfile.objects.create(user=user, phone="1", college=self.college, university_no="U1", address="A", age=21, department=self.department, current_year=4, cgpa=8, backlogs=0, passout_year=2026)
        self.client.login(email=user.email, password="Pass1234!abc")

    def test_college_announcement_is_visible(self):
        announcement = Announcement.objects.create(title="College Notice", content="Only CEM", status=AnnouncementStatus.PUBLISHED, audience=AnnouncementAudience.COLLEGE)
        announcement.colleges.add(self.college)
        response = self.client.get(reverse("placements:dashboard"))
        self.assertContains(response, "College Notice")
