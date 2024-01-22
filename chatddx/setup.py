import os
import subprocess
from django.core.management import execute_from_command_line
from django.conf import settings

def ensure_path(path, owner):
    try:
        if not os.path.exists(path):
            os.makedirs(path, mode=0o755)
        subprocess.run(['chown', owner, path], check=True)
    except Exception as e:
        print(f"Error {e}")

def run():
    ensure_path(settings.DB_ROOT, settings.USER)
    execute_from_command_line(('','migrate'))

if __name__ == '__main__':
    run()
