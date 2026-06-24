from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

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

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ScamScript(BaseModel):
    id: str
    scam_type: str = Field(description="'digital_arrest' | 'kyc_fraud' | 'customs_seizure' | 'drug_trafficking'")
    agency_impersonated: str = Field(description="'CBI' | 'ED' | 'Customs' | 'TRAI' | 'Police'")
    script_text: str
    embedding: List[float] = Field(default_factory=list)
    reported_count: int = 0
    first_seen: datetime
    last_seen: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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
