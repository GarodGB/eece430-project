
from datetime import date, timedelta
from decimal import Decimal
from random import Random

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Pharmacy
from inventory.models import Medicine, Stock
from prediction.models import DailySales, StockAlert, Supplier


class Command(BaseCommand):
    help = "Populate PharmaLink with synthetic demo data"

    @transaction.atomic
    def handle(self, *args, **options):

        rng = Random(430)

        # ---------------------------------------
        # 1. CREATE 15 DEMO PHARMACIES
        # ---------------------------------------

        pharmacy_data = [
            ("Demo Pharmacy Beirut", "Hamra, Beirut"),
            ("Demo Pharmacy Achrafieh", "Achrafieh, Beirut"),
            ("Demo Pharmacy Verdun", "Verdun, Beirut"),
            ("Demo Pharmacy Badaro", "Badaro, Beirut"),
            ("Demo Pharmacy Baabda", "Baabda"),
            ("Demo Pharmacy Hazmieh", "Hazmieh"),
            ("Demo Pharmacy Jounieh", "Jounieh"),
            ("Demo Pharmacy Jbeil", "Jbeil"),
            ("Demo Pharmacy Tripoli", "Tripoli"),
            ("Demo Pharmacy Saida", "Saida"),
            ("Demo Pharmacy Zahle", "Zahle"),
            ("Demo Pharmacy Nabatieh", "Nabatieh"),
            ("Demo Pharmacy Broummana", "Broummana"),
            ("Demo Pharmacy Dekwaneh", "Dekwaneh"),
            ("Demo Pharmacy Aley", "Aley"),
        ]

        pharmacies = []

        for name, address in pharmacy_data:
            pharmacy, created = Pharmacy.objects.get_or_create(
                name=name,
                defaults={
                    "address": address,
                    "phone": "00000000",
                    "shares_stock": True,
                },
            )
            pharmacies.append(pharmacy)

        self.stdout.write("15 demo pharmacies prepared.")

        # ---------------------------------------
        # 2. CREATE 100 DEMO MEDICINES
        # ---------------------------------------

        # Keep the original 8 medicines and barcodes
        # so earlier demo records are reused.

        medicine_data = [
            ("Demo Paracetamol 500mg", "Paracetamol", "3.50", "2.00"),
            ("Demo Ibuprofen 200mg", "Ibuprofen", "4.00", "2.50"),
            ("Demo Amoxicillin 500mg", "Amoxicillin", "6.00", "4.00"),
            ("Demo Cetirizine 10mg", "Cetirizine", "3.00", "1.80"),
            ("Demo Omeprazole 20mg", "Omeprazole", "5.50", "3.50"),
            ("Demo Vitamin C 500mg", "Vitamin C", "2.50", "1.20"),
            ("Demo Metformin 500mg", "Metformin", "4.50", "2.80"),
            ("Demo Loratadine 10mg", "Loratadine", "3.80", "2.20"),
        ]

        # Generate 92 additional demo products
        # using 23 names and 4 fictional variants.

        medicine_names = [
            "Aspirin",
            "Naproxen",
            "Diclofenac",
            "Fexofenadine",
            "Pantoprazole",
            "Famotidine",
            "Simethicone",
            "Loperamide",
            "Lactulose",
            "Zinc",
            "Vitamin B12",
            "Folic Acid",
            "Calcium",
            "Magnesium",
            "Iron",
            "Multivitamin",
            "Saline Nasal Spray",
            "Artificial Tears",
            "Clotrimazole",
            "Hydrocortisone",
            "Guaifenesin",
            "Dextromethorphan",
            "Oral Rehydration Salts",
        ]

        for name in medicine_names:
            for variant in range(1, 5):
                number = len(medicine_data) + 1

                price = Decimal("2.00") + (
                    Decimal(number % 13) * Decimal("0.75")
                )

                cost = (
                    price * Decimal("0.65")
                ).quantize(Decimal("0.01"))

                medicine_data.append((
                    f"Demo {name} Variant {variant}",
                    name,
                    str(price),
                    str(cost),
                ))

        medicines = []

        for index, (name, generic, price, cost) in enumerate(
            medicine_data, start=1
        ):
            barcode = f"2000000000{index:03d}"

            medicine, created = Medicine.objects.get_or_create(
                barcode=barcode,
                defaults={
                    "name": name,
                    "generic_name": generic,
                    "price": Decimal(price),
                    "cost": Decimal(cost),
                    "needs_prescription": False,
                },
            )

            medicines.append(medicine)

        self.stdout.write("100 demo medicines prepared.")

        # ---------------------------------------
        # 3. CREATE 750 STOCK RECORDS
        # ---------------------------------------

        stock_records = []
        expiry = date(2027, 12, 31)

        # Each pharmacy receives 50 of the
        # 100 different medicines.

        for pharmacy_index, pharmacy in enumerate(pharmacies):
            for index in range(50):

                medicine_index = (
                    pharmacy_index * 7 + index * 3
                ) % len(medicines)

                medicine = medicines[medicine_index]

                quantity = (
                    pharmacy_index * 11 + index * 7
                ) % 61

                stock, created = Stock.objects.get_or_create(
                    pharmacy=pharmacy,
                    medicine=medicine,
                    expiry_date=expiry,
                    defaults={
                        "quantity": quantity,
                        "reorder_level": 10,
                    },
                )

                stock_records.append(stock)

        self.stdout.write("750 demo stock records prepared.")

        # ---------------------------------------
        # 4. CREATE 1000 DAILY SALES RECORDS
        # ---------------------------------------

        # Fixed dates keep the dataset reproducible.
        # These are historical summaries, not POS
        # Sale and SaleItem transactions.

        start_date = date(2026, 10, 1)
        history_days = 35

        # Select 1000 distinct stock/date combinations.
        selections = rng.sample(
            range(len(stock_records) * history_days),
            1000
        )

        for selection in selections:

            stock_index = selection // history_days
            day_index = selection % history_days

            stock = stock_records[stock_index]
            sale_date = start_date + timedelta(days=day_index)

            DailySales.objects.get_or_create(
                pharmacy=stock.pharmacy,
                medicine=stock.medicine,
                date=sale_date,
                defaults={
                    "quantity_sold": rng.randint(1, 8),
                },
            )

        self.stdout.write("1000 daily sales records prepared.")

        # ---------------------------------------
        # 5. CREATE 15 SUPPLIERS
        # ---------------------------------------

        for index in range(1, 16):

            Supplier.objects.get_or_create(
                name=f"Demo Supplier {index:02d}",
                defaults={
                    "phone": "00000000",
                    "email": f"supplier{index:02d}@example.com",
                },
            )

        self.stdout.write("15 demo suppliers prepared.")

        # ---------------------------------------
        # 6. CREATE 30 STOCK ALERTS
        # ---------------------------------------

        # Choose products with the smallest quantities.

        low_stock = sorted(
            stock_records,
            key=lambda stock: (
                stock.quantity,
                stock.pharmacy_id,
                stock.medicine_id,
            )
        )[:30]

        for index, stock in enumerate(low_stock):

            predicted_date = (
                date(2026, 11, 20)
                + timedelta(days=index % 12)
            )

            StockAlert.objects.get_or_create(
                stock=stock,
                predicted_run_out_date=predicted_date,
                defaults={
                    "status": "open",
                },
            )

        self.stdout.write("30 demo stock alerts prepared.")

        # ---------------------------------------
        # COMPLETE
        # ---------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "PharmaLink synthetic data prepared successfully!"
            )
        )
