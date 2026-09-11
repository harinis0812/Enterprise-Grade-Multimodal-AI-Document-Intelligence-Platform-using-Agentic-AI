class ExtractionAgent:

    def __init__(self):
        self.name = "Information Extraction Agent"

    def extract(self, extracted_text, document_type):

        print(f"[{self.name}] Extracting information...")

        text = extracted_text.lower()

        information = {
            "document_type": document_type,
            "text_length": len(extracted_text)
        }

        if document_type == "Employee Report":

            information["category"] = "Employee Information"

            if "employee" in text:
                information["employee_data_found"] = True

            if "department" in text:
                information["department_data_found"] = True

            if "salary" in text:
                information["salary_data_found"] = True

        elif document_type == "Invoice":

            information["category"] = "Financial Document"

            if "invoice number" in text:
                information["invoice_number_found"] = True

            if "total amount" in text:
                information["total_amount_found"] = True

        elif document_type == "Contract":

            information["category"] = "Legal Document"

            if "agreement" in text:
                information["agreement_found"] = True

            if "terms and conditions" in text:
                information["terms_found"] = True

        else:

            information["category"] = "General Document"

        return information