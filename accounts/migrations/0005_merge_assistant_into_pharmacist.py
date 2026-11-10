from django.db import migrations, models


def assistants_to_pharmacists(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(role='assistant').update(role='pharmacist')


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_pharmacy_phone"),
    ]

    operations = [
        migrations.RunPython(assistants_to_pharmacists, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("admin", "System admin"),
                    ("owner", "Owner"),
                    ("pharmacist", "Pharmacist"),
                ],
                default="pharmacist",
                max_length=20,
            ),
        ),
    ]