from backend.agents.graph_workflow import DocumentGraphWorkflow


def make_workflow():
    return DocumentGraphWorkflow()


def test_document_agent():
    workflow = make_workflow()

    result = workflow._document_node({
        "filename": "test.pdf",
        "extracted_text": "Employee Report",
        "agent_trace": []
    })

    assert result["status"] == "document_received"
    assert "Document Agent" in result["agent_trace"]


def test_classification_agent_employee():
    workflow = make_workflow()

    result = workflow._classification_node({
        "extracted_text": "Employee Name: Harini Department: AI ML",
        "agent_trace": []
    })

    assert result["document_type"] == "Employee Report"
    assert "Classification Agent" in result["agent_trace"]


def test_classification_agent_invoice():
    workflow = make_workflow()

    result = workflow._classification_node({
        "extracted_text": "Invoice Number: INV001 Total Amount: 5000",
        "agent_trace": []
    })

    assert result["document_type"] == "Invoice"


def test_classification_agent_contract():
    workflow = make_workflow()

    result = workflow._classification_node({
        "extracted_text": "This agreement is between two parties.",
        "agent_trace": []
    })

    assert result["document_type"] == "Contract"


def test_extraction_agent():
    workflow = make_workflow()

    result = workflow._extraction_node({
        "extracted_text": "Employee Name: Harini Department: AI",
        "document_type": "Employee Report",
        "agent_trace": []
    })

    info = result["document_information"]

    assert info["document_type"] == "Employee Report"
    assert info["category"] == "Employee Information"
    assert info["employee_data_found"] is True
    assert info["department_data_found"] is True


def test_analysis_agent():
    workflow = make_workflow()

    text = "Employee Name Harini Department AI Python Machine Learning"

    result = workflow._analysis_node({
        "extracted_text": text,
        "document_type": "Employee Report",
        "agent_trace": []
    })

    analysis = result["analysis"]

    assert analysis["document_type"] == "Employee Report"
    assert analysis["status"] == "analysis_completed"
    assert len(analysis["key_findings"]) >= 3


def test_supervisor_routes_to_verification_when_complete():
    workflow = make_workflow()

    result = workflow._supervisor_node({
        "extracted_text": "Employee Report Harini AI",
        "document_type": "Employee Report",
        "document_information": {
            "category": "Employee Information"
        },
        "analysis": {
            "status": "analysis_completed"
        },
        "agent_trace": []
    })

    decision = result["supervisor_decision"]

    assert decision["next_agent"] == "verification"
    assert decision["requires_verification"] is True
    assert "Supervisor Agent" in result["agent_trace"]


def test_supervisor_routes_to_classification_when_type_missing():
    workflow = make_workflow()

    result = workflow._supervisor_node({
        "extracted_text": "Employee Report Harini AI",
        "document_type": "",
        "document_information": {},
        "analysis": {},
        "agent_trace": []
    })

    assert result["supervisor_decision"]["next_agent"] == "classification"


def test_supervisor_routes_to_extraction_when_information_missing():
    workflow = make_workflow()

    result = workflow._supervisor_node({
        "extracted_text": "Employee Report Harini AI",
        "document_type": "Employee Report",
        "document_information": {},
        "analysis": {},
        "agent_trace": []
    })

    assert result["supervisor_decision"]["next_agent"] == "extraction"


def test_supervisor_routes_to_analysis_when_analysis_missing():
    workflow = make_workflow()

    result = workflow._supervisor_node({
        "extracted_text": "Employee Report Harini AI",
        "document_type": "Employee Report",
        "document_information": {
            "category": "Employee Information"
        },
        "analysis": {},
        "agent_trace": []
    })

    assert result["supervisor_decision"]["next_agent"] == "analysis"


def test_verification_agent():
    workflow = make_workflow()

    result = workflow._verification_node({
        "document_type": "Employee Report",
        "document_information": {
            "category": "Employee Information"
        },
        "analysis": {
            "status": "analysis_completed"
        },
        "agent_trace": []
    })

    verification = result["verification"]

    assert verification["status"] == "verified"
    assert verification["document_type_valid"] is True
    assert verification["information_valid"] is True
    assert verification["analysis_valid"] is True
    assert verification["issues"] == []
    assert "Verification Agent" in result["agent_trace"]


def test_verification_detects_missing_information():
    workflow = make_workflow()

    result = workflow._verification_node({
        "document_type": "Employee Report",
        "document_information": {},
        "analysis": {
            "status": "analysis_completed"
        },
        "agent_trace": []
    })

    assert result["verification"]["status"] == "needs_review"
    assert result["verification"]["information_valid"] is False


def test_complete_agentic_workflow():
    workflow = make_workflow()

    result = workflow.process(
        "employee_test.pdf",
        "Employee Report Employee Name Harini Department AI ML Python"
    )

    assert result["document_type"] == "Employee Report"
    assert result["document_information"]
    assert result["analysis"]
    assert result["supervisor_decision"]
    assert result["verification"]["status"] == "verified"

    expected_agents = [
        "Document Agent",
        "Classification Agent",
        "Extraction Agent",
        "Analysis Agent",
        "Supervisor Agent",
        "Verification Agent",
    ]

    for agent in expected_agents:
        assert agent in result["agent_trace"]
