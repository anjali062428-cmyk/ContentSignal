# ContentSignal

> **"Turn search data into smarter content decisions."**
> An end-to-end Machine Learning and SaaS platform that identifies and prioritizes web content performance opportunities for digital publishing and content teams.

---

## 📌 Project Overview

The **ContentSignal** platform addresses the fundamental operational bottleneck in digital publishing and enterprise SEO: **editorial bandwidth is finite**. When managing thousands of published articles, content teams need to know exactly:
1. **Which pages should we review first?** (Prioritized Opportunity Review Queue)
2. **Why is the page declining?** (Model-driven feature attributions & deterministic reason codes)
3. **What specific editorial action is required?** (Evidence-based prescriptive directives: `REFRESH`, `OPTIMIZE`, `PROTECT`, etc.)

Trained on a real-world multi-tenant dataset of **30,000 pages across 32 clients**, this platform enforces strict scientific data guardrails:
- **Zero Target-Construction Leakage**: 9 proprietary platform columns quarantined; target derivation strictly isolated.
- **Client-Group Holdout Validation**: Evaluated on 6 completely unseen enterprise client domains.
- **Operational Decision Metrics**: Prioritizing **Precision@20 (60%)**, **Precision@50 (68%)**, and **Precision@100 (72%)** to match human editorial workflows.
- **Dual Explainability**: Global feature importances + local feature attributions with non-causal caveats.
- **Dynamic Multi-Dataset Management**: Upload and analyze custom CSV datasets with strict 44-column contract enforcement while permanently preserving the starter dataset.
- **Domain & Page Intelligence**: Optional domain and URL extraction with automatic page type classification (`Blog / Article`, `Product / Pricing`, `Documentation / Guide`, etc.).
- **Evidence Center & Executive Exports**: Instant vector-print PDF executive briefs (ReportLab), Word editorial memos (python-docx), and formatted Excel workbooks (openpyxl).
- **Starred Watchlist & Smart Filters**: Quick triage by Watchlist, High Impact, Quick Wins, Fast Decaying, and High Visibility.
- **Intervention History & Impact Tracking**: Pre-intervention baseline metric snapshotting with post-update delta readiness.
- **Attention Center & Today's Brief**: Real-time triage categorizing Critical, At-Risk, and Stable content alongside deterministic daily briefs.
- **Sub-sampled Opportunity Map**: 250-point interactive SVG scatter matrix (Visibility vs. Opportunity Score) with quadrant overlays and direct inspect links.

---

## 🚀 Key Machine Learning Results

All models evaluated strictly on **unseen client domains** (3,381 holdout pages across 6 clients):

| Model | ROC-AUC | PR-AUC | Precision | Recall | F1 | P@20 | P@50 | P@100 | Selected |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Heuristic Baseline** | 0.5938 | 0.5669 | 0.4600 | 0.0777 | 0.1330 | 0.3500 | 0.3600 | 0.3300 | No |
| **Logistic Regression** | 0.6510 | 0.6428 | 0.6109 | 0.7324 | 0.6662 | **0.7500** | 0.7000 | 0.7000 | Baseline |
| **Random Forest** | 0.6617 | 0.6287 | 0.6095 | **0.7915** | 0.6887 | 0.4500 | 0.4400 | 0.4800 | Benchmark |
| **Gradient Boosting** | **0.6945** | **0.6791** | **0.6400** | 0.7470 | **0.6894** | 0.6000 | **0.6800** | **0.7200** | **CHAMPION** |

### Why Gradient Boosting was Selected:
- **Highest ROC-AUC (0.6945)** and **PR-AUC (0.6791)** on unseen client holdouts.
- **72.0% Precision@100**: In an editorial review queue of 100 pages, 72 pages are genuine decay candidates—more than 2x the hit rate of traditional heuristics (33%).

---

## 🧱 Architecture & Technology Stack

```
content-intelligence-engine/
├── backend/                  # FastAPI REST API & Async Endpoints
│   ├── auth.py               # JWT Authentication & Password Hashing
│   ├── database.py           # SQLAlchemy 2.0 Engine, Migration & Session Local
│   ├── models.py             # Database Models (Pages, Metrics, Opportunities, Datasets)
│   ├── schemas.py            # Pydantic v2 Request/Response Schemas
│   ├── ai_assistant.py       # Grounded AI Assistant with Query Planning
│   ├── seed.py               # 30k Database Seeder
│   ├── main.py               # FastAPI Application Entrypoint
│   └── routers/              # Modular Route Handlers (auth, datasets, opportunities, models)
├── src/content_engine/       # Machine Learning Package
│   ├── config.py             # Column Definitions & Quarantine Lists
│   ├── validation/           # Quarantine & EDA Pipeline
│   ├── features/             # Safe Feature Builder & 6-Tier Leakage Audit
│   ├── models/               # Training, Evaluation & Baseline Scripts
│   ├── scoring/              # Opportunity Score, Reason & Action Engines
│   ├── archetypes/           # Unsupervised K-Means Behavioral Clustering
│   ├── classification/       # URL & Domain Page Type Classifier
│   └── explainability/       # Local & Global Feature Attributions
├── frontend/                 # Next.js 14 Web Application (App Router)
│   ├── app/                  # 13 App Routes (Dashboard, Queue, Datasets, Groups, Analytics, Models, AI)
│   ├── components/           # Reusable UI Components & Navigation (Navbar, Charts, DatasetSelector)
│   └── lib/                  # API Client & Authentication Handlers
├── reports/                  # Generated JSON & Markdown Reports
│   ├── capstone_report.md    # Full Technical Capstone Report
│   ├── model_report.json     # Comprehensive Model Metrics
│   ├── leakage_audit.md      # 6-Tier Leakage Verification Report
│   └── content_archetypes.json# Cluster Archetype Profiles
└── tests/                    # Pytest Suite (40 Unit & Integration Tests)
```

---

## ⚡ Getting Started Locally

### 1. Prerequisites
- **Python 3.11+** (Tested on Python 3.13)
- **Node.js 18+** & `npm`

### 2. Backend Setup
```bash
# Navigate to project root
cd content-intelligence-engine

# Create & activate virtual environment
python -m venv .venv
# Windows (PowerShell):
.\.venv\Scripts\activate
# Linux / macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database seeder (seeds 30,000 pages & demo user)
python backend/seed.py

# Start FastAPI backend server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
```bash
# In a separate terminal, navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Next.js development server
npm run dev
```
Open `http://localhost:3000` in your browser.

### 4. Demo Login Credentials
- **Email**: `demo@contentintelligence.ai`
- **Password**: `DemoPass123!`

---

## 🧪 Running Automated Tests

The complete test suite validates data quarantine integrity, leakage-free feature building, model scoring determinism, domain intelligence, dataset management, and API endpoints:
```bash
pytest tests/ -v
```
**Result**: 45 / 45 tests passing (100%).

---

## ⚙️ Environment Variables

Create a `.env` file in the root directory (or copy from `.env.example`):
```ini
JWT_SECRET=production_secret_key_content_intelligence_engine_2026_xyz
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./content_intelligence.db
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
GEMINI_API_KEY=
```

---

## 📜 License
MIT License. Built as an end-to-end Machine Learning Capstone Project.