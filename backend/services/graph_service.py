"""
Fraud network graph service for ShieldAI.

Operates on SQLite entities, relationships, and fraud_clusters tables.
Provides network queries, entity lookups, cluster management, and stats.
"""

from typing import Optional, List, Dict
from collections import deque
import sqlite3
import networkx as nx
from community import community_louvain

from config import settings
from logging_config import get_logger
from models.database import get_sqlite_connection
from models import task_store

logger = get_logger("shield_ai.graph")


class GraphService:
    """Fraud network graph operations on SQLite."""

    def get_network(self, cluster_id: Optional[int] = None, limit: int = 100) -> dict:
        """
        Get fraud network graph data (nodes, edges, clusters).

        Args:
            cluster_id: Optional filter by cluster
            limit: Maximum number of nodes to return

        Returns:
            dict with nodes, edges, clusters lists
        """
        with get_sqlite_connection() as conn:
            # Fetch nodes
            if cluster_id is not None:
                nodes_rows = conn.execute(
                    "SELECT * FROM entities WHERE cluster_id = ? LIMIT ?",
                    (cluster_id, limit),
                ).fetchall()
            else:
                nodes_rows = conn.execute(
                    "SELECT * FROM entities ORDER BY risk_score DESC LIMIT ?",
                    (limit,),
                ).fetchall()

            nodes = [dict(row) for row in nodes_rows]
            node_ids = {n["id"] for n in nodes}

            # Fetch edges between these nodes
            if node_ids:
                placeholders = ",".join("?" * len(node_ids))
                edges_rows = conn.execute(
                    f"""SELECT * FROM relationships
                        WHERE source_id IN ({placeholders})
                           OR target_id IN ({placeholders})""",
                    list(node_ids) + list(node_ids),
                ).fetchall()
            else:
                edges_rows = []

            edges = [dict(row) for row in edges_rows]

            # Fetch relevant clusters
            cluster_ids = {n.get("cluster_id") for n in nodes if n.get("cluster_id") is not None}
            clusters = []
            for cid in cluster_ids:
                cluster_row = conn.execute(
                    "SELECT * FROM fraud_clusters WHERE id = ?", (cid,)
                ).fetchone()
                if cluster_row:
                    cluster = dict(cluster_row)
                    # Add entity count
                    count = conn.execute(
                        "SELECT COUNT(*) as cnt FROM entities WHERE cluster_id = ?", (cid,)
                    ).fetchone()
                    cluster["entity_count"] = count["cnt"] if count else 0
                    cluster["name"] = cluster.get("cluster_name")
                    clusters.append(cluster)

        logger.info("network_fetched", node_count=len(nodes), edge_count=len(edges), cluster_count=len(clusters))
        return {"nodes": nodes, "edges": edges, "clusters": clusters}

    def get_node(self, entity_id: str) -> Optional[dict]:
        """
        Get detailed info for a single entity node.

        Args:
            entity_id: Entity ID to look up

        Returns:
            dict with entity, connected_reports, centrality_score, cluster
        """
        with get_sqlite_connection() as conn:
            # Fetch entity
            entity_row = conn.execute(
                "SELECT * FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()

            if not entity_row:
                return None

            entity = dict(entity_row)

            # Fetch connected edges
            edges = conn.execute(
                """SELECT * FROM relationships
                   WHERE source_id = ? OR target_id = ?""",
                (entity_id, entity_id),
            ).fetchall()

            # Compute centrality score (degree centrality within cluster)
            cluster_id = entity.get("cluster_id")
            centrality = 0.0

            if cluster_id is not None:
                total_edges_in_cluster = conn.execute(
                    """SELECT COUNT(*) as cnt FROM relationships r
                       JOIN entities e1 ON r.source_id = e1.id
                       JOIN entities e2 ON r.target_id = e2.id
                       WHERE e1.cluster_id = ? OR e2.cluster_id = ?""",
                    (cluster_id, cluster_id),
                ).fetchone()

                total = total_edges_in_cluster["cnt"] if total_edges_in_cluster else 0
                if total > 0:
                    centrality = round(len(edges) / total, 4)

            # Fetch cluster info
            cluster = None
            if cluster_id is not None:
                cluster_row = conn.execute(
                    "SELECT * FROM fraud_clusters WHERE id = ?", (cluster_id,)
                ).fetchone()
                if cluster_row:
                    cluster = dict(cluster_row)
                    count = conn.execute(
                        "SELECT COUNT(*) as cnt FROM entities WHERE cluster_id = ?", (cluster_id,)
                    ).fetchone()
                    cluster["entity_count"] = count["cnt"] if count else 0
                    cluster["name"] = cluster.get("cluster_name")

            # Gather linked report IDs from edges
            report_ids = set()
            for edge in edges:
                rid = dict(edge).get("linked_report_id")
                if rid:
                    report_ids.add(rid)

            # Fetch connected reports from Firestore
            connected_reports = []
            if report_ids:
                try:
                    from models.database import get_firestore_client
                    db = get_firestore_client()
                    for rid in list(report_ids)[:10]:  # Limit to 10 reports
                        doc = db.collection("fraud_reports").document(rid).get()
                        if doc.exists:
                            data = doc.to_dict()
                            connected_reports.append({
                                "id": rid,
                                "report_type": data.get("report_type", "unknown"),
                                "description": data.get("description", "")[:200],
                                "risk_score": data.get("risk_score", 0.0),
                                "created_at": str(data.get("created_at", "")),
                            })
                except Exception as e:
                    logger.error("fetch_connected_reports_failed", error=str(e))

        return {
            "entity": entity,
            "connected_reports": connected_reports,
            "centrality_score": centrality,
            "cluster": cluster,
        }

    def query_entity(self, phone_number: Optional[str] = None, account_number: Optional[str] = None) -> dict:
        """
        Query the fraud graph for a phone number or account number.

        Args:
            phone_number: Phone number to search
            account_number: Account number to search

        Returns:
            dict matching GraphQueryResponse schema
        """
        search_value = phone_number or account_number

        with get_sqlite_connection() as conn:
            # Search by value in entities
            entity_row = conn.execute(
                "SELECT * FROM entities WHERE value = ?", (search_value,)
            ).fetchone()

            if not entity_row:
                # Try partial match
                entity_row = conn.execute(
                    "SELECT * FROM entities WHERE value LIKE ?",
                    (f"%{search_value}%",),
                ).fetchone()

            if not entity_row:
                return {
                    "risk_score": 0.0,
                    "found": False,
                    "entity": None,
                    "network_depth": 0,
                    "connected_entities": [],
                }

            entity = dict(entity_row)

            # BFS to find network depth and connected entities
            connected = []
            visited = {entity["id"]}
            queue = deque([(entity["id"], 0)])
            max_depth = 0

            while queue:
                current_id, depth = queue.popleft()
                max_depth = max(max_depth, depth)

                if depth >= 3:  # Limit BFS depth
                    continue

                neighbors = conn.execute(
                    """SELECT e.* FROM entities e
                       JOIN relationships r ON (r.source_id = e.id OR r.target_id = e.id)
                       WHERE (r.source_id = ? OR r.target_id = ?) AND e.id != ?""",
                    (current_id, current_id, current_id),
                ).fetchall()

                for neighbor in neighbors:
                    n = dict(neighbor)
                    if n["id"] not in visited:
                        visited.add(n["id"])
                        connected.append(n)
                        queue.append((n["id"], depth + 1))

        return {
            "risk_score": entity.get("risk_score", 0.0),
            "found": True,
            "entity": entity,
            "network_depth": max_depth,
            "connected_entities": connected[:20],  # Limit to 20
        }

    def get_clusters(self) -> list:
        """
        Get all fraud clusters with entity counts.

        Returns:
            List of cluster dicts
        """
        with get_sqlite_connection() as conn:
            rows = conn.execute(
                """SELECT fc.*, COUNT(e.id) as entity_count
                   FROM fraud_clusters fc
                   LEFT JOIN entities e ON e.cluster_id = fc.id
                   GROUP BY fc.id
                   ORDER BY fc.risk_level DESC, entity_count DESC"""
            ).fetchall()

        clusters = []
        for row in rows:
            c = dict(row)
            c["name"] = c.get("cluster_name")
            clusters.append(c)

        return clusters

    async def start_evidence_package(self, cluster_id: int) -> str:
        """
        Start async evidence package generation via Celery.

        Args:
            cluster_id: Cluster to generate evidence for

        Returns:
            task_id for polling
        """
        task_id = task_store.create_task(task_type="evidence_package")
        
        # Dispatch Celery task
        from tasks.graph_tasks import generate_evidence_task
        generate_evidence_task.delay(cluster_id, task_id)
        
        logger.info("evidence_package_queued_to_celery", task_id=task_id, cluster_id=cluster_id)
        return task_id

    def get_stats(self) -> dict:
        """
        Get fraud network graph statistics.

        Returns:
            dict matching GraphStatsResponse schema
        """
        with get_sqlite_connection() as conn:
            total_entities = conn.execute("SELECT COUNT(*) as cnt FROM entities").fetchone()["cnt"]
            total_edges = conn.execute("SELECT COUNT(*) as cnt FROM relationships").fetchone()["cnt"]
            active_clusters = conn.execute(
                "SELECT COUNT(*) as cnt FROM fraud_clusters WHERE status = 'active'"
            ).fetchone()["cnt"]

            # Find highest risk cluster
            highest_row = conn.execute(
                """SELECT fc.*, COUNT(e.id) as entity_count
                   FROM fraud_clusters fc
                   LEFT JOIN entities e ON e.cluster_id = fc.id
                   WHERE fc.risk_level = 'HIGH' AND fc.status = 'active'
                   GROUP BY fc.id
                   ORDER BY entity_count DESC
                   LIMIT 1"""
            ).fetchone()

            highest_risk_cluster = None
            if highest_row:
                c = dict(highest_row)
                c["name"] = c.get("cluster_name")
                highest_risk_cluster = c

        return {
            "total_entities": total_entities,
            "total_edges": total_edges,
            "active_clusters": active_clusters,
            "highest_risk_cluster": highest_risk_cluster,
        }

    def add_report_to_graph(self, report_id: str, phone_numbers: List[str] = [], account_numbers: List[str] = [], description: str = ""):
        """
        Called every time a new fraud report is processed to build out the network graph.
        """
        victim_id = f"victim_{report_id}"
        
        with get_sqlite_connection() as conn:
            # Add victim node
            conn.execute("""
                INSERT OR IGNORE INTO entities (id, entity_type, value, risk_score)
                VALUES (?, 'victim', ?, 0.1)
            """, (victim_id, description[:50]))
            
            # Add phone number nodes + link to victim
            for phone in phone_numbers:
                if not phone:
                    continue
                node_id = f"phone_{phone}"
                conn.execute("""
                    INSERT OR IGNORE INTO entities (id, entity_type, value, risk_score, report_count)
                    VALUES (?, 'phone', ?, 0.9, 0)
                """, (node_id, phone))
                
                # Update report count
                conn.execute("""
                    UPDATE entities SET report_count = report_count + 1 WHERE id = ?
                """, (node_id,))
                
                # Check if relationship already exists
                existing = conn.execute(
                    "SELECT id, weight FROM relationships WHERE source_id = ? AND target_id = ? AND relationship = ?",
                    (node_id, victim_id, "called")
                ).fetchone()
                
                if existing:
                    conn.execute(
                        "UPDATE relationships SET weight = weight + 1.0 WHERE id = ?",
                        (existing["id"],)
                    )
                else:
                    conn.execute("""
                        INSERT INTO relationships (source_id, target_id, relationship, weight, linked_report_id)
                        VALUES (?, ?, 'called', 1.0, ?)
                    """, (node_id, victim_id, report_id))
            
            # Add account number nodes + link to victim
            for account in account_numbers:
                if not account:
                    continue
                node_id = f"account_{account}"
                conn.execute("""
                    INSERT OR IGNORE INTO entities (id, entity_type, value, risk_score, report_count)
                    VALUES (?, 'account', ?, 0.8, 0)
                """, (node_id, account))
                
                # Update report count
                conn.execute("""
                    UPDATE entities SET report_count = report_count + 1 WHERE id = ?
                """, (node_id,))
                
                # Check if relationship already exists
                existing = conn.execute(
                    "SELECT id, weight FROM relationships WHERE source_id = ? AND target_id = ? AND relationship = ?",
                    (node_id, victim_id, "transacted_with")
                ).fetchone()
                
                if existing:
                    conn.execute(
                        "UPDATE relationships SET weight = weight + 1.0 WHERE id = ?",
                        (existing["id"],)
                    )
                else:
                    conn.execute("""
                        INSERT INTO relationships (source_id, target_id, relationship, weight, linked_report_id)
                        VALUES (?, ?, 'transacted_with', 1.0, ?)
                    """, (node_id, victim_id, report_id))
        
        # Recompute community detection and centrality after adding new data
        self._recompute_clusters()

    def _load_graph_from_db(self) -> nx.Graph:
        """Load the entities and relationships from the database into a NetworkX graph."""
        G = nx.Graph()
        with get_sqlite_connection() as conn:
            # Load all nodes
            nodes = conn.execute("SELECT id FROM entities").fetchall()
            for node in nodes:
                G.add_node(node["id"])
            
            # Load all edges
            edges = conn.execute("SELECT source_id, target_id, weight FROM relationships").fetchall()
            for edge in edges:
                if edge["source_id"] and edge["target_id"]:
                    G.add_edge(edge["source_id"], edge["target_id"], weight=edge["weight"])
        return G

    def _recompute_clusters(self):
        """Runs Louvain community detection and centrality updates on the current graph."""
        try:
            G = self._load_graph_from_db()
            if len(G.nodes) < 3:
                logger.info("graph_too_small_skipping_clustering", node_count=len(G.nodes))
                return
            
            # 1. Louvain Community Detection (requires undirected graph)
            partition = community_louvain.best_partition(G)
            
            # 2. Degree and betweenness centrality to identify mastermind/mule nodes
            centrality = nx.betweenness_centrality(G)
            
            # 3. Update SQLite database with new cluster_id and is_central flag
            with get_sqlite_connection() as conn:
                for node_id, cluster_id in partition.items():
                    # Centrality threshold: top nodes in the network or score > 0.2
                    is_central = 1 if centrality.get(node_id, 0.0) > 0.2 else 0
                    conn.execute("""
                        UPDATE entities
                        SET cluster_id = ?, is_central = ?
                        WHERE id = ?
                    """, (cluster_id, is_central, node_id))
                
                # 4. Synchronize the fraud_clusters table
                cluster_groups = {}
                for node_id, cluster_id in partition.items():
                    if cluster_id not in cluster_groups:
                        cluster_groups[cluster_id] = []
                    cluster_groups[cluster_id].append(node_id)
                
                for cid, members in cluster_groups.items():
                    size = len(members)
                    placeholders = ",".join("?" * size)
                    risk_row = conn.execute(
                        f"SELECT MAX(risk_score) as max_risk FROM entities WHERE id IN ({placeholders})",
                        members
                    ).fetchone()
                    max_risk = risk_row["max_risk"] if risk_row and risk_row["max_risk"] is not None else 0.0
                    
                    risk_level = "LOW"
                    if max_risk >= 0.7:
                        risk_level = "HIGH"
                    elif max_risk >= 0.4:
                        risk_level = "MEDIUM"
                        
                    # Check if cluster entry exists
                    exists = conn.execute("SELECT id FROM fraud_clusters WHERE id = ?", (cid,)).fetchone()
                    if not exists:
                        # Find operation type: most common entity type in the cluster
                        op_row = conn.execute(
                            f"SELECT entity_type, COUNT(*) as cnt FROM entities WHERE id IN ({placeholders}) GROUP BY entity_type ORDER BY cnt DESC LIMIT 1",
                            members
                        ).fetchone()
                        op_type = op_row["entity_type"] if op_row else "general"
                        
                        conn.execute("""
                            INSERT INTO fraud_clusters (id, cluster_name, size, risk_level, operation_type, status)
                            VALUES (?, ?, ?, ?, ?, 'active')
                        """, (cid, f"Fraud Ring {cid}", size, risk_level, op_type))
                    else:
                        conn.execute("""
                            UPDATE fraud_clusters
                            SET size = ?, risk_level = ?
                            WHERE id = ?
                        """, (size, risk_level, cid))
                        
            logger.info("graph_clusters_recomputed", total_nodes=len(G.nodes), total_clusters=len(cluster_groups))
        except Exception as e:
            logger.error("graph_clustering_failed", error=str(e))


# Module-level singleton
_graph_service: Optional[GraphService] = None


def get_graph_service() -> GraphService:
    """Get the GraphService singleton."""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
