"""
Gunicorn Configuration File
Production WSGI Server Settings
"""

import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "ganglioside_django"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn_ganglioside.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
# keyfile = "/path/to/key.pem"
# certfile = "/path/to/cert.pem"

# Environment variables
raw_env = [
    "DJANGO_SETTINGS_MODULE=config.settings.production",
]

# Reload on code changes (development only)
reload = os.getenv("GUNICORN_RELOAD", "False").lower() == "true"
