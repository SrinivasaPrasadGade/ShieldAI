"""
Fraud network graph API router for ShieldAI.

Endpoints:
  GET  /api/graph/network                         — Get fraud network graph
  GET  /api/graph/node/{entity_id}                — Get entity details
  POST /api/graph/query                           — Query entity by phone/account
  GET  /api/graph/clusters                        — List fraud clusters
  POST /api/graph/evidence-package/{cluster_id}   — Start evidence PDF generation
  GET  /api/graph/stats                           — Graph statistics
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from models.schemas import (
    GraphNetworkResponse,
    GraphNodeResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphClustersResponse,
    GraphStatsResponse,
)
from services.graph_service import get_graph_service
from services.evidence_service import get_evidence_service
from logging_config import get_logger

logger = get_logger("shield_ai.router.graph")

router = APIRouter(prefix="/api/graph", tags=["Fraud Network Graph"])


@router.get("/network", response_model=GraphNetworkResponse)
async def get_network(
    cluster_id: Optional[int] = Query(None, description="Filter by cluster ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum nodes to return"),
):
    """
    Get fraud network graph data including nodes, edges, and clusters.

    Optionally filter by cluster_id. Returns up to `limit` nodes
    ordered by risk score (descending), with all connecting edges.
    """
    service = get_graph_service()
    result = service.get_network(cluster_id=cluster_id, limit=limit)
    return result


@router.get("/node/{entity_id}", response_model=GraphNodeResponse)
async def get_node(entity_id: str):
    """
    Get detailed information for a single entity in the fraud network.

    Returns the entity, its connected reports, centrality score,
    and cluster membership.
    """
    service = get_graph_service()
    result = service.get_node(entity_id)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found")

    return result


@router.post("/query", response_model=GraphQueryResponse)
async def query_entity(request: GraphQueryRequest):
    """
    Query the fraud network graph by phone number or account number.

    Returns whether the entity was found, its risk score, network depth
    (via BFS traversal), and connected entities.
    """
    service = get_graph_service()
    result = service.query_entity(
        phone_number=request.phone_number,
        account_number=request.account_number,
    )
    return result


@router.get("/clusters", response_model=GraphClustersResponse)
async def get_clusters():
    """
    List all fraud clusters with entity counts.
    Ordered by risk level (HIGH first) and entity count.
    """
    service = get_graph_service()
    clusters = service.get_clusters()
    return {"clusters": clusters}


@router.post("/evidence-package/{cluster_id}", status_code=202)
async def start_evidence_package(cluster_id: int):
    """
    Start async evidence package generation for a fraud cluster.

    Returns a task_id. Poll GET /api/graph/evidence-package/result/{task_id} for the result.
    The evidence package includes entities, relationships, linked reports,
    and key findings.
    """
    service = get_graph_service()
    task_id = await service.start_evidence_package(cluster_id)

    return {"task_id": task_id}


@router.get("/evidence-package/result/{task_id}")
async def get_evidence_package_result(task_id: str):
    """
    Poll for the result of an evidence package generation task.
    """
    from models import task_store

    task = task_store.get_task(task_id)
    if task is None or task.get("task_type") != "evidence_package":
        raise HTTPException(status_code=404, detail=f"Evidence package task {task_id} not found")

    return {
        "status": task["status"],
        "result": task.get("result"),
        "error": task.get("error"),
    }


@router.get("/stats", response_model=GraphStatsResponse)
async def get_stats():
    """
    Get fraud network graph statistics.
    Includes total entities, edges, active clusters, and highest-risk cluster.
    """
    service = get_graph_service()
    stats = service.get_stats()
    return stats

@router.get("/recompute-status")
async def get_recompute_status():
    """Get the current graph recomputation status."""
    service = get_graph_service()
    return service.get_recompute_status()
