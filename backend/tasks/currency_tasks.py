from celery_app import app
from services.currency_analyzer import get_currency_analyzer
from tasks.async_utils import run_async

@app.task(name="tasks.currency_tasks.verify_currency_task")
def verify_currency_task(task_id: str, file_url: str, denomination: int = None, location: str = None):
    analyzer = get_currency_analyzer()
    run_async(analyzer.run_verification(
        task_id=task_id,
        file_url=file_url,
        denomination=denomination,
        location=location
    ))
