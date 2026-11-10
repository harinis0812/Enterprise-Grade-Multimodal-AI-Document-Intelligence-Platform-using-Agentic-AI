from sqlalchemy import text
from backend.core.encryption import encrypt_text, is_encrypted
from backend.database.database import engine


def migrate_data_to_encrypted():
    """
    Idempotent, non-destructive migration that encrypts existing plaintext records
    at rest in docuai.db for sensitive document and Q&A fields.
    Never deletes or truncates any records.
    """
    migrated_docs = 0
    migrated_qa = 0

    try:
        with engine.begin() as conn:
            # 1. Migrate documents table
            doc_rows = conn.execute(
                text("SELECT id, extracted_text, analysis, agent_trace FROM documents")
            ).fetchall()

            for row in doc_rows:
                doc_id, extracted_text, analysis, agent_trace = row
                updates = {}

                if extracted_text and not is_encrypted(extracted_text):
                    updates["extracted_text"] = encrypt_text(extracted_text)

                if analysis and not is_encrypted(analysis):
                    updates["analysis"] = encrypt_text(analysis)

                if agent_trace and not is_encrypted(agent_trace):
                    updates["agent_trace"] = encrypt_text(agent_trace)

                if updates:
                    set_clauses = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    updates["doc_id"] = doc_id
                    conn.execute(
                        text(f"UPDATE documents SET {set_clauses} WHERE id = :doc_id"),
                        updates
                    )
                    migrated_docs += 1

            # 2. Migrate qa_history table
            qa_rows = conn.execute(
                text("SELECT id, question, answer FROM qa_history")
            ).fetchall()

            for row in qa_rows:
                qa_id, question, answer = row
                updates = {}

                if question and not is_encrypted(question):
                    updates["question"] = encrypt_text(question)

                if answer and not is_encrypted(answer):
                    updates["answer"] = encrypt_text(answer)

                if updates:
                    set_clauses = ", ".join([f"{k} = :{k}" for k in updates.keys()])
                    updates["qa_id"] = qa_id
                    conn.execute(
                        text(f"UPDATE qa_history SET {set_clauses} WHERE id = :qa_id"),
                        updates
                    )
                    migrated_qa += 1

        if migrated_docs > 0 or migrated_qa > 0:
            print(
                f"[Encryption Migration] Successfully encrypted {migrated_docs} existing documents "
                f"and {migrated_qa} Q&A records at rest."
            )
        else:
            print("[Encryption Migration] Database is already encrypted at rest. No migration required.")

        return migrated_docs, migrated_qa

    except Exception as e:
        print(f"[Encryption Migration] Warning: Migration encountered an issue: {e}")
        return 0, 0


if __name__ == "__main__":
    migrate_data_to_encrypted()
