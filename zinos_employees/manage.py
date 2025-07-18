#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import sqlite3
#this a modefied file
#tamer is bitch


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zinos_project.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)



try:
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("الجداول المتاحة:", tables)
except sqlite3.Error as e:
    print("حدث خطأ في SQLite:", e)
finally:
    if conn:
        conn.close()

if __name__ == '__main__':
    main()
