import os
import django
from pathlib import Path

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

print("🔧 Проверка загрузки .env:")
print(f"BASE_DIR: {settings.BASE_DIR}")
print(f"PROJECT_ROOT: {getattr(settings, 'PROJECT_ROOT', 'Не найден')}")

# Проверяем переменные
token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
debug = getattr(settings, 'DEBUG', None)
secret = getattr(settings, 'SECRET_KEY', None)

print(f"\n📋 Загруженные настройки:")
print(f"TELEGRAM_BOT_TOKEN: {'✅' if token else '❌'} {'Найден' if token else 'Не найден'}")
print(f"DEBUG: {debug}")
print(f"SECRET_KEY: {'✅' if secret else '❌'}")

if token:
    print(f"   Токен: {token[:10]}...")
    print(f"   Длина: {len(token)} символов")

    # Проверяем бота через API
    import requests

    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Бот доступен: {bot_info['result']['first_name']} (@{bot_info['result']['username']})")
        else:
            print(f"❌ Бот недоступен: {response.json()}")
    except Exception as e:
        print(f"⚠️  Не удалось проверить бота: {e}")
