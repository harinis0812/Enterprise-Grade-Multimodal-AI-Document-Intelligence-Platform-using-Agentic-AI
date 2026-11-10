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

    table_analysis: Dict[str, Any]
    chart_analysis: Dict[str, Any]

    analysis: Dict[str, Any]

    supervisor_decision: Dict[str, Any]

    verification: Dict[str, Any]

    agent_trace: List[str]
    agent_metrics: Dict[str, Dict[str, Any]]
    retry_counts: Dict[str, int]
    execution_log: List[Dict[str, Any]]

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

        # Multimodal content detection in Agentic Workflow
        information["has_tables"] = "[Table " in text or ("\n|" in text and text.count("|") >= 4)
        information["has_charts"] = "[Visual Element:" in text or "[Chart" in text
        information["has_ocr"] = "[Image Document via OCR]" in text or "[Scanned Content via OCR]" in text

        trace = state.get("agent_trace", [])

        trace.append("Extraction Agent")


        return {

            "document_information": information,

            "agent_trace": trace

        }


    # =========================================================
    # TABLE ANALYSIS AGENT
    # =========================================================

    def _table_analysis_node(self, state: DocumentState):

        print("[LangGraph] Table Analysis Agent")

        text = state.get(
            "extracted_text",
            ""
        )

        table_count = text.count("[Table ")
        has_markdown_tables = "\n|" in text and text.count("|") >= 4

        findings = []
        if table_count > 0:
            findings.append(f"Identified {table_count} structured table block(s).")
        if has_markdown_tables:
            findings.append("Markdown tabular alignment verified.")

        table_analysis = {
            "tables_found": table_count,
            "has_markdown_tables": has_markdown_tables,
            "findings": findings,
            "status": "table_analysis_completed"
        }

        trace = state.get("agent_trace", [])
        trace.append("Table Analysis Agent")

        return {
            "table_analysis": table_analysis,
            "agent_trace": trace
        }


    # =========================================================
    # CHART / VISUAL ANALYSIS AGENT
    # =========================================================

    def _chart_analysis_node(self, state: DocumentState):

        print("[LangGraph] Chart Analysis Agent")

        text = state.get(
            "extracted_text",
            ""
        )

        visual_count = text.count("[Visual Element:")
        chart_count = text.count("[Chart")
        total_visuals = max(visual_count, chart_count)

        findings = []
        if total_visuals > 0:
            findings.append(f"Identified {total_visuals} visual diagram/chart element(s).")

        chart_analysis = {
            "visuals_found": total_visuals,
            "findings": findings,
            "status": "chart_analysis_completed"
        }

        trace = state.get("agent_trace", [])
        trace.append("Chart Analysis Agent")

        return {
            "chart_analysis": chart_analysis,
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

            "multimodal_insights": {
                "tabular_data_present": "[Table " in text or ("\n|" in text and text.count("|") >= 4),
                "visual_elements_present": "[Visual Element:" in text or "[Chart" in text,
                "ocr_processed": "[Image Document via OCR]" in text or "[Scanned Content via OCR]" in text
            },

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


        retries = dict(state.get("retry_counts", {}))
        metrics = dict(state.get("agent_metrics", {}))

        # Decide next action with retry safeguards
        if not extracted_text.strip():
            ext_retries = retries.get("extraction", 0)
            if ext_retries >= 2:
                next_agent = "verification"
                reason = "Extraction retry threshold reached (2 retries). Escalating to verification."
            else:
                retries["extraction"] = ext_retries + 1
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
            ext_retries = retries.get("extraction", 0)
            if ext_retries >= 2:
                next_agent = "verification"
                reason = "Structured extraction retry threshold reached. Escalating to verification."
            else:
                retries["extraction"] = ext_retries + 1
                next_agent = "extraction"
                reason = (
                    "Structured information is missing."
                )

        elif information.get("has_tables") and "table_analysis" not in state:

            next_agent = "table_analysis"

            reason = (
                "Document contains tabular data requiring specialized table analysis."
            )

        elif information.get("has_charts") and "chart_analysis" not in state:

            next_agent = "chart_analysis"

            reason = (
                "Document contains visual elements requiring specialized chart analysis."
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

            "requires_verification": True,

            "retry_counts": retries

        }


        trace = state.get("agent_trace", [])

        trace.append("Supervisor Agent")

        metrics["Supervisor Agent"] = {
            "status": "completed",
            "decision": next_agent,
            "reason": reason
        }


        return {

            "supervisor_decision": decision,

            "agent_trace": trace,

            "retry_counts": retries,

            "agent_metrics": metrics

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
            "table_analysis",
            self._table_analysis_node
        )

        workflow.add_node(
            "chart_analysis",
            self._chart_analysis_node
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

        workflow.add_edge(
            "table_analysis",
            "supervisor"
        )

        workflow.add_edge(
            "chart_analysis",
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

                "table_analysis":
                    "table_analysis",

                "chart_analysis":
                    "chart_analysis",

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

            "agent_trace": [],

            "agent_metrics": {},

            "retry_counts": {},

            "execution_log": []

        }


        result = self.graph.invoke(
            initial_state
        )


        return result