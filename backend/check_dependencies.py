import importlib.util
import sys

def check_module(module_name):
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            return True, f"✅ {module_name}"
        else:
            return False, f"❌ {module_name}"
    except ImportError:
        return False, f"❌ {module_name}"

print("🔧 Проверка зависимостей:")
modules = [
    'django',
    'rest_framework',
    'telegram',
    'telegram.ext',
    'sqlalchemy',
    'dotenv'
]

for module in modules:
    success, message = check_module(module)
    print(message)

print(f"\n🐍 Python версия: {sys.version}")
