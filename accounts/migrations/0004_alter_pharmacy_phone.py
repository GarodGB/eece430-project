import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_user_role"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pharmacy",
            name="phone",
            field=models.CharField(
                max_length=20,
                validators=[
                    django.core.validators.RegexValidator(
                        "^[\\d +]+$", "Phone can only contain digits, spaces and +."
                    )
                ],
            ),
        ),
    ]