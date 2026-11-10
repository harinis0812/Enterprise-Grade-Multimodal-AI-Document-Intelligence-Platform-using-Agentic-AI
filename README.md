# Enterprise-Grade Multimodal AI Document Intelligence Platform Using Agentic AI

An autonomous, production-grade enterprise document intelligence platform that ingests, parses, analyzes, verifies, and cross-synthesizes heterogeneous business documents using multimodal AI and agentic workflows. The system seamlessly handles native digital PDFs, scanned documents, mixed-content files, complex financial tables, charts, and diagrams. It extracts structured content and visual metadata via PyMuPDF and PaddleOCR, orchestrates a 7-agent state machine using LangGraph with supervisor verification and retry boundaries, performs grounded dual-mode question answering with page-level citations, and enforces defense-in-depth cybersecurity controls (authenticated AES-128-CBC field-level encryption at rest, JTI token revocation, sliding-window rate limiting, and strict multi-tenant isolation).

---

## Table of Contents

- [Project Overview](#project-overview)
- [Problem Statement](#problem-statement)
- [Objectives](#objectives)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Seven Development Phases](#seven-development-phases)
- [Agentic AI Workflow](#agentic-ai-workflow)
- [Multimodal Document Processing](#multimodal-document-processing)
- [RAG and PDF Question Answering](#rag-and-pdf-question-answering)
- [Security Implementation](#security-implementation)
- [Database Design](#database-design)
- [API Endpoints](#api-endpoints)
- [Installation and Setup](#installation-and-setup)
- [Running the Application](#running-the-application)
- [Testing and Verification Results](#testing-and-verification-results)
- [Known Limitations](#known-limitations)
- [Future Enhancements](#future-enhancements)
- [Project Structure](#project-structure)

---

## Project Overview

Modern enterprises process thousands of mission-critical documents daily—invoices, regulatory filings, financial disclosures, contracts, technical specifications, and executive reports. These documents arrive in diverse formats, often blending structured tables, unstructured prose, scanned pages, and visual diagrams. 

Traditional Optical Character Recognition (OCR) systems extract uncontextualized text streams, while standard Large Language Model (LLM) pipelines suffer from hallucinations, context window overflow, lack of verifiable source attribution, and vulnerability to prompt injection. Furthermore, enterprise adoption is frequently halted by stringent security, privacy, and regulatory requirements (GDPR, HIPAA, SOC 2) prohibiting unencrypted storage, leaky logs, or cross-tenant data exposure.

The **Enterprise-Grade Multimodal AI Document Intelligence Platform Using Agentic AI** solves these challenges by combining:
1. **Multimodal Ingestion Engine:** Accurately parses digital text, extracts table structures into Markdown, detects embedded charts and visual diagrams, and routes low-density scanned pages to PaddleOCR.
2. **LangGraph Multi-Agent Orchestration:** Deploys a cyclic graph of specialized agents (Intake, Classification, Extraction, Analysis, Supervisor, Verification, and Multi-Document Synthesis) with deterministic retry limits and quality safeguards.
3. **Dual-Mode Grounded RAG:** Delivers high-precision Question Answering across single documents and multi-document corpora, providing verbatim quotes, page numbers, document filename badges, and honest abstention when evidence is insufficient.
4. **Air-Gapped & Resilient Fallback:** Automatically switches between Google Gemini generative synthesis and a high-precision extractive retrieval engine when offline or when API credentials are not provisioned.
5. **Zero-Trust Enterprise Security:** Incorporates authenticated field-level encryption at rest (Fernet AES-128-CBC + HMAC-SHA256), JWT token revocation via database blacklisting, IP-isolated rate limiting, non-leaking distributed request tracing (`X-Request-ID`), and strict multi-tenant data isolation.

---

## Problem Statement

Enterprise document workflows face several persistent operational and technological hurdles:

- **Heterogeneous Document Formats:** Real-world documents are rarely clean digital text. They contain scanned receipts, multi-page financial tables spanning page breaks, embedded charts, and handwritten annotations.
- **LLM Hallucination and Traceability Deficits:** Standard generative AI applications frequently generate plausible-sounding but factually inaccurate answers without verifiable citations to specific pages, tables, or source documents.
- **Cross-Document Synthesis Bottlenecks:** Comparing data across multiple documents (e.g., comparing FY2023 revenue in an annual report against FY2024 projections in a strategy memo) requires manual correlation and cross-referencing.
- **Brittle Monolithic Pipelines:** Traditional extraction pipelines lack self-correction. If a parser fails on a corrupted table or scanned page, the entire extraction pipeline crashes without retry mechanisms or human-in-the-loop review flags.
- **Security and Compliance Exposure:** Storing extracted text, executive summaries, and Q&A transcripts in plaintext exposes sensitive enterprise data. Additionally, missing request rate limits, lack of distributed tracing, and unmitigated cross-tenant authorization flaws risk severe regulatory violations.

---

## Objectives

The platform was designed, implemented, and verified to achieve the following core objectives:

1. **High-Fidelity Multimodal Parsing:** Extract textual, tabular, and visual content from PDFs and images with automated OCR routing, bounding-box coverage calculation, and text deduplication.
2. **Autonomous Agentic Coordination:** Implement a multi-agent system using LangGraph where specialized agents collaborate, cross-verify outputs, track execution metrics, and handle failures with bounded retries (maximum 2 retries) before graceful escalation.
3. **Verifiable, Grounded Retrieval-Augmented Generation (RAG):** Provide question-answering with authentic page-level and document-level citations, eliminating hallucinated responses and layout metadata artifacts (such as headers or page labels).
4. **Cross-Document Comparative Intelligence:** Enable authenticated users to select multiple documents and ask cross-cutting comparative questions with clear multi-source attribution.
5. **Cryptographic Protection at Rest:** Enforce field-level authenticated encryption (AES-128-CBC + HMAC-SHA256) across all sensitive columns in the database, ensuring zero plaintext exposure in storage dumps.
6. **Robust Multi-Tenancy & Access Governance:** Enforce strict user-level data boundaries across all document access and synthesis routes, logging access violations as security audit events.
7. **Production-Ready Observability & Deployment:** Containerize backend and database services using Docker Compose, support distributed tracing via ASGI request ID middleware, implement zero-leak latency logging, and integrate MLflow for experiment tracking.

---

## Key Features

### 1. Multimodal Document Ingestion
- **Native Digital Text Extraction:** High-speed text extraction via PyMuPDF (`fitz`), preserving structural reading order and page boundaries.
- **Intelligent Mixed-Content OCR:** Analyzes text density per page; automatically activates PaddleOCR for scanned or image-heavy pages, calculating bounding-box coverage and deduplicating overlapping text.
- **Structural Table Extraction:** Detects tables with PyMuPDF `find_tables()`, converts them into standard GitHub Flavored Markdown, preserves row/column alignments, and maintains page continuity markers.
- **Visual Element & Chart Detection:** Identifies embedded vector drawings, plots, and layout diagrams, distinguishing structural separators from semantic business charts.

### 2. Autonomous Multi-Agent Reasoning (LangGraph)
- **Specialized Agent Roles:** Deploys Document Intake, Classification, Extraction, Analysis, Supervisor, Verification, and Multi-Document Synthesis agents.
- **Cyclic Supervisor Graph:** The Supervisor Agent evaluates extraction completeness, dispatches corrective retries (capped at 2 attempts), prevents infinite loops, and escalates unresolved ambiguities to human review (`needs_review`).
- **Telemetry & Execution Metrics:** The shared state tracks per-agent timestamps, execution duration in milliseconds, decision outcomes, and retry counts.

### 3. Dual-Mode Grounded Question Answering
- **Single Document Q&A:** Targeted, in-depth questioning against a specific active document with page citations and multimodal evidence badges (Table, Chart, OCR, Text).
- **Multi-Document Synthesis:** Cross-document intelligence across user-selected document sets. Provides synthesis responses highlighting source files consulted, contrasting findings, and citing individual documents.
- **Intent Classification:** Word-boundary regex tokenization identifies question intent (`financial`, `comparison`, `tabular`, `visual`, `summary`, `factual`) without substring collisions.
- **Domain Synonym & Acronym Expansion:** Expands financial, technical, and executive terminology (e.g., `revenue` $\leftrightarrow$ `sales, income, turnover`; `CEO`, `OCR`, `NLP`) to maximize passage recall.
- **Zero-Hallucination Fallback:** Operates with Google Gemini 1.5 Flash when API keys are configured; seamlessly switches to a high-precision multi-sentence extractive fallback engine when offline or unconfigured.
- **Layout & Metadata Filtration:** Robust filtering (`is_header_or_metadata`, `clean_passage_text`) ensures running headers, page numbers, and title tags are never returned as answers or citation quotes.

### 4. Enterprise-Grade Defense-in-Depth Security
- **Authenticated Encryption at Rest:** Sensitive database columns (`extracted_text`, `analysis`, `agent_trace`, `QAHistory`, `MultiDocQAHistory`) are encrypted using Fernet (AES-128-CBC + HMAC-SHA256) via an automatic SQLAlchemy `EncryptedText` TypeDecorator.
- **JWT Authentication & Lifecycle:** HMAC-SHA256 tokens with cryptographically enforced secret length (minimum 32 characters). Includes a database-backed `RevokedToken` blacklist (`POST /auth/logout`) tracking JTI claims.
- **Brute-Force Rate Limiting:** Sliding-window in-memory rate limiting applied to authentication endpoints (`/auth/login` capped at 5/min, `/auth/register` capped at 3/min).
- **Role-Based Access Control (RBAC):** Distinct `user` and `admin` permission tiers with administrative APIs for user listing, role promotion, and system telemetry (`/admin/users`, `/admin/stats`).
- **Strict Multi-Tenant Isolation:** All document lookups, single-doc Q&A, and multi-doc synthesis requests verify document ownership against `current_user.id`. Any unauthorized access attempts return HTTP 403/404 and record `CROSS_USER_ACCESS_DENIED` in the immutable audit log.
- **Prompt Injection Defense:** Untrusted document context is strictly isolated within `<document_context>` XML boundaries.

### 5. Production Observability & Scalability
- **Distributed Request Tracing:** Pure ASGI `RequestIDMiddleware` validates incoming `X-Request-ID` headers against `^[a-zA-Z0-9\-_]{1,64}$` or generates UUID4 fallbacks, propagating them across response headers and application logs.
- **Zero-Leak Latency Logging:** Structured timing logs capture HTTP method, path, status, and duration in milliseconds while strictly redacting authorization tokens, passwords, cookies, query parameters, and document payloads.
- **Database Connection Pooling:** Dynamic SQLAlchemy configuration supporting SQLite for lightweight development and PostgreSQL 16 with pre-ping validation (`pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`, `pool_timeout=30`) for production.
- **Container Orchestration:** Optimized multi-stage `Dockerfile` (Python 3.11-slim) and `docker-compose.yml` orchestrating FastAPI and PostgreSQL 16 with health check dependencies.
- **MLOps Tracking:** MLflow tracking logs document processing runs, file types, word counts, and agent execution times.

### 6. Modern Dual-Mode User Interface
- **Vite + React 19 Frontend:** Modern, high-performance web interface styled with vanilla CSS.
- **Dual-Mode Switcher Tabs:** Seamless switching between Single Document Q&A and Multi-Document Synthesis.
- **Multi-Document Scope Controls:** Interactive document chips with one-click **Select All** and **Clear All** capabilities, selection counters, and safety validation.
- **Rich Citation Cards:** Expandable citation cards displaying source document badges (`📄 filename.pdf` or `Doc #id`), page numbers, evidence types, and retrieval relevance percentages.
- **Documents-Consulted Indicators:** Visual pills highlighting all files synthesized during cross-document analysis.

---

## Technology Stack

| Layer | Component | Version / Specification | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | React | 19.x | Component-based interactive user interface |
| | Vite | 8.2.x | Next-generation frontend tooling and bundler |
| | Lucide React | Latest | Modern iconography |
| | Axios | Latest | Promise-based HTTP client with auth interceptors |
| **Backend & API** | Python | 3.11.x | Core programming language |
| | FastAPI | 0.110+ | High-performance asynchronous REST API framework |
| | Uvicorn | Latest | ASGI web server implementation |
| | Pydantic | v2 | Request/response data validation and schema management |
| **Multimodal AI** | PyMuPDF (`fitz`) | 1.23+ | High-performance PDF parsing, text, table, and layout extraction |
| | PaddleOCR | 2.7+ | Optical Character Recognition for scanned pages |
| | Pillow & OpenCV | Latest | Image processing, conversion, and geometry calculation |
| **Agentic AI & LLM** | LangGraph | 0.0.30+ | Multi-agent state graph orchestration and cyclic execution |
| | LangChain Core | Latest | Base agent interfaces and prompt message structures |
| | Google Gemini API | 1.5 Flash | Multimodal generative question answering and reasoning |
| **Security & Auth** | Cryptography (Fernet) | Latest | Authenticated AES-128-CBC + HMAC-SHA256 field-level encryption |
| | PyJWT | Latest | JSON Web Token encoding, decoding, and JTI claims |
| | Passlib & Bcrypt | Latest | Cryptographic password hashing with unique salt |
| **Database & MLOps** | SQLAlchemy | 2.x | Database ORM, dynamic engine pooling, and TypeDecorators |
| | PostgreSQL | 16 | Production relational database |
| | SQLite | 3.x | Zero-configuration local development database |
| | MLflow | 2.11+ | MLOps experiment tracking and document processing telemetry |
| **DevOps & Infra** | Docker & Compose | Compose v2 | Containerization and multi-service orchestration |
| | ASGI Middleware | Custom | Distributed tracing (`X-Request-ID`) and safe latency logging |
| **Testing** | Pytest | Latest | Automated testing framework (128 passing tests) |
| | HTTPX | Latest | Async HTTP testing client |

---

## System Architecture

The platform is architected across five distinct layers to guarantee separation of concerns, scalability, and security:

```
+----------------------------------------------------------------------------------------------------+
| 1. PRESENTATION LAYER (React 19 + Vite)                                                            |
|    - Dual-Mode Q&A Workspace (Single-Doc Target vs Multi-Doc Synthesis)                           |
|    - Multi-Doc Scope Selector Bar (Interactive Chips, Select All, Clear All)                       |
|    - Attributed Citations (Document Badges, Page Numbers, Evidence Pills, Relevance Scores)        |
|    - Real-Time Dashboard, Document Inspection Modal, and Multimodal Visual Indicators             |
+----------------------------------------------------------------------------------------------------+
                                                 │ (HTTPS / REST API)
                                                 ▼
+----------------------------------------------------------------------------------------------------+
| 2. API & PERIMETER SECURITY LAYER (FastAPI + ASGI Middleware)                                      |
|    - Distributed Tracing: Pure ASGI RequestIDMiddleware (Validates / Generates X-Request-ID)      |
|    - Zero-Leak Latency Logging: Structured millisecond timing (Redacts Auth, Passwords, Bodies)    |
|    - In-Memory Bucket Rate Limiter: /auth/login (5/min), /auth/register (3/min)                    |
|    - JWT Authentication: HMAC-SHA256 (>=32-char secret) with JTI Blacklist (/auth/logout)          |
|    - Role-Based Access Control (RBAC): 'user' and 'admin' roles with dedicated admin APIs          |
|    - Multi-Tenant Isolation: Strict scoping by current_user.id (HTTP 403 on tenant violations)    |
+----------------------------------------------------------------------------------------------------+
                                                 │
                                                 ▼
+----------------------------------------------------------------------------------------------------+
| 3. MULTIMODAL INGESTION & PROCESSING LAYER                                                         |
|    - PyMuPDF Native Text Parser: Structural order extraction & page boundary isolation            |
|    - PaddleOCR Scanned Page Router: Density analysis, bounding-box coverage, text deduplication    |
|    - Table Extraction Engine: PyMuPDF find_tables(), Markdown formatting, page continuity markers  |
|    - Visual Element Detector: Identifies charts, diagrams, drawings; prepares Gemini Vision payload|
+----------------------------------------------------------------------------------------------------+
                                                 │
                                                 ▼
+----------------------------------------------------------------------------------------------------+
| 4. AGENTIC AI REASONING LAYER (LangGraph Cyclic State Graph)                                       |
|    - Document Intake Agent ──► Ingestion validation & metadata normalization                       |
|    - Classification Agent  ──► Identifies document category (Contract, Invoice, Report, Resume)   |
|    - Extraction Agent      ──► Structured entities, key-value pairs, dates, financial amounts      |
|    - Analysis Agent        ──► Executive summary, risk factors, financial health signals           |
|    - Supervisor Agent      ──► Evaluates quality, enforces retry cap (max 2), escalates failures   |
|    - Verification Agent    ──► Verifies schema completeness, sets final verification status        |
|    - Multi-Doc Synthesis   ──► Cross-document comparative reasoning & multi-source attribution     |
+----------------------------------------------------------------------------------------------------+
                                                 │
                                                 ▼
+----------------------------------------------------------------------------------------------------+
| 5. PERSISTENCE & DATA-AT-REST SECURITY LAYER                                                       |
|    - Authenticated Encryption at Rest: Fernet (AES-128-CBC + HMAC-SHA256) via EncryptedText        |
|      (Encrypted columns: extracted_text, analysis, agent_trace, question, answer)                  |
|    - Dynamic Database Engine: SQLite (Local Dev) / PostgreSQL 16 with Pool Pre-Ping (Production)   |
|    - MLOps Telemetry: MLflow tracking for runs, parameters, metrics, and document metadata         |
+----------------------------------------------------------------------------------------------------+
```

### System Architecture Flowchart

```mermaid
flowchart TD
    subgraph UI["Presentation Layer (React 19 + Vite)"]
        A["User Upload / Query"] --> B["Dual-Mode Q&A UI"]
        B --> B1["Single Document Mode"]
        B --> B2["Multi-Document Synthesis"]
    end

    subgraph API["API & Security Layer (FastAPI)"]
        C["Pure ASGI RequestIDMiddleware"] --> D["Rate Limiter (5/min login, 3/min register)"]
        D --> E["JWT Auth & JTI Blacklist Verification"]
        E --> F["Multi-Tenant Boundary Guard (Ownership Verification)"]
    end

    subgraph MULTIMODAL["Multimodal Ingestion Pipeline"]
        G["File Validator (10MB, 100 Pages)"] --> H{"Content Type"}
        H -- "Native Text" --> I["PyMuPDF Parser"]
        H -- "Scanned / Image" --> J["PaddleOCR Engine"]
        H -- "Tables & Charts" --> K["Table Extractor & Visual Detector"]
    end

    subgraph AGENTS["LangGraph Multi-Agent Orchestration"]
        L["Document Agent"] --> M["Classification Agent"]
        M --> N["Extraction Agent"]
        N --> O["Analysis Agent"]
        O --> P{"Supervisor Agent"}
        P -- "Retry < 2" --> N
        P -- "Retry >= 2 / Success" --> Q["Verification Agent"]
    end

    subgraph RAG["Grounded Q&A & Synthesis Engine"]
        R["Intent Classifier & Query Expander"]
        S["Passage Chunking & Scoring"]
        T{"Gemini Configured?"}
        T -- "Yes" --> U["Gemini 1.5 Flash (Generative Synthesis)"]
        T -- "No / Offline" --> V["Extractive Fallback Engine (No Headers / Metadata)"]
        W["Attributed Citations Generator"]
    end

    subgraph DATA["Persistence & Security at Rest"]
        X["Fernet Authenticated Encryption (AES-128-CBC)"]
        Y[("PostgreSQL 16 / SQLite Engine")]
        Z["MLflow Telemetry Tracking"]
    end

    UI --> API
    API --> MULTIMODAL
    MULTIMODAL --> AGENTS
    AGENTS --> DATA
    API --> RAG
    RAG --> DATA
```

### End-to-End Processing Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant Pipe as Multimodal Ingestion
    participant Graph as LangGraph Multi-Agent
    participant QA as RAG & QA Service
    participant DB as Encrypted Database

    User->>UI: Upload Document (PDF / Image)
    UI->>API: POST /upload (with Bearer Token & X-Request-ID)
    API->>API: Verify Token & JTI Revocation Status
    API->>Pipe: Validate file size (<=10MB) & page ceiling (<=100)
    Pipe->>Pipe: PyMuPDF Text + PaddleOCR (if scanned) + Tables + Charts
    Pipe->>Graph: Initiate DocumentState
    Graph->>Graph: Classify -> Extract -> Analyze
    Graph->>Graph: Supervisor checks completeness (max 2 retries)
    Graph->>Graph: Verification agent sets final status & metrics
    Graph->>DB: Write Record (Fernet encrypts text, analysis, traces)
    DB-->>API: Document ID & Status
    API-->>UI: HTTP 200 (Document Processed & Verified)

    User->>UI: Submit Question (Single or Multi-Document)
    UI->>API: POST /documents/{id}/qa OR /documents/multi-qa
    API->>API: Verify Ownership of All Specified Document IDs
    alt Cross-User Unauthorized ID Detected
        API-->>UI: HTTP 403 Forbidden (Log CROSS_USER_ACCESS_DENIED)
    else Authorized Ownership Confirmed
        API->>QA: Retrieve Passages & Classify Intent
        QA->>QA: Filter layout headers/metadata (is_header_or_metadata)
        alt Gemini API Key Available
            QA->>QA: Generative Synthesis (Gemini 1.5 Flash)
        else Offline / Unconfigured Key
            QA->>QA: High-Precision Extractive Fallback Engine
        end
        QA->>DB: Store Turn in QAHistory / MultiDocQAHistory (Encrypted)
        QA-->>API: Grounded Answer + Citations + Consulted Docs
        API-->>UI: HTTP 200 Answer Payload
        UI-->>User: Render Answer with Badges, Citations, & Evidence Pills
    end
```

---

## Seven Development Phases

The project was executed through seven structured, sequentially verified development phases, followed by a dedicated post-phase pipeline remediation:

```
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Core Document Intake, Multi-Agent Architecture, and MLOps                                │
│ - PyMuPDF parsing, PaddleOCR integration, LangGraph baseline, MLflow tracking.                    │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 2: Advanced Enterprise Security, Encryption at Rest, and RBAC                               │
│ - Fernet field-level encryption, JWT revocation blacklist, sliding rate limiter, RBAC.            │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 3: Generative AI Q&A Enhancement and Grounded Retrieval                                     │
│ - Google Gemini provider, TF-IDF passage chunking, prompt injection guardrails, citations.        │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 4: Advanced Multimodal Document Understanding (Tables, Charts, Mixed OCR)                   │
│ - Mixed-content OCR deduplication, PyMuPDF Markdown table extraction, chart/diagram detector.    │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 5: Advanced Agentic Intelligence and Cross-Document Retrieval                               │
│ - Supervisor retry limits (cap=2), agent execution telemetry, multi-document synthesis backend.   │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 6: Enterprise Deployment, Observability, and Scalability                                    │
│ - Docker Compose, PostgreSQL 16 pooling, pure ASGI RequestIDMiddleware, zero-leak latency logs.  │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Phase 7: Final Integration, Dual-Mode Frontend, and Acceptance                                    │
│ - Dual-mode UI (Single vs Multi-Doc), document selection chips, consulted pills, Vite build.      │
└──────────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                                   ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Post-Phase Remediation: PDF QA Pipeline & Extractive Fallback Remediation                         │
│ - Header/layout filtering, concept overlap scoring, multi-sentence extractive fallback.          │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### Phase 1: Core Document Intake, Multi-Agent Architecture, and MLOps
- Built the foundational FastAPI application supporting file upload validation (10 MB size limit, 100-page limit, MIME type checks).
- Implemented hybrid text ingestion combining native digital PyMuPDF extraction with PaddleOCR for scanned documents.
- Established the initial LangGraph agent state graph coordinating Document, Classification, Extraction, Analysis, and Verification agents.
- Integrated MLflow to log run parameters, document classification tags, word counts, and agent execution times.

### Phase 2: Advanced Enterprise Security, Encryption at Rest, and RBAC
- Built authenticated field-level encryption at rest using Fernet (AES-128-CBC + HMAC-SHA256) via a custom SQLAlchemy `EncryptedText` TypeDecorator, encrypting sensitive fields (`extracted_text`, `analysis`, `agent_trace`).
- Developed JWT authentication enforcing a minimum 32-character secret key and created a database-backed `RevokedToken` blacklist (`POST /auth/logout`) tracking JTI claims.
- Implemented an IP-isolated sliding-window rate limiter protecting `/auth/login` (5/min) and `/auth/register` (3/min).
- Introduced Role-Based Access Control (RBAC) with `user` and `admin` roles, providing administrative endpoints for user management and telemetry (`/admin/users`, `/admin/stats`).

### Phase 3: Generative AI Q&A Enhancement and Grounded Retrieval
- Implemented an HTTP-based Google Gemini provider supporting Gemini 1.5 Flash with exponential backoff retries.
- Created passage-level retrieval segmenting document text into overlapping windows (~900 characters with 150-character overlap) respecting page boundaries.
- Designed prompt injection defense wrapping untrusted document context inside `<document_context>` XML boundaries.
- Built a citation attribution engine deriving citations strictly from retrieved passages, with clean abstention when evidence is insufficient.

### Phase 4: Advanced Multimodal Document Understanding
- Solved mixed-content PDF extraction by calculating bounding-box coverage of native text versus embedded images, routing image regions to PaddleOCR and deduplicating text.
- Implemented table extraction via PyMuPDF `find_tables()`, converting raw table cells into formatted Markdown tables with row/column alignment and multi-page continuation headers.
- Created a visual element detection engine distinguishing structural lines and layout borders from meaningful charts and diagrams.
- Prepared Base64 image payloads for multimodal Gemini Vision reasoning.

### Phase 5: Advanced Agentic Intelligence and Cross-Document Retrieval
- Hardened the LangGraph Supervisor Agent with explicit retry boundaries (`retry_counts["extraction"] < 2`), preventing infinite execution loops and escalating unresolved failures to `needs_review`.
- Extended the state schema with `agent_metrics` to record per-agent execution duration, timestamps, and status.
- Built word-boundary regex intent classification (`financial`, `comparison`, `tabular`, `visual`, `summary`, `factual`) preventing false substring collisions.
- Developed domain synonym and acronym expansion to enhance retrieval recall.
- Engineered the cross-document intelligence engine (`POST /documents/multi-qa`, `GET /documents/multi-qa/history`) supporting synthesis across multiple owned files with strict cross-user access denial (HTTP 403 + `CROSS_USER_ACCESS_DENIED` audit logging).

### Phase 6: Enterprise Deployment, Observability, and Scalability
- Containerized the platform using a production-ready `Dockerfile` (Python 3.11-slim) and `docker-compose.yml` coordinating the backend and a PostgreSQL 16 database.
- Implemented dynamic database pooling in SQLAlchemy (`pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`, `pool_timeout=30`).
- Engineered a pure ASGI `RequestIDMiddleware` validating incoming client `X-Request-ID` headers against `^[a-zA-Z0-9\-_]{1,64}$` or generating UUID4 fallbacks.
- Built zero-leak latency logging recording request duration in milliseconds while strictly redacting authorization tokens, passwords, cookies, and document bodies.

### Phase 7: Final Integration, Dual-Mode Frontend, and Acceptance
- Upgraded the React Q&A workspace (`frontend/src/views/AskView.jsx`) to a dual-mode interface: Single Document Q&A and Multi-Document Synthesis.
- Built interactive multi-document selection chips with **Select All** and **Clear All** controls and real-time selection counters.
- Designed rich citation cards displaying source document badges (`📄 filename.pdf` or `Doc #id`), page numbers, evidence types, and retrieval relevance scores.
- Implemented visual **Documents Consulted** indicators rendering badges for all files referenced in multi-document synthesis turns.
- Verified frontend production compilation using Vite with zero errors and zero warnings.

### Post-Phase Remediation: PDF QA Pipeline & Extractive Fallback Remediation
- Diagnosed and resolved an issue where extractive fallback returned layout headers or page numbers (e.g., `Page 1 - Overview - Introduction.`) when `GEMINI_API_KEY` was not configured.
- Added comprehensive layout and header filtration (`is_header_or_metadata`, `clean_passage_text`, `get_substantive_sentences`) to strip running headers, page markers, and title fragments.
- Implemented conceptual overlap scoring and query intent routing, delivering coherent multi-sentence answers for factual, definition, summary, and comparative inquiries across single and multi-document modes.
- Authoring 13 dedicated unit and integration tests (`backend/tests/test_qa_pipeline_remediation.py`), bringing the full test suite to 128 passing tests.

---

## Agentic AI Workflow

The platform orchestrates document analysis using LangGraph, modeling the workflow as a stateful, cyclic directed graph.

### The 7 Specialized Agents

1. **Document Intake Agent (`document`):** Validates uploaded file dimensions, MIME type, and page count; initializes the execution state and telemetry logs.
2. **Classification Agent (`classification`):** Analyzes the text and layout structure to classify the document into enterprise categories: `Contract`, `Invoice`, `Financial Report`, `Technical Specification`, or `Resume`.
3. **Extraction Agent (`extraction`):** Extracts key-value pairs, dates, currencies, party names, line items, and structural Markdown tables.
4. **Analysis Agent (`analysis`):** Generates an executive summary, detects financial health signals, identifies compliance risks, and compiles operational metadata.
5. **Supervisor Agent (`supervisor`):** Acts as the orchestrator and quality gatekeeper. Evaluates extraction completeness and consistency. If critical data is missing and retries are under the threshold (`retries < 2`), it increments `retry_counts["extraction"]` and routes execution back to the Extraction Agent. If retries reach 2, it halts the loop and escalates to Verification with `status="needs_review"`.
6. **Verification Agent (`verification`):** Validates the final document state against the Pydantic schema, records execution duration in `agent_metrics`, and flags the document as `verified` or `needs_review`.
7. **Multi-Document Synthesis Agent (`multi_doc_qa`):** Operates on demand during multi-document Q&A. Collects candidate passages across multiple files, identifies cross-document correlations and discrepancies, and formats synthesized comparative answers.

### LangGraph State Schema (`DocumentState`)

```python
class DocumentState(TypedDict):
    document_id: int
    filename: str
    file_type: str
    file_size: int
    page_count: int
    raw_text: str
    cleaned_text: str
    tables: List[Dict[str, Any]]
    charts: List[Dict[str, Any]]
    classification: Dict[str, Any]
    extracted_data: Dict[str, Any]
    analysis: Dict[str, Any]
    verification: Dict[str, Any]
    status: str                         # "processed", "verified", "needs_review", "failed"
    agent_trace: List[Dict[str, Any]]
    agent_metrics: Dict[str, Dict[str, Any]]  # Per-agent execution duration & status
    retry_counts: Dict[str, int]        # e.g., {"extraction": 1} (strictly capped at 2)
```

---

## Multimodal Document Processing

Enterprise documents frequently combine native text, scanned receipts, complex tables, and diagrams. The platform employs a specialized multimodal processing pipeline:

### 1. Mixed-Content PDF Parsing & OCR
- **PyMuPDF Extraction:** Directly extracts font-encoded text and spatial coordinates with near-zero latency.
- **Scanned Page Detection:** Computes the character density and image area coverage per page. Pages with low text density (< 50 characters) or high image coverage (> 50% page area) are automatically flagged as scanned.
- **PaddleOCR Routing:** Scanned pages and embedded raster images are rendered at 300 DPI and processed through PaddleOCR.
- **Bounding-Box Deduplication:** When a page contains both digital text and OCR-extracted text, bounding-box intersection calculations prevent duplicate sentences from entering the passage index.

### 2. High-Precision Table Extraction
- **Boundary Detection:** Uses PyMuPDF `Page.find_tables()` to detect horizontal and vertical grid lines, cell intersections, and header rows.
- **Markdown Conversion:** Transforms extracted cells into clean GitHub Flavored Markdown tables:
  ```markdown
  | Fiscal Quarter | Gross Revenue | Operating Expenses | Net Margin |
  | :--- | :--- | :--- | :--- |
  | Q1 2024 | $12.4M | $8.1M | 34.6% |
  | Q2 2024 | $14.2M | $8.9M | 37.3% |
  ```
- **Page Continuity:** Tables spanning multiple pages are linked using continuous page index markers (`[Table 1 - Page 2 Continued]`).

### 3. Visual Element & Chart Detection
- **Vector Graphic Analysis:** Inspects drawing commands (curves, rectangles, line segments). Distinguishes cosmetic borders and dividing rules from complex graphical plots.
- **Chart Classification:** Elements with multi-axis paths, legends, or clustered labels are categorized as charts/diagrams (`bar_chart`, `line_graph`, `flowchart`, `architecture_diagram`).
- **Vision Payload Preparation:** High-resolution crops of detected visual regions are Base64-encoded to enable multimodal reasoning with Google Gemini Vision.

---

## RAG and PDF Question Answering

The Retrieval-Augmented Generation (RAG) engine powers both Single Document Q&A and Multi-Document Synthesis.

### 1. Passage Segmentation & Indexing
- Documents are segmented into overlapping text passages of approximately 900 characters with 150-character overlaps.
- Chunk boundaries strictly respect page breaks, guaranteeing that every retrieved passage maps to an exact `page_number`.
- Extracted Markdown tables and chart descriptions are indexed as dedicated passages with their corresponding `evidence_type` (`table`, `chart`, `ocr`, `text`).

### 2. Query Intent Classification & Synonym Expansion
- **Token-Boundary Intent Classifier:** Analyzes incoming questions using regex word boundaries (`\b\w+\b`) to detect:
  - `financial`: `amount`, `total`, `revenue`, `cost`, `budget`, `profit`, `margin`
  - `comparison`: `compare`, `difference`, `versus`, `vs`, `between`, `contrast`
  - `tabular`: `table`, `column`, `row`, `matrix`, `breakdown`, `grid`
  - `visual`: `chart`, `graph`, `diagram`, `trend`, `figure`, `plot`
  - `summary`: `summary`, `summarize`, `overview`, `key findings`, `main points`
  - `factual`: General informational inquiries
- **Domain Synonym Expansion:** Expands financial, technical, and operational terms (e.g., `revenue` $\rightarrow$ `sales, turnover, income`; `profit` $\rightarrow$ `margin, earnings, net income`; `expenses` $\rightarrow$ `spending, expenditure`).

### 3. Layout & Metadata Filtration
To prevent running headers, section titles, and page indicators from being selected as answers or citation quotes, the engine applies multi-stage filtering:
- `PAGE_HEADER_FOOTER_REGEX`: Strips layout tags like `Page 1 - Overview`, `Page 1 of 10`, `--- Page 2 ---`, and `[Table ...]`.
- `is_header_or_metadata(sentence)`: Identifies and rejects sentence candidates lacking substantive predicates or full narrative clauses.
- `clean_passage_text(text)`: Removes layout noise while fully preserving Markdown tables and explanatory prose.

### 4. Dual-Engine Generation & Fallback Architecture

```
                          Incoming Query & Retrieved Passages
                                          │
                                          ▼
                       Does GEMINI_API_KEY exist in .env?
                                    /           \
                             Yes   /             \   No / Offline
                                  ▼               ▼
                   [Gemini 1.5 Flash Provider]   [Extractive Fallback Engine]
                   - XML Context Isolation       - Intent-Specific Synthesis
                   - Natural Language Synthesis  - Coherent Multi-Sentence Assembly
                   - Verbatim Retrieved Quotes   - Direct Passage Grounding
                   - answer_mode: "generative"   - answer_mode: "retrieval_fallback"
                                  \               /
                                   \             /
                                    ▼           ▼
                           Final Attributed Response
                           - Grounded Answer Text
                           - Page & Document Badges
                           - Evidence Type & Relevance Scores
                           - Documents Consulted Pills
```

- **Generative Mode (`answer_mode="generative"`):** When `GEMINI_API_KEY` is provisioned, the prompt is wrapped in `<document_context>` XML boundaries. Gemini 1.5 Flash generates comprehensive natural-language answers citing specific evidence passages.
- **Extractive Fallback Mode (`answer_mode="retrieval_fallback"`):** When offline or unconfigured, the fallback engine constructs complete, multi-sentence answers directly from the highest-scoring substantive passages. It handles factual questions, definitions, multi-sentence summaries, and comparative queries without generative hallucination.
- **Honest Abstention:** When the retrieved passages do not contain sufficient evidence to answer the user's question, both engines return:
  > *"The document does not contain enough evidence to answer this question."*  
  with zero citations, preventing misleading outputs.

### 5. Multi-Document Synthesis (`POST /documents/multi-qa`)
- Accepts a list of document IDs (`document_ids: [1, 2, 4]`) and a user query.
- Validates that every document ID exists and is owned by `current_user.id`.
- Segments and ranks passages across all selected documents.
- In generative mode, formats a `<multi_document_context>` grouped by Document ID and Filename. In extractive mode, extracts substantive evidence sentences per document formatted as:
  `- In **{filename}** (page {num}): {substantive_finding}`
- Emits citations containing the source `document_id` and `filename`, alongside an array of `documents_consulted`.

---

## Security Implementation

The platform implements a multi-layered defense-in-depth security model:

```
+-----------------------------------------------------------------------------------+
| 1. PERIMETER & NETWORK SECURITY                                                   |
|    - CORS origin whitelisting with credentials support                            |
|    - Pure ASGI RequestIDMiddleware with alphanumeric/hyphen sanitization          |
|    - Zero-leak structured latency logging (strictly redacts tokens, bodies, keys)  |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 2. RATE LIMITING & DOS MITIGATION                                                 |
|    - Sliding-window in-memory bucket limiter: /auth/login (5/min), register (3/min)|
|    - Strict upload ceilings: 10 MB file size limit, 100 PDF page maximum          |
|    - LangGraph supervisor retry cap: Maximum 2 retries before forced escalation   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 3. IDENTITY, AUTHENTICATION & ACCESS CONTROL (IAM)                                |
|    - Cryptographically strong JWT keys (minimum 32 characters, validated at boot) |
|    - JTI claim tracking with RevokedToken database blacklist (/auth/logout)       |
|    - Bcrypt password hashing with unique per-user cryptographic salts             |
|    - Role-Based Access Control (RBAC): 'user' and 'admin' roles                   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 4. STRICT MULTI-TENANT ISOLATION                                                  |
|    - Document queries strictly scoped by Document.user_id == current_user.id      |
|    - Single Q&A returns HTTP 404 / 403 on unowned documents                       |
|    - Multi-Doc Q&A verifies ownership across all IDs; returns HTTP 403 on breach  |
|    - Logs CROSS_USER_ACCESS_DENIED audit events for tenant violation attempts     |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 5. GENAI & PROMPT INJECTION DEFENSE                                               |
|    - Untrusted document context strictly encapsulated in <document_context> XML   |
|    - Clean abstention when evidence is insufficient                               |
|    - Citations derived strictly from retrieved passages (prevents model spoofing) |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| 6. DATA AT REST ENCRYPTION & AUDIT LOGGING                                        |
|    - Authenticated encryption at rest (Fernet AES-128-CBC + HMAC-SHA256)          |
|    - Encrypted columns: extracted_text, analysis, agent_trace, question, answer   |
|    - Immutable audit log tracking user ID, IP address, event type, and timestamp  |
+-----------------------------------------------------------------------------------+
```

### 1. Authenticated Field-Level Encryption at Rest
- Sensitive database fields are protected using Fernet encryption (AES-128-CBC with PKCS7 padding and HMAC-SHA256 authentication).
- Implemented as a transparent SQLAlchemy `TypeDecorator` (`EncryptedText`). When saving to the database, plaintext is encrypted into a base64 ciphertext token (`gAAAAA...`). When loading from the database, the token is verified and decrypted.
- Inspecting the raw database file (`docuai.db`) confirms that sensitive document text, executive summaries, agent traces, and Q&A transcripts are 100% encrypted.
- Enforces cryptographic separation: `DOCUMENT_ENCRYPTION_KEY` must be completely distinct from `JWT_SECRET_KEY`.

### 2. Token Revocation Blacklist (`POST /auth/logout`)
- Every issued JWT token includes a unique `jti` (JWT ID) UUID claim.
- When a user logs out, the token's JTI and its expiration timestamp are recorded in the `RevokedToken` database table.
- The authentication dependency checks the blacklist on every authenticated request. Revoked tokens are immediately rejected with HTTP 401 Unauthorized.

### 3. Multi-Tenant Cross-User Isolation
- All database queries filter strictly by `user_id == current_user.id`.
- Single-document queries for another user's document return HTTP 404 Not Found, preventing user enumeration.
- Multi-document queries (`POST /documents/multi-qa`) validate every document ID in the requested array. If any document belongs to another user:
  - The request is immediately aborted with HTTP 403 Forbidden.
  - A `CROSS_USER_ACCESS_DENIED` event is written to the immutable audit log recording the offending user ID, IP address, and requested document IDs.

### 4. Zero-Leak Request Latency Logging
- Implemented in `backend/main.py`. Records every incoming request with:
  - Method, Path, Status Code, Duration (ms), and Client IP.
- Strictly redacts all authorization headers, Bearer tokens, passwords, cookies, query parameters, and request/response bodies.

---

## Database Design

The platform uses SQLAlchemy ORM with support for both SQLite (local development) and PostgreSQL 16 (production container).

### Entity-Relationship Diagram

```mermaid
erDiagram
    User ||--o{ Document : "owns"
    User ||--o{ QAHistory : "submits"
    User ||--o{ MultiDocQAHistory : "submits"
    User ||--o{ AuditEvent : "triggers"
    Document ||--o{ QAHistory : "references"

    User {
        int id PK
        string email UK
        string hashed_password
        string full_name
        string role "user | admin"
        boolean is_active
        datetime created_at
    }

    Document {
        int id PK
        int user_id FK
        string filename
        string file_type
        int file_size
        int page_count
        string status "processed | verified | needs_review | failed"
        EncryptedText extracted_text "Fernet Encrypted"
        EncryptedText analysis "Fernet Encrypted"
        EncryptedText agent_trace "Fernet Encrypted"
        text tables "JSON Markdown Tables"
        text charts "JSON Visual Elements"
        datetime created_at
    }

    QAHistory {
        int id PK
        int document_id FK
        int user_id FK
        EncryptedText question "Fernet Encrypted"
        EncryptedText answer "Fernet Encrypted"
        text citations "JSON Citations"
        datetime created_at
    }

    MultiDocQAHistory {
        int id PK
        int user_id FK
        text document_ids "JSON Array of IDs"
        EncryptedText question "Fernet Encrypted"
        EncryptedText answer "Fernet Encrypted"
        text citations "JSON Citations"
        text documents_consulted "JSON Array"
        datetime created_at
    }

    RevokedToken {
        int id PK
        string jti UK
        datetime revoked_at
        datetime expires_at
    }

    AuditEvent {
        int id PK
        int user_id FK
        string event_type
        text details "JSON Details"
        string ip_address
        datetime created_at
    }
```

### Table Schemas & Encryption Mapping

| Model Name | Table Name | Key Columns | Encrypted Fields (Fernet AES-128-CBC) |
| :--- | :--- | :--- | :--- |
| `User` | `users` | `id`, `email`, `hashed_password`, `role`, `is_active` | None (password hashed via bcrypt) |
| `Document` | `documents` | `id`, `user_id`, `filename`, `file_type`, `status` | `extracted_text`, `analysis`, `agent_trace` |
| `QAHistory` | `qa_history` | `id`, `document_id`, `user_id`, `citations` | `question`, `answer` |
| `MultiDocQAHistory` | `multi_doc_qa_history` | `id`, `user_id`, `document_ids`, `citations`, `documents_consulted` | `question`, `answer` |
| `RevokedToken` | `revoked_tokens` | `id`, `jti`, `revoked_at`, `expires_at` | None |
| `AuditEvent` | `audit_events` | `id`, `user_id`, `event_type`, `ip_address`, `created_at` | None |

### Connection Pooling Configuration (`backend/database/database.py`)
- **`pool_pre_ping=True`:** Tests socket vitality before issuing queries, transparently recycling disconnected connections.
- **`pool_size=5`:** Base pool of persistent database connections per worker process.
- **`max_overflow=10`:** Allows up to 15 concurrent transactions during peak bursts.
- **`pool_timeout=30`:** Maximum seconds a worker waits for an available pool slot before failing safely.

---

## API Endpoints

All protected endpoints require a valid Bearer token passed in the `Authorization` header (`Bearer <token>`). Every request receives an `X-Request-ID` tracing header in the response.

| HTTP Method | Route Endpoint | Description | Auth Tier | Rate Limit |
| :--- | :--- | :--- | :---: | :---: |
| `POST` | `/auth/register` | Register an enterprise user account | Public | 3 / min |
| `POST` | `/auth/login` | Authenticate with email/password; returns JWT | Public | 5 / min |
| `POST` | `/auth/logout` | Revoke active JWT; adds JTI to blacklist | User | — |
| `GET` | `/auth/me` | Fetch authenticated user profile details | User | — |
| `POST` | `/upload` | Upload PDF/image (<=10MB); triggers LangGraph agent workflow | User | — |
| `GET` | `/documents` | List all documents owned by the authenticated user | User | — |
| `GET` | `/documents/{id}` | Retrieve document metadata, analysis, tables, and charts | User | — |
| `POST` | `/documents/{id}/qa` | Single-document grounded Q&A with page citations | User | — |
| `GET` | `/documents/{id}/qa/history` | Retrieve single-document conversation history | User | — |
| `POST` | `/documents/multi-qa` | Cross-document synthesis Q&A across selected document IDs | User | — |
| `GET` | `/documents/multi-qa/history` | Retrieve multi-document synthesis conversation history | User | — |
| `GET` | `/audit-logs` | Retrieve user-scoped audit security events | User | — |
| `GET` | `/admin/users` | List all platform users and roles | Admin | — |
| `PUT` | `/admin/users/{id}/role` | Update user role (`user` or `admin`) | Admin | — |
| `GET` | `/admin/stats` | Platform metrics: user count, documents, Q&A queries | Admin | — |
| `GET` | `/health` | System health check (API status, database connectivity) | Public | — |

---

## Installation and Setup

### Prerequisites

- **Python:** 3.11.x
- **Node.js:** 18.x or 20.x (with npm)
- **Git**
- **Docker & Docker Compose** (optional, for containerized multi-service run)

---

### Step-by-Step Local Setup

#### 1. Clone Repository & Setup Virtual Environment

```powershell
# Clone the repository
git clone https://github.com/harinis0812/Enterprise-Grade-Multimodal-AI-Document-Intelligence-Platform-using-Agentic-AI.git
cd "Enterprise-Grade-Multimodal-AI-Document-Intelligence-Platform-using-Agentic-AI"

# Create and activate Python 3.11 virtual environment
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

#### 2. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

#### 3. Configure Environment Variables

Create `.env` by copying the template file:

```bash
cp .env.example .env
```

Generate secure cryptographic keys using Python:

```powershell
# Generate 32-byte Fernet key for DOCUMENT_ENCRYPTION_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Generate 32-character secret for JWT_SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
```

Configure your `.env` file:

```env
# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database Connection (SQLite for local dev, PostgreSQL for production)
DATABASE_URL=sqlite:///./docuai.db

# Cryptographic Keys (Mandatory)
JWT_SECRET_KEY=your_generated_64_character_hex_secret_here_minimum_32_chars
DOCUMENT_ENCRYPTION_KEY=your_generated_32_byte_urlsafe_base64_fernet_key_here==

# Rate Limiting
LOGIN_RATE_LIMIT=5
REGISTER_RATE_LIMIT=3

# Google Gemini API (Optional: leave blank to use high-precision extractive fallback)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-flash

# CORS Settings
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000","http://127.0.0.1:5173"]
```

#### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### 1. Local Development Mode

#### Start Backend API Server
```powershell
# In project root with venv activated
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```
- Backend API: `http://localhost:8000`
- Interactive OpenAPI Swagger Docs: `http://localhost:8000/docs`
- Healthcheck Endpoint: `http://localhost:8000/health`

#### Start Frontend UI Development Server
```powershell
# In a separate terminal, navigate to frontend
cd frontend
npm run dev
```
- Frontend Web Application: `http://localhost:5173`

---

### 2. Frontend Production Build

To verify and compile the optimized production bundle:

```powershell
cd frontend
npm run build
```

The production assets compile into `frontend/dist/`:
- `dist/index.html` (~0.82 kB)
- `dist/assets/index-*.css` (~56.29 kB)
- `dist/assets/index-*.js` (~275.36 kB)

---

### 3. Containerized Deployment with Docker Compose

To orchestrate the backend API service alongside a PostgreSQL 16 database:

```bash
# Build and launch all container services
docker compose up --build

# Run in detached background mode
docker compose up -d --build

# View container logs
docker compose logs -f backend

# Stop containers
docker compose down
```

Services initialized by Docker Compose:
- **`postgres` container (`docuai-postgres`):** Accessible at `localhost:5432` with health checks.
- **`backend` container (`docuai-backend-compose`):** Accessible at `http://localhost:8000` with automated startup health probing.

---

## Testing and Verification Results

The platform incorporates comprehensive automated regression test coverage across all architectural layers, with **128 tests passing across 13 test modules in 31.08s (100% pass rate, 0 failures, 0 skips)**.

### Full Regression Test Execution

```powershell
.\venv\Scripts\python.exe -m pytest backend/tests/ -v
```

### Complete Test Suite Breakdown

| # | Test Module File | Architectural Domain / Target Capability | Tests | Status |
| :---: | :--- | :--- | :---: | :---: |
| 1 | `backend/tests/test_agent_workflow.py` | LangGraph state graph, agent routing, supervisor verification | 11 | **PASSED** |
| 2 | `backend/tests/test_document.py` | Document upload, file boundaries, MIME validation, intake limits | 9 | **PASSED** |
| 3 | `backend/tests/test_mlflow_tracking.py` | MLflow tracking setup, document run telemetry logging | 2 | **PASSED** |
| 4 | `backend/tests/test_phase2_security.py` | Fernet encryption at rest, JWT revocation, rate limiting, RBAC | 15 | **PASSED** |
| 5 | `backend/tests/test_phase3_qa.py` | Gemini provider, passage scoring, grounded retrieval, citations | 14 | **PASSED** |
| 6 | `backend/tests/test_phase4_multimodal.py` | PyMuPDF tables, markdown formatting, continuation, visual detector | 13 | **PASSED** |
| 7 | `backend/tests/test_phase4_remediation.py` | Mixed OCR bounding-box coverage, text deduplication, MIME checks | 17 | **PASSED** |
| 8 | `backend/tests/test_phase5_agentic.py` | Supervisor retry cap (max 2), intent classification, multi-doc API | 12 | **PASSED** |
| 9 | `backend/tests/test_phase6_deployment.py` | ASGI `X-Request-ID` middleware, zero-leak logging, `/health` | 5 | **PASSED** |
| 10 | `backend/tests/test_phase7_integration.py` | Single/multi Q&A end-to-end, cross-user isolation, schema validation | 3 | **PASSED** |
| 11 | `backend/tests/test_qa.py` | Single-document passage retrieval and citation unit tests | 10 | **PASSED** |
| 12 | `backend/tests/test_qa_pipeline_remediation.py` | Layout/header filtering, concept overlap scoring, extractive fallback | 13 | **PASSED** |
| 13 | `backend/tests/test_security.py` | User auth, login, password tampering, multi-tenant isolation | 11 | **PASSED** |
| **TOTAL** | **13 Test Modules** | **Full Platform End-to-End Regression** | **128** | **128/128 PASSED (100%)** |

### Verified Test Duration
- Total execution time: **31.08 seconds**
- Test execution output: `128 passed, 2 warnings in 31.08s`
- Zero failed, zero skipped, zero hanging processes.

### Master Backup Inventory
Twelve complete, non-overlapping physical backups are preserved on `D:\`:
1. `D:\Enterprise_Platform_Backup_Phase1`
2. `D:\Enterprise_Platform_Backup_Phase2`
3. `D:\Enterprise_Platform_Backup_Phase3`
4. `D:\Enterprise_Platform_Backup_Phase4`
5. `D:\Enterprise_Platform_Backup_Phase4_Final_Remediation`
6. `D:\Enterprise_Platform_Backup_Master`
7. `D:\Enterprise_Platform_Backup_Phases5_6_7`
8. `D:\Enterprise_Platform_Backup_Phase6_Investigation`
9. `D:\Enterprise_Platform_Backup_Phase7_PreIntegration`
10. `D:\Enterprise_Platform_Backup_Phase7_UI_Implementation`
11. `D:\Enterprise_Platform_Backup_QA_Pipeline_Fix`
12. `D:\Enterprise_Platform_Backup_Consolidate_README`

---

## Known Limitations

In the interest of full technical transparency, the following architectural and deployment characteristics are documented:

1. **Default Unconfigured Gemini API Key:** In the default development environment, `GEMINI_API_KEY` is not populated. The platform operates out-of-the-box in air-gapped / offline mode using its high-precision extractive retrieval fallback engine (`answer_mode="retrieval_fallback"`). Grounded answers and citations are directly extracted from verified document passages without generative hallucination. To activate generative synthesis, provide a valid Google Gemini API key in `.env`.
2. **Visual Chart & Diagram Semantic Interpretation:** Without Gemini Multimodal Vision API credentials, visual chart and diagram interpretation relies on bounding-box heuristics, drawing element counts, and extracted axis labels. Deep semantic visual reasoning on charts requires enabling Gemini Vision.
3. **In-Memory Rate Limiting Scope:** The built-in sliding-window rate limiter maintains state in memory per FastAPI worker process. In horizontally scaled multi-pod production environments behind a load balancer, rate limits should be backed by a centralized Redis cluster to prevent per-instance rate limiter bypass.
4. **Multi-Document Synthesis Scope Ceiling:** Multi-document Q&A is currently bounded to a maximum of 10 simultaneous documents per query to maintain predictable response latencies.
5. **Sequential Node Execution:** In the current LangGraph state machine, table extraction and visual element detection execute sequentially rather than concurrently across parallel worker branches.

---

## Future Enhancements

The following features represent the forward-looking development roadmap for the platform:

- **Redis-Backed Distributed Security Cache:** Migrate sliding-window rate limiting and JTI token revocation from in-memory/database storage to Redis for high-throughput distributed clusters.
- **Dense Vector Embedding Search:** Integrate pgvector with PostgreSQL or an external vector database (e.g., ChromaDB, Milvus) alongside the current lexical TF-IDF + subword retrieval engine.
- **Gemini 1.5 Pro Multimodal Vision:** Implement direct image-to-text visual reasoning for charts, plots, and complex mechanical schematics using Gemini 1.5 Pro.
- **Streaming Token Delivery:** Implement Server-Sent Events (SSE) or WebSockets to stream generative answer tokens and real-time LangGraph agent trace steps to the React user interface.
- **Enterprise RBAC Hierarchy:** Extend user roles to include fine-grained organizational tenants, workspace-level permissions, and an `auditor` role with read-only access to audit logs.
- **Batch Document Ingestion:** Provide asynchronous background worker queues (via Celery or ARQ) for bulk document uploads and asynchronous processing notifications.

---

## Project Structure

```text
Enterprise Platform/
│
├── Dockerfile                             # Multi-stage production container specification
├── docker-compose.yml                     # Multi-service Compose (FastAPI + PostgreSQL 16)
├── requirements.txt                       # Backend Python dependencies
├── .env.example                           # Safe environment configuration template
├── README.md                              # Master project documentation (Single Source of Truth)
│
├── backend/                               # Core Python FastAPI Application
│   ├── main.py                            # FastAPI lifespan, ASGI RequestIDMiddleware, routes
│   │
│   ├── agents/                            # LangGraph Multi-Agent Architecture
│   │   ├── __init__.py
│   │   └── graph_workflow.py              # 7-agent cyclic state graph, supervisor retry logic
│   │
│   ├── api/                               # REST API Endpoints & Routers
│   │   ├── __init__.py
│   │   ├── admin.py                       # RBAC admin endpoints (/admin/users, /admin/stats)
│   │   ├── auth.py                        # Authentication, JWT, JTI revocation, rate limiting
│   │   ├── document.py                    # Document intake, multimodal upload, ownership check
│   │   └── qa.py                          # Single-doc Q&A & multi-doc synthesis endpoints
│   │
│   ├── core/                              # Security & Infrastructure Core
│   │   ├── __init__.py
│   │   ├── config.py                      # App settings & strict cryptographic key validation
│   │   ├── encryption.py                  # Fernet AES-128-CBC + HMAC-SHA256 helpers
│   │   ├── rate_limit.py                  # In-memory sliding-window IP bucket rate limiter
│   │   └── security.py                    # JWT encoding/decoding, RBAC guards, audit events
│   │
│   ├── database/                          # Persistence & Data Modeling
│   │   ├── __init__.py
│   │   ├── database.py                    # Dynamic engine & PostgreSQL connection pooling
│   │   ├── init_db.py                     # Non-destructive schema initialization
│   │   ├── migrate_encryption.py          # Idempotent database encryption migration utility
│   │   └── models.py                      # SQLAlchemy models (User, Document, QA, MultiDocQA)
│   │
│   ├── schemas/                           # Pydantic v2 Request/Response Schemas
│   │   ├── __init__.py
│   │   ├── auth.py                        # User registration, login, token, admin schemas
│   │   ├── document.py                    # Document metadata, upload response schemas
│   │   └── qa.py                          # Q&A request, multi-doc request, citation schemas
│   │
│   ├── scripts/                           # Administrative CLI Utilities
│   │   ├── __init__.py
│   │   └── manage_users.py                # User role promotion and administration CLI
│   │
│   ├── services/                          # Business Logic & Processing Engines
│   │   ├── __init__.py
│   │   ├── llm_provider.py                # Google Gemini API provider with exponential backoff
│   │   ├── mlflow_service.py              # MLflow telemetry & experiment tracking
│   │   ├── multimodal_service.py          # Mixed-content OCR, PyMuPDF tables, chart detector
│   │   ├── pdf_service.py                 # PyMuPDF text, table, and layout extraction
│   │   └── qa_service.py                  # Intent classifier, synonym expansion, RAG fallback
│   │
│   └── tests/                             # Automated Test Suites (128 Tests Passing)
│       ├── conftest.py                    # Pytest fixtures, test database, mock OCR setup
│       ├── test_agent_workflow.py         # LangGraph state machine tests (11 tests)
│       ├── test_document.py               # Document intake & file boundary tests (9 tests)
│       ├── test_mlflow_tracking.py        # MLflow telemetry logging tests (2 tests)
│       ├── test_phase2_security.py        # Encryption at rest, JWT revocation, rate limits (15 tests)
│       ├── test_phase3_qa.py              # Gemini provider, passage scoring, citations (14 tests)
│       ├── test_phase4_multimodal.py      # PyMuPDF tables, markdown formatting, charts (13 tests)
│       ├── test_phase4_remediation.py     # OCR coverage, deduplication, MIME tests (17 tests)
│       ├── test_phase5_agentic.py         # Supervisor retry cap, intent, multi-doc API (12 tests)
│       ├── test_phase6_deployment.py      # ASGI RequestID middleware, safe latency logs (5 tests)
│       ├── test_phase7_integration.py     # Single/multi Q&A end-to-end, cross-user isolation (3 tests)
│       ├── test_qa.py                     # Single-doc retrieval & citation unit tests (10 tests)
│       ├── test_qa_pipeline_remediation.py# Layout/header filtering, extractive fallback (13 tests)
│       └── test_security.py               # Auth, password tampering, tenant isolation (11 tests)
│
└── frontend/                              # Modern React 19 + Vite User Interface
    ├── index.html                         # SPA HTML entry point
    ├── package.json                       # Frontend dependencies and build scripts
    ├── vite.config.js                     # Vite build configuration
    ├── public/                            # Static public web assets
    └── src/
        ├── App.jsx                        # Main application router and state wrapper
        ├── App.css                        # Modern CSS styling (tabs, chips, badges, cards)
        ├── main.jsx                       # React DOM entry point
        │
        ├── components/                    # Reusable UI Components
        │   ├── Header.jsx                 # Navigation bar, auth status, mode indicators
        │   └── DocumentList.jsx           # Document management table and status indicators
        │
        ├── services/                      # Frontend API Integration Layer
        │   └── api.js                     # Axios API client (auth, docs, single/multi Q&A)
        │
        └── views/                         # Primary Application Views
            ├── DashboardView.jsx          # Document upload, status cards, inspection modal
            ├── AskView.jsx                # Dual-mode Q&A workspace (Single-Doc vs Multi-Doc)
            └── LoginView.jsx              # User authentication and registration form
```

---

## License

This project is developed for enterprise demonstration, evaluation, and academic project review. All rights reserved.