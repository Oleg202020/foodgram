"""Очищает базу, возвращается в \backend и запускает сервер."""
import os
import subprocess
import shutil
import sys
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    """
    Команда для очистки базы (clear_db.sh), возврата
    в директорию backend и запуска сервера
    (если база была очищена корректно).
    """

    def handle(self, *args, **options):
        current_dir = Path(__file__).resolve().parent
        postman_dir = current_dir.parents[2].parent / 'postman_collection'
        backend_dir = current_dir.parents[2]  # ...\backend
        os.chdir(postman_dir)

        bash_path = self.find_git_bash()
        if not bash_path:
            self.stderr.write(self.style.ERROR(
                "Не удалось найти bash.\n"
                "1) Установите Git Bash и/или\n"
                "2) Добавьте его в PATH или\n"
                "3) Установите WSL, если хотите использовать WSL-Bash."
            ))
            return
        try:
            subprocess.run([bash_path, "clear_db.sh"], check=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(
                f"Ошибка при запуске clear_db.sh: {e}"
            ))
            return
        os.chdir(backend_dir)
        self.stdout.write(self.style.SUCCESS("База успешно очищена."))
        try:
            subprocess.run([sys.executable, "manage.py", "runserver"],
                           check=True)
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(
                f"Ошибка при запуске сервера: {e}"
            ))

    def find_git_bash(self) -> str:
        """
        Пытается найти bash.exe (Git Bash) наиболее универсальным способом:
        1. Читает из переменной окружения GIT_BASH_PATH (если есть).
        2. Проверяет дефолтные пути для Git на Windows (x64 / x86).
        3. Пытается использовать bash из PATH (shutil.which('bash')).
        Возвращает путь к bash.exe или None, если не найден.
        """

        # 1. Проверяем переменную окружения
        env_bash = os.environ.get("GIT_BASH_PATH")
        if env_bash and os.path.exists(env_bash):
            return env_bash

        # 2. Проверяем самые типичные пути
        possible_paths = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p

        # 3. Последняя попытка: bash, известный системе
        which_bash = shutil.which("bash")
        if which_bash and os.path.exists(which_bash):
            return which_bash

        return None
