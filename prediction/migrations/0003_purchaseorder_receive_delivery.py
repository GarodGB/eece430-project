from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('prediction', '0002_alter_dailysales_options'),
        ('inventory', '0002_alter_medicine_barcode_alter_medicine_cost_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchaseorder',
            name='received_quantity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='received_expiry_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='received_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='purchaseorder',
            name='received_stock',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='purchase_order_receipt', to='inventory.stock',
            ),
        ),
    ]
