class VerificationAgent:

    def __init__(self):
        self.name = "Document Verification Agent"

    def verify(
        self,
        extracted_text,
        document_type,
        extracted_information,
        analysis
    ):

        print(f"[{self.name}] Verifying results...")

        verification = {
            "status": "verified",
            "document_type_valid": False,
            "information_valid": False,
            "analysis_valid": False,
            "issues": []
        }

        # Verify document type
        if document_type:
            verification["document_type_valid"] = True
        else:
            verification["issues"].append(
                "Document type could not be determined."
            )

        # Verify extracted information
        if extracted_information:
            verification["information_valid"] = True
        else:
            verification["issues"].append(
                "No structured information was extracted."
            )

        # Verify analysis
        if analysis and analysis.get("summary"):
            verification["analysis_valid"] = True
        else:
            verification["issues"].append(
                "Document analysis is incomplete."
            )

        # Final verification status
        if verification["issues"]:
            verification["status"] = "needs_review"

        return verification