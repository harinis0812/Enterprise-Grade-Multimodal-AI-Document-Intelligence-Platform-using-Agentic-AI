class ClassificationAgent:

    def __init__(self):
        self.name = "Document Classification Agent"

    def classify(self, extracted_text):

        print(f"[{self.name}] Classifying document...")

        text = extracted_text.lower()

        if "employee" in text or "salary" in text or "department" in text:
            document_type = "Employee Report"

        elif "invoice" in text or "total amount" in text or "invoice number" in text:
            document_type = "Invoice"

        elif "agreement" in text or "contract" in text or "terms and conditions" in text:
            document_type = "Contract"

        elif "application" in text or "applicant" in text:
            document_type = "Application Form"

        else:
            document_type = "General Document"

        return document_type