from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.models import Role, User
from .models import (
    Announcement, AnnouncementAudience, Application, ApplicationStatus, Company, College,
    Department, Gallery, PlacementDrive, PlacementHistory, PlacementHistoryStatus,
    PlacementType, RecruiterProfile, Result, Skill, StudyMaterial, StudentProfile,
)


def validate_upload(file, allowed, max_mb=5):
    if not file:
        return
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"File must be {max_mb} MB or smaller.")
    ext = file.name.lower().rsplit(".", 1)[-1] if "." in file.name else ""
    if ext not in allowed:
        raise ValidationError(f"Allowed file types: {', '.join(sorted(allowed))}.")
    if ext == "pdf":
        pos = file.tell()
        try:
            file.seek(0)
            if file.read(5) != b"%PDF-":
                raise ValidationError("The uploaded file is not a valid PDF.")
        finally:
            file.seek(pos)


class StudentProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=150)
    email = forms.EmailField()

    class Meta:
        model = StudentProfile
        fields = [
            "name", "email", "phone", "photo", "college", "university_no", "address", "age",
            "department", "current_year", "cgpa", "backlogs", "passout_year", "skills", "resume",
        ]
        widgets = {"address": forms.Textarea(attrs={"rows": 4}), "skills": forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["college"].queryset = College.objects.filter(is_active=True).order_by("name")
        self.fields["department"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["skills"].queryset = Skill.objects.filter(is_active=True).order_by("name")
        if self.instance.pk:
            self.fields["name"].initial = self.instance.user.name
            self.fields["email"].initial = self.instance.user.email

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.user_id if self.instance.pk else None).exists():
            raise ValidationError("Another account already uses this email.")
        return value

    def clean_photo(self):
        photo = self.cleaned_data.get("photo")
        validate_upload(photo, {"png", "jpg", "jpeg", "webp"}, 3)
        return photo

    def clean_resume(self):
        f = self.cleaned_data.get("resume")
        validate_upload(f, {"pdf", "doc", "docx"}, 5)
        return f

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.name = self.cleaned_data["name"].strip()
        profile.user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            profile.user.save(update_fields=["name", "email"])
            profile.save()
            self.save_m2m()
        return profile


class RecruiterProfileForm(forms.ModelForm):
    name = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, required=False)

    class Meta:
        model = RecruiterProfile
        fields = ["name", "email", "password", "company", "phone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(is_active=True).order_by("name")
        if self.instance.pk:
            self.fields["name"].initial = self.instance.user.name
            self.fields["email"].initial = self.instance.user.email
            self.fields["password"].help_text = "Leave blank to keep the existing password."
        else:
            self.fields["password"].required = True

    def clean_email(self):
        value = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=value).exclude(pk=self.instance.user_id if self.instance.pk else None).exists():
            raise ValidationError("Another account already uses this email.")
        return value

    def save(self, commit=True):
        profile = super().save(commit=False)
        if profile.pk:
            user = profile.user
        else:
            user = User(email=self.cleaned_data["email"].strip().lower(), name=self.cleaned_data["name"].strip(), role=Role.RECRUITER)
        user.name = self.cleaned_data["name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()
        user.role = Role.RECRUITER
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
            profile.user = user
            profile.save()
        return profile


class PlacementDriveForm(forms.ModelForm):
    allowed_graduation_years = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "2026, 2027, 2028"}),
        help_text="Comma-separated graduating years. Leave blank for any year.",
    )

    class Meta:
        model = PlacementDrive
        fields = [
            "company", "title", "description", "job_role", "location", "employment_type",
            "salary_package", "eligibility_description", "minimum_cgpa", "maximum_backlogs",
            "allowed_colleges", "allowed_departments", "allowed_graduation_years", "required_skills",
            "application_start", "application_deadline", "drive_date", "status", "recruiters",
        ]
        widgets = {
            "application_start": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "application_deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "drive_date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "allowed_colleges": forms.CheckboxSelectMultiple,
            "allowed_departments": forms.CheckboxSelectMultiple,
            "required_skills": forms.CheckboxSelectMultiple,
            "recruiters": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = Company.objects.filter(is_active=True).order_by("name")
        self.fields["allowed_colleges"].queryset = College.objects.filter(is_active=True).order_by("name")
        self.fields["allowed_departments"].queryset = Department.objects.filter(is_active=True).order_by("name")
        self.fields["required_skills"].queryset = Skill.objects.filter(is_active=True).order_by("name")
        self.fields["recruiters"].queryset = RecruiterProfile.objects.select_related("user", "company").filter(user__is_active=True, company__is_active=True).order_by("company__name", "user__name")
        if self.instance.pk:
            self.initial["allowed_graduation_years"] = ", ".join(str(x) for x in (self.instance.allowed_graduation_years or []))

    def clean_allowed_graduation_years(self):
        raw = self.cleaned_data.get("allowed_graduation_years", "")
        if not raw:
            return []
        years = []
        for part in raw.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                year = int(part)
            except ValueError:
                raise ValidationError("Graduation years must be comma-separated numbers.")
            if year < 1950 or year > 2100:
                raise ValidationError("Graduation years must be between 1950 and 2100.")
            if year not in years:
                years.append(year)
        return sorted(years)

    def clean(self):
        cleaned = super().clean()
        start, deadline = cleaned.get("application_start"), cleaned.get("application_deadline")
        if start and deadline and deadline < start:
            raise ValidationError("Application deadline cannot be before application start.")
        company = cleaned.get("company")
        recruiters = cleaned.get("recruiters")
        if company and recruiters:
            wrong_company = recruiters.exclude(company=company).exists()
            if wrong_company:
                raise ValidationError("Every selected recruiter must belong to the drive's company.")
        return cleaned


class ApplicationStatusForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ["status", "remarks"]
        widgets = {"remarks": forms.Textarea(attrs={"rows": 3})}


class ResultEditForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ["test", "gd", "technical_interview", "hr_interview"]


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ["name", "description", "website", "location", "logo", "contact_name", "contact_email", "is_active"]

    def clean_logo(self):
        f = self.cleaned_data.get("logo")
        validate_upload(f, {"png", "jpg", "jpeg", "webp"}, 3)
        return f


class CollegeForm(forms.ModelForm):
    class Meta:
        model = College
        fields = ["name", "short_name", "location", "is_active"]


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "is_active"]


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ["name", "category", "is_active"]


class PlacementHistoryForm(forms.ModelForm):
    class Meta:
        model = PlacementHistory
        fields = ["student", "company", "placement_drive", "job_role", "package", "placement_date", "placement_type", "status", "remarks"]
        widgets = {"placement_date": forms.DateInput(attrs={"type": "date"}), "remarks": forms.Textarea(attrs={"rows": 3})}

    def clean(self):
        cleaned = super().clean()
        placement_type = cleaned.get("placement_type")
        drive = cleaned.get("placement_drive")
        if placement_type == PlacementType.ON_CAMPUS and not drive:
            raise ValidationError("Select a placement drive for an on-campus placement.")
        if placement_type == PlacementType.OFF_CAMPUS and drive:
            raise ValidationError("Off-campus placements should not be linked to a placement drive.")
        if drive and cleaned.get("company") and drive.company_id != cleaned["company"].id:
            raise ValidationError("The selected drive belongs to a different company.")
        return cleaned


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "content", "drive_date", "status", "audience", "colleges", "placement_drive", "students"]
        widgets = {"content": forms.Textarea(attrs={"rows": 5}), "colleges": forms.CheckboxSelectMultiple, "students": forms.CheckboxSelectMultiple}

    def clean(self):
        cleaned = super().clean()
        audience = cleaned.get("audience")
        if audience == AnnouncementAudience.COLLEGE and not cleaned.get("colleges"):
            raise ValidationError("Select at least one college for a college announcement.")
        if audience == AnnouncementAudience.DRIVE and not cleaned.get("placement_drive"):
            raise ValidationError("Select a placement drive for a drive announcement.")
        if audience == AnnouncementAudience.STUDENT and not cleaned.get("students"):
            raise ValidationError("Select at least one student for a targeted announcement.")
        return cleaned


class StudyMaterialForm(forms.ModelForm):
    class Meta:
        model = StudyMaterial
        fields = ["title", "description", "category", "file", "external_url", "company", "placement_drive", "drive_link", "is_published"]

    def clean_file(self):
        f = self.cleaned_data.get("file")
        validate_upload(f, {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "zip"}, 10)
        return f


class GalleryForm(forms.ModelForm):
    class Meta:
        model = Gallery
        fields = ["title", "description", "image", "company", "year", "display_order", "is_published"]

    def clean_image(self):
        f = self.cleaned_data.get("image")
        validate_upload(f, {"png", "jpg", "jpeg", "webp"}, 5)
        return f
