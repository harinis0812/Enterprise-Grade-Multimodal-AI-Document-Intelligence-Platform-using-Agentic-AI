class AgentSupervisor:

    def __init__(self):
        self.name = "AI Supervisor"

    def decide(
        self,
        extracted_text,
        document_type,
        extracted_information,
        analysis
    ):

        print(f"[{self.name}] Deciding next action...")

        decision = {
            "next_agent": None,
            "reason": "",
            "requires_verification": True
        }

        # No text extracted
        if not extracted_text.strip():

            decision["next_agent"] = "extraction_agent"

            decision["reason"] = (
                "No text was extracted. "
                "Document requires additional extraction."
            )

            return decision

        # Document type not identified
        if not document_type:

            decision["next_agent"] = "classification_agent"

            decision["reason"] = (
                "Document type is unavailable. "
                "Classification is required."
            )

            return decision

        # Information missing
        if not extracted_information:

            decision["next_agent"] = "extraction_agent"

            decision["reason"] = (
                "Structured information is missing. "
                "Extraction is required."
            )

            return decision

        # Analysis missing
        if not analysis:

            decision["next_agent"] = "analysis_agent"

            decision["reason"] = (
                "Document analysis is unavailable. "
                "Analysis is required."
            )

            return decision

        # Everything is available
        decision["next_agent"] = "verification_agent"

        decision["reason"] = (
            "Document processing is complete. "
            "Results should be verified."
        )

        return decision