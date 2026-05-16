import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception as e:
    import traceback
    # Write the exact error to a log file in the app directory
    with open(os.path.join(os.path.dirname(__file__), 'wsgi_error.log'), 'w') as f:
        f.write(traceback.format_exc())
    raise e
