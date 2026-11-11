import django.core.validators
from decimal import Decimal
from django.db import migrations, models


def old_sales_subtotal_equals_total(apps, schema_editor):
    # Sales made before discounts existed had no discount, so subtotal = total.
    Sale = apps.get_model('sales', 'Sale')
    Sale.objects.update(subtotal=models.F('total'))


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sale",
            name="discount_percent",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("0")),
                    django.core.validators.MaxValueValidator(Decimal("100")),
                ],
            ),
        ),
        migrations.AddField(
            model_name="sale",
            name="subtotal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="saleitem",
            name="unit_cost",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.RunPython(old_sales_subtotal_equals_total, migrations.RunPython.noop),
    ]
