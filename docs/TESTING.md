# Testing

## Existing API Tests

The project currently validates:

- Home endpoint
- Documents endpoint
- Missing document handling
- Health endpoint

## Agent Workflow Tests

The agentic workflow is additionally tested for:

- Document Agent
- Classification Agent
- Extraction Agent
- Analysis Agent
- Supervisor/Orchestrator routing
- Verification Agent
- Complete LangGraph workflow

## MLOps Tests

MLflow tracking setup and document-processing logging are tested independently.

## Validation

The project uses Pytest for automated backend validation and GitHub Actions for CI execution.
