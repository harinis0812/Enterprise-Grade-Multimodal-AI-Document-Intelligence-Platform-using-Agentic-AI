class AnalysisAgent:

    def __init__(self):
        self.name = "Document Analysis Agent"

    def analyze(self, extracted_text, document_type, extracted_information):

        print(f"[{self.name}] Analyzing document...")

        analysis = {
            "document_type": document_type,
            "summary": "",
            "key_findings": [],
            "status": "analysis_completed"
        }

        text = extracted_text.strip()

        if not text:
            analysis["summary"] = "No text was extracted from the document."
            analysis["key_findings"].append(
                "Document requires further processing."
            )
            return analysis

        words = text.split()

        analysis["summary"] = (
            f"This document was identified as a {document_type} "
            f"containing approximately {len(words)} words."
        )

        if extracted_information:
            analysis["key_findings"].append(
                "Structured information was successfully extracted."
            )

        analysis["key_findings"].append(
            f"Document contains {len(words)} words."
        )

        analysis["key_findings"].append(
            "Document is ready for verification."
        )

        return analysis