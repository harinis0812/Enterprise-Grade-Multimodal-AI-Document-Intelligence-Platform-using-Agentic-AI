# Enterprise-Grade Multimodal AI Document Intelligence Platform Using Agentic AI

An enterprise-grade document intelligence platform that autonomously processes, analyzes, and answers questions from complex business documents using multimodal AI and an agentic workflow. The system accepts diverse document types—such as native text PDFs, scanned documents, mixed-content PDFs, tables, charts/diagrams, and images—extracts structured data and visual metadata via PyMuPDF, PaddleOCR, and Gemini Vision, and orchestrates specialized reasoning agents using LangGraph with supervisor verification and strict security controls.

---

## Architecture Overview

The platform is designed across five core enterprise layers:

1. **Presentation Layer:** Modern React (Vite) single-page application featuring:
   - Real-time operational dashboard with status metrics (`processed`, `verified`, `needs_review`, `failed`).
   - Drag-and-drop document intake supporting PDFs, PNGs, and JPEGs up to 10 MB.
   - Deep document inspection modal with visual diagram breakdowns and extracted tables.
   - **Dual-Mode Document Q&A Workspace:**
     - **Single Document Q&A:** Grounded questions against a target document with page-level citations and multimodal indicators.
     - **Multi-Document Synthesis:** Cross-document intelligence across selected documents with source document badges, consulted-document indicators, and cross-referencing.
2. **API & Enterprise Security Layer:** FastAPI application providing:
   - JWT authentication with HMAC-SHA256, cryptographically strong key validation (minimum 32 characters), and JTI token revocation blacklist (`/auth/logout`).
   - Role-Based Access Control (RBAC): `user` and `admin` roles, with administrative user management and platform statistics.
   - In-memory IP-isolated rate limiting on authentication routes (`/auth/login` 5/min, `/auth/register` 3/min).
   - Distributed request tracing via `X-Request-ID` pure ASGI middleware with input sanitization.
   - Zero-leak structured latency logging strictly omitting authorization headers, passwords, tokens, query parameters, and document bodies.
   - Strict multi-tenant data isolation: all document queries, single-doc Q&A, and multi-doc synthesis enforce ownership verification (returning HTTP 403 and logging `CROSS_USER_ACCESS_DENIED` on boundary violations).
3. **Multimodal Processing Layer:**
   - Native text extraction and mixed-content detection via PyMuPDF.
   - On-demand scanned page OCR via PaddleOCR with bounding-box coverage calculation and text deduplication.
   - Table detection and extraction with column/row structure preservation and page continuity markers.
   - Visual element detection distinguishing structural drawings, diagrams, and embedded charts from semantic visual interpretation.
   - Vision foundation model integration via Google Gemini Vision API for multimodal visual query answering.
4. **Agentic AI Layer:**
   - Multi-agent state machine orchestrated with LangGraph: `Document Intake Agent`, `Classification Agent`, `Extraction Agent`, `Analysis Agent`, `Supervisor Agent`, and `Verification Agent`.
   - Supervisor execution metrics tracking, loop prevention, and retry boundary enforcement (capping retries at 2 before forced escalation).
   - Word-boundary token matching for question intent classification (financial, comparative, tabular, visual, summary).
   - Dynamic query expansion with domain acronyms and synonyms.
5. **Persistence & Data at Rest Security Layer:**
   - Authenticated field-level encryption at rest (Fernet AES-128-CBC + HMAC-SHA256) via SQLAlchemy `EncryptedText` TypeDecorator on `extracted_text`, `analysis`, `agent_trace`, `QAHistory`, and `MultiDocQAHistory`.
   - Dynamic database engine supporting SQLite (`sqlite:///./docuai.db`) for local development and PostgreSQL with connection pooling (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`) for production.
   - MLOps experiment tracking using MLflow.

---

## Agentic AI Workflow

```text
User Upload (PDF / Scanned Image / Mixed-Content)
                     │
                     ▼
         FastAPI Validation & Security
 (10MB File Size Limit, 100 PDF Page Limit, MIME Check)
                     │
                     ▼
      Multimodal Ingestion Pipeline
 (Native PyMuPDF + PaddleOCR + Tables + Charts)
                     │
                     ▼
              Document Agent
                     │
                     ▼
         Classification Agent ───► (Contract, Invoice, Report, Resume)
                     │
                     ▼
           Extraction Agent   ───► (Entities, Dates, Key-Value Pairs, Tables)
                     │
                     ▼
            Analysis Agent    ───► (Executive Summary, Financials, Risk Signals)
                     │
                     ▼
           Supervisor Agent   ───► (Orchestrates & tracks retries, max 2)
                     │
                     ▼
          Verification Agent  ───► (Validates completeness & flags issues)
                     │
                     ▼
 Authenticated Encryption at Rest (Fernet) & PostgreSQL / SQLite Storage
                     │
                     ▼
  React Frontend (Dashboard, Inspection, Single-Doc Q&A, Multi-Doc Synthesis)
```

---

## Getting Started

### Prerequisites

- **Python:** 3.11.x
- **Node.js:** 18.x or 20.x
- **Git**
- **Docker & Docker Compose** (optional, for containerized multi-service run)

---

### Local Development Setup

#### 1. Backend Setup

1. **Activate Python virtual environment:**
   ```powershell
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1

   # Linux/macOS
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   Ensure `.env` contains valid cryptographic keys:
   - `JWT_SECRET_KEY`: Minimum 32 random characters (no placeholders).
   - `DOCUMENT_ENCRYPTION_KEY`: Valid 32-byte url-safe base64 Fernet key distinct from `JWT_SECRET_KEY`.
   - `GEMINI_API_KEY`: Google AI Studio API key (optional for local mock/fallback mode).

4. **Start the backend server:**
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

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

3. **Start the development server:**
   ```bash
   npm run dev
   ```
   The application will run on `http://localhost:5173`.

4. **Build for production:**
   ```bash
   npm run build
   ```

---

### Running with Docker Compose

To orchestrate the backend with a PostgreSQL 16 database:

1. **Ensure environment variables are configured in `.env`:**
   ```env
   POSTGRES_USER=docuai
   POSTGRES_PASSWORD=your_secure_password
   POSTGRES_DB=docuai
   JWT_SECRET_KEY=your_secure_random_jwt_secret_key_at_least_32_chars
   DOCUMENT_ENCRYPTION_KEY=your_32_byte_base64_fernet_key
   GEMINI_API_KEY=your_gemini_api_key
   ```

2. **Build and launch containers:**
   ```bash
   docker compose up --build
   ```

3. **Verify container services:**
   - PostgreSQL 16 container: `localhost:5432`
   - FastAPI Backend container: `http://localhost:8000`
   - Healthcheck probe: `http://localhost:8000/health`

---

## API Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :---: |
| `POST` | `/auth/register` | Register an enterprise user account (rate limited: 3/min) | No |
| `POST` | `/auth/login` | Authenticate user and receive JWT access token (rate limited: 5/min) | No |
| `POST` | `/auth/logout` | Revoke current token and add JTI to database blacklist | Yes |
| `GET` | `/auth/me` | Fetch authenticated user profile details | Yes |
| `POST` | `/upload` | Upload document (PDF/Image) and trigger LangGraph agent workflow | Yes |
| `GET` | `/documents` | List all documents owned by current authenticated user | Yes |
| `GET` | `/documents/{id}` | Retrieve document metadata, analysis, and multimodal tables/charts | Yes |
| `POST` | `/documents/{id}/qa` | Single-document grounded Q&A with page citations | Yes |
| `GET` | `/documents/{id}/qa/history` | Retrieve single-document conversation history | Yes |
| `POST` | `/documents/multi-qa` | Cross-document synthesis Q&A across multiple owned document IDs | Yes |
| `GET` | `/documents/multi-qa/history` | Retrieve multi-document synthesis conversation history | Yes |
| `GET` | `/audit-logs` | Retrieve user-scoped audit event logs | Yes |
| `GET` | `/admin/users` | List platform users (Admin only) | Admin |
| `PUT` | `/admin/users/{id}/role` | Update user role (`user` or `admin`) (Admin only) | Admin |
| `GET` | `/admin/stats` | Platform statistics: users, documents, Q&A queries (Admin only) | Admin |
| `GET` | `/health` | Health check endpoint returning service and database vitality | No |

---

## Testing & Verification

The platform features a comprehensive end-to-end regression suite covering API routing, multimodal parsing, security controls, agent workflows, cross-document synthesis, and PDF QA remediation:

```bash
# Run full regression test suite (128 tests across 13 modules - 100% pass rate)
pytest backend/tests -v

# Run targeted test suites
pytest backend/tests/test_qa_pipeline_remediation.py -v
pytest backend/tests/test_phase7_integration.py -v
pytest backend/tests/test_phase6_deployment.py -v
pytest backend/tests/test_phase5_agentic.py -v
pytest backend/tests/test_phase4_remediation.py -v
pytest backend/tests/test_phase4_multimodal.py -v
pytest backend/tests/test_phase3_qa.py -v
pytest backend/tests/test_phase2_security.py -v
```

---

## Known Limitations & Deployment Considerations

1. **Gemini API Configuration:** In the current default deployment environment, `GEMINI_API_KEY` is not configured. The platform operates safely in offline/air-gapped mode.
2. **Extractive RAG Fallback:** When `GEMINI_API_KEY` is not configured or offline, the platform automatically activates its high-precision extractive retrieval fallback engine (`answer_mode="retrieval_fallback"`). Grounded answers and citations are directly extracted from verified document passages without generative hallucination. To enable Google Gemini generative synthesis, supply a valid `GEMINI_API_KEY` in `.env`.
3. **Chart & Diagram Interpretation:** Without Gemini Multimodal Vision API credentials, visual charts and diagram interpretations rely on extracted labels, titles, drawing counts, and heuristics. Deep visual semantic reasoning on charts requires enabling Gemini Vision.
4. **In-Memory Rate Limiting:** The built-in sliding-window rate limiter runs in-memory per FastAPI worker process. For horizontally scaled, multi-pod production environments behind a load balancer, a shared distributed cache (such as Redis) should be attached to prevent per-instance rate limiter bypass.

---

## License

This project is licensed under the MIT License.
