# Gunicorn configuration optimized for Render free tier
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker processes
workers = 1  # Use only 1 worker to minimize memory usage
worker_class = "sync"
timeout = 120  # Increase timeout for chart generation
keepalive = 10

# Memory management
max_requests = 100  # Restart workers after 100 requests to prevent memory leaks
max_requests_jitter = 20
preload_app = True  # Preload to save memory

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "expense_tracker"

# Memory limits (restart if worker uses too much memory)
worker_tmp_dir = "/dev/shm"  # Use shared memory for tmp files

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)