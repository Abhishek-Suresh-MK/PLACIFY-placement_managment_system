from django.db import migrations, models


def make_emails_unique(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    seen = set()
    for user in User.objects.order_by("id"):
        base = (user.email or "").strip().lower()
        if not base or base in seen:
            base = f"user{user.pk}@placify.local"
            suffix = 1
            while base in seen:
                base = f"user{user.pk}+{suffix}@placify.local"
                suffix += 1
        user.email = base
        user.save(update_fields=["email"])
        seen.add(base)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]

    operations = [
        migrations.RunPython(make_emails_unique, migrations.RunPython.noop),
        migrations.RemoveField(model_name="user", name="username"),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(max_length=254, unique=True, verbose_name="email address"),
        ),
    ]
