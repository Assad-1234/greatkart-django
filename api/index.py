import os
import sys

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "greatkart.settings")

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()