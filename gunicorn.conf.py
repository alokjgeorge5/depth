# Gunicorn configuration
bind = "0.0.0.0:10000"
workers = 1
timeout = 120  # Allow 120 seconds for long-running requests
keepalive = 5

