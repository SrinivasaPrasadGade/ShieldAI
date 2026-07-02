from celery_app import app
from services.evidence_service import get_evidence_service
from tasks.async_utils import run_async

@app.task(name="tasks.graph_tasks.generate_evidence_task")
def generate_evidence_task(cluster_id: int, task_id: str, officer_metadata: dict = None):
    evidence_svc = get_evidence_service()
    run_async(evidence_svc.generate_evidence_package(
        cluster_id=cluster_id,
        task_id=task_id,
        officer_metadata=officer_metadata
    ))

@app.task(name="tasks.graph_tasks.recompute_graph_clusters_task")
def recompute_graph_clusters_task(task_id: str = None):
    from services.graph_service import get_graph_service
    from models import task_store
    if task_id:
        task_store.update_task(task_id, status="processing")
    try:
        svc = get_graph_service()
        svc._recompute_clusters()
        if task_id:
            task_store.update_task(task_id, status="complete", result={"success": True})
    except Exception as e:
        if task_id:
            task_store.update_task(task_id, status="failed", error=str(e))
        raise

