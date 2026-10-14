import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
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


    def test_student_application_api_rejects_inactive_profile(self):
        start = timezone.now() - datetime.timedelta(hours=1)
        drive = PlacementDrive.objects.create(company=self.company, title="API Drive", job_role="SWE", application_start=start, application_deadline=start + datetime.timedelta(days=1), status="OPEN")
        self.student.is_active = False
        self.student.save(update_fields=["is_active"])
        self.client.force_authenticate(self.student_user)
        response = self.client.post("/api/applications/", {"placement_drive": drive.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Application.objects.filter(student=self.student, placement_drive=drive).exists())

    def test_student_can_withdraw_own_application_through_api(self):
        start = timezone.now() - datetime.timedelta(hours=1)
        drive = PlacementDrive.objects.create(company=self.company, title="API Drive", job_role="SWE", application_start=start, application_deadline=start + datetime.timedelta(days=1), status="OPEN")
        app = Application.objects.create(student=self.student, placement_drive=drive)
        Result.objects.create(application=app)
        self.client.force_authenticate(self.student_user)
        response = self.client.post(f"/api/applications/{app.pk}/withdraw/")
        self.assertEqual(response.status_code, 200)
        app.refresh_from_db()
        self.assertEqual(app.status, "WITHDRAWN")

    def test_recruiter_cannot_move_terminal_application_status(self):
        start = timezone.now() - datetime.timedelta(hours=1)
        drive = PlacementDrive.objects.create(company=self.company, title="API Drive", job_role="SWE", application_start=start, application_deadline=start + datetime.timedelta(days=1), status="OPEN")
        drive.recruiters.add(self.recruiter)
        app = Application.objects.create(student=self.student, placement_drive=drive, status="SELECTED")
        Result.objects.create(application=app)
        self.client.force_authenticate(self.recruiter_user)
        response = self.client.patch(f"/api/applications/{app.pk}/", {"status": "SHORTLISTED"}, format="json")
        self.assertEqual(response.status_code, 400)
        app.refresh_from_db()
        self.assertEqual(app.status, "SELECTED")

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



class StudentRecruiterManagementTests(APIBase):
    def test_student_can_edit_permitted_profile_fields_and_shared_skills(self):
        self.client.force_authenticate(self.student_user)
        another_skill = Skill.objects.create(name="Django", category="FRAMEWORK")
        response = self.client.patch(
            f"/api/students/{self.student.pk}/",
            {"phone": "9876543210", "skills": [self.skill.pk, another_skill.pk]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.student.refresh_from_db()
        self.assertEqual(self.student.phone, "9876543210")
        self.assertSetEqual(set(self.student.skills.values_list("id", flat=True)), {self.skill.pk, another_skill.pk})

    def test_admin_profile_validation_rejects_invalid_cgpa_and_graduation_year(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"cgpa": "10.50"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"passout_year": 2099}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"backlogs": -1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_cannot_reassign_profile_to_another_user(self):
        other_user = User.objects.create_user(email="other-student@example.com", name="Other", password="Pass1234!abc", role=Role.STUDENT)
        self.client.force_authenticate(self.student_user)
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"user_id": other_user.pk}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_admin_can_create_student_profile_for_existing_student_account(self):
        new_user = User.objects.create_user(email="new-student@example.com", name="New Student", password="Pass1234!abc", role=Role.STUDENT)
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/students/",
            {
                "user_id": new_user.pk,
                "phone": "9876543210",
                "college": self.college.pk,
                "university_no": "NEW-U-1",
                "address": "Munnar",
                "age": 21,
                "department": self.student.department_id,
                "current_year": 4,
                "cgpa": "8.25",
                "backlogs": 0,
                "passout_year": 2026,
                "skills": [self.skill.pk],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["email"], new_user.email)
        self.assertTrue(StudentProfile.objects.filter(user=new_user).exists())

    def test_recruiter_search_rejects_invalid_filter_values(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get("/api/recruiter/search/?cgpa=not-a-number")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.get("/api/recruiter/search/?skill_mode=neither")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resume_extension_is_validated(self):
        self.client.force_authenticate(self.student_user)
        bad_file = SimpleUploadedFile("resume.exe", b"not a resume", content_type="application/octet-stream")
        response = self.client.patch(f"/api/students/{self.student.pk}/", {"resume": bad_file}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("resume", response.data)

    def test_recruiter_can_edit_only_own_phone(self):
        self.client.force_authenticate(self.recruiter_user)
        response = self.client.patch(f"/api/recruiters/{self.recruiter.pk}/", {"phone": "9999999999"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.recruiter.refresh_from_db()
        self.assertEqual(self.recruiter.phone, "9999999999")
        denied = self.client.patch(f"/api/recruiters/{self.recruiter.pk}/", {"company": self.company.pk}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_recruiter_account_and_profile(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            "/api/recruiters/",
            {
                "email": "new-recruiter@example.com",
                "name": "New Recruiter",
                "password": "UniqueStrongPass!826",
                "company": self.company.pk,
                "phone": "1234567890",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["user"]["email"], "new-recruiter@example.com")
        created_user = User.objects.get(email="new-recruiter@example.com")
        self.assertEqual(created_user.role, Role.RECRUITER)
        self.assertFalse(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)

    def test_company_catalogue_is_readable_but_admin_managed(self):
        self.client.force_authenticate(self.student_user)
        response = self.client.get("/api/companies/?search=API")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        denied = self.client.post("/api/companies/", {"name": "Unauthorized Company"}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.client.force_authenticate(self.admin)
        allowed = self.client.post("/api/companies/", {"name": "Managed Company"}, format="json")
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED, allowed.data)
