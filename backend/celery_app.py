from celery import Celery
from config import settings

redis_url = settings.REDIS_URL

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
