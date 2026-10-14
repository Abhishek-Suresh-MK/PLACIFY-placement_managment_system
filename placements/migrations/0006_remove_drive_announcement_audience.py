from django.db import migrations, models


def convert_drive_audience(apps, schema_editor):
    Announcement = apps.get_model("placements", "Announcement")
    # Preserve the intended audience when upgrading old databases.
    for announcement in Announcement.objects.filter(audience="DRIVE"):
        announcement.audience = "GLOBAL"
        announcement.placement_drive = None
        announcement.save(update_fields=["audience", "placement_drive"])


class Migration(migrations.Migration):
    dependencies = [("placements", "0005_alter_skill_options_alter_announcement_audience_and_more")]
    operations = [
        migrations.RunPython(convert_drive_audience, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="announcement",
            name="audience",
            field=models.CharField(
                choices=[("GLOBAL", "Everyone"), ("COLLEGE", "Selected colleges"), ("STUDENT", "Specific students")],
                default="GLOBAL",
                max_length=20,
            ),
        ),
    ]
