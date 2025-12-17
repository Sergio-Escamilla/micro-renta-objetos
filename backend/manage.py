"""
Archivo de conveniencia para usar el CLI de Flask:
    python manage.py run
    python manage.py shell
    flask db init / migrate / upgrade (con FLASK_APP=wsgi.py)
"""

from flask.cli import main

if __name__ == "__main__":
    main()
