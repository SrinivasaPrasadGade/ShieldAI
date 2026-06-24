# Hackathon Battle Plan — Problem 6
## AI for Digital Public Safety: Defeating Counterfeiting, Fraud & Digital Arrest Scams

---

## SECTION 1: THE REAL PROBLEM — WHY IT BURNS AND WHY NOW

Before you write a single line of code, you need to feel the weight of this problem. This is not a made-up use case. These are real numbers:

- **1.14 million** cybercrime complaints in India in 2023 — **up 60% from 2022**
- **Rs 1,776 crore** stolen through digital arrest scams alone in the first **9 months of 2024**
- **Record FICN seizures** in 2025 — Rs 500 fake notes now good enough to fool bank tellers manually

The problem is not detection after the crime. Detection after the crime is what the police already do — it's called an FIR. That's the entire system today, and it's clearly failing at scale.

**The actual gap, stated precisely:** Law enforcement has no intelligence *before* victimisation occurs, and no tools that work *at the point of contact* — meaning at the moment the scam call is happening, the fake note is being handed over, or the fraud transaction is being initiated.

The shift this problem demands is: **Reactive → Predictive. Complaint-driven → Signal-driven.**

### Who is being hurt and how?

**Digital Arrest Scams** are not simple phishing calls. They are industrialised, multi-day psychological operations:
- Fraudsters impersonate CBI, ED, or Customs officials
- They trap victims in fake "digital arrest" situations over video call, sometimes for days
- They use AI-generated voices, spoofed caller IDs, and fake government portal websites
- The victim is so psychologically broken that they transfer money voluntarily
- These operations are run from fraud compounds, often cross-border

**Counterfeit Currency (FICN)** is an economic warfare tool:
- High-denomination Rs 500 fakes are now defeating manual detection in routine banking
- The RBI Annual Report 2025 flagged this as a record year for seizures
- The problem isn't that fakes exist — it's that the fakes are now *good enough* to enter circulation

**The Core Intelligence Failure:**
All of the existing law enforcement infrastructure operates on *post-event data*. Someone files a complaint → police investigate → evidence is gathered. By the time this happens, the fraudster has already moved, the mule account has been drained, and the victim has lost everything. The system is **always fighting the previous war**.

What is needed is a platform that catches signals *early* — at the first suspicious call, before the transfer, before the fake note enters circulation — and converts those signals into actionable intelligence for law enforcement in real time.

---

## SECTION 2: PROJECT IDENTITY — WHAT YOU ARE BUILDING

**Project Name Recommendation:** `ShieldAI` or `SafeNet Intelligence Platform`

**One-Line Pitch:** An AI-powered intelligence command centre that detects digital fraud, counterfeit currency, and scam networks *before* victimisation occurs — shifting India's cybercrime response from case-by-case complaints to proactive threat neutralisation.

**Who uses it and why:**

| User | Interface | What they get |
|---|---|---|
| Citizens | Web App / WhatsApp | Real-time fraud risk verdicts, guided reporting |
| Law Enforcement | Command Dashboard | Live alerts, fraud network maps, crime heatmaps |
| Bank Tellers | Mobile/Web tool | Instant currency authenticity verification |
| NCRB/MHA | Intelligence Feed | Aggregated threat patterns, evidence packages |

---

## SECTION 3: CORE FEATURES — WHAT THE PROBLEM EXPECTS YOU TO BUILD

These five are directly listed in the problem statement. All five must appear in your prototype, even if some are demo-level implementations for the hackathon.

---

### Feature 1: Digital Arrest Scam Detection & Alerting

**What:** A real-time AI classifier that can identify whether a call, transcript, or described scenario matches known digital arrest scam patterns.

**Why it matters:** Digital arrest scams follow recognisable scripts — they always involve impersonation of government agencies (CBI, ED, Customs), accusations of money laundering or drug trafficking, threats of immediate arrest, and demands for "verification" transfers. The script is industrialised. Which means it is classifiable.

**How it works:**
1. Citizen opens the app or WhatsApp and describes a call they received (or pastes a transcript)
2. The text goes through a multi-layer NLP pipeline:
   - Gemini API checks against a prompt-engineered knowledge base of known scam patterns
   - A BERT/RoBERTa classifier (HuggingFace) runs secondary classification
   - Keywords, entities, call-flow patterns, and authority impersonation markers are extracted
3. A risk score (0–100) is generated with a plain-English explanation
4. If high-risk: SocketIO broadcasts an immediate alert to the law enforcement dashboard
5. The citizen gets a real-time verdict: "This matches a known Digital Arrest Scam. Here is what you should do."
6. The phone number is logged, geocoded, and added to the fraud intelligence graph

**Key insight for judges:** You are doing *pre-complaint* detection. The system catches this while the call is potentially still happening.

---

### Feature 2: Counterfeit Currency Identification Agent

**What:** A computer vision system where a user uploads a photo of a currency note, and the AI determines authenticity by analysing security features.

**Why it matters:** The RBI has noted that current manual detection is failing. Bank tellers process hundreds of notes per hour under time pressure. An instant, reliable AI check on suspicious notes — deployable on a phone camera — changes this.

**How it works:**
1. User (bank teller, shopkeeper, field officer) uploads a currency image via the React app
2. OpenCV pre-processes the image: noise reduction, contrast enhancement, perspective correction, segmentation
3. The processed image goes to Gemini Vision API for multimodal analysis:
   - Microprint clarity check
   - Security thread presence/alignment
   - Serial number format validation (RBI serial number format rules)
   - Watermark detection
   - Colour-shift ink features
4. A secondary pattern-match against known FICN features (scraped from RBI public advisories)
5. Result: `GENUINE` / `SUSPICIOUS` / `COUNTERFEIT` with confidence score and which specific features failed
6. If flagged: Alert generated, location logged (Firestore), added to geospatial FICN map

**Key insight for judges:** This is deployable on any Android phone today. Zero specialised hardware required.

---

### Feature 3: Fraud Network Graph Intelligence

**What:** A graph visualisation system that shows how fraud accounts, phone numbers, mule accounts, and victims are connected — revealing the structure of the fraud operation.

**Why it matters:** Individual fraud cases look isolated when viewed one at a time. But when you map them as a network, patterns emerge — the same phone number appears in 40 complaints, the same bank account is a money mule for three different scam rings. This transforms individual complaints into intelligence about criminal organisations.

**How it works:**
1. Input: A set of fraud reports (phone numbers, account numbers, device IDs, victim locations, transaction metadata)
2. NetworkX builds a graph where nodes are entities (phone numbers, accounts, victims, devices) and edges are relationships (called, transacted with, used same device)
3. Louvain community detection algorithm identifies fraud clusters (rings operating together)
4. Centrality analysis identifies the *most important nodes* — the scam operators, the money mule account coordinators
5. D3.js renders this as an interactive, zoomable network graph in the React frontend
6. Law enforcement can click any node to see its full complaint history and linkages
7. The system can generate a structured intelligence package (PDF) that is court-admissible

**Key insight for judges:** This is the feature that turns citizen complaints into law enforcement intelligence. It answers: "Who are the masterminds, and how do we trace the network?"

---

### Feature 4: Geospatial Crime Pattern Intelligence

**What:** A live, interactive map showing where fraud complaints are originating, where FICN has been seized, and where cybercrime hotspots are forming — enabling patrol prioritisation.

**Why it matters:** Crime is not uniformly distributed. If you can see that 80% of digital arrest scam complaints this week are coming from one specific PIN code cluster, you know where to intensify awareness campaigns and where to station cyber cell teams.

**How it works:**
1. Every fraud report that enters the system is geocoded (using Nominatim / OpenStreetMap) based on victim location or reported origin
2. GeoPandas processes spatial clustering in the backend
3. A Leaflet.js map in the React frontend shows:
   - Individual incident markers (colour-coded by fraud type)
   - Heatmap overlay of complaint density
   - FICN seizure points
   - Trend lines (is an area getting more or less dangerous over time?)
4. Law enforcement command dashboard can filter by time range, fraud type, and severity
5. Inter-district pattern matching: if the same fraud ring is active in Hyderabad and Chennai, the map will show this
6. Alert zone generation: if a new cluster forms, all law enforcement in that district are notified via SocketIO

**Key insight for judges:** This is the command-centre layer. It is the feature that makes the whole platform feel like a *system* and not just a collection of tools.

---

### Feature 5: Citizen Fraud Shield (Multi-channel)

**What:** A conversational AI assistant that any citizen can access via the web app or WhatsApp to instantly assess whether they are being scammed, get guided through reporting, and receive advice in their language.

**Why it matters:** Most fraud victims do not report because they do not know where to report, or they report days later after all evidence has gone cold. A WhatsApp bot that responds in Telugu, Hindi, or Tamil and says "Yes, this is a scam. Here is the NCRB Cybercrime portal link. Here is what information you should save right now." — this is transformative at a population scale.

**How it works:**
1. User sends a WhatsApp message describing a suspicious call, message, or payment request
2. Twilio WhatsApp API receives and routes to the FastAPI backend
3. Gemini API (with language detection) generates a structured response:
   - Risk assessment (High / Medium / Low)
   - Explanation of why it is or is not a scam
   - Exact steps to take right now
   - Links to NCRB portal for reporting
   - Emotional acknowledgement (victims are scared)
4. The web app version has a clean chat UI built in React
5. 12-language support via Gemini's multilingual capability — no separate translation layer needed
6. If the user confirms they are in an active scam situation: immediate escalation path to human responders

**Key insight for judges:** This is the citizen-facing face of the platform. It has the broadest reach of all five features and directly targets the problem of under-reporting.

---

## SECTION 4: HACKATHON-WORTHY EXTRA FEATURES

These are features not explicitly listed but that will make judges lean forward. Add any two or three of these and your project goes from "good submission" to "winner material."

---

### Extra Feature 1: AI Evidence Package Generator
Automatically compile a structured, court-admissible evidence package from all intelligence gathered about a fraud case — including complaint history, graph analysis, geospatial data, and call patterns. Exported as a PDF. This directly targets the evaluation criterion: *"auditability of intelligence packages for legal admissibility."*

### Extra Feature 2: Deepfake Voice Detection Flag
When a user describes receiving a call with an unusually robotic or perfect voice, the system asks them to upload a short recording. Whisper transcribes it. A SpeechBrain anomaly detection model checks for prosody irregularities that indicate AI synthesis. This addresses the "AI-generated voices" threat explicitly mentioned in the problem.

### Extra Feature 3: Phone Number Risk Score API
A simple public-facing API endpoint: `POST /api/risk-score` with a phone number. The system checks it against the fraud report database, the fraud network graph, and known spoofed number patterns. Returns a JSON risk score. Banks and telecom providers could integrate this into their own systems.

### Extra Feature 4: Scam Script Similarity Matching
A database of known digital arrest scam call scripts. When a citizen submits a complaint transcript, sentence transformers compute semantic similarity to known scripts. If it matches at 85%+, the system immediately flags it as a known scam variant with certainty. This uses sentence-transformers from HuggingFace (all-MiniLM-L6-v2, free).

### Extra Feature 5: Predictive Fraud Hotspot Engine
Using historical complaint data, a lightweight time-series model (Prophet or ARIMA, both free) predicts where the next hotspot will emerge in the next 7 days. The geospatial map shows a "predicted risk zone" layer alongside the historical data. Judges love predictive features — they signal that you are thinking beyond detection into prevention.

### Extra Feature 6: Inter-Agency Intelligence Sharing (Mock)
A mock API gateway that simulates sharing an intelligence package securely across jurisdictions — Hyderabad Cyber Cell sends a fraud network package to Bengaluru Cyber Cell. Can be demo'd with two separate dashboard instances. Signals that you have thought about how this scales across the country.

### Extra Feature 7: NCRB Auto-Report Filing (Mock)
After a citizen completes the fraud shield interaction, the system auto-populates a complaint form with all the data collected (fraud type, phone number, description, screenshots) and shows the citizen exactly what to submit to the NCRB cybercrime portal (cybercrime.gov.in). One-click copy. Reduces the friction of reporting by ~80%.

---

## SECTION 5: TECHNOLOGY STACK — ALL FREE TOOLS, ALL EXPLAINED

Every tool listed here has a free tier or is open source. Each is chosen specifically for your existing stack alignment.

---

### TIER 1: FRONTEND

**React + Vite** — `FREE, Open Source`
- You already have this in your stack. React handles the interactive command dashboard, citizen chat interface, and currency upload tool
- Vite gives you near-instant hot reload during hackathon development, which is critical when time is compressed
- Component architecture lets you build the 5 feature UIs independently and compose them into one platform

**Tailwind CSS** — `FREE`
- Utility-first styling. You won't waste time writing custom CSS classes during a hackathon
- Paired with shadcn/ui (free component library), you get a polished, professional UI without design work

**Leaflet.js + OpenStreetMap** — `100% FREE, No API key needed`
- This is the most important geospatial stack choice. Google Maps API costs money. Leaflet + OSM is completely free, offline-capable, and battle-tested
- Leaflet renders the interactive crime map, heatmap overlays, and incident markers
- OpenStreetMap provides the tile layer (the map imagery itself) at zero cost
- Leaflet.heat plugin adds heatmap capability

**D3.js** — `FREE, Open Source`
- Handles the fraud network graph visualisation in the browser
- Force-directed graph layout makes the fraud network visually intuitive — nodes that are more connected pull toward the centre
- Allows zoom, pan, click-to-inspect on any node

**Recharts** — `FREE`
- For the analytics charts in the dashboard — complaint trend lines, fraud type breakdown, daily alert volumes
- Already available in your React environment

**Socket.io-client** — `FREE`
- Client-side half of the real-time alerting system
- Connects to Flask-SocketIO backend for push updates to the law enforcement dashboard

---

### TIER 2: BACKEND

**FastAPI** — `FREE, Open Source` — Already in your stack
- Primary API gateway and microservice framework
- Routes incoming requests to the correct intelligence service
- Why FastAPI over Flask here: async support for concurrent ML calls, auto-generated API docs (Swagger UI at /docs)
- Handles: image uploads for currency detection, text submissions for scam analysis, graph queries, geospatial queries

**Flask + Flask-SocketIO** — `FREE` — Already in your stack
- Dedicated real-time alert server
- When a high-risk fraud report comes in, Flask-SocketIO pushes an immediate event to all connected law enforcement dashboards
- Why keep it separate from FastAPI: SocketIO's room/namespace system is simpler in Flask-SocketIO than in FastAPI's WebSocket implementation

**Celery** — `FREE, Open Source`
- Background task queue. ML inference (especially vision models) can take 2–5 seconds. You don't want the HTTP request to block waiting for it.
- When a currency image is uploaded, FastAPI puts the analysis task on the Celery queue and immediately returns a `task_id`. The client polls or listens via SocketIO for the result.

**Redis** — `FREE (Upstash free tier or local)` — Task queue broker for Celery, and pub/sub for SocketIO
- Upstash offers a free Redis instance with 10K commands/day — enough for a hackathon demo
- Alternatively, run Redis locally in Docker (already in your stack): `docker run -p 6379:6379 redis`

---

### TIER 3: AI / ML CORE

**Google Gemini 2.0 Flash API** — `FREE TIER: 15 RPM, 1500 requests/day`
- This is your most powerful tool and the central intelligence brain of the platform
- Use it for:
  - **Scam Detection:** Classify call transcripts against prompt-engineered scam knowledge base
  - **Currency Analysis:** Gemini Vision is multimodal — it can directly analyse uploaded currency images and describe which security features are present or absent
  - **Citizen Shield:** Multilingual conversational AI responses (12 Indian languages natively)
  - **Evidence Packages:** Synthesise all collected intelligence into structured summaries
  - **Agentic Reasoning:** Chain multiple analysis steps together with Gemini's 1M context window
- Why Gemini over OpenAI: It is free at the tier you need, it supports Indian regional languages out of the box, and you already use it in your stack

**HuggingFace Inference API + Transformers** — `FREE TIER: Rate-limited, enough for hackathon`
- Models you will use:
  - `distilbert-base-uncased-finetuned-sst-2-english` — fast text classification baseline
  - `sentence-transformers/all-MiniLM-L6-v2` — semantic similarity for scam script matching (Scam Script Extra Feature)
  - `facebook/bart-large-mnli` — zero-shot classification when you don't have labelled data for a category
  - `openai/whisper-small` — speech-to-text for call recording analysis
- HuggingFace Inference API lets you call these without running them locally, saving GPU time
- For models you *do* run locally (Whisper, Detoxify), they run fine on CPU for demo purposes

**Detoxify** — `FREE, Open Source` — Already in your stack
- Detects toxic, abusive, and threatening content in text
- Apply it to scam transcripts: scam operators use high-pressure, threatening language. Detoxify scores this component independently and feeds it into the risk score alongside the Gemini classification
- It runs locally with no API key needed

**OpenCV** — `FREE, Open Source`
- Currency image pre-processing pipeline before sending to Gemini Vision
- Steps: resize → grayscale conversion → edge detection (Canny) → perspective transform (to correct camera angle) → contrast normalisation (CLAHE)
- Also used for: serial number extraction region-of-interest cropping

**scikit-learn** — `FREE, Open Source`
- Anomaly detection: Isolation Forest for flagging unusual transaction patterns in the fraud network
- Clustering: DBSCAN for spatial clustering of crime incidents on the geospatial map
- Pipeline creation: wrap multiple pre-processing steps for the scam detection text pipeline

**NetworkX** — `FREE, Open Source` — Python graph library
- Core library for building and analysing the fraud network graph
- Algorithms used:
  - `community.louvain_community()` (python-louvain library) — finds fraud ring clusters
  - `nx.betweenness_centrality()` — identifies the most connected nodes (the masterminds)
  - `nx.degree_centrality()` — identifies money mule hubs
  - `nx.shortest_path()` — traces the path between any two entities in the network

**PyVis** — `FREE, Open Source`
- Converts a NetworkX graph into an interactive HTML visualization
- Used as a fallback / export option alongside D3.js

---

### TIER 4: GEOSPATIAL

**GeoPandas** — `FREE, Open Source`
- Extends Pandas DataFrames with geographic data types (Points, Polygons)
- Processes incident location data, computes spatial statistics
- Performs hotspot cluster detection in the backend

**Shapely** — `FREE, Open Source`
- Geometric operations library — used for geofencing (is this incident inside a known high-risk zone?)

**Nominatim API (OpenStreetMap)** — `100% FREE, No key needed`
- Geocoding: converts a city name or PIN code from a complaint report into lat/lng coordinates
- Reverse geocoding: converts lat/lng back to a human-readable address
- Rate limit: 1 request/second — fine for a hackathon

**Folium** — `FREE, Open Source`
- Generates heatmap layers in the backend that Leaflet.js renders
- Alternative: render everything on the frontend with Leaflet.heat plugin directly

---

### TIER 5: DATABASE & STORAGE

**Firebase Firestore** — `FREE TIER: 50K reads/day, 20K writes/day, 1GB storage` — Already in your stack
- Stores: fraud reports, citizen submissions, scam alerts, currency check results, user sessions
- Real-time listeners: the law enforcement dashboard uses Firestore's `onSnapshot` to receive live updates without polling
- Why Firestore over SQL here: the data is hierarchical (a fraud_report has nested phone_numbers, transaction_ids, etc.) and Firestore handles this schema-less

**SQLite** — `FREE, Built into Python`
- Stores: the fraud network graph as an adjacency list, analysis results cache, scam script templates
- Why SQLite alongside Firestore: graph data (nodes + edges) is relational and SQL is better for it than Firestore

---

### TIER 6: SPEECH & COMMUNICATION

**OpenAI Whisper (local)** — `FREE, Open Source`
- `whisper-small` model runs on CPU, good accuracy, fast enough for demo
- Transcribes call recordings uploaded by citizens or law enforcement
- Output feeds directly into the scam detection NLP pipeline

**Twilio WhatsApp API** — `FREE TRIAL ($15 credit, enough for demo)`
- Powers the Citizen Fraud Shield WhatsApp channel
- Twilio Sandbox (free, no credit needed) lets you demo WhatsApp messaging for testing
- Webhook to FastAPI receives WhatsApp messages, Gemini generates response, Twilio sends it back

**Firebase Cloud Messaging (FCM)** — `FREE`
- Push notifications to the law enforcement mobile dashboard when a high-priority alert fires

---

### TIER 7: DEVOPS & INFRASTRUCTURE

**Docker + Docker Compose** — `FREE` — Already in your stack
- Services in your `docker-compose.yml`:
  - `frontend` — React/Vite dev server
  - `api` — FastAPI
  - `realtime` — Flask-SocketIO
  - `worker` — Celery worker
  - `redis` — Redis broker
- Why Docker: judges can run your project with `docker-compose up` and everything works. No "works on my machine" problem.

**Google Cloud Run** — `FREE TIER: 2M requests/month`
- Deploy your FastAPI containers here for the live demo
- Why not Heroku/Render: Cloud Run gives you a persistent URL, scales to zero (free when idle), and is part of the Google ecosystem your project already uses

---

## SECTION 6: HOW THE TECHNOLOGIES CONNECT — THE COMPLETE DATA FLOW

This is where the architecture comes together. Trace every request from user to response.

---

### Flow A: Citizen Reports a Suspicious Call

```
Citizen (WhatsApp) 
  → Twilio Webhook 
  → FastAPI /webhook/whatsapp 
  → Gemini API (scam classification + language detection) 
  + Detoxify (threat/pressure language scoring) 
  + HuggingFace BERT (secondary classification)
  → Risk Score Aggregator (weighted average of 3 model outputs)
  → If HIGH RISK:
    → Firestore (store alert) 
    → Flask-SocketIO (push to law enforcement dashboard)
    → Nominatim (geocode victim's PIN code)
    → Geospatial Service (add to crime heatmap)
    → Fraud Graph Service (add phone number to network)
  → Twilio (send verdict + guidance back to citizen via WhatsApp)
```

---

### Flow B: Bank Teller Checks a Currency Note

```
Bank Teller (React App) — uploads currency image
  → FastAPI /api/currency/verify (multipart form upload)
  → Celery Task Queue (async, don't block the HTTP response)
    → Worker picks up task:
      → OpenCV: preprocess image (denoise, perspective correct, contrast)
      → Gemini Vision API: multimodal security feature analysis
      → Pattern Matcher: check serial number format against RBI rules
      → Result: GENUINE / SUSPICIOUS / COUNTERFEIT + failed features list
    → Firestore: store result with location
    → If COUNTERFEIT:
      → Flask-SocketIO: alert law enforcement dashboard
      → Geospatial Service: add seizure point to FICN map
  → FastAPI: client receives result via polling or SocketIO
  → React: renders verdict with highlighted failed features
```

---

### Flow C: Law Enforcement Analyst Views Fraud Network

```
Analyst (React Dashboard) — selects fraud ring view
  → FastAPI /api/graph/network?cluster_id=X
  → Graph Service:
    → SQLite: query adjacency list for cluster
    → NetworkX: compute centrality metrics
    → Return: nodes (with attributes) + edges (with weights)
  → React: D3.js renders interactive force-directed graph
  → Analyst clicks a node (phone number)
    → FastAPI /api/node/{id}/history
    → Firestore: all complaints linked to this entity
    → React: shows complaint timeline, linked victims, linked accounts
  → Analyst requests evidence package
    → FastAPI /api/package/generate
    → Gemini API: synthesise all intelligence into structured PDF format
    → PDF generated, downloadable
```

---

### Flow D: Real-Time Alert to Command Dashboard

```
Any incoming high-risk event (from Flow A, B, or C)
  → Flask-SocketIO server receives alert from FastAPI (via Redis pub/sub)
  → Flask-SocketIO broadcasts to all connected dashboard clients in the 'law_enforcement' room
  → React Dashboard:
    → Toast notification (high-priority alert)
    → Map automatically pans to the incident location
    → Alert added to the live feed sidebar
    → Fraud network graph updates if new node/edge added
```

---

### System Architecture — Service Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REACT FRONTEND (Vite)                         │
│   Command Dashboard │ Citizen Shield │ Currency Tool │ Fraud Graph   │
└───────────────────┬────────────────────────────────────────────────-┘
                    │ HTTP / WebSocket
┌───────────────────▼──────────────────────────────────────────────┐
│                     FastAPI Gateway (Port 8000)                    │
│   /api/scam  │ /api/currency  │ /api/graph  │ /api/geo  │ /docs   │
└──────┬────────┬────────┬──────────┬──────────┬───────────────────┘
       │        │        │          │          │
  ┌────▼──┐ ┌───▼──┐ ┌───▼──┐  ┌───▼──┐  ┌───▼──────────────┐
  │Scam   │ │Curr. │ │Graph │  │Geo   │  │Flask-SocketIO    │
  │Detect.│ │Detect│ │Intel.│  │Intel.│  │(Real-time alerts)│
  │Service│ │Svc.  │ │Svc.  │  │Svc.  │  └──────────────────┘
  └────┬──┘ └───┬──┘ └───┬──┘  └───┬──┘
       │        │        │          │
  ┌────▼────────▼────────▼──────────▼──────────────────────┐
  │              AI / ML Layer                               │
  │  Gemini Flash API │ HuggingFace │ OpenCV │ NetworkX     │
  │  Detoxify │ Whisper │ scikit-learn │ GeoPandas          │
  └────────────────────────────────┬───────────────────────┘
                                   │
  ┌────────────────────────────────▼───────────────────────┐
  │              Data Layer                                  │
  │  Firebase Firestore (reports, alerts) │ SQLite (graphs) │
  │  Redis (task queue, pub/sub)          │                  │
  └────────────────────────────────────────────────────────┘
```

---

## SECTION 7: THE MAIN FOCUS — WHAT JUDGES WILL EVALUATE

Looking at the judging criteria:

### Innovation (25%) — Highest Weight
Your innovation angle is **Intelligence Fusion** — no existing tool does all five in one platform. More specifically, you are doing *cross-domain signal correlation*: a phone number flagged in the Citizen Shield also shows up in the Fraud Network Graph and pins a point on the Geospatial Map — automatically. This multi-source correlation is the core innovation. Make sure you demo this linkage explicitly.

### Business Impact (25%) — Tied for Highest
The problem statement gives you the numbers. Quote them in your presentation: 1.14M complaints, Rs 1,776 crore lost, 60% YoY growth. Then show your platform's impact model: if the Citizen Fraud Shield prevents 5% of digital arrest scams by flagging them in real time, that's Rs 88 crore saved. Business impact here is about the *before/after* story — today vs. with ShieldAI.

### Technical Excellence (20%)
You demonstrate this through:
- Working ML models (not hardcoded responses)
- Correct async architecture (Celery for heavy inference)
- Graph algorithms running on real data
- Real-time SocketIO updates working in the demo

### Scalability (15%)
Docker Compose shows you have thought about this. During your presentation, explain microservices — each feature is a separate service, so the currency detection module can be scaled independently from the scam detection module. Cloud Run auto-scales. Firestore handles millions of concurrent readers.

### User Experience (15%)
Two distinct UIs:
- **Citizen-facing:** Simple, clean, WhatsApp-first. Minimal friction. Works in 12 languages.
- **Law enforcement facing:** Dense, data-rich command dashboard. Real-time alerts. Map + graph + feed all visible simultaneously.

---

## SECTION 8: DELIVERABLES — EXACTLY WHAT YOU NEED TO SUBMIT

### 1. Working Prototype
- React dashboard with all 5 feature UIs
- Scam detection working with real Gemini API calls
- Currency detection working (even with a demo currency image)
- Fraud network graph with synthetic data showing realistic connections
- Geospatial map with pre-seeded complaint data
- Citizen shield chatbot (web version at minimum)

### 2. Architecture Diagram
- Use Excalidraw (free, browser-based) or draw.io (free)
- Show: services, data flows, external APIs, databases
- Match what is shown in Section 6 above

### 3. Presentation Deck
Use Gamma (free, AI-powered) or Canva (free)
Structure:
- Slide 1: Problem (the numbers — make it hurt)
- Slide 2: The gap (reactive vs. predictive)
- Slide 3: Solution overview (platform name, one-liner)
- Slide 4-8: Each of the 5 features (one slide each, with screenshots)
- Slide 9: Architecture diagram
- Slide 10: Technology stack
- Slide 11: Business impact model
- Slide 12: Team + what's next (scalability roadmap)

### 4. Demo Video
- Maximum 3–5 minutes
- Show: citizen reports a scam call → alert appears on dashboard → pin appears on map → entity added to fraud graph
- This chain reaction is your money shot — it proves the system is integrated, not just 5 separate tools

---

## SECTION 9: MVP PRIORITY ORDER FOR A 24-36 HOUR HACKATHON

You cannot build everything equally. Here is the exact build priority:

**Hour 0–2:** Setup — Docker Compose, Firestore config, Gemini API key, React scaffold, FastAPI base

**Hour 2–8:** Citizen Fraud Shield — the Gemini API chat interface. This is the fastest to build and demos perfectly.

**Hour 8–14:** Scam Detection Service — NLP pipeline, risk scoring, SocketIO alert to dashboard skeleton

**Hour 14–18:** Fraud Network Graph — seed with synthetic but realistic data, D3.js rendering, NetworkX centrality

**Hour 18–22:** Geospatial Map — Leaflet.js, pre-seed 50 incident data points across major cities, heatmap layer

**Hour 22–26:** Currency Detection — OpenCV + Gemini Vision, use 2–3 real currency images for demo

**Hour 26–30:** UI polish, integration testing, demo video recording, architecture diagram

**Hour 30+:** Presentation deck, rehearse demo, sleep

---

## SECTION 10: THE PITCH ANGLE — HOW TO WIN THE ROOM

When you present, do not start with technology. Start with a story:

> "In October 2024, a 67-year-old retired schoolteacher in Pune received a call from someone claiming to be a CBI officer. She was told she was under 'digital arrest' for a money laundering case. Over 72 hours, the caller — using an AI-generated voice — convinced her to transfer Rs 23 lakh to 'verification accounts.' She lost her life savings. She didn't know she could report it. She didn't know what to do. She had no one to ask."

Then: "ShieldAI exists so that she never has to face that situation alone."

That is your opening. Everything else is proof.

---

*This document is your complete battle plan. The problem is real, the technology is free, the architecture is solid. Build it feature by feature, integrate them into a unified platform, and tell the story of why it matters. Let's win this.*
