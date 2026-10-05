import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_departments_and_cleanup_recruiters(apps, schema_editor):
    StudentProfile = apps.get_model("placements", "StudentProfile")
    Department = apps.get_model("placements", "Department")
    RecruiterProfile = apps.get_model("placements", "RecruiterProfile")
    Company = apps.get_model("placements", "Company")
    User = apps.get_model("accounts", "User")

    for profile in StudentProfile.objects.all().iterator():
        raw = (getattr(profile, "department", "") or "").strip()
        if raw:
            code = raw.upper().replace(" ", "")[:20]
            dept, _ = Department.objects.get_or_create(code=code, defaults={"name": raw})
            # temporary field is added before this function in the migration
            profile.department_ref_id = dept.pk
            profile.save(update_fields=["department_ref"])

    fallback, _ = Company.objects.get_or_create(name="Unassigned Recruiter Company", defaults={"is_active": True})
    for recruiter in RecruiterProfile.objects.all().iterator():
        if not recruiter.company_id:
            recruiter.company_id = fallback.pk
            recruiter.save(update_fields=["company"])
        User.objects.filter(pk=recruiter.user_id).update(role="recruiter")


def migrate_history_and_material_companies(apps, schema_editor):
    Company = apps.get_model("placements", "Company")
    PlacementHistory = apps.get_model("placements", "PlacementHistory")
    StudyMaterial = apps.get_model("placements", "StudyMaterial")

    for row in PlacementHistory.objects.all().iterator():
        if not row.company_id:
            name = (getattr(row, "company_name", "") or "Unknown Company").strip() or "Unknown Company"
            company, _ = Company.objects.get_or_create(name=name)
            row.company_id = company.pk
        row.placement_type = "ON_CAMPUS" if row.placement_drive_id else "OFF_CAMPUS"
        row.save(update_fields=["company", "placement_type"])

    for row in StudyMaterial.objects.all().iterator():
        name = (getattr(row, "company_name", "") or "").strip()
        if name:
            company, _ = Company.objects.get_or_create(name=name)
            row.company_id = company.pk
            row.save(update_fields=["company"])


class Migration(migrations.Migration):
    dependencies = [
        ("placements", "0003_production_features"),
        ("accounts", "0002_email_only"),
    ]

    operations = [
        migrations.CreateModel(
            name="Department",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150, unique=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, unique=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="studentprofile", name="department_ref",
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.PROTECT, related_name="temporary_student_profiles", to="placements.department"),
        ),
        migrations.RunPython(populate_departments_and_cleanup_recruiters, migrations.RunPython.noop),
        migrations.DeleteModel(name="Skill"),
        migrations.RenameModel(old_name="SkillCatalog", new_name="Skill"),
        migrations.AddField(
            model_name="skill", name="category",
            field=models.CharField(choices=[("PROGRAMMING", "Programming"), ("FRAMEWORK", "Framework"), ("DATABASE", "Database"), ("CLOUD", "Cloud"), ("DEVOPS", "DevOps"), ("AI_ML", "AI / ML"), ("FRONTEND", "Frontend"), ("TOOL", "Tool"), ("OTHER", "Other")], default="OTHER", max_length=20),
        ),
        migrations.AlterField(model_name="skill", name="name", field=models.CharField(max_length=150, unique=True)),
        migrations.RemoveField(model_name="studentprofile", name="college"),
        migrations.RenameField(model_name="studentprofile", old_name="college_ref", new_name="college"),
        migrations.AlterField(
            model_name="studentprofile", name="college",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_profiles", to="placements.college"),
        ),
        migrations.RemoveField(model_name="studentprofile", name="department"),
        migrations.RenameField(model_name="studentprofile", old_name="department_ref", new_name="department"),
        migrations.AlterField(
            model_name="studentprofile", name="department",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="student_profiles", to="placements.department"),
        ),
        migrations.RenameField(model_name="studentprofile", old_name="skills_catalog", new_name="skills"),
        migrations.AddField(
            model_name="studentprofile", name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="students/photos/%Y/%m/"),
        ),
        migrations.AlterField(
            model_name="studentprofile", name="current_year",
            field=models.PositiveSmallIntegerField(choices=[(1, "1st Year"), (2, "2nd Year"), (3, "3rd Year"), (4, "4th Year")]),
        ),
        migrations.AddField(
            model_name="studentprofile", name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddConstraint(
            model_name="studentprofile",
            constraint=models.UniqueConstraint(fields=("college", "university_no"), name="unique_college_university_no"),
        ),
        migrations.RemoveField(model_name="placementdrive", name="allowed_departments"),
        migrations.AddField(
            model_name="placementdrive", name="allowed_departments",
            field=models.ManyToManyField(blank=True, related_name="placement_drives", to="placements.department"),
        ),
        migrations.RemoveField(model_name="placementdrive", name="recruiters"),
        migrations.AddField(
            model_name="placementdrive", name="recruiters",
            field=models.ManyToManyField(blank=True, related_name="placement_drives", to="placements.recruiterprofile"),
        ),
        migrations.AlterField(
            model_name="recruiterprofile", name="company",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="recruiters", to="placements.company"),
        ),
        migrations.AddField(
            model_name="recruiterprofile", name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.DeleteModel(name="Result"),
        migrations.CreateModel(
            name="Result",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("test", models.CharField(choices=[("PENDING", "Pending"), ("PASSED", "Passed"), ("FAILED", "Failed")], default="PENDING", max_length=10)),
                ("gd", models.CharField(choices=[("PENDING", "Pending"), ("PASSED", "Passed"), ("FAILED", "Failed")], default="PENDING", max_length=10, verbose_name="Group Discussion")),
                ("technical_interview", models.CharField(choices=[("PENDING", "Pending"), ("PASSED", "Passed"), ("FAILED", "Failed")], default="PENDING", max_length=10)),
                ("hr_interview", models.CharField(choices=[("PENDING", "Pending"), ("PASSED", "Passed"), ("FAILED", "Failed")], default="PENDING", max_length=10)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("application", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="result", to="placements.application")),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddField(
            model_name="placementhistory", name="placement_type",
            field=models.CharField(choices=[("ON_CAMPUS", "On-campus"), ("OFF_CAMPUS", "Off-campus")], default="ON_CAMPUS", max_length=20),
        ),
        migrations.AddField(model_name="placementhistory", name="remarks", field=models.TextField(blank=True)),
        migrations.AddField(model_name="placementhistory", name="created_at", field=models.DateTimeField(auto_now_add=True)),
        migrations.AddField(model_name="placementhistory", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AddField(
            model_name="placementhistory", name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_placement_history", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name="studymaterial", name="company",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="study_materials", to="placements.company"),
        ),
        migrations.AddField(
            model_name="studymaterial", name="placement_drive",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="study_materials", to="placements.placementdrive"),
        ),
        migrations.RunPython(migrate_history_and_material_companies, migrations.RunPython.noop),
        migrations.RemoveField(model_name="placementhistory", name="company_name"),
        migrations.AlterField(
            model_name="placementhistory", name="company",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="placement_history", to="placements.company"),
        ),
        migrations.AlterField(
            model_name="placementhistory", name="package",
            field=models.DecimalField(blank=True, decimal_places=2, help_text="Package in LPA", max_digits=8, null=True),
        ),
        migrations.AlterField(
            model_name="placementhistory", name="status",
            field=models.CharField(choices=[("PLACED", "Placed"), ("WITHDRAWN", "Withdrawn"), ("CANCELLED", "Cancelled")], default="PLACED", max_length=20),
        ),
        migrations.RemoveField(model_name="studymaterial", name="company_name"),
        migrations.AddField(model_name="studymaterial", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AddField(model_name="announcement", name="updated_at", field=models.DateTimeField(auto_now=True)),
        migrations.AlterField(model_name="studymaterial", name="drive_link", field=models.URLField(blank=True, verbose_name="External resource link")),
    ]
