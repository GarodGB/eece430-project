from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0002_alter_medicine_barcode_alter_medicine_cost_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name='MedicineReservation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(validators=[MinValueValidator(1)])),
                ('customer_name', models.CharField(max_length=120)),
                ('customer_phone', models.CharField(blank=True, max_length=25)),
                ('status', models.CharField(
                    choices=[('active', 'Reserved'), ('released', 'Released')],
                    default='active', max_length=12)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('released_at', models.DateTimeField(blank=True, null=True)),
                ('request_key', models.UUIDField(blank=True, null=True, unique=True)),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='inventory.medicine')),
                ('pharmacy', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.pharmacy')),
                ('reserved_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_medicine_reservations', to=settings.AUTH_USER_MODEL)),
                ('released_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='released_medicine_reservations', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at', '-id']},
        ),
        migrations.AddIndex(
            model_name='medicinereservation',
            index=models.Index(fields=['pharmacy', 'medicine', 'status'], name='res_lookup_idx'),
        ),
    ]
