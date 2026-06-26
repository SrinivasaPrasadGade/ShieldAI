import os
import sys
import random
import uuid
import sqlite3
from datetime import datetime, timedelta, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import get_sqlite_connection, get_firestore_client, init_sqlite_db

# ==========================================================
# DEMO DATA CONSTANTS FROM SECTION 14
# ==========================================================

DEMO_INCIDENTS = [
    # Digital Arrest Scams — Major metros get the most
    {"type": "digital_arrest", "city": "Hyderabad", "lat": 17.3850, "lng": 78.4867, "severity": "HIGH", "count": 23},
    {"type": "digital_arrest", "city": "Mumbai", "lat": 19.0760, "lng": 72.8777, "severity": "HIGH", "count": 31},
    {"type": "digital_arrest", "city": "Delhi", "lat": 28.7041, "lng": 77.1025, "severity": "CRITICAL", "count": 45},
    {"type": "digital_arrest", "city": "Bengaluru", "lat": 12.9716, "lng": 77.5946, "severity": "HIGH", "count": 28},
    {"type": "digital_arrest", "city": "Chennai", "lat": 13.0827, "lng": 80.2707, "severity": "MEDIUM", "count": 17},
    {"type": "digital_arrest", "city": "Pune", "lat": 18.5204, "lng": 73.8567, "severity": "HIGH", "count": 19},
    {"type": "digital_arrest", "city": "Kolkata", "lat": 22.5726, "lng": 88.3639, "severity": "MEDIUM", "count": 14},
    {"type": "digital_arrest", "city": "Ahmedabad", "lat": 23.0225, "lng": 72.5714, "severity": "MEDIUM", "count": 11},
    
    # FICN — Border regions + financial hubs
    {"type": "ficn", "city": "Malda", "lat": 25.0108, "lng": 88.1406, "severity": "HIGH", "count": 8},
    {"type": "ficn", "city": "Kolkata", "lat": 22.5726, "lng": 88.3639, "severity": "HIGH", "count": 12},
    {"type": "ficn", "city": "Mumbai", "lat": 19.0760, "lng": 72.8777, "severity": "MEDIUM", "count": 6},
    {"type": "ficn", "city": "Surat", "lat": 21.1702, "lng": 72.8311, "severity": "MEDIUM", "count": 5},
    {"type": "ficn", "city": "Amritsar", "lat": 31.6340, "lng": 74.8723, "severity": "HIGH", "count": 7},
    
    # Investment Fraud
    {"type": "investment_fraud", "city": "Hyderabad", "lat": 17.3850, "lng": 78.4867, "severity": "HIGH", "count": 16},
    {"type": "investment_fraud", "city": "Bengaluru", "lat": 12.9716, "lng": 77.5946, "severity": "HIGH", "count": 21},
    {"type": "investment_fraud", "city": "Gurgaon", "lat": 28.4595, "lng": 77.0266, "severity": "HIGH", "count": 13},
]

DEMO_FRAUD_CLUSTERS = [
    {
        "id": 101,  # Non-conflicting custom IDs
        "name": "Operation Mamba", 
        "type": "digital_arrest", 
        "size": 12,
        "risk": "CRITICAL",
        "geographic_span": "Cross-border",
        "phone_nodes": ["+917892019283", "+919987123456", "+918891987654"],
        "account_nodes": ["HDFC00010023", "AXIS00230045", "SBIN00670089"],
        "victim_nodes": 34,
        "estimated_damage": "Rs 4.2 crore"
    },
    {
        "id": 102,
        "name": "Ring Kappa",
        "type": "investment_fraud",
        "size": 8,
        "risk": "HIGH",
        "geographic_span": "Inter-state",
        "phone_nodes": ["+919878112233", "+916541445566"],
        "account_nodes": ["ICIC00891234", "KKBK00419876"],
        "victim_nodes": 67,
        "estimated_damage": "Rs 1.8 crore"
    }
]

# ==========================================================
# NARRATIVE TEMPLATES FOR UNIQUE REPORT GENERATION
# ==========================================================

DIGITAL_ARREST_TEMPLATES = [
    "Received a WhatsApp call from {phone} claiming to be CBI Officer {name}. They stated my Aadhaar number was found linked to a drug trafficking case in Mumbai. They threatened me with immediate arrest and forced me to stay on Skype video call for verification. Under psychological pressure, I transferred Rs {amount} to a 'verification account' they provided.",
    "A person pretending to be Customs Officer {name} called me saying a courier package sent from Taiwan containing MDMA and fake passports was seized in my name. They demanded Rs {amount} as a security clearance fee to avoid prosecution. I transferred the money to their account.",
    "I was contacted by someone claiming to be from TRAI. They told me my phone line would be disconnected in 2 hours because a duplicate SIM in my name was used to send illegal harassment messages. They connected me to a fake 'cyber cell' officer {name} who forced me to verify my bank balance and transfer Rs {amount} for verification.",
    "Received a phone call from ED inspector {name}. He claimed my bank account was flagged in a money laundering transaction related to Jet Airways. He threatened me with digital arrest and demanded Rs {amount} as a temporary clearance deposit. I complied because I was extremely scared."
]

INVESTMENT_FRAUD_TEMPLATES = [
    "I was added to a Telegram group promising 300% daily returns on stock market tips. The admin, {name}, convinced me to download a custom trading app. I deposited Rs {amount} into their provided UPI/bank account. Now they are demanding another 20% tax before I can withdraw any funds, and I cannot access my money.",
    "A WhatsApp contact named {name} introduced me to a high-yield crypto investment platform. I made multiple transfers totaling Rs {amount} to various bank accounts. The platform dashboard showed huge profits, but when I attempted to withdraw, the account was blocked and they stopped responding to my messages.",
    "I invested Rs {amount} in a part-time job scam offering commissions for rating hotels online. The contact person, {name}, kept asking for higher deposit amounts to unlock VIP tasks. After transferring the money, I was kicked out of the group and all contact was cut off."
]

FICN_TEMPLATES = [
    "A customer at a retail counter attempted to pass a counterfeit Rs 500 note. Serial number matches {serial}. Note lacks the correct colour-shift ink and security thread alignment under inspection.",
    "During cash sorting at the bank branch teller counter, a suspicious high-denomination Rs 500 fake note was detected. Security features are extremely poor with a printed watermark and misaligned serial number: {serial}.",
    "Counterfeit Rs 500 note seized from a local vendor. The note has a paper-like texture and no microprint under magnifying glass. Serial number: {serial}."
]

FAILED_FEATURES_FICN = [
    ["Security thread printed instead of embedded", "Color-shift ink lacks luster", "Watermark pattern is crude"],
    ["Microprint is blurred under 10x magnification", "Serial number font alignment is incorrect"],
    ["Intaglio printing texture is completely flat", "No fluorescence under UV light", "Security thread has incorrect placement"]
]

def generate_narrative(scam_type):
    """Generates a realistic scam report description and related entities."""
    names = ["Aarav Sharma", "Priya Patel", "Amit Verma", "Suresh Kumar", "Neha Gupta", "Vikram Singh", "Anjali Rao", "Rajesh Iyer", "Sunita Devi", "Karan Malhotra"]
    cbi_officers = ["Rajesh Kumar", "Inspector Vijay", "Officer K. K. Sharma", "CBI Agent Alok Sen", "ED Director Sanjay Mishra"]
    serials = ["4AB123456", "7CD654321", "2EF987654", "9GH345678"]

    name = random.choice(names)
    officer = random.choice(cbi_officers)
    amount = f"{random.randint(2, 95) * 10000:,}"
    phone = f"91{random.randint(7000000000, 9999999999)}"
    serial = random.choice(serials) + str(random.randint(10, 99))

    if scam_type == "digital_arrest":
        desc_template = random.choice(DIGITAL_ARREST_TEMPLATES)
        description = desc_template.format(phone="+" + phone, name=officer, amount=amount)
        return description, ["+" + phone], []
    elif scam_type == "investment_fraud":
        desc_template = random.choice(INVESTMENT_FRAUD_TEMPLATES)
        description = desc_template.format(name=name, amount=amount)
        return description, [f"+91{random.randint(7000000000, 9999999999)}"], [f"ACC{random.randint(100000000, 999999999)}"]
    else:  # ficn
        desc_template = random.choice(FICN_TEMPLATES)
        description = desc_template.format(serial=serial)
        return description, [], []

# ==========================================================
# SQLITE SEEDING OPERATIONS
# ==========================================================

def seed_sqlite_rings(conn):
    """Seeds the coordinated fraud rings Operation Mamba & Ring Kappa into SQLite."""
    print("Seeding coordinated fraud rings in SQLite...")
    cursor = conn.cursor()
    
    # 1. Clean existing demo rings
    cursor.execute("DELETE FROM fraud_clusters WHERE id IN (101, 102)")
    cursor.execute("""
        DELETE FROM entities 
        WHERE id IN (
            'ent-ph-m1', 'ent-ph-m2', 'ent-ph-m3', 'ent-ac-m1', 'ent-ac-m2', 'ent-ac-m3', 'ent-su-m1', 'ent-vi-m1', 'ent-vi-m2', 'ent-vi-m3',
            'ent-ph-k1', 'ent-ph-k2', 'ent-ac-k1', 'ent-ac-k2', 'ent-su-k1', 'ent-vi-k1', 'ent-vi-k2'
        )
    """)
    cursor.execute("""
        DELETE FROM relationships 
        WHERE source_id IN (
            'ent-ph-m1', 'ent-ph-m2', 'ent-ph-m3', 'ent-ac-m1', 'ent-ac-m2', 'ent-ac-m3', 'ent-su-m1', 'ent-vi-m1', 'ent-vi-m2', 'ent-vi-m3',
            'ent-ph-k1', 'ent-ph-k2', 'ent-ac-k1', 'ent-ac-k2', 'ent-su-k1', 'ent-vi-k1', 'ent-vi-k2'
        ) OR target_id IN (
            'ent-ph-m1', 'ent-ph-m2', 'ent-ph-m3', 'ent-ac-m1', 'ent-ac-m2', 'ent-ac-m3', 'ent-su-m1', 'ent-vi-m1', 'ent-vi-m2', 'ent-vi-m3',
            'ent-ph-k1', 'ent-ph-k2', 'ent-ac-k1', 'ent-ac-k2', 'ent-su-k1', 'ent-vi-k1', 'ent-vi-k2'
        )
    """)
    
    # 2. Insert fraud clusters
    for cluster in DEMO_FRAUD_CLUSTERS:
        cursor.execute("""
            INSERT INTO fraud_clusters (id, cluster_name, size, risk_level, operation_type, geographic_span, first_activity, last_activity, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (
            cluster["id"],
            cluster["name"],
            cluster["size"],
            cluster["risk"],
            cluster["type"],
            cluster["geographic_span"],
            "2025-01-01T10:00:00Z",
            "2025-06-25T12:00:00Z"
        ))

    # 3. Seed entities for Operation Mamba (cluster_id = 101)
    mamba_entities = [
        ("ent-ph-m1", "phone", "+917892019283", 0.98, 15, "2025-01-01", "2025-06-25", 101, 1),
        ("ent-ph-m2", "phone", "+919987123456", 0.92, 12, "2025-01-10", "2025-06-24", 101, 0),
        ("ent-ph-m3", "phone", "+918891987654", 0.88, 10, "2025-01-15", "2025-06-22", 101, 0),
        
        ("ent-ac-m1", "account", "HDFC00010023", 0.85, 8, "2025-02-01", "2025-06-25", 101, 0),
        ("ent-ac-m2", "account", "AXIS00230045", 0.82, 7, "2025-02-10", "2025-06-24", 101, 0),
        ("ent-ac-m3", "account", "SBIN00670089", 0.78, 6, "2025-02-15", "2025-06-22", 101, 0),
        
        ("ent-su-m1", "suspect", "SUSP-MAMBA-001", 0.99, 20, "2025-01-01", "2025-06-25", 101, 1),
        
        ("ent-vi-m1", "victim", "VIC-MAMBA-001 (Hyderabad)", 0.10, 1, "2025-06-18", "2025-06-18", 101, 0),
        ("ent-vi-m2", "victim", "VIC-MAMBA-002 (Mumbai)", 0.10, 1, "2025-06-20", "2025-06-20", 101, 0),
        ("ent-vi-m3", "victim", "VIC-MAMBA-003 (Delhi)", 0.10, 1, "2025-06-22", "2025-06-22", 101, 0)
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO entities (id, entity_type, value, risk_score, report_count, first_seen, last_seen, cluster_id, is_central)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, mamba_entities)
    
    # 4. Seed entities for Ring Kappa (cluster_id = 102)
    kappa_entities = [
        ("ent-ph-k1", "phone", "+919878112233", 0.88, 9, "2025-02-01", "2025-06-24", 102, 1),
        ("ent-ph-k2", "phone", "+916541445566", 0.82, 6, "2025-02-15", "2025-06-20", 102, 0),
        
        ("ent-ac-k1", "account", "ICIC00891234", 0.78, 5, "2025-03-01", "2025-06-24", 102, 0),
        ("ent-ac-k2", "account", "KKBK00419876", 0.70, 4, "2025-03-10", "2025-06-20", 102, 0),
        
        ("ent-su-k1", "suspect", "SUSP-KAPPA-001", 0.90, 12, "2025-02-01", "2025-06-24", 102, 1),
        
        ("ent-vi-k1", "victim", "VIC-KAPPA-001 (Bengaluru)", 0.10, 1, "2025-06-15", "2025-06-15", 102, 0),
        ("ent-vi-k2", "victim", "VIC-KAPPA-002 (Gurgaon)", 0.10, 1, "2025-06-19", "2025-06-19", 102, 0)
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO entities (id, entity_type, value, risk_score, report_count, first_seen, last_seen, cluster_id, is_central)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, kappa_entities)

    # 5. Seed relationships
    relationships = [
        # Operation Mamba Relationships
        ("ent-ph-m1", "ent-su-m1", "called", 5.0, "2025-01-01", "2025-06-25", "mamba_rpt_1"),
        ("ent-ph-m2", "ent-su-m1", "called", 4.0, "2025-01-10", "2025-06-24", "mamba_rpt_2"),
        ("ent-ph-m3", "ent-su-m1", "called", 3.0, "2025-01-15", "2025-06-22", "mamba_rpt_3"),
        
        ("ent-su-m1", "ent-ac-m1", "transacted_with", 8.0, "2025-02-01", "2025-06-25", None),
        ("ent-su-m1", "ent-ac-m2", "transacted_with", 7.0, "2025-02-10", "2025-06-24", None),
        ("ent-su-m1", "ent-ac-m3", "transacted_with", 6.0, "2025-02-15", "2025-06-22", None),
        
        ("ent-ph-m1", "ent-vi-m1", "called", 1.0, "2025-06-18", "2025-06-18", "mamba_rpt_v1"),
        ("ent-ph-m1", "ent-vi-m2", "called", 1.0, "2025-06-20", "2025-06-20", "mamba_rpt_v2"),
        ("ent-ph-m1", "ent-vi-m3", "called", 1.0, "2025-06-22", "2025-06-22", "mamba_rpt_v3"),
        
        ("ent-vi-m1", "ent-ac-m1", "transacted_with", 2.0, "2025-06-18", "2025-06-18", "mamba_rpt_v1"),
        ("ent-vi-m2", "ent-ac-m2", "transacted_with", 2.5, "2025-06-20", "2025-06-20", "mamba_rpt_v2"),
        ("ent-vi-m3", "ent-ac-m3", "transacted_with", 3.0, "2025-06-22", "2025-06-22", "mamba_rpt_v3"),
        
        # Ring Kappa Relationships
        ("ent-ph-k1", "ent-su-k1", "called", 4.0, "2025-02-01", "2025-06-24", "kappa_rpt_1"),
        ("ent-ph-k2", "ent-su-k1", "called", 3.0, "2025-02-15", "2025-06-20", "kappa_rpt_2"),
        
        ("ent-su-k1", "ent-ac-k1", "transacted_with", 6.0, "2025-03-01", "2025-06-24", None),
        ("ent-su-k1", "ent-ac-k2", "transacted_with", 5.0, "2025-03-10", "2025-06-20", None),
        
        ("ent-ph-k1", "ent-vi-k1", "called", 1.0, "2025-06-15", "2025-06-15", "kappa_rpt_v1"),
        ("ent-ph-k1", "ent-vi-k2", "called", 1.0, "2025-06-19", "2025-06-19", "kappa_rpt_v2"),
        
        ("ent-vi-k1", "ent-ac-k1", "transacted_with", 1.5, "2025-06-15", "2025-06-15", "kappa_rpt_v1"),
        ("ent-vi-k2", "ent-ac-k2", "transacted_with", 2.0, "2025-06-19", "2025-06-19", "kappa_rpt_v2"),
    ]
    cursor.executemany("""
        INSERT INTO relationships (source_id, target_id, relationship, weight, first_seen, last_seen, linked_report_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, relationships)
    print("✅ Coordinated rings seeded in SQLite.")

# ==========================================================
# FIRESTORE SEEDING OPERATIONS
# ==========================================================

def seed_demo_story_reports_firestore(db):
    """Seeds target case reports linked to fraud rings in Firestore."""
    print("Seeding specific case reports in Firestore for the demo storyline...")
    
    story_reports = [
        # Mamba reports
        {
            "id": "mamba_rpt_1",
            "source": "api",
            "report_type": "digital_arrest",
            "description": "Report from cyber cell: suspicious number +917892019283 detected calling multiple elderly citizens claiming to be CBI Officer Rajesh Kumar, forcing them into digital arrest.",
            "phone_numbers": ["+917892019283"],
            "account_numbers": ["HDFC00010023"],
            "victim_location": {"city": "Hyderabad", "state": "Telangana", "pincode": "500001", "lat": 17.3850, "lng": 78.4867},
            "risk_score": 0.98,
            "risk_label": "CRITICAL",
            "gemini_classification": "Digital Arrest Case",
            "detoxify_scores": {"toxicity": 0.1, "threat": 0.8, "insult": 0.1},
            "bert_confidence": 0.92,
            "scam_script_match": 0.95,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=20),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=20)
        },
        {
            "id": "mamba_rpt_2",
            "source": "whatsapp",
            "report_type": "digital_arrest",
            "description": "WhatsApp alert: suspect +919987123456 impersonating Customs officials claiming drug courier parcel found, asking victim to connect on Skype to transfer clearance fee.",
            "phone_numbers": ["+919987123456"],
            "account_numbers": ["AXIS00230045"],
            "victim_location": {"city": "Mumbai", "state": "Maharashtra", "pincode": "400001", "lat": 19.0760, "lng": 72.8777},
            "risk_score": 0.95,
            "risk_label": "CRITICAL",
            "gemini_classification": "Digital Arrest Case",
            "detoxify_scores": {"toxicity": 0.05, "threat": 0.85, "insult": 0.05},
            "bert_confidence": 0.89,
            "scam_script_match": 0.91,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=15),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=15)
        },
        {
            "id": "mamba_rpt_3",
            "source": "web",
            "report_type": "digital_arrest",
            "description": "Scammer calling from +918891987654 claiming to be TRAI official and accusing me of duplicate Aadhaar SIM fraud. Demanded Rs 4,50,000.",
            "phone_numbers": ["+918891987654"],
            "account_numbers": ["SBIN00670089"],
            "victim_location": {"city": "Delhi", "state": "Delhi", "pincode": "110001", "lat": 28.7041, "lng": 77.1025},
            "risk_score": 0.92,
            "risk_label": "HIGH",
            "gemini_classification": "Digital Arrest Case",
            "detoxify_scores": {"toxicity": 0.0, "threat": 0.75, "insult": 0.1},
            "bert_confidence": 0.86,
            "scam_script_match": 0.88,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=10),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=10)
        },
        {
            "id": "mamba_rpt_v1",
            "source": "web",
            "report_type": "digital_arrest",
            "description": "I received a Skype call from CBI officer claiming my Aadhaar card was linked to Jet Airways money laundering case. They kept me under digital arrest for 12 hours. I transferred Rs 5,00,000 to HDFC00010023.",
            "phone_numbers": ["+917892019283"],
            "account_numbers": ["HDFC00010023"],
            "victim_location": {"city": "Hyderabad", "state": "Telangana", "pincode": "500001", "lat": 17.3850, "lng": 78.4867},
            "risk_score": 0.98,
            "risk_label": "CRITICAL",
            "gemini_classification": "Digital Arrest Case",
            "detoxify_scores": {"toxicity": 0.1, "threat": 0.9, "insult": 0.2},
            "bert_confidence": 0.94,
            "scam_script_match": 0.96,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=8),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=8)
        },
        {
            "id": "mamba_rpt_v2",
            "source": "web",
            "report_type": "digital_arrest",
            "description": "Falsely accused of smuggling drugs via Taiwan courier. Transferred Rs 2,50,000 to AXIS00230045 under threat of immediate arrest. Call originated from +917892019283.",
            "phone_numbers": ["+917892019283"],
            "account_numbers": ["AXIS00230045"],
            "victim_location": {"city": "Mumbai", "state": "Maharashtra", "pincode": "400001", "lat": 19.0760, "lng": 72.8777},
            "risk_score": 0.96,
            "risk_label": "CRITICAL",
            "gemini_classification": "Digital Arrest Case",
            "detoxify_scores": {"toxicity": 0.1, "threat": 0.88, "insult": 0.15},
            "bert_confidence": 0.92,
            "scam_script_match": 0.94,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=6),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=6)
        },
        {
            "id": "mamba_rpt_v3",
            "source": "web",
            "report_type": "digital_arrest",
            "description": "Caller from +917892019283 claiming to be Customs officer locked me in my room over Zoom call, saying drug parcel seized. I transferred Rs 8,00,000 to SBIN00670089.",
            "phone_numbers": ["+917892019283"],
            "account_numbers": ["SBIN00670089"],
            "victim_location": {"city": "Delhi", "state": "Delhi", "pincode": "110001", "lat": 28.7041, "lng": 77.1025},
            "risk_score": 0.97,
            "risk_label": "CRITICAL",
            "gemini_classification": "Digital Arrest Case",
            "detoxify_scores": {"toxicity": 0.15, "threat": 0.92, "insult": 0.25},
            "bert_confidence": 0.95,
            "scam_script_match": 0.97,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=4),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=4)
        },
        
        # Kappa reports
        {
            "id": "kappa_rpt_1",
            "source": "whatsapp",
            "report_type": "financial_fraud",
            "description": "WhatsApp group 'Daily Stock Earnings' admin named Priya Patel (number +919878112233) claiming 300% daily returns. Got locked out of withdrawals after Rs 3,00,000 deposit.",
            "phone_numbers": ["+919878112233"],
            "account_numbers": ["ICIC00891234"],
            "victim_location": {"city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "lat": 12.9716, "lng": 77.5946},
            "risk_score": 0.88,
            "risk_label": "HIGH",
            "gemini_classification": "Investment Fraud Ring",
            "detoxify_scores": {"toxicity": 0.0, "threat": 0.1, "insult": 0.0},
            "bert_confidence": 0.85,
            "scam_script_match": 0.87,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=12),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=12)
        },
        {
            "id": "kappa_rpt_2",
            "source": "web",
            "report_type": "financial_fraud",
            "description": "Stock trading platform recommendation on WhatsApp +916541445566. Invested Rs 1,50,000, account frozen and support demanding tax payment to withdraw.",
            "phone_numbers": ["+916541445566"],
            "account_numbers": ["KKBK00419876"],
            "victim_location": {"city": "Gurgaon", "state": "Haryana", "pincode": "122001", "lat": 28.4595, "lng": 77.0266},
            "risk_score": 0.82,
            "risk_label": "HIGH",
            "gemini_classification": "Investment Fraud Ring",
            "detoxify_scores": {"toxicity": 0.0, "threat": 0.05, "insult": 0.0},
            "bert_confidence": 0.81,
            "scam_script_match": 0.82,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=9),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=9)
        },
        {
            "id": "kappa_rpt_v1",
            "source": "web",
            "report_type": "financial_fraud",
            "description": "Invested Rs 1,80,000 in hotel review part-time job scam introduced on WhatsApp by +919878112233. Demanded more money to withdraw earnings.",
            "phone_numbers": ["+919878112233"],
            "account_numbers": ["ICIC00891234"],
            "victim_location": {"city": "Bengaluru", "state": "Karnataka", "pincode": "560001", "lat": 12.9716, "lng": 77.5946},
            "risk_score": 0.84,
            "risk_label": "HIGH",
            "gemini_classification": "Investment Fraud Ring",
            "detoxify_scores": {"toxicity": 0.0, "threat": 0.1, "insult": 0.05},
            "bert_confidence": 0.84,
            "scam_script_match": 0.86,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=5),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=5)
        },
        {
            "id": "kappa_rpt_v2",
            "source": "web",
            "report_type": "financial_fraud",
            "description": "Victim in Gurgaon lost Rs 1,20,000 on stock tips group admin by +919878112233. Transfer done to KKBK00419876.",
            "phone_numbers": ["+919878112233"],
            "account_numbers": ["KKBK00419876"],
            "victim_location": {"city": "Gurgaon", "state": "Haryana", "pincode": "122001", "lat": 28.4595, "lng": 77.0266},
            "risk_score": 0.87,
            "risk_label": "HIGH",
            "gemini_classification": "Investment Fraud Ring",
            "detoxify_scores": {"toxicity": 0.0, "threat": 0.1, "insult": 0.0},
            "bert_confidence": 0.82,
            "scam_script_match": 0.85,
            "status": "verified",
            "created_at": datetime.now(timezone.utc) - timedelta(days=3),
            "updated_at": datetime.now(timezone.utc) - timedelta(days=3)
        }
    ]
    
    for r in story_reports:
        db.collection("fraud_reports").document(r["id"]).set(r)
        print(f"  Firestore case report seeded: {r['id']}")
        
    print("✅ Firestore story case reports seeded.")

def seed_demo_incidents(db, conn):
    """Seeds the 276 incidents distributed across 30 cities into Firestore & SQLite."""
    print("Seeding demo incidents (Firestore + SQLite)...")
    cursor = conn.cursor()
    
    # 1. Clean existing seeded incidents in SQLite
    cursor.execute("DELETE FROM incidents WHERE report_id LIKE 'seed_demo_%'")
    
    count_seeded = 0
    base_date = datetime.now(timezone.utc)

    for i, incident in enumerate(DEMO_INCIDENTS):
        sqlite_type = "scam_call"
        if incident["type"] == "ficn":
            sqlite_type = "ficn"
        elif incident["type"] == "investment_fraud":
            sqlite_type = "financial_fraud"
            
        firestore_type = "digital_arrest"
        if incident["type"] == "ficn":
            firestore_type = "fake_currency"
        elif incident["type"] == "investment_fraud":
            firestore_type = "financial_fraud"

        for j in range(incident["count"]):
            # Add slight geographic scatter around city center
            lat_scatter = incident["lat"] + random.uniform(-0.15, 0.15)
            lng_scatter = incident["lng"] + random.uniform(-0.15, 0.15)
            
            # Smart time-series distribution: 30-day time window with a slight upward trend
            days_ago = random.randint(0, 30)
            # Upward trend weights: higher probability of being recent
            if random.random() > 0.4:
                days_ago = random.randint(0, 10)
            
            report_id = f"seed_demo_{i}_{j}_{str(uuid.uuid4())[:8]}"
            created_time = base_date - timedelta(days=days_ago)
            created_str = created_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # Generate narrative
            description, phone_numbers, account_numbers = generate_narrative(incident["type"])
            
            # Firestore doc
            report_data = {
                "id": report_id,
                "source": "web" if random.random() > 0.5 else "whatsapp",
                "report_type": firestore_type,
                "description": description,
                "phone_numbers": phone_numbers,
                "account_numbers": account_numbers,
                "victim_location": {
                    "city": incident["city"],
                    "state": "State",
                    "pincode": "000000",
                    "lat": lat_scatter,
                    "lng": lng_scatter
                },
                "risk_score": 0.95 if incident["severity"] == "CRITICAL" else 0.85 if incident["severity"] == "HIGH" else 0.55 if incident["severity"] == "MEDIUM" else 0.25,
                "risk_label": incident["severity"],
                "gemini_classification": incident["type"].replace("_", " ").title(),
                "detoxify_scores": {"toxicity": 0.0, "threat": 0.0, "insult": 0.0},
                "bert_confidence": 0.0,
                "scam_script_match": 0.0,
                "status": "verified",
                "created_at": created_time,
                "updated_at": created_time
            }
            
            # Set in Firestore
            if db:
                try:
                    db.collection("fraud_reports").document(report_id).set(report_data)
                except Exception as e:
                    print(f"Error seeding Firestore report {report_id}: {e}")
            
            # Insert in SQLite
            cursor.execute("""
                INSERT INTO incidents (report_id, incident_type, lat, lng, city, state, pincode, severity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                sqlite_type,
                round(lat_scatter, 6),
                round(lng_scatter, 6),
                incident["city"],
                "State",
                "000000",
                incident["severity"],
                created_str
            ))
            
            count_seeded += 1
            
    print(f"✅ Seeding complete: {count_seeded} incidents seeded in SQLite (and Firestore if connected).")

# ==========================================================
# CURRENCY & ALERTS SEEDING
# ==========================================================

def seed_currency_checks(db):
    """Seeds currency checks history in Firestore."""
    print("Seeding currency checks history in Firestore...")
    if not db:
        return
        
    cities = ["Mumbai", "Delhi", "Bengaluru", "Kolkata", "Hyderabad", "Amritsar", "Malda"]
    verdicts = ["GENUINE", "GENUINE", "GENUINE", "COUNTERFEIT", "SUSPICIOUS"]
    denominations = [500, 500, 100, 200, 500]
    
    for i in range(15):
        check_id = f"seed_curr_{i}_{str(uuid.uuid4())[:8]}"
        city = random.choice(cities)
        verdict = random.choices(verdicts, weights=[0.6, 0.2, 0.1, 0.08, 0.02], k=1)[0]
        denom = random.choice(denominations)
        days_ago = random.randint(0, 15)
        created_time = datetime.now(timezone.utc) - timedelta(days=days_ago)
        
        failed = []
        analysis = "Gemini Analysis: The note contains correct microprinting and watermark. Embedded security thread is present and aligned."
        confidence = round(random.uniform(0.92, 0.99), 2)
        
        if verdict == "COUNTERFEIT":
            failed = random.choice(FAILED_FEATURES_FICN)
            analysis = f"Gemini Analysis: Suspicious features detected. Failed details: {', '.join(failed)}. Note lacks UV fluorescence under ultraviolet light check. High probability of forgery."
            confidence = round(random.uniform(0.85, 0.98), 2)
        elif verdict == "SUSPICIOUS":
            failed = [random.choice(FAILED_FEATURES_FICN)[0]]
            analysis = f"Gemini Analysis: Minor anomalies found. Failed feature: {failed[0]}. Security thread looks altered or printed. Recommend bank level verify."
            confidence = round(random.uniform(0.70, 0.85), 0.2)

        check_data = {
            "id": check_id,
            "submitted_by": random.choice(["teller", "officer", "citizen"]),
            "denomination": denom,
            "image_url": f"https://firebasestorage.googleapis.com/v0/b/shieldai-hackathon.appspot.com/o/currency_checks%2Fcheck_{i}.jpg?alt=media",
            "verdict": verdict,
            "confidence": confidence,
            "failed_features": failed,
            "gemini_analysis": analysis,
            "location": {
                "lat": 19.0760 if city == "Mumbai" else 28.7041 if city == "Delhi" else 12.9716 if city == "Bengaluru" else 17.3850,
                "lng": 72.8777 if city == "Mumbai" else 77.1025 if city == "Delhi" else 77.5946 if city == "Bengaluru" else 78.4867,
                "city": city
            },
            "created_at": created_time
        }
        db.collection("currency_checks").document(check_id).set(check_data)
        
    print("✅ Currency checks seeded in Firestore.")

def seed_alerts(db):
    """Seeds mock alerts feed in Firestore."""
    print("Seeding alerts in Firestore...")
    if not db:
        return
        
    alerts_data = [
        {
            "id": "alert_mamba_critical",
            "alert_type": "fraud_ring_identified",
            "severity": "CRITICAL",
            "title": "Critical Fraud Ring Identified: Operation Mamba",
            "description": "Louvain community detection flagged an active digital arrest ring spanning Hyderabad, Delhi, and Mumbai. Estimated damage is Rs 4.2 crore across 34 victims.",
            "linked_report_id": "mamba_rpt_1",
            "linked_phone": "+917892019283",
            "location": {"lat": 17.3850, "lng": 78.4867, "city": "Hyderabad"},
            "is_read": False,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=2)
        },
        {
            "id": "alert_kappa_high",
            "alert_type": "fraud_ring_identified",
            "severity": "HIGH",
            "title": "New Fraud Ring Detected: Ring Kappa",
            "description": "Telegram investment fraud ring detected. Linked to 67 victims and Rs 1.8 crore losses. Main phone node: +919878112233.",
            "linked_report_id": "kappa_rpt_1",
            "linked_phone": "+919878112233",
            "location": {"lat": 12.9716, "lng": 77.5946, "city": "Bengaluru"},
            "is_read": False,
            "created_at": datetime.now(timezone.utc) - timedelta(hours=5)
        },
        {
            "id": "alert_ficn_malda",
            "alert_type": "ficn_detected",
            "severity": "HIGH",
            "title": "Counterfeit Currency Alert: Malda Hotspot",
            "description": "A high concentration of Rs 500 fakes has been reported at bank tellers in Malda, West Bengal. Security thread failures detected.",
            "linked_report_id": None,
            "linked_phone": None,
            "location": {"lat": 25.0108, "lng": 88.1406, "city": "Malda"},
            "is_read": False,
            "created_at": datetime.now(timezone.utc) - timedelta(days=1)
        },
        {
            "id": "alert_scam_delhi",
            "alert_type": "scam_detected",
            "severity": "HIGH",
            "title": "High-Risk Digital Arrest Scam: Delhi",
            "description": "Active CBI impersonation scam targeting elderly victims reported in New Delhi. Victim forced under Zoom digital arrest.",
            "linked_report_id": "mamba_rpt_3",
            "linked_phone": "+918891987654",
            "location": {"lat": 28.7041, "lng": 77.1025, "city": "Delhi"},
            "is_read": True,
            "created_at": datetime.now(timezone.utc) - timedelta(days=2)
        }
    ]
    
    for a in alerts_data:
        db.collection("alerts").document(a["id"]).set(a)
        
    print("✅ Firestore alerts seeded.")

# ==========================================================
# MAIN EXECUTION SCRIPT
# ==========================================================

def main():
    print("🌱 ShieldAI Demo Data Seeding Script (Smarter & Pitch-Ready)")
    print("=" * 60)
    
    # 1. Initialize Firestore client
    db = None
    try:
        db = get_firestore_client()
        print("✅ Cloud Firestore client successfully initialized.")
    except Exception as e:
        print(f"⚠️ Could not initialize Firestore client: {e}")
        print("   The script will continue but Firestore collections ('fraud_reports', 'currency_checks', 'alerts') will be skipped.")
        print("   If you have a service account JSON, place it at 'backend/firebase-credentials.json'.")

    # 2. Initialize and Seed SQLite database
    try:
        print("Initializing SQLite schema...")
        init_sqlite_db()
        with get_sqlite_connection() as conn:
            seed_sqlite_rings(conn)
            seed_demo_incidents(db, conn)
        print("✅ SQLite database tables successfully seeded.")
    except Exception as e:
        print(f"❌ Error seeding SQLite: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 3. Seed Firestore collections
    if db:
        try:
            seed_demo_story_reports_firestore(db)
            seed_currency_checks(db)
            seed_alerts(db)
            print("✅ All Firestore collections successfully seeded.")
        except Exception as e:
            print(f"❌ Error seeding Firestore collections: {e}", file=sys.stderr)
            sys.exit(1)
            
    print("=" * 60)
    print("🎉 Demo data seeding complete! Safe to run again.")
    print("   Run your backend & frontend and search for +917892019283 to demo the storyline.")

if __name__ == "__main__":
    main()
