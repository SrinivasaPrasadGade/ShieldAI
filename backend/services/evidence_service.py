"""
Evidence package generation service for ShieldAI.

Compiles fraud cluster data into structured evidence summaries
for law enforcement use.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from logging_config import get_logger
from models.database import get_sqlite_connection
from models import task_store

logger = get_logger("shield_ai.evidence")


class EvidenceService:
    """Generates evidence packages for fraud clusters."""

    async def generate_evidence_package(self, cluster_id: int, task_id: str) -> None:
        """
        Generate a structured evidence package for a fraud cluster.
        Called as a background task.

        Args:
            cluster_id: Cluster to generate evidence for
            task_id: Task ID to update with results
        """
        try:
            task_store.update_task(task_id, status="processing")

            # 1. Fetch cluster details
            with get_sqlite_connection() as conn:
                cluster_row = conn.execute(
                    "SELECT * FROM fraud_clusters WHERE id = ?", (cluster_id,)
                ).fetchone()

                if not cluster_row:
                    task_store.update_task(task_id, status="failed", error=f"Cluster {cluster_id} not found")
                    return

                cluster = dict(cluster_row)

                # 2. Fetch all entities in the cluster
                raw_entities = [
                    dict(row) for row in conn.execute(
                        "SELECT * FROM entities WHERE cluster_id = ? ORDER BY risk_score DESC",
                        (cluster_id,),
                    ).fetchall()
                ]
                
                # Mask/redact sensitive values (PII)
                entities = []
                for entity in raw_entities:
                    if entity.get("entity_type") == "phone":
                        p = entity["value"]
                        entity["value"] = p[-4:].rjust(len(p), '*') if len(p) > 4 else p
                    entities.append(entity)

                # 3. Fetch all relationships between these entities
                entity_ids = [e["id"] for e in entities]
                relationships = []
                if entity_ids:
                    placeholders = ",".join("?" * len(entity_ids))
                    relationships = [
                        dict(row) for row in conn.execute(
                            f"""SELECT * FROM relationships
                                WHERE source_id IN ({placeholders})
                                   OR target_id IN ({placeholders})""",
                            entity_ids + entity_ids,
                        ).fetchall()
                    ]

            # 4. Fetch linked fraud reports from Firestore
            linked_reports = []
            report_ids = {r.get("linked_report_id") for r in relationships if r.get("linked_report_id")}

            if report_ids:
                try:
                    from models.database import get_firestore_client
                    db = get_firestore_client()
                    for rid in report_ids:
                        doc = db.collection("fraud_reports").document(rid).get()
                        if doc.exists:
                            data = doc.to_dict()
                            
                            # Mask phone numbers in linked reports
                            phone_numbers = data.get("phone_numbers", [])
                            masked_phones = [p[-4:].rjust(len(p), '*') if len(p) > 4 else p for p in phone_numbers]
                            
                            # Clean/redact description of email addresses and phone numbers
                            desc = data.get("description", "")
                            import re
                            # Redact email addresses
                            desc = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[REDACTED_EMAIL]', desc)
                            # Redact phone numbers (simple pattern)
                            desc = re.sub(r'\+?\d{10,12}', '[REDACTED_PHONE]', desc)

                            linked_reports.append({
                                "id": rid,
                                "report_type": data.get("report_type", "unknown"),
                                "description": desc,
                                "risk_score": data.get("risk_score", 0),
                                "phone_numbers": masked_phones,
                                "created_at": str(data.get("created_at", "")),
                            })
                except Exception as e:
                    logger.error("fetch_linked_reports_failed", error=str(e))

            # 5. Compile evidence package
            now = datetime.now(timezone.utc).isoformat()

            evidence = {
                "package_id": task_id,
                "generated_at": now,
                "cluster": {
                    "id": cluster["id"],
                    "name": cluster.get("cluster_name", f"Cluster #{cluster['id']}"),
                    "risk_level": cluster.get("risk_level", "UNKNOWN"),
                    "operation_type": cluster.get("operation_type", "Unknown"),
                    "geographic_span": cluster.get("geographic_span", "Unknown"),
                    "status": cluster.get("status", "active"),
                    "first_activity": cluster.get("first_activity"),
                    "last_activity": cluster.get("last_activity"),
                },
                "summary": {
                    "total_entities": len(entities),
                    "total_relationships": len(relationships),
                    "total_linked_reports": len(linked_reports),
                    "high_risk_entities": sum(1 for e in entities if e.get("risk_score", 0) >= 0.7),
                    "central_nodes": sum(1 for e in entities if e.get("is_central")),
                    "entity_types": {},
                    "relationship_types": {},
                },
                "entities": entities,
                "relationships": relationships,
                "linked_reports": linked_reports,
                "key_findings": [],
            }

            # Compute entity type breakdown
            for e in entities:
                etype = e.get("entity_type", "unknown")
                evidence["summary"]["entity_types"][etype] = evidence["summary"]["entity_types"].get(etype, 0) + 1

            # Compute relationship type breakdown
            for r in relationships:
                rtype = r.get("relationship", "unknown")
                evidence["summary"]["relationship_types"][rtype] = evidence["summary"]["relationship_types"].get(rtype, 0) + 1

            # Generate key findings
            central = [e for e in entities if e.get("is_central")]
            if central:
                evidence["key_findings"].append(
                    f"Identified {len(central)} central node(s) in the network: "
                    f"{', '.join(e['value'] for e in central[:5])}"
                )

            high_risk = [e for e in entities if e.get("risk_score", 0) >= 0.7]
            if high_risk:
                evidence["key_findings"].append(
                    f"{len(high_risk)} entities flagged as high risk (score ≥ 0.7)"
                )

            if linked_reports:
                evidence["key_findings"].append(
                    f"Network linked to {len(linked_reports)} fraud report(s)"
                )

            # 5.5 Generate Gemini Text Synthesis report
            from services.gemini_service import get_gemini_service
            gemini_svc = get_gemini_service()
            try:
                synthesis = await gemini_svc.generate_evidence_package(evidence)
                evidence["gemini_synthesis"] = synthesis
            except Exception as e:
                logger.error("evidence_synthesis_failed", error=str(e))
                evidence["gemini_synthesis"] = "Failed to generate AI synthesis report."

            # 5.6 Add Chain of Custody and Digital Signature
            evidence["chain_of_custody"] = {
                "generated_by": "ShieldAI System",
                "timestamp": now,
                "version": "1.0",
                "hash_algorithm": "SHA-256",
            }
            
            import json, hashlib, hmac
            from config import settings
            evidence_str = json.dumps(evidence, sort_keys=True)
            secret = settings.SECRET_KEY.encode('utf-8')
            signature = hmac.new(secret, evidence_str.encode('utf-8'), hashlib.sha256).hexdigest()
            
            evidence["digital_signature"] = signature

            # 6. Store result
            task_store.update_task(task_id, status="complete", result=evidence)

            logger.info(
                "evidence_package_generated",
                task_id=task_id,
                cluster_id=cluster_id,
                entities=len(entities),
                relationships=len(relationships),
            )

        except Exception as e:
            logger.error("evidence_generation_failed", task_id=task_id, error=str(e))
            task_store.update_task(task_id, status="failed", error=str(e))


# Module-level singleton
_evidence_service: EvidenceService | None = None


def get_evidence_service() -> EvidenceService:
    """Get the EvidenceService singleton."""
    global _evidence_service
    if _evidence_service is None:
        _evidence_service = EvidenceService()
    return _evidence_service
