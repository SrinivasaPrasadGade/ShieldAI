"""
Pydantic models for ShieldAI backend.

Contains:
- Firestore document schemas (existing)
- SQLite model schemas (existing)
- API request/response models (new)
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


# ==========================================
# FIRESTORE NESTED HELPER MODELS
# ==========================================

class VictimLocation(BaseModel):
    city: str
    state: str
    pincode: str
    lat: float
    lng: float

class DetoxifyScores(BaseModel):
    toxicity: float
    threat: float
    insult: float

class CurrencyLocation(BaseModel):
    lat: float
    lng: float
    city: str

class AlertLocation(BaseModel):
    lat: float
    lng: float
    city: str

# ==========================================
# FIRESTORE COLLECTION SCHEMAS
# ==========================================

class FraudReport(BaseModel):
    id: str
    source: str = Field(description="'whatsapp' | 'web' | 'api'")
    report_type: str = Field(description="'digital_arrest' | 'financial_fraud' | 'fake_currency' | 'other'")
    description: str
    phone_numbers: List[str] = Field(default_factory=list)
    account_numbers: List[str] = Field(default_factory=list)
    victim_location: VictimLocation
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_label: str = Field(description="'HIGH' | 'MEDIUM' | 'LOW'")
    gemini_classification: str
    detoxify_scores: DetoxifyScores
    bert_confidence: float
    scam_script_match: float
    status: str = Field(default="pending", description="'pending' | 'verified' | 'resolved'")
    created_at: datetime
    updated_at: datetime

class CurrencyCheck(BaseModel):
    id: str
    submitted_by: str = Field(description="'teller' | 'citizen' | 'officer'")
    denomination: int = Field(description="500 | 2000 | 200 | 100 etc.")
    image_url: str
    verdict: str = Field(description="'GENUINE' | 'SUSPICIOUS' | 'COUNTERFEIT'")
    confidence: float
    failed_features: List[str] = Field(default_factory=list)
    gemini_analysis: str
    location: CurrencyLocation
    created_at: datetime

class Alert(BaseModel):
    id: str
    alert_type: str = Field(description="'scam_detected' | 'ficn_detected' | 'fraud_ring_identified' | 'new_hotspot'")
    severity: str = Field(description="'CRITICAL' | 'HIGH' | 'MEDIUM'")
    title: str
    description: str
    linked_report_id: Optional[str] = None
    linked_phone: Optional[str] = None
    location: AlertLocation
    is_read: bool = False
    created_at: datetime

class ScamScript(BaseModel):
    id: str
    scam_type: str = Field(description="'digital_arrest' | 'kyc_fraud' | 'customs_seizure' | 'drug_trafficking'")
    agency_impersonated: str = Field(description="'CBI' | 'ED' | 'Customs' | 'TRAI' | 'Police'")
    script_text: str
    embedding: List[float] = Field(default_factory=list)
    reported_count: int = 0
    first_seen: datetime
    last_seen: datetime

class DailySummary(BaseModel):
    total_reports: int = 0
    high_risk_count: int = 0
    ficn_detected: int = 0
    cities_affected: List[str] = Field(default_factory=list)
    fraud_types_breakdown: Dict[str, int] = Field(default_factory=dict)

# ==========================================
# SQLITE MODEL SCHEMAS
# ==========================================

class EntityModel(BaseModel):
    id: str
    entity_type: str = Field(description="'phone' | 'account' | 'device' | 'victim' | 'suspect'")
    value: str
    risk_score: float = 0.0
    report_count: int = 0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    cluster_id: Optional[int] = None
    is_central: bool = False

class RelationshipModel(BaseModel):
    id: Optional[int] = None
    source_id: str
    target_id: str
    relationship: str = Field(description="'called' | 'transacted_with' | 'same_device' | 'mule_for'")
    weight: float = 1.0
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    linked_report_id: Optional[str] = None

class FraudClusterModel(BaseModel):
    id: Optional[int] = None
    cluster_name: Optional[str] = None
    size: Optional[int] = 0
    risk_level: Optional[str] = Field(default="LOW", description="'HIGH' | 'MEDIUM' | 'LOW'")
    operation_type: Optional[str] = None
    geographic_span: Optional[str] = Field(default="Local", description="'Local' | 'Inter-state' | 'Cross-border'")
    first_activity: Optional[str] = None
    last_activity: Optional[str] = None
    status: str = "active"

class IncidentModel(BaseModel):
    id: Optional[int] = None
    report_id: Optional[str] = None
    incident_type: str = Field(description="'scam_call' | 'ficn' | 'financial_fraud'")
    lat: float
    lng: float
    city: str
    state: str
    pincode: str
    severity: str
    created_at: str


# ==========================================
# API REQUEST / RESPONSE SCHEMAS
# ==========================================

# ── Scam Detection ───────────────────────────────────────────

class ScamAnalyzeRequest(BaseModel):
    """Request body for POST /api/scam/analyze"""
    text: str = Field(..., min_length=1, max_length=10000, description="Text to analyze for scam patterns")
    source_phone: Optional[str] = Field(None, description="Phone number the text/call originated from")
    language: str = Field("en", description="Language code (en, hi, ta, te, etc.)")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Text cannot be empty or whitespace only")
        return v.strip()


class ScamAnalyzeResponse(BaseModel):
    """Response for POST /api/scam/analyze"""
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_label: str = Field(..., description="HIGH | MEDIUM | LOW")
    classification: str = Field(..., description="Classification category")
    scam_type: Optional[str] = Field(None, description="Specific scam type if identified")
    explanation: str = Field(..., description="Human-readable explanation of the analysis")
    recommended_action: str = Field(..., description="What the user should do")
    alert_id: Optional[str] = Field(None, description="Alert ID if high risk triggered an alert")


class ScamAudioResponse(ScamAnalyzeResponse):
    """Response for POST /api/scam/analyze-audio"""
    transcript: str = Field(..., description="Transcribed text from the audio file")


class AlertItem(BaseModel):
    """Single alert in the alerts list."""
    id: str
    alert_type: str
    severity: str
    title: str
    description: str
    linked_report_id: Optional[str] = None
    linked_phone: Optional[str] = None
    location: Optional[AlertLocation] = None
    is_read: bool = False
    created_at: str


class AlertListResponse(BaseModel):
    """Response for GET /api/scam/alerts"""
    alerts: List[AlertItem]
    total: int


class TrendPoint(BaseModel):
    """Single data point in a trend series."""
    date: str
    count: int


class ScamStatsResponse(BaseModel):
    """Response for GET /api/scam/stats"""
    total_analyzed: int
    high_risk: int
    medium_risk: int
    top_scam_types: Dict[str, int]
    trend: List[TrendPoint]


# ── Currency Detection ───────────────────────────────────────

class CurrencyVerifyResponse(BaseModel):
    """Response for POST /api/currency/verify"""
    task_id: str


class CurrencyResultResponse(BaseModel):
    """Response for GET /api/currency/result/{task_id}"""
    status: Literal["pending", "processing", "complete", "failed"]
    verdict: Optional[str] = None
    confidence: Optional[float] = None
    failed_features: Optional[List[str]] = None
    analysis: Optional[str] = None
    alert_generated: Optional[bool] = None


class FICNIncident(BaseModel):
    """Single FICN incident on the map."""
    lat: float
    lng: float
    city: str
    denomination: int
    date: str


class FICNMapResponse(BaseModel):
    """Response for GET /api/currency/ficn-map"""
    incidents: List[FICNIncident]


class CurrencyStatsResponse(BaseModel):
    """Response for GET /api/currency/stats"""
    total_checked: int
    ficn_detected: int
    detection_rate: float
    top_denominations: Dict[str, int]


# ── Fraud Network Graph ─────────────────────────────────────

class NodeSchema(BaseModel):
    """Node in the fraud network graph."""
    id: str
    entity_type: str
    value: str
    risk_score: float
    report_count: int
    cluster_id: Optional[int] = None
    is_central: bool = False


class EdgeSchema(BaseModel):
    """Edge in the fraud network graph."""
    id: Optional[int] = None
    source_id: str
    target_id: str
    relationship: str
    weight: float = 1.0
    linked_report_id: Optional[str] = None


class ClusterSchema(BaseModel):
    """Fraud cluster summary."""
    id: int
    name: Optional[str] = None
    size: int = 0
    risk_level: str = "LOW"
    operation_type: Optional[str] = None
    entity_count: int = 0


class GraphNetworkResponse(BaseModel):
    """Response for GET /api/graph/network"""
    nodes: List[NodeSchema]
    edges: List[EdgeSchema]
    clusters: List[ClusterSchema]


class ReportSchema(BaseModel):
    """Connected report summary."""
    id: str
    report_type: str
    description: str
    risk_score: float
    created_at: str


class GraphNodeResponse(BaseModel):
    """Response for GET /api/graph/node/{entity_id}"""
    entity: NodeSchema
    connected_reports: List[ReportSchema]
    centrality_score: float
    cluster: Optional[ClusterSchema] = None


class GraphQueryRequest(BaseModel):
    """Request body for POST /api/graph/query"""
    phone_number: Optional[str] = None
    account_number: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_required(self):
        if not self.phone_number and not self.account_number:
            raise ValueError("At least one of phone_number or account_number must be provided")
        return self


class GraphQueryResponse(BaseModel):
    """Response for POST /api/graph/query"""
    risk_score: float
    found: bool
    entity: Optional[NodeSchema] = None
    network_depth: int = 0
    connected_entities: List[NodeSchema] = Field(default_factory=list)


class GraphClustersResponse(BaseModel):
    """Response for GET /api/graph/clusters"""
    clusters: List[ClusterSchema]


class GraphStatsResponse(BaseModel):
    """Response for GET /api/graph/stats"""
    total_entities: int
    total_edges: int
    active_clusters: int
    highest_risk_cluster: Optional[ClusterSchema] = None


# ── Geospatial ───────────────────────────────────────────────

class GeoIncident(BaseModel):
    """Single geospatial incident."""
    lat: float
    lng: float
    type: str
    severity: str
    city: str
    created_at: str


class GeoIncidentsResponse(BaseModel):
    """Response for GET /api/geo/incidents"""
    incidents: List[GeoIncident]


class HeatmapPoint(BaseModel):
    """Single point for Leaflet.heat."""
    lat: float
    lng: float
    weight: float


class HeatmapResponse(BaseModel):
    """Response for GET /api/geo/heatmap"""
    points: List[HeatmapPoint]


class Hotspot(BaseModel):
    """Detected hotspot."""
    lat: float
    lng: float
    radius: float
    incident_count: int
    dominant_type: str
    risk_level: str


class HotspotsResponse(BaseModel):
    """Response for GET /api/geo/hotspots"""
    hotspots: List[Hotspot]


class CityStats(BaseModel):
    """Per-city statistics."""
    name: str
    lat: float
    lng: float
    total_incidents: int
    high_risk_count: int


class CityStatsResponse(BaseModel):
    """Response for GET /api/geo/city-stats"""
    cities: List[CityStats]


# ── Citizen Shield ───────────────────────────────────────────

class CitizenChatRequest(BaseModel):
    """Request body for POST /api/citizen/chat"""
    message: str = Field(..., min_length=1, max_length=5000)
    session_id: str = Field(..., min_length=1)
    language: str = Field("en")

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace only")
        return v.strip()


class CitizenChatResponse(BaseModel):
    """Response for POST /api/citizen/chat"""
    response: str
    risk_assessment: Optional[Dict[str, Any]] = None
    report_link: Optional[str] = None
    session_id: str


class CitizenReportRequest(BaseModel):
    """Request body for POST /api/citizen/report"""
    description: str = Field(..., min_length=10, max_length=10000)
    phone_number: Optional[str] = None
    location: Optional[str] = None
    contact_email: Optional[str] = None

    @field_validator("contact_email")
    @classmethod
    def validate_email(cls, v):
        if v is not None and v.strip():
            v = v.strip()
            if "@" not in v or "." not in v.split("@")[-1]:
                raise ValueError("Invalid email format")
        return v


class CitizenReportResponse(BaseModel):
    """Response for POST /api/citizen/report"""
    report_id: str
    reference_number: str
    next_steps: List[str]


class ReportStatusResponse(BaseModel):
    """Response for GET /api/citizen/report/{report_id}"""
    status: str
    updates: List[str]
    created_at: str


# ── Phone Number Risk Score ──────────────────────────────────

class PhoneRiskRequest(BaseModel):
    """Request body for POST /api/risk/phone"""
    phone_number: str = Field(..., min_length=10, max_length=15)

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = v.strip().replace(" ", "").replace("-", "")
        if cleaned.startswith("+91"):
            cleaned = cleaned[3:]
        elif cleaned.startswith("91") and len(cleaned) == 12:
            cleaned = cleaned[2:]
        elif cleaned.startswith("0"):
            cleaned = cleaned[1:]
        
        if not cleaned.isdigit() or len(cleaned) < 10:
            raise ValueError("Invalid phone number format. Expected Indian phone number (10+ digits)")
        return v


class PhoneRiskResponse(BaseModel):
    """Response for POST /api/risk/phone"""
    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_label: str
    report_count: int
    last_reported: Optional[str] = None
    fraud_types: List[str] = Field(default_factory=list)
    in_network: bool


# ── Common Error Response ────────────────────────────────────

class ErrorResponse(BaseModel):
    """Standard error response structure."""
    error: str
    message: str
    request_id: Optional[str] = None
