from datetime import date, timedelta
from random import Random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Pharmacy
from inventory.models import Stock
from prediction.models import DailySales
from sales.models import SaleItem


class Command(BaseCommand):
    help = 'Add synthetic forecast history in a dedicated demo database.'

    def add_arguments(self, parser):
        parser.add_argument('--pharmacy-id', required=True, type=int)
        parser.add_argument('--as-of', type=date.fromisoformat, help='Beirut date (YYYY-MM-DD).')
        parser.add_argument('--demo-only', action='store_true', help='Confirm this is an isolated demo database.')

    @transaction.atomic
    def handle(self, *args, **options):
        if not options['demo_only']:
            raise CommandError('Use --demo-only to confirm this is an isolated demo database.')

        today = timezone.localdate()
        as_of = options['as_of'] or today
        if as_of > today or as_of <= date.min + timedelta(days=30):
            raise CommandError('Choose a valid reference date on or before today.')

        pharmacy = Pharmacy.objects.select_for_update().filter(
            pk=options['pharmacy_id'], name__startswith='Demo Pharmacy ',
        ).first()
        if pharmacy is None:
            raise CommandError('Choose a seeded Demo Pharmacy by ID.')

        real_sale_medicines = SaleItem.objects.filter(
            sale__pharmacy=pharmacy,
        ).values('medicine_id')
        medicine_ids = (
            Stock.objects.filter(pharmacy=pharmacy, medicine__name__startswith='Demo ')
            .exclude(medicine_id__in=real_sale_medicines)
            .order_by('medicine_id').values_list('medicine_id', flat=True).distinct()
        )
        created_count = 0
        for index, medicine_id in enumerate(medicine_ids):
            rng = Random(f'phar12:{pharmacy.pk}:{medicine_id}')
            base_rate = (0, 1, 4, 10)[index % 4]
            if not base_rate:
                continue
            for offset in range(30, 0, -1):
                day = as_of - timedelta(days=offset)
                quantity = max(0, base_rate + rng.randint(-2, 3) - (day.weekday() >= 5))
                if quantity:
                    _, created = DailySales.objects.get_or_create(
                        pharmacy=pharmacy, medicine_id=medicine_id, date=day,
                        defaults={'quantity_sold': quantity},
                    )
                    created_count += created

        self.stdout.write(f'Added {created_count} synthetic daily sales summaries for {pharmacy.name}.')
