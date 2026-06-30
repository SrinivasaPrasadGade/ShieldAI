# ShieldAI API Documentation

## Overview

ShieldAI provides a FastAPI-powered backend with AI-driven analysis capabilities for digital public safety and fraud detection. 
The API is divided into public endpoints (used by the Citizen App) and protected endpoints (used by Law Enforcement Dashboards).

## Authentication

Law-Enforcement routes (`/api/graph`, `/api/geo`) require authentication.
Provide an API key via one of the following headers:
- `Authorization: Bearer <your_api_key>`
- `X-API-Key: <your_api_key>`

---

## 1. Fraud Network Graph API (Protected)
*Prefix: `/api/graph`*

### `GET /api/graph/network`
Retrieves the fraud network graph (nodes and edges).
- **Query Parameters**: 
  - `limit` (int, default=100)
  - `cluster_id` (int, optional)
- **Response**: `GraphNetworkResponse` (List of nodes, list of edges)

### `GET /api/graph/clusters`
Retrieves all identified fraud rings/clusters.
- **Response**: `GraphClustersResponse` (List of clusters sorted by risk and size)

### `GET /api/graph/stats`
Retrieves network statistics.
- **Response**: `GraphStatsResponse` (Total nodes, total edges, high risk clusters)

---

## 2. Geospatial Intelligence API (Protected)
*Prefix: `/api/geo`*

### `GET /api/geo/heatmap`
Retrieves heatmap data points aggregated by grid for Leaflet rendering.
- **Query Parameters**:
  - `incident_type` (string, optional)
- **Response**: List of `{lat, lng, weight}`

### `GET /api/geo/incidents`
Retrieves list of raw incidents for map markers.
- **Query Parameters**:
  - `days` (int, default=7)
  - `north`, `south`, `east`, `west` (float, optional bounding box)
- **Response**: List of incidents

---

## 3. Realtime Alert System (Redis Pub/Sub)
- **Socket.IO Endpoint**: `ws://<host>:5001/law_enforcement`
- The realtime server broadcasts alerts as they are created in the database.
- Use this socket namespace to receive instant pushes without polling the REST API.

---

## 4. Citizen Reporting APIs (Public)

### `POST /api/scam/report`
Submit a new scam report. Supports file uploads for media.

### `POST /api/citizen/chat`
Real-time conversation with the AI safety agent. Returns responses and risk evaluations in real-time.
