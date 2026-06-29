from celery_app import app
from services.evidence_service import get_evidence_service
import asyncio

@app.task(name="tasks.graph_tasks.generate_evidence_task")
def generate_evidence_task(cluster_id: int, task_id: str):
    evidence_svc = get_evidence_service()
    asyncio.run(evidence_svc.generate_evidence_package(
        cluster_id=cluster_id,
        task_id=task_id
    ))
