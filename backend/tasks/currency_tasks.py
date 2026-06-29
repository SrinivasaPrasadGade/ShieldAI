from celery_app import app
from services.currency_analyzer import get_currency_analyzer
import asyncio

@app.task(name="tasks.currency_tasks.verify_currency_task")
def verify_currency_task(task_id: str, file_url: str, denomination: int = None, location: str = None):
    analyzer = get_currency_analyzer()
    asyncio.run(analyzer.run_verification(
        task_id=task_id,
        file_url=file_url,
        denomination=denomination,
        location=location
    ))
