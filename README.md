# Enterprise-Grade Multimodal AI Document Intelligence Platform Using Agentic AI

An enterprise-grade document intelligence platform that autonomously processes, analyzes, and answers questions from business documents using multimodal AI and an agentic workflow. The system accepts documents such as PDFs and images, extracts content via PyMuPDF and PaddleOCR, performs document classification, information extraction, and analysis, and verifies outputs using a multi-agent orchestration graph powered by LangGraph.

---

## Architecture Overview

The platform is designed across five core layers:

1. **Presentation Layer:** Modern React (Vite) single-page application with dashboard statistics, document upload, history views, modal inspection, and interactive AI Q&A.
2. **API & Security Layer:** FastAPI application providing JWT authentication, role-based access control, multi-tenant document isolation, immutable audit logging, and RESTful endpoints.
3. **Multimodal Processing Layer:** Hybrid document extraction pipeline utilizing PyMuPDF for native text extraction and PaddleOCR for scanned pages/images.
4. **Agentic AI Layer:** Multi-agent state graph orchestrated with LangGraph, including Document, Classification, Extraction, Analysis, Supervisor, and Verification agents.
5. **Persistence & MLOps Layer:** SQLAlchemy ORM supporting both SQLite (local development) and PostgreSQL (containerized environments), paired with MLflow for document processing tracking.

---

## Agentic AI Workflow

```text
User Upload (PDF / Image)
           │
           ▼
    FastAPI Ingestion
           │
           ▼
  Multimodal Extraction (PyMuPDF / PaddleOCR)
           │
           ▼
     Document Agent
           │
           ▼
  Classification Agent ───► (Contract, Invoice, Financial, etc.)
           │
           ▼
   Extraction Agent    ───► (Entities, Dates, Key-Value Pairs)
           │
           ▼
    Analysis Agent     ───► (Executive Summary, Risk Signals)
           │
           ▼
   Supervisor Agent    ───► (Orchestrates & verifies state completeness)
           │
           ▼
  Verification Agent   ───► (Validates extracted fields & flags discrepancies)
           │
           ▼
 Database Persistence (PostgreSQL / SQLite) & MLflow Tracking
           │
           ▼
 React Frontend (Interactive Dashboard, Inspection & Grounded Q&A)
```

---

## Key Features

- **Multimodal Document Processing:** Handles native digital PDFs and scanned images with automated text extraction and OCR fallback.
- **Autonomous Multi-Agent Orchestration:** LangGraph state machine routes documents through specialized agents with supervisor verification.
- **Grounded Document Q&A:** Question answering engine with passage retrieval, concrete entity/financial value extraction, and exact page citations. Missing information is explicitly flagged without hallucinations.
- **Enterprise Security & Isolation:** JWT-based bearer authentication, bcrypt password hashing, multi-tenant document isolation (preventing cross-user access), and tamper-resistant audit logs.
- **Operational Dashboard:** Real-time metrics reflecting actual document processing statuses (`verified`, `processed`, `needs_review`, `failed`).
- **MLOps Integration:** MLflow tracking for document parsing runs, classification tags, word counts, and agent execution times.
- **Containerization & CI/CD:** Docker containerization, Docker Compose for local full-stack development, Kubernetes manifests for container orchestration, and GitHub Actions CI for automated backend and frontend validation.

---

## Project Structure

```text
├── backend/
│   ├── agents/            # LangGraph agent definitions & supervisor workflow
│   ├── api/               # FastAPI route controllers (auth, document, qa)
│   ├── core/              # Security, JWT utilities, and settings
│   ├── database/          # SQLAlchemy models, database connection, init scripts
│   ├── schemas/           # Pydantic validation schemas
│   ├── services/          # OCR, text extraction, and Q&A retrieval service
│   ├── tests/             # Backend test suite (Pytest, TestClient)
│   └── main.py            # FastAPI application entry point
├── frontend/
│   ├── src/
│   │   ├── components/    # Reusable UI components & modals
│   │   ├── services/      # API client and authentication service
│   │   ├── views/         # Dashboard, Upload, History, AskView (Q&A)
│   │   ├── App.jsx        # Main application state and router
│   │   └── main.jsx       # React application root
│   ├── package.json       # Frontend dependencies and build scripts
│   └── vite.config.js     # Vite build configuration
├── docs/                  # System architecture and testing documentation
├── k8s/                   # Kubernetes deployment and service manifests
├── .github/workflows/     # GitHub Actions CI/CD workflows
├── docker-compose.yml     # Multi-container local orchestration (Postgres + Backend)
├── Dockerfile             # Production backend container build
├── requirements.txt       # Python dependencies
└── .env.example           # Environment configuration template
```

---

## Getting Started

### Prerequisites

- **Python:** 3.11 or higher
- **Node.js:** 18.x or 20.x
- **Git**
- **Docker & Docker Compose** (optional, for containerized run)

---

### Local Development Setup

#### 1. Backend Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/enterprise-document-intelligence.git
   cd enterprise-document-intelligence
   ```

2. **Create and activate a Python virtual environment:**
   ```bash
   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   # Copy sample environment configuration
   cp .env.example .env
   ```
   *By default, if `DATABASE_URL` is omitted, the backend automatically uses local SQLite (`sqlite:///./docuai.db`).*

5. **Start the backend server:**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The backend API will be available at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

---

#### 2. Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install frontend dependencies:**
   ```bash
   npm install
   ```

3. **Start the Vite development server:**
   ```bash
   npm run dev
   ```
   The frontend application will run on `http://localhost:5173`.

---

### Running with Docker Compose

To run the backend with a PostgreSQL database in Docker:

1. **Configure environment variables in `.env`:**
   ```env
   POSTGRES_USER=docuai
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=docuai
   JWT_SECRET_KEY=your_secure_random_jwt_secret_key
   ```

2. **Build and start containers:**
   ```bash
   docker compose up --build
   ```

3. **Verify running containers:**
   ```bash
   docker compose ps
   ```
   - PostgreSQL service: `localhost:5432`
   - FastAPI Backend service: `http://localhost:8000`

---

## Testing & Quality Assurance

### Run Backend Tests

The backend test suite covers API routes, authentication, document processing, multi-tenant isolation, and agent workflows:

```bash
# Run all tests with Pytest
pytest backend/tests -v

# Run targeted test suites
pytest backend/tests/test_qa.py -v
pytest backend/tests/test_security.py -v
pytest backend/tests/test_document.py -v
pytest backend/tests/test_agent_workflow.py -v
```

### Run Frontend Production Build Check

Verify that the frontend builds with zero errors:

```bash
cd frontend
npm run build
```

---

## Kubernetes Manifests

Deployment manifests are provided in the [`k8s/`](./k8s) directory for container orchestration:

- `k8s/secrets.example.yaml`: Template for required secrets (`DATABASE_URL`, `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`).
- `k8s/postgres-pvc.yaml`: PersistentVolumeClaim requesting persistent storage for PostgreSQL data.
- `k8s/postgres-deployment.yaml`: PostgreSQL Deployment manifest with persistent storage mount and readiness probe.
- `k8s/postgres-service.yaml`: ClusterIP service for internal database access.
- `k8s/deployment.yaml`: Backend application Deployment with startup, readiness, and liveness probes.
- `k8s/service.yaml`: ClusterIP service exposing the backend API on port 8000.

To apply manifests to a Kubernetes cluster:
```bash
# 1. Create secrets from template
kubectl apply -f k8s/secrets.example.yaml

# 2. Deploy PostgreSQL storage, database, and service
kubectl apply -f k8s/postgres-pvc.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/postgres-service.yaml

# 3. Deploy Backend application and service
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

---

## API Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user account | No |
| `POST` | `/auth/login` | Authenticate user and receive JWT access token | No |
| `GET` | `/auth/me` | Fetch profile details of currently authenticated user | Yes |
| `POST` | `/upload` | Upload a document (PDF / Image) and trigger agent workflow | Yes |
| `GET` | `/documents` | List documents owned by the authenticated user | Yes |
| `GET` | `/documents/{id}` | Retrieve details, analysis, and verification status | Yes |
| `POST` | `/documents/{id}/qa` | Ask a grounded question against the selected document | Yes |
| `GET` | `/documents/{id}/qa/history` | Retrieve conversation and question history | Yes |
| `GET` | `/audit-logs` | Retrieve security and access audit logs | Yes |
| `GET` | `/health` | Health check probe endpoint | No |

---

## License

This project is licensed under the MIT License.
