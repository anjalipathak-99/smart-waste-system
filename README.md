# Smart Waste Segregation & Collection System
### Software-only prototype for SIH 2026 (no physical hardware / ESP32 required)

A full-stack system that simulates a citywide smart-bin network end-to-end:
AI image-based waste classification, virtual IoT sensors, an admin
dashboard with live charts/maps, ML-based overflow & waste-generation
forecasting, graph-based route optimization for collection trucks, and
role-based portals for Admins, Workers and Citizens.

**Every feature runs entirely in software.** A background "Simulation
Engine" generates realistic, evolving fill-level/weight/temperature data
per bin so the whole system behaves like it's connected to real sensors,
without needing ESP32 boards, ultrasonic sensors, or load cells.

---

## 1. Tech Stack

| Layer          | Technology |
|----------------|------------|
| Frontend       | React.js + Vite + Tailwind CSS + Chart.js (react-chartjs-2) + Leaflet (react-leaflet) |
| Backend        | Python 3.10+, Flask, Flask-JWT-Extended, Flask-APScheduler |
| Database       | MySQL 8 (via SQLAlchemy + PyMySQL) |
| AI/ML (vision) | OpenCV + TensorFlow/Keras (MobileNetV2 transfer learning) |
| ML (prediction)| scikit-learn (RandomForestRegressor) |
| Route Optimization | NetworkX (Dijkstra / A*) + Nearest-Neighbor + 2-opt heuristic |
| Auth           | JWT (Admin / Worker / Citizen roles) |
| Maps           | Leaflet + OpenStreetMap tiles |

---

## 2. Features

1. **AI Waste Classification** — upload a photo, get Plastic / Paper / Metal
   / Glass / Organic / E-waste / Other with per-class confidence scores.
2. **Virtual Smart Bins** — every bin has simulated fill-level, weight and
   temperature "sensors."
3. **Automatic Sensor Data Generation** — a background scheduler advances
   every bin's sensors realistically (type-specific fill rates, daily
   temperature cycles, random "traffic," occasional simulated sensor
   damage), so historical data accumulates for ML training even with zero
   physical hardware.
4. **Admin Dashboard** — bin status table, doughnut/bar charts, live map
   (Leaflet/OSM), alert feed, ML predictions tab, route optimization tab.
5. **ML Prediction** — RandomForestRegressor forecasts each bin's fill
   level at +6h/+12h/+24h and flags overflow risk; a second model forecasts
   daily waste generation (kg) per area for the next 7 days.
6. **Route Optimization** — builds a geographic graph of bins needing
   collection, orders stops with Nearest-Neighbor + 2-opt, then computes
   real leg distances with Dijkstra or A*.
7. **Citizen Reporting** — citizens can report overflowing/damaged bins
   with photo + geolocation.
8. **Worker Module** — workers see their assigned optimized route and mark
   stops collected as they go.
9. **JWT Auth** — Admin / Worker / Citizen roles, each with scoped
   permissions on every endpoint.
10. **Simulation Mode** — a `SIMULATION_MODE=true` flag (default) drives
    everything above without any ESP32/sensor hardware; a "⏱ Advance
    Simulation" button in the dashboard also lets you fast-forward time for
    demos/judging.

---

## 3. Project Structure

```
smart-waste-system/
├── backend/
│   ├── app.py                  # Flask app factory + scheduler wiring
│   ├── config.py                # env-driven configuration
│   ├── extensions.py            # db / jwt / cors / scheduler singletons
│   ├── models.py                 # SQLAlchemy models (8 tables)
│   ├── schema.sql                # raw MySQL DDL (reference / manual setup)
│   ├── seed_data.py               # creates tables + demo users/bins/history
│   ├── requirements.txt
│   ├── .env.example
│   ├── routes/
│   │   ├── auth.py                # register/login/me + role_required decorator
│   │   ├── bins.py                 # CRUD + collect/repair + manual sim tick
│   │   ├── classify.py              # image upload + AI classification
│   │   ├── reports.py                # citizen reports
│   │   ├── routes_api.py              # route optimization + route/stop mgmt
│   │   ├── predictions.py              # ML training + prediction endpoints
│   │   ├── dashboard.py                 # aggregate stats + alerts
│   │   └── workers.py                    # worker list (admin)
│   ├── ml/
│   │   ├── waste_classifier.py     # CNN inference + OpenCV heuristic fallback
│   │   ├── train_classifier.py      # real MobileNetV2 transfer-learning trainer
│   │   ├── fill_predictor.py         # scikit-learn overflow + forecast models
│   │   └── route_optimizer.py         # graph build + NN/2-opt + Dijkstra/A*
│   ├── simulation/
│   │   └── sensor_simulator.py     # virtual sensor tick logic
│   └── uploads/                    # uploaded/report images (gitignored)
└── frontend/
    ├── package.json / vite.config.js / tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx / App.jsx / index.css
        ├── api/client.js            # axios instance + JWT interceptor
        ├── context/AuthContext.jsx
        ├── components/               # Navbar, ProtectedRoute, StatusBadge
        └── pages/
            ├── Login.jsx / Register.jsx
            ├── AdminDashboard.jsx      # charts + map + table + ML + routes
            ├── WorkerPortal.jsx
            ├── CitizenPortal.jsx
            └── ClassifyWaste.jsx
```

---

## 4. Backend Setup

### 4.1 Prerequisites
- Python 3.10+
- MySQL 8.x running locally (or a remote instance)

### 4.2 Install & configure

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: set DB_USER, DB_PASSWORD, DB_NAME, SECRET_KEY, JWT_SECRET_KEY
```

Create the database (schema.sql is provided for reference, but `seed_data.py`
below creates the tables automatically via SQLAlchemy — you only need to
create the empty database):

```sql
CREATE DATABASE smart_waste_db CHARACTER SET utf8mb4;
```

### 4.3 Seed the database

This creates all tables, demo user accounts, ~20 virtual bins across city
areas, and **14 days of simulated hourly sensor history** (so the ML models
have real data to train on immediately):

```bash
python seed_data.py
```

Demo accounts created:

| Role    | Email                          | Password   |
|---------|---------------------------------|-----------|
| Admin   | admin@smartwaste.gov.in         | admin123  |
| Worker  | worker1@smartwaste.gov.in       | worker123 |
| Citizen | citizen1@example.com            | citizen123|

### 4.4 Run the API

```bash
python app.py
```

The API runs at `http://localhost:5000`. Health check: `GET /api/health`.

Simulation Mode is on by default (`SIMULATION_MODE=true` in `.env`) — a
background job advances every bin's sensors every
`SIMULATION_INTERVAL_SECONDS` (default 30s, accelerated ~20x per tick so
you can see meaningful change during a live demo).

---

## 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite is pre-configured to proxy `/api` and
`/uploads` to `http://localhost:5000` (see `vite.config.js`), so no CORS
configuration is needed in development.

---

## 6. Training the Real CNN Image Classifier (optional but recommended)

Out of the box, `ml/waste_classifier.py` uses a transparent OpenCV
heuristic (color/texture/edge features) as a fallback, so the full system
works end-to-end even before you've trained a model — every classification
response's `model_used` field tells you which path produced the result.

To get real CNN accuracy:

1. Gather a labeled dataset with 7 folders: `Plastic/ Paper/ Metal/ Glass/
   Organic/ E-waste/ Other/` (each full of representative images). A good
   starting point is the public **TrashNet** dataset plus extra E-waste /
   Other images.
2. Run:
   ```bash
   cd backend
   python ml/train_classifier.py --data_dir /path/to/dataset --epochs 15
   ```
   This trains a MobileNetV2 transfer-learning model (frozen base + new
   dense head, then fine-tunes the top 30 layers) and saves
   `ml/saved_models/waste_cnn.h5`.
3. Restart the Flask app — `waste_classifier.py` automatically detects and
   loads the trained model on the next classification request.

---

## 7. Training the ML Prediction Models

From the Admin Dashboard, click **"🧠 Train ML Models"** (or `POST
/api/predictions/train` directly). This trains:

- **Overflow model** — RandomForestRegressor on all historical
  `sensor_readings`, predicting fill level from hours-since-collection,
  weight, temperature, bin type, capacity, hour-of-day, day-of-week.
- **Forecast model** — RandomForestRegressor on daily per-area collected
  weight, predicting the next 7 days.

Because `seed_data.py` already generates 14 days of hourly history, both
models can be trained immediately after seeding.

---

## 8. Key REST API Endpoints

All endpoints except `/api/auth/register` and `/api/auth/login` require
`Authorization: Bearer <token>`.

```
POST   /api/auth/register              Create account (role: admin|worker|citizen)
POST   /api/auth/login
GET    /api/auth/me

GET    /api/bins                       List all bins (filters: area, status)
GET    /api/bins/<id>
GET    /api/bins/<id>/history          Sensor reading history
POST   /api/bins                       [admin] Create bin
PUT    /api/bins/<id>                  [admin] Update bin
DELETE /api/bins/<id>                  [admin]
POST   /api/bins/<id>/collect          [admin/worker] Simulate emptying a bin
POST   /api/bins/<id>/repair           [admin] Mark damaged bin as repaired
POST   /api/bins/simulate/tick         [admin] Manually advance simulation

POST   /api/classify                   Upload + classify a waste image
GET    /api/classify/history
GET    /api/classify/stats

POST   /api/reports                    Citizen submits overflow/damage report
GET    /api/reports
PUT    /api/reports/<id>/status        [admin/worker]

POST   /api/routes/optimize            [admin] Generate optimized collection route
GET    /api/routes
GET    /api/routes/<id>
POST   /api/routes/stops/<id>/complete [admin/worker]

POST   /api/predictions/train          [admin] Train both ML models
GET    /api/predictions/overflow       Per-bin overflow risk + projections
GET    /api/predictions/waste-generation  7-day forecast per area

GET    /api/dashboard/summary
GET    /api/dashboard/alerts
POST   /api/dashboard/alerts/<id>/resolve

GET    /api/workers                    [admin]
```

---

## 9. Notes on Design Choices

- **Route graph**: bins + a fixed depot form a fully-connected graph
  weighted by haversine distance (a standard, honest simplification when a
  real OSM road-network graph isn't wired in). Stop *ordering* comes from a
  Nearest-Neighbor + 2-opt TSP heuristic; Dijkstra/A* then compute the
  reported leg distances on that graph, satisfying the "use Dijkstra/A*"
  requirement for real shortest-path search (a single shortest-path
  algorithm alone can't solve multi-stop ordering).
- **Simulation engine**: fill/weight/temperature evolve using type-specific
  rates + daily temperature cycles + Gaussian noise + a small chance of
  simulated sensor damage — not static/random placeholder numbers.
- **Image classifier**: ships with a real, deterministic OpenCV
  feature-based classifier so the pipeline is fully functional immediately;
  swapping in a trained CNN (`train_classifier.py`) is a drop-in
  replacement with no API changes.

---

## 10. Troubleshooting

- **`Can't connect to MySQL`**: check `DB_HOST/PORT/USER/PASSWORD/NAME` in
  `backend/.env` and that MySQL is running.
- **CORS errors in the browser**: make sure you're hitting the frontend via
  `http://localhost:5173` (uses the Vite proxy) rather than opening
  `index.html` directly.
- **TensorFlow install issues**: TensorFlow is only required for the
  optional trained-CNN path; the app runs fine without it using the OpenCV
  fallback classifier — you can remove the `tensorflow` line from
  `requirements.txt` if you don't plan to train the CNN.
