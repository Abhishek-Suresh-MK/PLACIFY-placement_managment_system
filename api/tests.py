import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Role, User
from placements.models import College, Department, Skill, Company, RecruiterProfile, StudentProfile, PlacementDrive, Application, Result


class APIBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.college = College.objects.create(name="CEM")
        self.department = Department.objects.create(name="Computer Science and Engineering", code="CSE")
        self.skill = Skill.objects.create(name="Python", category="PROGRAMMING")
        self.company = Company.objects.create(name="API Company")
        self.student_user = User.objects.create_user(email="student@example.com", name="Student", password="Pass1234!abc", role=Role.STUDENT)
        self.student = StudentProfile.objects.create(user=self.student_user, phone="1", college=self.college, university_no="U1", address="A", age=21, department=self.department, current_year=4, cgpa=8, backlogs=0, passout_year=2026)
        self.student.skills.add(self.skill)
        self.recruiter_user = User.objects.create_user(email="recruiter@example.com", name="Recruiter", password="Pass1234!abc", role=Role.RECRUITER)
        self.recruiter = RecruiterProfile.objects.create(user=self.recruiter_user, company=self.company)
        self.admin = User.objects.create_superuser(email="admin@example.com", password="Pass1234!abc", name="Admin")


class APIArchitectureTests(APIBase):
    def test_student_serializer_has_email_not_username(self):
        self.client.force_authenticate(self.student_user)
        response = self.client.get("/api/students/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.data["results"][0])
        self.assertNotIn("username", response.data["results"][0])

    def test_recruiter_cannot_modify_student_profile(self):
        self.client.force_authenticate(self.recruiter_user)
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"cgpa": "9.00"}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_recruiter_can_only_update_application_status_and_remarks(self):
        start = timezone.now() - datetime.timedelta(hours=1)
        drive = PlacementDrive.objects.create(company=self.company, title="API Drive", job_role="SWE", application_start=start, application_deadline=start + datetime.timedelta(days=1), status="OPEN")
        drive.recruiters.add(self.recruiter)
        app = Application.objects.create(student=self.student, placement_drive=drive)
        Result.objects.create(application=app)
        self.client.force_authenticate(self.recruiter_user)
        response = self.client.patch(f"/api/applications/{app.pk}/", {"status": "SHORTLISTED", "remarks": "Good"}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.client.patch(f"/api/applications/{app.pk}/", {"student": self.student.pk}, format="json")
        self.assertEqual(response.status_code, 403)

    def test_admin_can_manage_results(self):
        start = timezone.now()
        drive = PlacementDrive.objects.create(company=self.company, title="API Drive", job_role="SWE", application_start=start, application_deadline=start + datetime.timedelta(days=1))
        app = Application.objects.create(student=self.student, placement_drive=drive)
        result = Result.objects.create(application=app)
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"/api/results/{result.pk}/", {"test": "PASSED"}, format="json")
        self.assertEqual(response.status_code, 200)
