#!/usr/bin/env python
# مسیر: image_service/manage.py
import os
import sys
from pathlib import Path

def main():
    """Run administrative tasks."""
    
    # --- تغییر کلیدی: اضافه کردن ریشه پروژه به مسیر جستجوی پایتون ---
    # این کار به پایتون اجازه می‌دهد تا پوشه‌هایی مانند 'apps' و 'messaging' را پیدا کند.
    
    # BASE_DIR به پوشه image_service اشاره می‌کند
    BASE_DIR = Path(__file__).resolve().parent
    # ما BASE_DIR را به sys.path اضافه می‌کنیم
    sys.path.append(str(BASE_DIR))
    # -----------------------------------------------------------------

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()