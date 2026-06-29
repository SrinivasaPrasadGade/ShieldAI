import os
from celery import Celery

# Default to localhost if running outside docker, else use the environment variable
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "shield_ai",
    broker=redis_url,
    backend=redis_url,
    include=["tasks.currency_tasks", "tasks.graph_tasks", "tasks.scam_tasks"]
)

# Optional configuration, see the Celery application user guide.
app.conf.update(
    task_serializer="json",
    accept_content=["json"],  # Ignore other content
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

if __name__ == '__main__':
    app.start()
