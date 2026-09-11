class DocumentAgent:

    def __init__(self):
        self.name = "Document Intake Agent"

    def process(self, filename, extracted_text):
        print(f"[{self.name}] Processing document...")

        result = {
            "filename": filename,
            "text_length": len(extracted_text),
            "status": "document_received"
        }

        return result