from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("placements", "0007_remove_drive_links_from_history_and_announcements")]
    operations = [migrations.RemoveField(model_name="company", name="contact_name")]
