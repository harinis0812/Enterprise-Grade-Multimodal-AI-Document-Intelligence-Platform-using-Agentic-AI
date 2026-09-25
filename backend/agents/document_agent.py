from backend.agents.graph_workflow import DocumentGraphWorkflow


class DocumentAgent:

    def __init__(self):
        self.name = "Document Intake Agent"
        self.workflow = DocumentGraphWorkflow()

    def process(self, filename, extracted_text):
        print(f"[{self.name}] Processing document...")

        result = self.workflow.process(
            filename,
            extracted_text
        )

        return result