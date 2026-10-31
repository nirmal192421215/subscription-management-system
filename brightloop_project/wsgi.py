"""
WSGI config for brightloop_project project.

It exposes the WSGI callable as a module-level variable named ``application``.
Also exports ``app`` for Vercel serverless deployment.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brightloop_project.settings')

application = get_wsgi_application()

# Alias for Vercel Serverless Function entrypoint
app = application
