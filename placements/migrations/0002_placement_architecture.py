# Generated manually for the Phase 1 architecture additions.
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("placements", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="College",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("short_name", models.CharField(blank=True, max_length=50)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="SkillCatalog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"], "verbose_name": "Skill", "verbose_name_plural": "Skills"},
        ),
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("description", models.TextField(blank=True)),
                ("website", models.URLField(blank=True)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("logo", models.ImageField(blank=True, null=True, upload_to="companies/logos/")),
                ("contact_name", models.CharField(blank=True, max_length=150)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="PlacementDrive",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("job_role", models.CharField(max_length=255)),
                ("location", models.CharField(blank=True, max_length=255)),
                ("employment_type", models.CharField(choices=[("FULL_TIME", "Full-time"), ("PART_TIME", "Part-time"), ("INTERNSHIP", "Internship"), ("CONTRACT", "Contract")], default="FULL_TIME", max_length=20)),
                ("salary_package", models.DecimalField(blank=True, decimal_places=2, help_text="Package in LPA", max_digits=8, null=True)),
                ("eligibility_description", models.TextField(blank=True)),
                ("minimum_cgpa", models.DecimalField(decimal_places=2, default=0, max_digits=4, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(10)])),
                ("maximum_backlogs", models.PositiveSmallIntegerField(default=0)),
                ("allowed_departments", models.JSONField(blank=True, default=list)),
                ("allowed_graduation_years", models.JSONField(blank=True, default=list)),
                ("application_start", models.DateTimeField()),
                ("application_deadline", models.DateTimeField()),
                ("drive_date", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("OPEN", "Open"), ("CLOSED", "Closed"), ("CANCELLED", "Cancelled"), ("ARCHIVED", "Archived")], default="DRAFT", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="drives", to="placements.company")),
                ("allowed_colleges", models.ManyToManyField(blank=True, related_name="placement_drives", to="placements.college")),
                ("required_skills", models.ManyToManyField(blank=True, related_name="placement_drives", to="placements.skillcatalog")),
            ],
            options={"ordering": ["-application_deadline"]},
        ),
        migrations.CreateModel(
            name="Application",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("APPLIED", "Applied"), ("UNDER_REVIEW", "Under review"), ("SHORTLISTED", "Shortlisted"), ("ASSESSMENT", "Assessment"), ("INTERVIEW", "Interview"), ("SELECTED", "Selected"), ("REJECTED", "Rejected"), ("WITHDRAWN", "Withdrawn")], default="APPLIED", max_length=20)),
                ("applied_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("remarks", models.TextField(blank=True)),
                ("placement_drive", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="applications", to="placements.placementdrive")),
                ("student", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="applications", to="placements.studentprofile")),
            ],
            options={"ordering": ["-applied_at"]},
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="college_ref",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="student_profiles", to="placements.college"),
        ),
        migrations.AddConstraint(
            model_name="placementdrive",
            constraint=models.CheckConstraint(condition=models.Q(("application_deadline__gte", models.F("application_start"))), name="drive_deadline_after_start"),
        ),
        migrations.AddConstraint(
            model_name="application",
            constraint=models.UniqueConstraint(fields=("student", "placement_drive"), name="unique_student_drive_application"),
        ),
    ]
