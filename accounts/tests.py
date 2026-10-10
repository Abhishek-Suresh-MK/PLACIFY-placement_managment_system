from django.test import TestCase
from django.urls import reverse

from .models import Role, User


class EmailAuthenticationTests(TestCase):
    def setUp(self):
        self.password = "Pass1234!abc"
        self.user = User.objects.create_user(email="student@example.com", password=self.password, name="Student", role=Role.STUDENT)

    def test_email_is_login_identifier(self):
        self.assertTrue(self.client.login(email="student@example.com", password=self.password))
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.pk))

    def test_email_is_unique(self):
        with self.assertRaises(Exception):
            User.objects.create_user(email="student@example.com", password=self.password, name="Other", role=Role.STUDENT)

    def test_register_page_does_not_show_username(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Username")
