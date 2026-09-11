from backend.agents.document_agent import DocumentAgent
from backend.agents.classification_agent import ClassificationAgent
from backend.agents.extraction_agent import ExtractionAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.verification_agent import VerificationAgent
from backend.agents.supervisor import AgentSupervisor


class DocumentAgentWorkflow:

    def __init__(self):

        self.document_agent = DocumentAgent()
        self.classification_agent = ClassificationAgent()
        self.extraction_agent = ExtractionAgent()
        self.analysis_agent = AnalysisAgent()
        self.verification_agent = VerificationAgent()

        self.supervisor = AgentSupervisor()

    def process(self, filename, extracted_text):

        print("\n========== AGENT WORKFLOW STARTED ==========")

        # Step 1: Document Intake
        document_result = self.document_agent.process(
            filename,
            extracted_text
        )

        # Step 2: Classification
        document_type = self.classification_agent.classify(
            extracted_text
        )

        # Step 3: Information Extraction
        extracted_information = self.extraction_agent.extract(
            extracted_text,
            document_type
        )

        # Step 4: Analysis
        analysis = self.analysis_agent.analyze(
            extracted_text,
            document_type,
            extracted_information
        )

        # Step 5: Supervisor decides what happens next
        decision = self.supervisor.decide(
            extracted_text,
            document_type,
            extracted_information,
            analysis
        )

        print(
            f"[AI Supervisor] Next agent: "
            f"{decision['next_agent']}"
        )

        print(
            f"[AI Supervisor] Reason: "
            f"{decision['reason']}"
        )

        # Step 6: Verification
        verification = self.verification_agent.verify(
            extracted_text,
            document_type,
            extracted_information,
            analysis
        )

        print("========== AGENT WORKFLOW COMPLETED ==========\n")

        return {
            "document": document_result,
            "document_type": document_type,
            "document_information": extracted_information,
            "analysis": analysis,
            "supervisor_decision": decision,
            "verification": verification
        }