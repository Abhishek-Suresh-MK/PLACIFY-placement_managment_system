from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from placements.models import College, Department, Skill, StudentProfile
from .models import User


class PlacifyPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"placeholder": "Enter your email", "autocomplete": "email"}))


class RegistrationForm(forms.Form):
    name = forms.CharField(max_length=150, label="Full Name")
    email = forms.EmailField(label="Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    phone = forms.CharField(max_length=20, label="Phone", widget=forms.TextInput(attrs={"type": "tel"}))
    photo = forms.ImageField(required=False, label="Photo")
    college = forms.ModelChoiceField(queryset=College.objects.none(), label="College")
    university_no = forms.CharField(max_length=100, label="University Register No")
    address = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    age = forms.IntegerField(min_value=15, max_value=100)
    department = forms.ModelChoiceField(queryset=Department.objects.none(), label="Department")
    current_year = forms.ChoiceField(choices=StudentProfile.CurrentYear.choices, label="Current Year")
    cgpa = forms.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10)
    backlogs = forms.IntegerField(min_value=0, initial=0)
    passout_year = forms.IntegerField(min_value=1950, max_value=2100)
    skills = forms.ModelMultipleChoiceField(queryset=Skill.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)
    resume = forms.FileField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["college"].queryset = College.objects.filter(is_active=True).order_by("name")
        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["skills"].queryset = Skill.objects.filter(is_active=True).order_by("name")

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise ValidationError("An account with this email already exists.")
        return value

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        if photo and photo.size > 3 * 1024 * 1024:
            raise ValidationError("Photo must be 3 MB or smaller.")
        return photo

    def clean_resume(self):
        f = self.cleaned_data.get("resume")
        if f and f.size > 5 * 1024 * 1024:
            raise ValidationError("Resume must be 5 MB or smaller.")
        if f and not f.name.lower().endswith((".pdf", ".doc", ".docx")):
            raise ValidationError("Resume must be PDF, DOC or DOCX.")
        if f and f.name.lower().endswith(".pdf"):
            f.seek(0)
            if f.read(5) != b"%PDF-":
                raise ValidationError("The uploaded PDF is invalid.")
            f.seek(0)
        return f

    def clean_password(self):
        value = self.cleaned_data["password"]
        validate_password(value)
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") and cleaned.get("password2") and cleaned["password"] != cleaned["password2"]:
            self.add_error("password2", "Passwords do not match.")
        return cleaned
