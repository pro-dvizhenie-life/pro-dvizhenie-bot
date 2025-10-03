#!/usr/bin/env python
import os
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("🔧 Исправление импортов...")

# Временно заменим проблемные файлы
problem_files = [
    "apps/applications/bots/telegram/handlers/form.py",
    "apps/applications/bots/telegram/handlers/documents.py",
    "apps/applications/bots/telegram/handlers/preview.py"
]

for file_path in problem_files:
    full_path = BASE_DIR / file_path
    if full_path.exists():
        print(f"Проверяем {file_path}...")
        content = full_path.read_text(encoding='utf-8')

        # Заменяем проблемные импорты
        new_content = content.replace(
            "from ....bots.telegram.models",
            "from apps.applications.bots.telegram.models"
        ).replace(
            "from ....bots.telegram.database",
            "from apps.applications.bots.telegram.database"
        ).replace(
            "from .keyboards",
            "from apps.applications.bots.telegram.handlers.keyboards"
        )

        if content != new_content:
            full_path.write_text(new_content, encoding='utf-8')
            print(f"✅ Исправлен {file_path}")
        else:
            print(f"✅ {file_path} уже в порядке")

print("✅ Исправления завершены")
