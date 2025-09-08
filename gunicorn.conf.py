import os

# Server socket
bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "jarvis-bot"

# Application
wsgi_module = "app:create_app()"

# Preload app for better memory usage
preload_app = True
