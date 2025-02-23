import csv

from django.core.management import BaseCommand

from foodgram_app.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open(
            'foodgram_app/management/commands/data/ingredients.csv',
            encoding='utf-8'
        ) as csv_file:
            load_csv_readed = csv.reader(csv_file)
            ingredients = []
            for row in load_csv_readed:
                ingredients.append(
                    Ingredient(
                        name=row[0].strip(),
                        measurement_unit=row[1].strip()
                    )
                )
        Ingredient.objects.bulk_create(ingredients, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS('Ингредиенты загружены.'))
