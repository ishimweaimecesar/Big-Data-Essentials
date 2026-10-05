import json
from pathlib import Path

from django.core.management.base import BaseCommand

from products.models import Product


class Command(BaseCommand):

    help = "Import products"

    def handle(self, *args, **kwargs):

        with open(Path("products.json"), encoding="utf8") as f:
            data = json.load(f)

        Product.objects.all().delete()

        for product in data:

            Product.objects.create(

                product_id=product["product_id"],

                name=product["name"],

                category_id=product["category_id"],

                subcategory_id=product["subcategory_id"],

                base_price=product["base_price"],

                current_stock=product["current_stock"],

                is_active=product["is_active"],

                creation_date=product["creation_date"],

                image=f'{product["product_id"]}.png'

            )

        self.stdout.write(self.style.SUCCESS("Products Imported Successfully"))