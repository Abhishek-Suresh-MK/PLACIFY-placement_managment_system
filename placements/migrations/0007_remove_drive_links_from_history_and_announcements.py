from django.db import migrations


def clear_legacy_announcement_targets(apps, schema_editor):
    Announcement = apps.get_model("placements", "Announcement")
    Announcement.objects.filter(audience="DRIVE").update(audience="GLOBAL")


class Migration(migrations.Migration):
    dependencies = [("placements", "0006_remove_drive_announcement_audience")]
    operations = [
        migrations.RunPython(clear_legacy_announcement_targets, migrations.RunPython.noop),
        migrations.RemoveField(model_name="placementhistory", name="placement_drive"),
        migrations.RemoveField(model_name="announcement", name="placement_drive"),
    ]
