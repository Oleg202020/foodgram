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
            for row in load_csv_readed:
                Ingredient.objects.update_or_create(  # чтобы не делать дублей
                    name=row[0].strip(),
                    measurement_unit=row[1].strip()
                )
        self.stdout.write(
            self.style.SUCCESS('Ингредиентов загружены.'))

# python manage.py load_ingredients
