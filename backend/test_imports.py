#!/usr/bin/env python
import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

print("🔍 Детальная диагностика импортов...")
print(f"BASE_DIR: {BASE_DIR}")
print(f"Python path: {sys.path}")

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
    print("✅ Django настроен")
except Exception as e:
    print(f"❌ Django: {e}")

# Проверяем каждый импорт отдельно
imports_to_check = [
    ("telegram", "Update"),
    ("telegram.ext", "Application"),
    ("apps.applications.bots.telegram_models", "TelegramUser"),
    ("apps.applications.bots.database", "init_telegram_db"),
    ("apps.applications.bots.handlers.telegram_handlers.start", "start"),
    ("apps.applications.bots.handlers.telegram_handlers.help", "help_command"),
    ("apps.applications.bots.handlers.telegram_handlers.form", "form_entry"),
    ("apps.applications.bots.handlers.telegram_handlers.telegram_handler", "telegram_bot"),
]

for module_path, item_name in imports_to_check:
    try:
        if "." in module_path:
            # Для модулей с точками
            module_parts = module_path.split(".")
            module = __import__(module_path)
            for part in module_parts[1:]:
                module = getattr(module, part)
        else:
            # Для простых модулей
            module = __import__(module_path)

        if item_name:
            item = getattr(module, item_name)
            print(f"✅ {module_path}.{item_name} - ОК")
        else:
            print(f"✅ {module_path} - ОК")

    except ImportError as e:
        print(f"❌ {module_path}.{item_name}: {e}")
    except AttributeError as e:
        print(f"❌ {module_path}.{item_name}: {e}")

print("✅ Диагностика завершена")
