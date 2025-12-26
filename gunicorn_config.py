"""
Gunicorn configuration for production deployment
"""
import multiprocessing
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes
# For Railway serverless (free tier): Use 1 worker for faster cold starts and lower memory usage
# This optimizes for the sleep/wake cycle where apps restart frequently
# Can be overridden with GUNICORN_WORKERS env var (e.g., set to 2 for paid plans)
workers = int(os.environ.get('GUNICORN_WORKERS', 1))
worker_class = 'sync'
worker_connections = 1000
max_requests = 1000  # Restart workers after this many requests to prevent memory leaks
max_requests_jitter = 50
timeout = 60  # 60 seconds timeout for requests
keepalive = 2

# Process naming
proc_name = 'finance_tracker'

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stdout
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Server mechanics
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# SSL (configure if needed)
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

def on_starting(server):
    """Called just before the master process is initialized"""
    server.log.info("Gunicorn master process starting")

def on_reload(server):
    """Called when the server is reloading"""
    server.log.info("Gunicorn master process reloading")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info(f"Gunicorn server is ready. Listening on: {bind}")
    server.log.info(f"Using {workers} worker processes")

def on_exit(server):
    """Called just before exiting Gunicorn"""
    server.log.info("Gunicorn master process exiting")
