from typing import TypedDict, Dict, Any, List

from langgraph.graph import StateGraph, START, END

from backend.services.document_classifier import detect_document_type
from backend.services.information_extractor import (
    extract_report_information,
    extract_invoice_information,
    extract_resume_information
)


class DocumentState(TypedDict, total=False):

    filename: str
    extracted_text: str

    document_type: str
    document_information: Dict[str, Any]

    analysis: Dict[str, Any]

    supervisor_decision: Dict[str, Any]

    verification: Dict[str, Any]

    agent_trace: List[str]

    status: str


class DocumentGraphWorkflow:

    def __init__(self):

        self.graph = self._build_graph()


    # =========================================================
    # DOCUMENT AGENT
    # =========================================================

    def _document_node(self, state: DocumentState):

        print("[LangGraph] Document Agent")

        trace = state.get("agent_trace", [])

        trace.append("Document Agent")

        return {
            "status": "document_received",
            "agent_trace": trace
        }


    # =========================================================
    # CLASSIFICATION AGENT
    # =========================================================

    def _classification_node(self, state: DocumentState):

        print("[LangGraph] Classification Agent")

        raw_text = state.get(
            "extracted_text",
            ""
        )
        text = raw_text.lower()

        detected = detect_document_type(raw_text)

        if (
            "employee" in text
            or "salary" in text
            or "department" in text
            or detected == "Report"
        ):

            document_type = "Employee Report"

        elif (
            "invoice" in text
            or "total amount" in text
            or "invoice number" in text
            or detected == "Invoice"
        ):

            document_type = "Invoice"

        elif (
            "agreement" in text
            or "contract" in text
        ):

            document_type = "Contract"

        elif (
            "resume" in text
            or "curriculum vitae" in text
            or "education" in text
            or "work experience" in text
            or detected == "Resume"
        ):

            document_type = "Resume"

        else:

            document_type = "General Document"


        trace = state.get("agent_trace", [])

        trace.append("Classification Agent")


        return {
            "document_type": document_type,
            "agent_trace": trace
        }


    # =========================================================
    # EXTRACTION AGENT
    # =========================================================

    def _extraction_node(self, state: DocumentState):

        print("[LangGraph] Extraction Agent")

        text = state.get(
            "extracted_text",
            ""
        )

        document_type = state.get(
            "document_type",
            "General Document"
        )


        information = {

            "document_type": document_type,

            "text_length": len(text)

        }


        # Employee Report

        if document_type == "Employee Report":

            information["category"] = (
                "Employee Information"
            )

            if "employee" in text.lower():

                information["employee_data_found"] = True

            if "department" in text.lower():

                information["department_data_found"] = True

            if "salary" in text.lower():

                information["salary_data_found"] = True

            parsed_report = extract_report_information(text)
            for k, v in parsed_report.items():
                if v:
                    information[k] = v


        # Invoice

        elif document_type == "Invoice":

            information["category"] = (
                "Financial Document"
            )

            if "invoice" in text.lower():

                information["invoice_data_found"] = True

            if "total" in text.lower():

                information["total_amount_found"] = True

            parsed_invoice = extract_invoice_information(text)
            for k, v in parsed_invoice.items():
                if v:
                    information[k] = v


        # Contract

        elif document_type == "Contract":

            information["category"] = (
                "Legal Document"
            )

            information["contract_data_found"] = True


        # Resume

        elif document_type == "Resume":

            information["category"] = (
                "Personal Document"
            )

            parsed_resume = extract_resume_information(text)
            for k, v in parsed_resume.items():
                if v:
                    information[k] = v


        # General

        else:

            information["category"] = (
                "General Document"
            )


        trace = state.get("agent_trace", [])

        trace.append("Extraction Agent")


        return {

            "document_information": information,

            "agent_trace": trace

        }



    # =========================================================
    # ANALYSIS AGENT
    # =========================================================

    def _analysis_node(self, state: DocumentState):

        print("[LangGraph] Analysis Agent")

        text = state.get(
            "extracted_text",
            ""
        )

        document_type = state.get(
            "document_type",
            "General Document"
        )

        word_count = len(
            text.split()
        )


        analysis = {

            "document_type": document_type,

            "summary": (
                f"This document was identified as a "
                f"{document_type} containing approximately "
                f"{word_count} words."
            ),

            "key_findings": [

                "Structured information was extracted.",

                f"Document contains {word_count} words.",

                "Document is ready for verification."

            ],

            "status": "analysis_completed"

        }


        trace = state.get("agent_trace", [])

        trace.append("Analysis Agent")


        return {

            "analysis": analysis,

            "agent_trace": trace

        }


    # =========================================================
    # SUPERVISOR AGENT
    # =========================================================

    def _supervisor_node(self, state: DocumentState):

        print("[LangGraph] Supervisor Agent")


        extracted_text = state.get(
            "extracted_text",
            ""
        )

        document_type = state.get(
            "document_type",
            ""
        )

        information = state.get(
            "document_information",
            {}
        )

        analysis = state.get(
            "analysis",
            {}
        )


        # Decide next action

        if not extracted_text.strip():

            next_agent = "extraction"

            reason = (
                "No text was extracted. "
                "Extraction must be performed again."
            )

        elif not document_type:

            next_agent = "classification"

            reason = (
                "Document type is unavailable. "
                "Classification is required."
            )

        elif not information:

            next_agent = "extraction"

            reason = (
                "Structured information is missing."
            )

        elif not analysis:

            next_agent = "analysis"

            reason = (
                "Document analysis is missing."
            )

        else:

            next_agent = "verification"

            reason = (
                "All processing stages are complete. "
                "Verification is required."
            )


        decision = {

            "next_agent": next_agent,

            "reason": reason,

            "requires_verification": True

        }


        trace = state.get("agent_trace", [])

        trace.append("Supervisor Agent")


        return {

            "supervisor_decision": decision,

            "agent_trace": trace

        }


    # =========================================================
    # VERIFICATION AGENT
    # =========================================================

    def _verification_node(self, state: DocumentState):

        print("[LangGraph] Verification Agent")


        verification = {

            "status": "verified",

            "document_type_valid": bool(
                state.get("document_type")
            ),

            "information_valid": bool(
                state.get("document_information")
            ),

            "analysis_valid": bool(
                state.get("analysis")
            ),

            "issues": []

        }


        if not verification["document_type_valid"]:

            verification["status"] = "needs_review"

            verification["issues"].append(
                "Document type could not be determined."
            )


        if not verification["information_valid"]:

            verification["status"] = "needs_review"

            verification["issues"].append(
                "No structured information was extracted."
            )


        if not verification["analysis_valid"]:

            verification["status"] = "needs_review"

            verification["issues"].append(
                "Document analysis is incomplete."
            )


        trace = state.get("agent_trace", [])

        trace.append("Verification Agent")


        return {

            "verification": verification,

            "status": verification["status"],

            "agent_trace": trace

        }


    # =========================================================
    # BUILD LANGGRAPH
    # =========================================================

    def _build_graph(self):

        workflow = StateGraph(
            DocumentState
        )


        workflow.add_node(
            "document",
            self._document_node
        )

        workflow.add_node(
            "classification",
            self._classification_node
        )

        workflow.add_node(
            "extraction",
            self._extraction_node
        )

        workflow.add_node(
            "analysis",
            self._analysis_node
        )

        workflow.add_node(
            "supervisor",
            self._supervisor_node
        )

        workflow.add_node(
            "verification",
            self._verification_node
        )


        # Initial flow

        workflow.add_edge(
            START,
            "document"
        )

        workflow.add_edge(
            "document",
            "classification"
        )

        workflow.add_edge(
            "classification",
            "extraction"
        )

        workflow.add_edge(
            "extraction",
            "analysis"
        )

        workflow.add_edge(
            "analysis",
            "supervisor"
        )


        # Supervisor decides next agent

        workflow.add_conditional_edges(

            "supervisor",

            lambda state:
                state[
                    "supervisor_decision"
                ][
                    "next_agent"
                ],

            {

                "verification":
                    "verification",

                "classification":
                    "classification",

                "extraction":
                    "extraction",

                "analysis":
                    "analysis"

            }

        )


        workflow.add_edge(
            "verification",
            END
        )


        return workflow.compile()


    # =========================================================
    # PROCESS DOCUMENT
    # =========================================================

    def process(
        self,
        filename,
        extracted_text
    ):

        initial_state = {

            "filename": filename,

            "extracted_text": extracted_text,

            "agent_trace": []

        }


        result = self.graph.invoke(
            initial_state
        )


        return result