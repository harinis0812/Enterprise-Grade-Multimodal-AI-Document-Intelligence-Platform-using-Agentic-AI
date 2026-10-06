# System Architecture

## Enterprise-Grade Multimodal AI Document Intelligence Platform

The system is organized into five major layers:

1. User Interface
2. Application/API Layer
3. Multimodal Document Processing
4. Agentic AI Workflow
5. Persistence and MLOps

## Processing Flow

User Upload
→ FastAPI
→ PDF/Image Processing
→ PyMuPDF / PaddleOCR
→ Document Agent
→ Classification Agent
→ Extraction Agent
→ Analysis Agent
→ Supervisor/Orchestrator
→ Verification Agent
→ PostgreSQL
→ React Frontend

## Agentic AI Layer

The Supervisor Agent acts as the orchestration layer.

Specialized agents:

- Document Agent
- Classification Agent
- Extraction Agent
- Analysis Agent
- Verification Agent

The document intake stage initiates the workflow.

LangGraph maintains the shared document state and controls conditional routing.

## Deployment

The application supports:

- Local development
- Docker
- Docker Compose
- PostgreSQL
- Kubernetes deployment manifests

## MLOps

MLflow is used for experiment and document-processing tracking.

Tracked information includes:

- Document type
- Word count
- Processing status
