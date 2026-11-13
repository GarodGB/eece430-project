from datetime import date, timedelta
from decimal import Decimal
from random import Random
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Pharmacy, User  # CHANGED: added User
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
                    # CHANGED: Verdun does not share (privacy demo)
                    "shares_stock": name != "Demo Pharmacy Verdun",
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

        for pharmacy_index, pharmacy in enumerate(pharmacies):
            for index in range(50):

                medicine_index = (
                    pharmacy_index * 7 + index * 3
                ) % len(medicines)

                medicine = medicines[medicine_index]

                quantity = (
                    pharmacy_index * 11 + index * 7
                ) % 61

                # Different reorder levels: 5 to 25
                reorder_level = 5 + (
                    (pharmacy_index * 13 + index * 7) % 21
                )

                # Different expiry dates:
                # Some expired, some expiring soon,
                # and some with longer shelf lives.

                # Different expiry dates throughout 2027 and 2028
                days_until_expiry = (
                    pharmacy_index * 41 + index * 17
                ) % 730

                expiry_date = date(2027, 1, 1) + timedelta(
                    days=days_until_expiry
                )

                # Reuse the original stock record.
                # This avoids creating duplicates when
                # updating its expiry date.
                stock = Stock.objects.filter(
                    pharmacy=pharmacy,
                    medicine=medicine,
                ).order_by("id").first()

                if stock is None:
                    stock = Stock.objects.create(
                        pharmacy=pharmacy,
                        medicine=medicine,
                        quantity=quantity,
                        reorder_level=reorder_level,
                        expiry_date=expiry_date,
                    )
                else:
                    changes = []

                    # Update old default reorder levels.
                    if stock.reorder_level == 10:
                        stock.reorder_level = reorder_level
                        changes.append("reorder_level")

                    # Update old default expiry dates.
                    if stock.expiry_date.year < 2027 or stock.expiry_date == date(2027, 12, 31):
                        stock.expiry_date = expiry_date
                        changes.append("expiry_date")

                    if changes:
                        stock.save(update_fields=changes)

                stock_records.append(stock)

        self.stdout.write(
            "750 demo stock records prepared."
        )



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
            phone = f"000000{index:02d}"

            supplier, created = Supplier.objects.get_or_create(
                name=f"Demo Supplier {index:02d}",
                defaults={
                    "phone": phone,
                    "email": f"supplier{index:02d}@example.com",
                },
            )

            # Update existing placeholder numbers only
            if not created and supplier.phone == "00000000":
                supplier.phone = phone
                supplier.save(update_fields=["phone"])

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
        # 7. CREATE DEMO USERS
        # ---------------------------------------

        # Password supplied through an environment variable,
        # never hardcoded into the GitHub repository.
        demo_password = os.environ.get("DEMO_USER_PASSWORD")

        if not demo_password:
            self.stdout.write(
                "Demo users skipped: DEMO_USER_PASSWORD not set."
            )
        else:
            owners_created = 0
            pharmacists_created = 0

            for index, pharmacy in enumerate(pharmacies, start=1):

                # One owner per pharmacy
                owner_username = f"demo_owner_{index:02d}"

                if not User.objects.filter(
                    username=owner_username
                ).exists():
                    User.objects.create_user(
                        username=owner_username,
                        password=demo_password,
                        role="owner",
                        pharmacy=pharmacy,
                    )
                    owners_created += 1

                # One pharmacist per pharmacy
                pharmacist_username = (
                    f"demo_pharmacist_{index:02d}"
                )

                if not User.objects.filter(
                    username=pharmacist_username
                ).exists():
                    User.objects.create_user(
                        username=pharmacist_username,
                        password=demo_password,
                        role="pharmacist",
                        pharmacy=pharmacy,
                    )
                    pharmacists_created += 1

            self.stdout.write(
                f"Created {owners_created} owners and "
                f"{pharmacists_created} pharmacists."
            )
            self.stdout.write(
                "Existing users and passwords preserved."
            )

        
        
        
        

        # ---------------------------------------
        # 8. DEMO EXPIRY CASES (PHAR-6)
        # ---------------------------------------

        beirut = pharmacies[0]

        # Replace the original 2026 expiry dates
        # with different dates in 2027.
        demo_expiry = [
            (
                medicines[0],
                date(2026, 11, 25),
                date(2027, 1, 15),
                12,
            ),
            (
                medicines[1],
                date(2026, 11, 30),
                date(2027, 2, 10),
                6,
            ),
            (
                medicines[2],
                date(2026, 11, 1),
                date(2027, 3, 5),
                8,
            ),
        ]

        for medicine, old_date, new_date, quantity in demo_expiry:

            old_stock = Stock.objects.filter(
                pharmacy=beirut,
                medicine=medicine,
                expiry_date=old_date,
            ).first()

            if old_stock:
                old_stock.expiry_date = new_date
                old_stock.save(update_fields=["expiry_date"])
            else:
                Stock.objects.get_or_create(
                    pharmacy=beirut,
                    medicine=medicine,
                    expiry_date=new_date,
                    defaults={
                        "quantity": quantity,
                        "reorder_level": 10,
                    },
                )

        self.stdout.write(
            "Demo 2027+ expiry cases prepared."
        )



        # ---------------------------------------
        # COMPLETE
        # ---------------------------------------

        self.stdout.write(
            self.style.SUCCESS(
                "PharmaLink synthetic data prepared successfully!"
            )
        )