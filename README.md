# ⚡ AeroMetrics // Enterprise API Observability Engine

AeroMetrics is a production-grade, highly optimized, distributed-ready API Performance Monitoring platform built from scratch in Python and Flask. Designed to move away from generic templates, it features a custom **Deep Cyber-Slate Dark Mode UI**, an **Asynchronous Background Polling Engine**, **Thread-Safe SQLite Connection Pooling**, and **Statistical Outlier/Anomaly Detection**.

---

## 🛠️ Key Architectural Highlights

* **Thread-Safe SQLite Pooling Context (`database.py`):** Utilizes a synchronization-locked queue-backed connection manager enforcing Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) to handle parallel reads and sequential worker writes concurrently without blocking.
* **Statistical Outlier Filters (`engine.py`):** Features an anomaly detection engine that tracks a moving historical data baseline (past 30 dispatches) utilizing a rolling **Z-score metric** ($Z > 2.5$) to instantly isolate and log real-time performance latency drift.
* **Automated Project Bootstrapper (`run.py`):** Requires zero manual directory provisioning. On initial startup, the core layer dynamically verifies, builds, and scales out application storage folders (`logs/`, `exports/`), indexes the tracking matrix schema database, and seeds administrative keys automatically.
* **Decoupled Workflows (`scheduler.py` & `reporting.py`):** Offloads runtime performance polling completely out of the active Flask client execution frame using daemonized background threads (`APScheduler`) and exports metrics to clean CSV, Excel workbooks, or multi-page executive PDFs via ReportLab.

---

## 📂 System Project Footprint

```text
api_monitor/
│
├── run.py                 # Application Entry Point & Auto-Bootstrapper
├── config.py              # Configuration Global Environment Variables
├── database.py            # Thread-Safe SQLite Connection Pooler & Indices
├── auth.py                # Session-Based Access Middleware Gatekeeper
├── engine.py              # Advanced Performance Monitor Worker & Outlier Detection
├── scheduler.py           # Background APScheduler Worker Orchestrator
├── reporting.py           # Report Exporter Component (CSV, Excel, PDF)
│
├── logs/                  # System Runtime Tracking Buffers (Auto-created)
│   ├── monitor.log
│   └── app.log
│
├── exports/               # Generated On-Demand Management Reports (Auto-created)
│
└── templates/             # UI Presentation Template Layouts
    ├── base.html          # Global Design Template Frame
    ├── login.html         # Portal Administrative Login UI
    ├── dashboard.html     # Interactive Metrics & Anomaly Interface
    └── manage_apis.html   # System Endpoints Administration Panel
🚀 Installation & Rapid Deployment Guide
1. Provision Platform Environment Dependencies
Ensure your local Python path execution pipeline is mapped correctly and install core dependencies:

Bash
python -m pip install Flask requests apscheduler pandas openpyxl reportlab
2. Launch the Control Server
Run the bootstrapper directly from the terminal console. The engine will dynamically build storage paths and launch the interface:

Bash
python run.py
3. Authenticate Access
URL Link Target: http://127.0.0.1:5000/

Default Operator Handle: admin

Default Operator Secret Key: admin123

🧪 Live Telemetry Field Verification Framework
To test your premium layout metrics graphs and validation warnings instantly, add these verified public endpoints inside the Node Manager panel:

🟩 Target A: Fast Processing Uptime Ping
Name: Production Gateway Ping

URL String: https://jsonplaceholder.typicode.com/todos/1

Verb / Interval: GET / 10 seconds

🟨 Target B: Controlled Latency Outlier Tracker
Name: Upstream Auth Microservice

URL String: https://reqres.in/api/users?delay=1

Verb / Interval: GET / 15 seconds

🟥 Target C: Client-Error Handler Test
Name: Legacy Profile Endpoint

URL String: https://reqres.in/api/unknown/23

Verb / Interval: GET / 20 seconds

⚡ How to Trigger the Live Statistical Anomaly Warning:
Add Target B (https://reqres.in/api/users?delay=1) and allow it to cycle roughly 10 consecutive times until its moving window baseline stabilizes around 1000ms.

Click Scrub Node to wipe out its target record context.

Immediately re-add the endpoint with the exact same name, but swap out the delay variable: https://reqres.in/api/users?delay=4.

On the very next check cycle execution, the Moving Z-Score algorithmic filter will notice the sudden spike from 1s to 4s, identify it as a major data variant, and trigger the red Statistical Latency Outlier Triggered warning bar on the interface.

💼 Production Grade Environment Architecture
When exiting local sandbox modes for enterprise cloud environments:

Enforce Cryptographic Tokens: Change Config.SECRET_KEY inside config.py to a long random hexadecimal hash signature or read it out of your system environment flags (os.environ.get).

WSGI Server Wrapper Integration: Avoid running the integrated python runtime engine loop (app.run()) directly. Run the platform scaling workers securely behind a dedicated production proxy layer such as gunicorn:

Bash
gunicorn --workers 4 --threads 2 --bind 0.0.0.0:8000 run:app
