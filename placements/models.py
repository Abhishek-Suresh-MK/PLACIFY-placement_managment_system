from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ActiveNameModel(models.Model):
    name = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["name"]


class College(ActiveNameModel):
    short_name = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return self.name


class Department(ActiveNameModel):
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class Skill(ActiveNameModel):
    class Category(models.TextChoices):
        PROGRAMMING = "PROGRAMMING", "Programming"
        FRAMEWORK = "FRAMEWORK", "Framework"
        DATABASE = "DATABASE", "Database"
        CLOUD = "CLOUD", "Cloud"
        DEVOPS = "DEVOPS", "DevOps"
        AI_ML = "AI_ML", "AI / ML"
        FRONTEND = "FRONTEND", "Frontend"
        TOOL = "TOOL", "Tool"
        OTHER = "OTHER", "Other"

    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name"], name="unique_skill_name"),
        ]

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="companies/logos/", blank=True, null=True)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StudentProfile(models.Model):
    class CurrentYear(models.IntegerChoices):
        FIRST = 1, "1st Year"
        SECOND = 2, "2nd Year"
        THIRD = 3, "3rd Year"
        FOURTH = 4, "4th Year"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    photo = models.ImageField(upload_to="students/photos/%Y/%m/", blank=True, null=True)
    phone = models.CharField(max_length=20)
    college = models.ForeignKey(College, on_delete=models.PROTECT, related_name="student_profiles")
    university_no = models.CharField(max_length=100, verbose_name="University Register No")
    address = models.TextField()
    age = models.PositiveSmallIntegerField(validators=[MinValueValidator(15), MaxValueValidator(100)])
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="student_profiles")
    current_year = models.PositiveSmallIntegerField(choices=CurrentYear.choices)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(10)])
    backlogs = models.PositiveSmallIntegerField(default=0)
    passout_year = models.PositiveIntegerField()
    skills = models.ManyToManyField(Skill, blank=True, related_name="students")
    resume = models.FileField(upload_to="resumes/%Y/%m/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["college", "university_no"], name="unique_college_university_no"),
        ]

    def __str__(self):
        return f"{self.user.name} <{self.user.email}>"


class RecruiterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recruiter_profile")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="recruiters")
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.name} — {self.company.name}"


class PlacementDriveStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    OPEN = "OPEN", "Open"
    CLOSED = "CLOSED", "Closed"
    CANCELLED = "CANCELLED", "Cancelled"
    ARCHIVED = "ARCHIVED", "Archived"


class EmploymentType(models.TextChoices):
    FULL_TIME = "FULL_TIME", "Full-time"
    PART_TIME = "PART_TIME", "Part-time"
    INTERNSHIP = "INTERNSHIP", "Internship"
    CONTRACT = "CONTRACT", "Contract"


class PlacementDrive(models.Model):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="drives")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    job_role = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    salary_package = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Package in LPA")
    eligibility_description = models.TextField(blank=True)
    minimum_cgpa = models.DecimalField(max_digits=4, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(10)])
    maximum_backlogs = models.PositiveSmallIntegerField(default=0)
    allowed_colleges = models.ManyToManyField(College, blank=True, related_name="placement_drives")
    allowed_departments = models.ManyToManyField(Department, blank=True, related_name="placement_drives")
    allowed_graduation_years = models.JSONField(default=list, blank=True)
    required_skills = models.ManyToManyField(Skill, blank=True, related_name="placement_drives")
    recruiters = models.ManyToManyField(RecruiterProfile, blank=True, related_name="placement_drives")
    application_start = models.DateTimeField()
    application_deadline = models.DateTimeField()
    drive_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=PlacementDriveStatus.choices, default=PlacementDriveStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-application_deadline"]
        constraints = [
            models.CheckConstraint(condition=models.Q(application_deadline__gte=models.F("application_start")), name="drive_deadline_after_start"),
        ]

    def __str__(self):
        return f"{self.company.name} — {self.title}"


class ApplicationStatus(models.TextChoices):
    APPLIED = "APPLIED", "Applied"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    SHORTLISTED = "SHORTLISTED", "Shortlisted"
    ASSESSMENT = "ASSESSMENT", "Assessment"
    INTERVIEW = "INTERVIEW", "Interview"
    SELECTED = "SELECTED", "Selected"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class Application(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.PROTECT, related_name="applications")
    placement_drive = models.ForeignKey(PlacementDrive, on_delete=models.PROTECT, related_name="applications")
    status = models.CharField(max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.APPLIED)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-applied_at"]
        constraints = [
            models.UniqueConstraint(fields=["student", "placement_drive"], name="unique_student_drive_application"),
        ]

    def __str__(self):
        return f"{self.student.user.name} — {self.placement_drive}"


class StageStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PASSED = "PASSED", "Passed"
    FAILED = "FAILED", "Failed"


class Result(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name="result")
    test = models.CharField(max_length=10, choices=StageStatus.choices, default=StageStatus.PENDING)
    gd = models.CharField(max_length=10, choices=StageStatus.choices, default=StageStatus.PENDING, verbose_name="Group Discussion")
    technical_interview = models.CharField(max_length=10, choices=StageStatus.choices, default=StageStatus.PENDING)
    hr_interview = models.CharField(max_length=10, choices=StageStatus.choices, default=StageStatus.PENDING)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    @property
    def student(self):
        return self.application.student

    def __str__(self):
        return f"Result — {self.application.student.user.name} — {self.application.placement_drive.title}"


class PlacementType(models.TextChoices):
    ON_CAMPUS = "ON_CAMPUS", "On-campus"
    OFF_CAMPUS = "OFF_CAMPUS", "Off-campus"


class PlacementHistoryStatus(models.TextChoices):
    PLACED = "PLACED", "Placed"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    CANCELLED = "CANCELLED", "Cancelled"


class PlacementHistory(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name="placement_history")
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="placement_history")
    placement_drive = models.ForeignKey(PlacementDrive, null=True, blank=True, on_delete=models.PROTECT, related_name="placement_history")
    job_role = models.CharField(max_length=255)
    package = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="Package in LPA")
    placement_date = models.DateField()
    placement_type = models.CharField(max_length=20, choices=PlacementType.choices, default=PlacementType.ON_CAMPUS)
    status = models.CharField(max_length=20, choices=PlacementHistoryStatus.choices, default=PlacementHistoryStatus.PLACED)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_placement_history")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-placement_date"]
        verbose_name_plural = "Placement history"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.placement_type == PlacementType.ON_CAMPUS and not self.placement_drive_id:
            raise ValidationError({"placement_drive": "An on-campus placement must be linked to a placement drive."})
        if self.placement_type == PlacementType.OFF_CAMPUS and self.placement_drive_id:
            raise ValidationError({"placement_drive": "Off-campus placements should not be linked to a campus drive."})

    def __str__(self):
        return f"{self.student.user.name} — {self.company.name} — {self.job_role}"


class AnnouncementStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"


class AnnouncementAudience(models.TextChoices):
    GLOBAL = "GLOBAL", "Everyone"
    COLLEGE = "COLLEGE", "Selected colleges"
    DRIVE = "DRIVE", "Placement drive applicants"
    STUDENT = "STUDENT", "Specific students"


class Announcement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    drive_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=AnnouncementStatus.choices, default=AnnouncementStatus.DRAFT)
    audience = models.CharField(max_length=20, choices=AnnouncementAudience.choices, default=AnnouncementAudience.GLOBAL)
    colleges = models.ManyToManyField(College, blank=True, related_name="announcements")
    placement_drive = models.ForeignKey(PlacementDrive, null=True, blank=True, on_delete=models.PROTECT, related_name="announcements")
    students = models.ManyToManyField(StudentProfile, blank=True, related_name="targeted_announcements")
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class StudyMaterial(models.Model):
    title = models.CharField(max_length=255, default="Study Material")
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    file = models.FileField(upload_to="materials/%Y/%m/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_materials")
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name="study_materials")
    placement_drive = models.ForeignKey(PlacementDrive, null=True, blank=True, on_delete=models.SET_NULL, related_name="study_materials")
    drive_link = models.URLField(blank=True, verbose_name="External resource link")
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Study materials"

    def __str__(self):
        return self.title


class Gallery(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="gallery/%Y/%m/")
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name="gallery_entries")
    year = models.PositiveIntegerField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return self.title
