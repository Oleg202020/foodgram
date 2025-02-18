"""Очищает базу и возвращается на вкладку \backend"""
import os
import subprocess

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def handle(self, *args, **options):
        os.chdir(r"..\postman_collection")
        try:
            subprocess.run([r"C:\Program Files\Git\bin\bash.exe",
                            "clear_db.sh"], check=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(
                f"Ошибка при запуске clear_db.sh: {e}")
            )
            return

        os.chdir(r"..\backend")

# python manage.py сlean_and_back
