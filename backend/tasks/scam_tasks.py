from celery_app import app
from services.citizen_service import get_citizen_service
from services.scam_detector import get_scam_detector
from models.database import get_sqlite_connection, get_firestore_client
from datetime import datetime, timezone
from tasks.async_utils import run_async
import random

# Dictionary of 30 major Indian cities with their coordinates, state, and pincode
INDIAN_CITIES = {
    "Delhi": {"lat": 28.7041, "lng": 77.1025, "state": "Delhi", "pincode": "110001"},
    "Mumbai": {"lat": 19.0760, "lng": 72.8777, "state": "Maharashtra", "pincode": "400001"},
    "Bengaluru": {"lat": 12.9716, "lng": 77.5946, "state": "Karnataka", "pincode": "560001"},
    "Hyderabad": {"lat": 17.3850, "lng": 78.4867, "state": "Telangana", "pincode": "500001"},
    "Ahmedabad": {"lat": 23.0225, "lng": 72.5714, "state": "Gujarat", "pincode": "380001"},
    "Chennai": {"lat": 13.0827, "lng": 80.2707, "state": "Tamil Nadu", "pincode": "600001"},
    "Kolkata": {"lat": 22.5726, "lng": 88.3639, "state": "West Bengal", "pincode": "700001"},
    "Pune": {"lat": 18.5204, "lng": 73.8567, "state": "Maharashtra", "pincode": "411001"},
    "Jaipur": {"lat": 26.9124, "lng": 75.7873, "state": "Rajasthan", "pincode": "302001"},
    "Lucknow": {"lat": 26.8467, "lng": 80.9462, "state": "Uttar Pradesh", "pincode": "226001"},
    "Kanpur": {"lat": 26.4499, "lng": 80.3319, "state": "Uttar Pradesh", "pincode": "208001"},
    "Nagpur": {"lat": 21.1458, "lng": 79.0882, "state": "Maharashtra", "pincode": "440001"},
    "Indore": {"lat": 22.7196, "lng": 75.8577, "state": "Madhya Pradesh", "pincode": "452001"},
    "Thane": {"lat": 19.2183, "lng": 72.9781, "state": "Maharashtra", "pincode": "400601"},
    "Bhopal": {"lat": 23.2599, "lng": 77.4126, "state": "Madhya Pradesh", "pincode": "462001"},
    "Visakhapatnam": {"lat": 17.6868, "lng": 83.2185, "state": "Andhra Pradesh", "pincode": "530001"},
    "Pimpri-Chinchwad": {"lat": 18.6298, "lng": 73.7997, "state": "Maharashtra", "pincode": "411019"},
    "Patna": {"lat": 25.5941, "lng": 85.1376, "state": "Bihar", "pincode": "800001"},
    "Vadodara": {"lat": 22.3072, "lng": 73.1812, "state": "Gujarat", "pincode": "390001"},
    "Ghaziabad": {"lat": 28.6692, "lng": 77.4538, "state": "Uttar Pradesh", "pincode": "201001"},
    "Ludhiana": {"lat": 30.9010, "lng": 75.8573, "state": "Punjab", "pincode": "141001"},
    "Agra": {"lat": 27.1767, "lng": 78.0081, "state": "Uttar Pradesh", "pincode": "282001"},
    "Nashik": {"lat": 19.9975, "lng": 73.7898, "state": "Maharashtra", "pincode": "422001"},
    "Faridabad": {"lat": 28.4089, "lng": 77.3178, "state": "Haryana", "pincode": "121001"},
    "Meerut": {"lat": 28.9845, "lng": 77.7064, "state": "Uttar Pradesh", "pincode": "250001"},
    "Rajkot": {"lat": 22.3039, "lng": 70.8022, "state": "Gujarat", "pincode": "360001"},
    "Kalyan-Dombivli": {"lat": 19.2403, "lng": 73.1305, "state": "Maharashtra", "pincode": "421301"},
    "Vasai-Virar": {"lat": 19.3913, "lng": 72.8397, "state": "Maharashtra", "pincode": "401201"},
    "Varanasi": {"lat": 25.3176, "lng": 82.9739, "state": "Uttar Pradesh", "pincode": "221001"},
    "Srinagar": {"lat": 34.0837, "lng": 74.7973, "state": "Jammu and Kashmir", "pincode": "190001"},
    "Malda": {"lat": 25.0108, "lng": 88.1406, "state": "West Bengal", "pincode": "732101"},
    "Amritsar": {"lat": 31.6340, "lng": 74.8723, "state": "Punjab", "pincode": "143001"},
    "Gurgaon": {"lat": 28.4595, "lng": 77.0266, "state": "Haryana", "pincode": "122001"}
}

def geocode_location(city_name: str) -> dict:
    """Helper to offline-geocode one of the 30 major Indian cities."""
    if not city_name:
        city_name = random.choice(list(INDIAN_CITIES.keys()))
        
    # Case-insensitive lookup
    for city, data in INDIAN_CITIES.items():
        if city_name.strip().lower() == city.lower():
            return {
                "city": city,
                "state": data["state"],
                "pincode": data["pincode"],
                "lat": data["lat"] + random.uniform(-0.05, 0.05), # add slight scatter
                "lng": data["lng"] + random.uniform(-0.05, 0.05)
            }
            
    # Default to a random city
    random_city = random.choice(list(INDIAN_CITIES.keys()))
    data = INDIAN_CITIES[random_city]
    return {
        "city": random_city,
        "state": data["state"],
        "pincode": data["pincode"],
        "lat": data["lat"] + random.uniform(-0.05, 0.05),
        "lng": data["lng"] + random.uniform(-0.05, 0.05)
    }

@app.task(name="tasks.scam_tasks.process_citizen_report_task")
def process_citizen_report_task(report_id: str):
    """Asynchronously analyze citizen fraud report and register incident in geodb."""
    async def _run():
        db = get_firestore_client()
        if not db:
            return
            
        doc_ref = db.collection("fraud_reports").document(report_id)
        doc = doc_ref.get()
        if not doc.exists:
            return
            
        data = doc.to_dict()
        description = data.get("description", "")
        phone_numbers = data.get("phone_numbers", [])
        phone_number = phone_numbers[0] if phone_numbers else None
        
        # 1. Analyze text for scam patterns
        detector = get_scam_detector()
        result = await detector.analyze_text(
            text=description,
            source_phone=phone_number,
            language="en"
        )
        
        # 2. Geocode report location
        loc_str = data.get("victim_location", {}).get("city", "Unknown")
        geo_data = geocode_location(loc_str)
        
        # 3. Update report in Firestore
        now = datetime.now(timezone.utc)
        updates = data.get("updates", [])
        updates.append(f"AI scam analysis completed. Flagged as {result['classification']} ({result['risk_label']}) on {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        doc_ref.update({
            "risk_score": result["risk_score"],
            "risk_label": result["risk_label"],
            "gemini_classification": result["classification"],
            "status": "verified" if result["risk_label"] in ("HIGH", "CRITICAL") else "resolved",
            "victim_location": {
                "city": geo_data["city"],
                "state": geo_data["state"],
                "pincode": geo_data["pincode"],
                "lat": geo_data["lat"],
                "lng": geo_data["lng"]
            },
            "updates": updates,
            "updated_at": now
        })
        
        # 4. Insert incident into SQLite incidents table for heatmap/geo overlay
        sqlite_type = "scam_call"
        if result["classification"] in ("fake_currency", "ficn"):
            sqlite_type = "ficn"
        elif "invest" in result["classification"].lower() or "financial" in result["classification"].lower():
            sqlite_type = "financial_fraud"
            
        with get_sqlite_connection() as conn:
            conn.execute("""
                INSERT INTO incidents (report_id, incident_type, lat, lng, city, state, pincode, severity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report_id,
                sqlite_type,
                round(geo_data["lat"], 6),
                round(geo_data["lng"], 6),
                geo_data["city"],
                geo_data["state"],
                geo_data["pincode"],
                result["risk_label"],
                now.isoformat()
            ))
            
    run_async(_run())
