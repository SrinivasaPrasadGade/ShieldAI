from celery_app import app
from services.evidence_service import get_evidence_service
from tasks.async_utils import run_async

@app.task(name="tasks.graph_tasks.generate_evidence_task")
def generate_evidence_task(cluster_id: int, task_id: str):
    evidence_svc = get_evidence_service()
    run_async(evidence_svc.generate_evidence_package(
        cluster_id=cluster_id,
        task_id=task_id
    ))

@app.task(name="tasks.graph_tasks.recompute_graph_clusters_task")
def recompute_graph_clusters_task():
    from services.graph_service import get_graph_service
    svc = get_graph_service()
    svc._recompute_clusters()
