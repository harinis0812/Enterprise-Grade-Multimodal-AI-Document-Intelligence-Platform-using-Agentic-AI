import { useState, useEffect, useRef } from "react";
import {
  IconSparkles,
  IconSend,
  IconCheckCircle,
  IconAlertTriangle,
  IconFileText,
  IconBrain,
  IconShield
} from "../components/Icons";

const STARTER_PROMPTS = [
  "What is the total amount or financial value mentioned?",
  "Who are the primary parties, organizations, or individuals involved?",
  "What are the critical dates, terms, or deadlines specified?",
  "Provide a concise summary of the key findings in this document."
];

export default function AskView({
  documents = [],
  selectedDocId,
  setSelectedDocId,
  token,
  qaHistory = [],
  isLoadingHistory = false,
  isAsking = false,
  qaAnswer = null,
  qaError = "",
  onAskQuestion,
  onOpenAuth,
  onNavigate
}) {
  const [question, setQuestion] = useState("");
  const messagesEndRef = useRef(null);

  // Auto-scroll when history or answer changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [qaHistory, qaAnswer, isAsking]);

  const activeDoc = documents.find((d) => String(d.id) === String(selectedDocId));

  // Check if latest answer is already represented in qaHistory to prevent duplicate rendering
  const isAnswerInHistory = Boolean(
    qaAnswer &&
    qaHistory.some(
      (item) =>
        item.question?.trim().toLowerCase() === qaAnswer.question?.trim().toLowerCase() &&
        item.answer?.trim() === qaAnswer.answer?.trim()
    )
  );

  function handleSubmit(e) {
    e?.preventDefault();
    if (isAsking) return;
    if (!token) {
      onOpenAuth("login");
      return;
    }
    if (!selectedDocId) return;
    const trimmed = question.trim();
    if (!trimmed) return;

    onAskQuestion(selectedDocId, trimmed);
    setQuestion("");
  }

  function handlePromptClick(prompt) {
    if (!selectedDocId || isAsking) return;
    onAskQuestion(selectedDocId, prompt);
  }

  return (
    <div className="view-content-wrapper ask-view">
      {/* Top Document Selector Bar */}
      <div className="qa-doc-selector-bar">
        <div className="selector-left">
          <label htmlFor="qa-document-select" className="selector-label">
            <IconFileText size={16} />
            <span>Target Document:</span>
          </label>

          <div className="select-wrapper">
            <select
              id="qa-document-select"
              value={selectedDocId || ""}
              onChange={(e) => setSelectedDocId(e.target.value)}
              disabled={documents.length === 0}
            >
              {documents.length === 0 ? (
                <option value="">No documents available</option>
              ) : (
                <>
                  <option value="" disabled>Select a document to query...</option>
                  {documents.map((doc) => (
                    <option key={doc.id} value={doc.id}>
                      {doc.filename} ({doc.document_type || "Doc"} • #{doc.id})
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>
        </div>

        {activeDoc && (
          <div className="selector-right">
            <span className="active-doc-type-pill">{activeDoc.document_type || "Document"}</span>
            <span className={`active-doc-status-pill status-${activeDoc.status || "processed"}`}>
              {activeDoc.status || "Processed"}
            </span>
          </div>
        )}
      </div>

      {/* Main Q&A Chat Surface */}
      <div className="qa-workspace-container">
        {!token ? (
          <div className="qa-empty-state">
            <div className="qa-empty-orb">
              <IconShield size={36} />
            </div>
            <h3>Authentication Required for Document Q&A</h3>
            <p>Sign in to query enterprise documents with grounded citations and multi-tenant isolation.</p>
            <button
              type="button"
              className="btn-hero-primary"
              onClick={() => onOpenAuth("login")}
            >
              Sign In to Continue
            </button>
          </div>
        ) : documents.length === 0 ? (
          <div className="qa-empty-state">
            <div className="qa-empty-orb">
              <IconFileText size={36} />
            </div>
            <h3>No Documents Found</h3>
            <p>You need to upload at least one document before you can query it with AI.</p>
            <button
              type="button"
              className="btn-hero-primary"
              onClick={() => onNavigate("upload")}
            >
              Upload a Document
            </button>
          </div>
        ) : !selectedDocId ? (
          <div className="qa-empty-state">
            <div className="qa-empty-orb">
              <IconBrain size={36} />
            </div>
            <h3>Select a Document to Start</h3>
            <p>Choose any processed document from the dropdown above to begin grounded Q&A.</p>
          </div>
        ) : (
          <div className="qa-chat-stream">
            {/* Document Header in Chat */}
            <div className="qa-stream-header">
              <div className="stream-badge">
                <IconSparkles size={14} />
                <span>Grounded Citations Active</span>
              </div>
              <h4>Querying &ldquo;{activeDoc?.filename}&rdquo;</h4>
              <p>Every response is verified against the document's extracted text to eliminate hallucinations.</p>
            </div>

            {/* Conversation History */}
            {isLoadingHistory ? (
              <div className="qa-history-loading">
                <span className="spinner-dot" />
                <span>Loading conversation history...</span>
              </div>
            ) : (
              <>
                {qaHistory.length === 0 && !qaAnswer && (
                  <div className="qa-starter-prompts-container">
                    <span className="starter-label">Suggested Inquiries:</span>
                    <div className="starter-chips-grid">
                      {STARTER_PROMPTS.map((prompt, i) => (
                        <button
                          key={i}
                          type="button"
                          className="starter-chip-btn"
                          onClick={() => handlePromptClick(prompt)}
                          disabled={isAsking}
                        >
                          <IconSparkles size={13} />
                          <span>{prompt}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {qaHistory.map((item) => (
                  <div className="qa-turn-container" key={item.id}>
                    {/* User Question */}
                    <div className="qa-user-bubble-row">
                      <div className="user-avatar-tag">You</div>
                      <div className="user-question-content">
                        <p>{item.question}</p>
                      </div>
                    </div>

                    {/* AI Answer */}
                    <div className="qa-ai-bubble-row">
                      <div className="ai-avatar-tag">
                        <IconSparkles size={16} />
                      </div>
                      <div className="ai-answer-content">
                        <div className="ai-bubble-top">
                          <span className="ai-tag-name">DocuAI Grounded Response</span>
                        </div>
                        <p className="ai-answer-text">{item.answer}</p>

                        {/* Citations */}
                        {Array.isArray(item.citations) && item.citations.length > 0 && (
                          <div className="citations-wrapper">
                            <span className="citations-header">Supporting Citations:</span>
                            <div className="citations-list">
                              {item.citations.map((cite, cIdx) => (
                                <div className="citation-pill-card" key={cIdx}>
                                  <p className="citation-quote-text">&ldquo;{cite.quote}&rdquo;</p>
                                  <div className="citation-badges-row">
                                    {cite.page_number && (
                                      <span className="citation-page-badge">
                                        Page {cite.page_number}
                                      </span>
                                    )}
                                    <span className="citation-match-badge">
                                      {Math.round((cite.confidence || 0) * 100)}% Match
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Latest Question/Answer Turn (only displayed if not already merged in history) */}
                {qaAnswer && !isAnswerInHistory && String(qaAnswer.document_id) === String(selectedDocId) && (
                  <div className="qa-turn-container new-turn">
                    <div className="qa-user-bubble-row">
                      <div className="user-avatar-tag">You</div>
                      <div className="user-question-content">
                        <p>{qaAnswer.question}</p>
                      </div>
                    </div>

                    <div className="qa-ai-bubble-row">
                      <div className="ai-avatar-tag">
                        <IconSparkles size={16} />
                      </div>
                      <div className="ai-answer-content">
                        <div className="ai-bubble-top">
                          <span className="ai-tag-name">DocuAI Grounded Response</span>
                          <span
                            className={`evidence-status-pill ${
                              qaAnswer.has_sufficient_evidence ? "supported" : "insufficient"
                            }`}
                          >
                            {qaAnswer.has_sufficient_evidence ? (
                              <>
                                <IconCheckCircle size={13} />
                                <span>Evidence Grounded</span>
                              </>
                            ) : (
                              <>
                                <IconAlertTriangle size={13} />
                                <span>Insufficient Evidence</span>
                              </>
                            )}
                          </span>
                        </div>

                        <p className="ai-answer-text">{qaAnswer.answer}</p>

                        {Array.isArray(qaAnswer.citations) && qaAnswer.citations.length > 0 && (
                          <div className="citations-wrapper">
                            <span className="citations-header">Supporting Citations:</span>
                            <div className="citations-list">
                              {qaAnswer.citations.map((cite, cIdx) => (
                                <div className="citation-pill-card" key={cIdx}>
                                  <p className="citation-quote-text">&ldquo;{cite.quote}&rdquo;</p>
                                  <div className="citation-badges-row">
                                    {cite.page_number && (
                                      <span className="citation-page-badge">
                                        Page {cite.page_number}
                                      </span>
                                    )}
                                    <span className="citation-match-badge">
                                      {Math.round((cite.confidence || 0) * 100)}% Match
                                    </span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Generating Answer Loading State */}
                {isAsking && (
                  <div className="qa-ai-bubble-row loading-turn">
                    <div className="ai-avatar-tag pulse-anim">
                      <IconSparkles size={16} />
                    </div>
                    <div className="ai-answer-content">
                      <div className="thinking-row">
                        <span className="agent-radar-dot" />
                        <span>Verifying extracted context and generating grounded answer...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </>
            )}
          </div>
        )}

        {/* Error Banner */}
        {qaError && (
          <div className="qa-error-alert" role="alert">
            <IconAlertTriangle size={18} />
            <span>{qaError}</span>
          </div>
        )}

        {/* Input Bar */}
        {selectedDocId && token && (
          <form className="qa-input-bar" onSubmit={handleSubmit}>
            <input
              type="text"
              className="qa-input-field"
              placeholder={`Ask a question about "${activeDoc?.filename || "this document"}"...`}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={isAsking}
            />

            <button
              type="submit"
              className="qa-send-btn"
              disabled={isAsking || !question.trim()}
              title="Submit question"
            >
              <IconSend size={16} />
              <span>Ask Document</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
