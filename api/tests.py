import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

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
        # This candidate has not applied to a drive assigned to this recruiter,
        # so the object is intentionally not discoverable (404 rather than leak existence).
        self.client.force_authenticate(self.recruiter_user)
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"cgpa": "9.00"}, format="json")
        self.assertEqual(response.status_code, 404)

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


class JWTAuthorizationMatrixTests(APIBase):
    def setUp(self):
        super().setUp()
        self.other_college = College.objects.create(name="Other College")
        self.other_user = User.objects.create_user(email="other@example.com", name="Other Candidate", password="Pass1234!abc", role=Role.STUDENT)
        self.other_student = StudentProfile.objects.create(user=self.other_user, phone="2", college=self.other_college, university_no="U2", address="Private", age=21, department=self.student.department, current_year=4, cgpa=9, backlogs=0, passout_year=2026)
        self.other_company = Company.objects.create(name="Other Company")
        self.other_recruiter_user = User.objects.create_user(email="other-recruiter@example.com", name="Other Recruiter", password="Pass1234!abc", role=Role.RECRUITER)
        self.other_recruiter = RecruiterProfile.objects.create(user=self.other_recruiter_user, company=self.other_company)
        now = timezone.now()
        self.drive = PlacementDrive.objects.create(company=self.company, title="Assigned Drive", job_role="Developer", application_start=now-datetime.timedelta(hours=1), application_deadline=now+datetime.timedelta(days=1), status="OPEN")
        self.drive.recruiters.add(self.recruiter)
        self.assigned_app = Application.objects.create(student=self.student, placement_drive=self.drive)
        Result.objects.get_or_create(application=self.assigned_app)
        self.other_drive = PlacementDrive.objects.create(company=self.other_company, title="Unassigned Drive", job_role="Developer", application_start=now-datetime.timedelta(hours=1), application_deadline=now+datetime.timedelta(days=1), status="OPEN")
        self.other_drive.recruiters.add(self.other_recruiter)
        self.other_app = Application.objects.create(student=self.other_student, placement_drive=self.other_drive)
        Result.objects.get_or_create(application=self.other_app)

    def obtain_tokens(self, email, password="Pass1234!abc"):
        response = self.client.post("/api/auth/token/", {"email": email, "password": password}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        return response.data["access"], response.data["refresh"]

    def authenticate(self, email):
        access, refresh = self.obtain_tokens(email)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return access, refresh

    def test_unauthenticated_endpoints_are_denied(self):
        for url in ("/api/users/", "/api/students/", "/api/applications/", "/api/results/"):
            with self.subTest(url=url):
                self.client.credentials()
                self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_public_registration_cannot_assign_privileged_role(self):
        # The public registration form has no role field and always creates students.
        response = self.client.post("/accounts/register/", {
            "name": "Role Attack", "email": "attack@example.com", "password": "Pass1234!abc", "password2": "Pass1234!abc",
            "role": "admin", "phone": "9999999999", "college": self.college.pk, "university_no": "ATTACK1", "address": "A", "age": 21,
            "department": self.student.department_id, "current_year": 4, "cgpa": "9.50", "backlogs": 0, "passout_year": 2026,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(User.objects.get(email="attack@example.com").role, Role.STUDENT)
        self.assertFalse(User.objects.get(email="attack@example.com").is_staff)
        self.assertFalse(User.objects.get(email="attack@example.com").is_superuser)

    def test_student_cannot_read_or_mutate_another_students_profile(self):
        self.authenticate(self.student_user.email)
        self.assertEqual(self.client.get(f"/api/students/{self.other_student.pk}/").status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"cgpa": "10.00", "backlogs": 0, "role": "admin"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.student.refresh_from_db()
        self.assertEqual(str(self.student.cgpa), "8.00")
        self.assertEqual(self.student.user.role, Role.STUDENT)

    def test_recruiter_only_sees_assigned_drive_candidates_and_minimum_fields(self):
        self.authenticate(self.recruiter_user.email)
        response = self.client.get("/api/students/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {item["id"] for item in response.data["results"]}
        self.assertEqual(returned_ids, {self.student.pk})
        self.assertNotIn("address", response.data["results"][0])
        self.assertNotIn("university_no", response.data["results"][0])
        search = self.client.get("/api/recruiter/search/")
        self.assertEqual(search.status_code, status.HTTP_200_OK)
        self.assertEqual({item["id"] for item in search.data["results"]}, {self.student.pk})

    def test_recruiter_cannot_access_unassigned_drive_or_cross_account_application(self):
        self.authenticate(self.recruiter_user.email)
        self.assertEqual(self.client.get(f"/api/placement-drives/{self.other_drive.pk}/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(f"/api/applications/{self.other_app.pk}/").status_code, status.HTTP_404_NOT_FOUND)
        response = self.client.patch(f"/api/applications/{self.assigned_app.pk}/", {"student": self.other_student.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_refresh_rotation_and_logout_revokes_refresh_token(self):
        access, refresh = self.obtain_tokens(self.student_user.email)
        refreshed = self.client.post("/api/auth/token/refresh/", {"refresh": refresh}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK, refreshed.data)
        self.assertIn("access", refreshed.data)
        rotated_refresh = refreshed.data.get("refresh")
        self.assertTrue(rotated_refresh)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
        logout = self.client.post("/api/auth/logout/", {"refresh": rotated_refresh}, format="json")
        self.assertEqual(logout.status_code, status.HTTP_205_RESET_CONTENT, logout.data)
        retry = self.client.post("/api/auth/token/refresh/", {"refresh": rotated_refresh}, format="json")
        self.assertEqual(retry.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_cannot_be_revoked_by_another_account(self):
        _, refresh = self.obtain_tokens(self.student_user.email)
        self.authenticate(self.other_user.email)
        response = self.client.post("/api/auth/logout/", {"refresh": refresh}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_application_admin_is_not_django_superuser(self):
        app_admin = User.objects.create_user(email="app-admin@example.com", name="Application Admin", password="Pass1234!abc", role=Role.ADMIN, is_staff=True, is_superuser=True)
        self.assertFalse(app_admin.is_staff)
        self.assertFalse(app_admin.is_superuser)
        self.assertTrue(app_admin.is_admin_role)
        self.authenticate(app_admin.email)
        self.assertEqual(self.client.get("/api/users/").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get("/django-admin/").status_code, status.HTTP_302_FOUND)
