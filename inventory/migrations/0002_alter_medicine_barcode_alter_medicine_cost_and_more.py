import django.core.validators
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="medicine",
            name="barcode",
            field=models.CharField(
                max_length=50,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        "^\\d+$", "Barcode must contain digits only."
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="medicine",
            name="cost",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0.00"), "Cost can't be negative."
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name="medicine",
            name="price",
            field=models.DecimalField(
                decimal_places=2,
                max_digits=10,
                validators=[
                    django.core.validators.MinValueValidator(
                        Decimal("0.01"), "Price must be greater than 0."
                    )
                ],
            ),
        ),
    ]