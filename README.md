# Iran Monitor — Strategic Defense Intelligence & OSINT Monitoring Platform

**Iran Monitor** is a comprehensive, production-grade intelligence monitoring and open-source intelligence (OSINT) analytics platform. It continuously crawls, classifies, indexes, and analyzes defense, geopolitical, military, and strategic developments concerning Iran and the Middle East.

Engineered with a microservices-based, containerized Docker architecture, the complete platform can be orchestrated with a single command.

---

## 1. Container Topology & Microservices

| Service | Container Name | Host Port | Technology Stack | Core Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| **frontend** | `iran_monitor_web` | `3000` | Next.js 16 (App Router) + React 19 + TypeScript | High-performance dashboard, 3D interactive login, and news visualizer |
| **backend** | `iran_monitor_api` | `8000` | Python 3.12 + FastAPI + Uvicorn | RESTful API, PBKDF2 database authentication, and search/analytics engine |
| **collector** | `iran_monitor_collector` | — | Python 3.12 + Ingestion Scheduler | Automated periodic crawler running every 15 minutes across verified feeds |
| **postgres** | `iran_monitor_db` | `5433` (5432 internal) | PostgreSQL 16 Alpine | Persistent relational database storing 8,000+ indexed intelligence articles |

---

## 2. Quickstart Guide

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (version 24+ recommended with Docker Compose v2)
- [Git](https://git-scm.com/)

### Step-by-Step Launch
```bash
# 1. Clone repository (if not already local)
git clone <repository-url>
cd "Iran monitor-local-ai"

# 2. Configure environment variables from template
cp .env.example .env

# 3. Build and launch all services in detached mode
docker compose up -d --build

# 4. Verify container health status
docker compose ps
```

### Access Endpoints
- **Intelligence Dashboard:** [http://localhost:3000](http://localhost:3000)
- **3D Security Authentication:** [http://localhost:3000/login](http://localhost:3000/login)
- **FastAPI Health & Metrics:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
- **PostgreSQL Database:** `localhost:5433` (`iran_monitor_user` / `iran_monitor`)

---

## 3. Institutional Authentication & Role Access Control

User accounts are authenticated against the PostgreSQL database. Passwords are encrypted using **PBKDF2-HMAC-SHA256 (100,000 iterations)** with cryptographically unique salts.

Institutional analyst and operator accounts configured in the system:

| Username | Role & Title | Clearance Level | Department |
| :--- | :--- | :--- | :--- |
| `admin` | Chief Information Security Officer | Level 5 (Top Secret // SCI) | Strategic Command & Defense Intelligence |
| `r.karimi` | Senior Defense Analyst | Level 5 (Top Secret) | Geopolitical & Strategic Studies |
| `m.alavi` | Head of Geopolitical Research | Level 4 (Secret) | Regional Analysis & Assessment |
| `s.hashemi` | OSINT Collection Lead | Level 4 (Secret) | Satellite & Open-Source Collection |
| `a.moradi` | Aerospace & Missile Analyst | Level 4 (Secret) | Missile Defense & Aerospace Operations |
| `f.tehrani` | Cyber Intelligence Architect | Level 4 (Secret) | Cyber Defense & Signal Infrastructure |
| `n.ebrahimi` | Regional Strategic Forecaster | Level 4 (Secret) | Strategic Forecasting & Scenario Modeling |
| `k.rostami` | Senior Data Pipeline Engineer | Level 3 (Confidential) | Intelligence Ingestion & Pipeline Ops |
| `z.ahmadi` | 24/7 Watch Operations Officer | Level 3 (Confidential) | 24/7 Global Surveillance & Tactical Watch |
| `h.soleimani` | Advanced Threat Analyst | Level 3 (Confidential) | Tactical Threat Evaluation |
| `d.rezvani` | Compliance & Security Auditor | Level 3 (Confidential) | Compliance, Integrity & Audit |

> [!IMPORTANT]
> Operational passwords must be issued directly to authorized personnel or provisioned via secure deployment environment variables. Plaintext credentials must never be committed to public repository documentation.

---

## 4. News Ingestion Rate & Source Coverage

- **Scheduler Frequency:** Every 15 minutes (96 collection cycles per 24 hours).
- **Average Intake Rate:** **~120 to 140 new strategic articles per day** (~4 to 6 items per hour).
- **Total Ingested Articles:** Over **8,000 indexed articles** with complete historical timelines.
- **Active Sources:** **21 high-priority verified sources** (including Reuters, Al Jazeera, Defensenews, RealClearDefense, CENTCOM, USNI News, Brookings, CSIS, RAND, Defense Post, Air Force Magazine, Army Recognition, and more).

---

## 5. Project Directory Structure

```text
├── apps/
│   ├── api/                    # FastAPI REST backend service
│   │   ├── Dockerfile          # Multi-stage Python 3.12-slim production image
│   │   └── src/api/            # Routers (health, news, auth, stats, timeline)
│   ├── collector/              # Automated intelligence crawling service
│   │   └── src/collector/      # Crawlers, parsers, and deduplication logic
│   └── web-next/               # Next.js 16 modern dashboard & 3D login
│       ├── Dockerfile          # Multi-stage standalone Next.js image
│       └── app/login/          # 3D interactive Earth login with raycast extrusion
├── config/
│   └── sources/                # Source registries and execution readiness matrices
├── docs/                       # Technical architecture and operational runbooks
│   ├── ARCHITECTURE.md         # System architecture, schemas, and vLLM integration
│   ├── SOURCES_AND_COLLECTION.md # Intake rates, source catalog & sites.docx coverage
│   ├── AUTHENTICATION.md       # PBKDF2 hashing, user roles & security model
│   └── DEPLOYMENT_RUNBOOK.md   # Deployment, backup restore, and disaster recovery
├── docker-compose.yml          # Container orchestration configuration
└── tests/                      # Pytest automated test suites (480+ unit/integration tests)
```

---

## 6. Comprehensive Technical Documentation

Detailed technical documentation is maintained in the [`docs/`](docs/) directory:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): Architectural diagram, data pipeline, microservices decoupling, and future vLLM neural translation engine.
- [docs/SOURCES_AND_COLLECTION.md](docs/SOURCES_AND_COLLECTION.md): Complete mapping of `sites.docx` sources, RSS feeds, intake velocity, and scheduler controls.
- [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md): Detailed cryptographic specifications, user schema, and token workflows.
- [docs/DEPLOYMENT_RUNBOOK.md](docs/DEPLOYMENT_RUNBOOK.md): Container maintenance, database backup/restore procedures, and troubleshooting guide.
