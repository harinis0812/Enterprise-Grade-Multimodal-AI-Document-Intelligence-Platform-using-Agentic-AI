import { useState, useEffect, useRef, useMemo } from "react";
import {
  IconSparkles,
  IconSend,
  IconCheckCircle,
  IconAlertTriangle,
  IconFileText,
  IconBrain,
  IconShield
} from "../components/Icons";
import { api } from "../services/api";

const STARTER_PROMPTS = [
  "Explain the core concepts and methodologies discussed in this document.",
  "What are the primary financial values, figures, or metrics specified?",
  "Who are the key executives, personnel, or organizations mentioned?",
  "Provide a structured overview of the document's key findings."
];

const MULTI_STARTER_PROMPTS = [
  "Compare financial figures and operational metrics across the selected reports.",
  "Synthesize key strategic objectives and executive decisions from these files.",
  "What common themes, discrepancies, or overlapping entities exist across documents?",
  "Provide an executive multi-document summary of findings and conclusions."
];

/**
 * Lightweight, safe React Markdown renderer.
 * Safely parses headings (###), bullet points (- ), bold (**), and inline code (`)
 * into native React elements without external dependencies or dangerouslySetInnerHTML.
 */
function renderInlineFormatting(text) {
  if (!text) return "";
  const regex = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  const tokens = text.split(regex);

  return tokens.map((token, i) => {
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={i}>{token.slice(2, -2)}</strong>;
    }
    if (token.startsWith("`") && token.endsWith("`")) {
      return (
        <code key={i} className="inline-code">
          {token.slice(1, -1)}
        </code>
      );
    }
    return token;
  });
}

function MarkdownContent({ content }) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements = [];
  let currentList = [];
  let currentTable = [];

  function flushList() {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`ul-${elements.length}`} className="markdown-ul">
          {currentList.map((item, i) => (
            <li key={i}>{renderInlineFormatting(item)}</li>
          ))}
        </ul>
      );
      currentList = [];
    }
  }

  function flushTable() {
    if (currentTable.length >= 2) {
      const headerRow = currentTable[0]
        .split("|")
        .slice(1, -1)
        .map((cell) => cell.trim());
      const dataRows = currentTable
        .slice(2)
        .map((row) =>
          row
            .split("|")
            .slice(1, -1)
            .map((cell) => cell.trim())
        );

      elements.push(
        <div key={`table-wrapper-${elements.length}`} className="markdown-table-wrapper">
          <table className="markdown-table">
            <thead>
              <tr>
                {headerRow.map((h, i) => (
                  <th key={i}>{renderInlineFormatting(h)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataRows.map((row, rIdx) => (
                <tr key={rIdx}>
                  {row.map((cell, cIdx) => (
                    <td key={cIdx}>{renderInlineFormatting(cell)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      currentTable = [];
    } else if (currentTable.length > 0) {
      currentTable.forEach((tblLine, idx) => {
        elements.push(
          <p key={`table-line-${elements.length}-${idx}`} className="markdown-p">
            {renderInlineFormatting(tblLine)}
          </p>
        );
      });
      currentTable = [];
    }
  }

  lines.forEach((line, index) => {
    const trimmed = line.trim();

    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      flushList();
      currentTable.push(trimmed);
      return;
    }

    flushTable();

    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      currentList.push(trimmed.slice(2));
      return;
    }

    flushList();

    if (!trimmed) {
      return;
    }

    if (trimmed.startsWith("### ")) {
      elements.push(
        <h4 key={index} className="markdown-h3">
          {renderInlineFormatting(trimmed.slice(4))}
        </h4>
      );
    } else if (trimmed.startsWith("## ")) {
      elements.push(
        <h3 key={index} className="markdown-h2">
          {renderInlineFormatting(trimmed.slice(3))}
        </h3>
      );
    } else if (trimmed.startsWith("# ")) {
      elements.push(
        <h2 key={index} className="markdown-h1">
          {renderInlineFormatting(trimmed.slice(2))}
        </h2>
      );
    } else if (trimmed.startsWith("> ")) {
      elements.push(
        <blockquote key={index} className="markdown-quote">
          {renderInlineFormatting(trimmed.slice(2))}
        </blockquote>
      );
    } else {
      elements.push(
        <p key={index} className="markdown-p">
          {renderInlineFormatting(trimmed)}
        </p>
      );
    }
  });

  flushList();
  flushTable();
  return <div className="markdown-body">{elements}</div>;
}

function CitationCard({ cite, index }) {
  const [expanded, setExpanded] = useState(false);
  const quote = cite.quote || "";
  const isLong = quote.length > 140;
  const displayedQuote = isLong && !expanded ? `${quote.slice(0, 140)}...` : quote;
  const relevance = Math.round((cite.relevance_score || cite.confidence || 0) * 100);
  const evType = (cite.evidence_type || "text").toLowerCase();

  const evLabels = {
    table: "Table Evidence",
    chart: "Chart / Diagram",
    ocr: "Scanned OCR",
    text: "Document Text"
  };

  const evIcons = {
    table: "📊",
    chart: "📈",
    ocr: "🔍",
    text: "📄"
  };

  return (
    <div className={`citation-pill-card evidence-${evType}`}>
      <p className="citation-quote-text">
        &ldquo;{displayedQuote}&rdquo;
        {isLong && (
          <button
            type="button"
            className="citation-expand-btn"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? "Show less" : "Show full"}
          </button>
        )}
      </p>
      <div className="citation-badges-row">
        {/* Source Document Badge (for multi-document synthesis & attributed retrieval) */}
        {(cite.filename || cite.document_id) && (
          <span className="citation-doc-badge" title={`Document #${cite.document_id || ""}`}>
            📄 {cite.filename || `Doc #${cite.document_id}`}
          </span>
        )}

        <span className={`citation-evidence-badge badge-${evType}`}>
          <span>{evIcons[evType] || "📄"}</span>
          <span>{evLabels[evType] || "Document Evidence"}</span>
        </span>
        {cite.page_number && (
          <span className="citation-page-badge">
            Page {cite.page_number}
          </span>
        )}
        <span
          className="citation-match-badge"
          title="Retrieval Relevance: indicates lexical and semantic overlap between the passage and the query."
        >
          {relevance}% Retrieval Relevance
        </span>
      </div>
    </div>
  );
}

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
  // Mode selection: "single" for targeted single-doc Q&A, "multi" for cross-document synthesis
  const [qaMode, setQaMode] = useState(() => {
    try {
      const searchParams = new URLSearchParams(window.location.search);
      const modeParam = searchParams.get("mode");
      if (modeParam === "multi" || modeParam === "single") {
        return modeParam;
      }
    } catch {
      // fallback
    }
    return "single";
  });

  function handleModeChange(newMode) {
    setQaMode(newMode);
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("mode", newMode);
      window.history.replaceState(null, "", url.toString());
    } catch {
      // fallback
    }
  }

  const [selectedMultiDocIds, setSelectedMultiDocIds] = useState(() =>
    documents.map((d) => d.id)
  );

  // Multi-document QA state
  const [multiQaHistory, setMultiQaHistory] = useState([]);
  const [isLoadingMultiHistory, setIsLoadingMultiHistory] = useState(false);
  const [isAskingMulti, setIsAskingMulti] = useState(false);
  const [multiQaAnswer, setMultiQaAnswer] = useState(null);
  const [multiQaError, setMultiQaError] = useState("");

  const [question, setQuestion] = useState("");
  const messagesEndRef = useRef(null);

  // Auto-select all documents for multi-doc mode when documents change
  useEffect(() => {
    if (documents.length > 0 && selectedMultiDocIds.length === 0) {
      setSelectedMultiDocIds(documents.map((d) => d.id));
    }
  }, [documents]);

  // Load multi-document history when entering multi mode
  useEffect(() => {
    if (qaMode !== "multi" || !token) return;
    let ignore = false;

    async function loadMultiHistory() {
      try {
        setIsLoadingMultiHistory(true);
        setMultiQaError("");
        const history = await api.getMultiDocumentQAHistory(token);
        if (!ignore) {
          setMultiQaHistory(history);
        }
      } catch (err) {
        if (!ignore) {
          setMultiQaError(err.message || "Failed to load multi-document history.");
        }
      } finally {
        if (!ignore) {
          setIsLoadingMultiHistory(false);
        }
      }
    }

    loadMultiHistory();
    return () => {
      ignore = true;
    };
  }, [qaMode, token]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [qaHistory, qaAnswer, isAsking, multiQaHistory, multiQaAnswer, isAskingMulti, qaMode]);

  const activeDoc = documents.find((d) => String(d.id) === String(selectedDocId));

  const multimodalMeta = useMemo(() => {
    if (!activeDoc || !activeDoc.analysis) return null;
    try {
      const parsed = typeof activeDoc.analysis === "string" ? JSON.parse(activeDoc.analysis) : activeDoc.analysis;
      return parsed?.multimodal_metadata || null;
    } catch {
      return null;
    }
  }, [activeDoc]);

  const isAnswerInHistory = Boolean(
    qaAnswer &&
    qaHistory.some(
      (item) =>
        item.question?.trim().toLowerCase() === qaAnswer.question?.trim().toLowerCase() &&
        item.answer?.trim() === qaAnswer.answer?.trim()
    )
  );

  const isMultiAnswerInHistory = Boolean(
    multiQaAnswer &&
    multiQaHistory.some(
      (item) =>
        item.question?.trim().toLowerCase() === multiQaAnswer.question?.trim().toLowerCase() &&
        item.answer?.trim() === multiQaAnswer.answer?.trim()
    )
  );

  function toggleMultiDoc(id) {
    setSelectedMultiDocIds((prev) => {
      if (prev.includes(id)) {
        return prev.filter((item) => item !== id);
      } else {
        return [...prev, id];
      }
    });
  }

  function handleSelectAll() {
    setSelectedMultiDocIds(documents.map((d) => d.id));
  }

  function handleClearAll() {
    setSelectedMultiDocIds([]);
  }

  function handleSingleSubmit(e) {
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

  async function handleMultiSubmit(e) {
    e?.preventDefault();
    if (isAskingMulti) return;
    if (!token) {
      onOpenAuth("login");
      return;
    }
    if (selectedMultiDocIds.length === 0) {
      setMultiQaError("Please select at least one document for multi-document synthesis.");
      return;
    }
    const trimmed = question.trim();
    if (!trimmed) return;

    try {
      setIsAskingMulti(true);
      setMultiQaError("");
      setMultiQaAnswer(null);

      const res = await api.askMultiDocumentQuestion(selectedMultiDocIds, trimmed, token);
      setMultiQaAnswer(res);

      // Refresh multi-document conversation history
      const refreshedHistory = await api.getMultiDocumentQAHistory(token);
      setMultiQaHistory(refreshedHistory);
      setQuestion("");
    } catch (err) {
      setMultiQaError(err.message || "Failed to synthesize answer across documents.");
    } finally {
      setIsAskingMulti(false);
    }
  }

  function handlePromptClick(prompt) {
    if (qaMode === "single") {
      if (!selectedDocId || isAsking) return;
      onAskQuestion(selectedDocId, prompt);
    } else {
      if (selectedMultiDocIds.length === 0 || isAskingMulti) return;
      setQuestion(prompt);
    }
  }

  return (
    <div className="view-content-wrapper ask-view">
      {/* Top Mode Selector Tabs */}
      <div className="qa-mode-tabs-container">
        <button
          type="button"
          data-testid="tab-single-mode"
          className={`qa-mode-tab-btn ${qaMode === "single" ? "active" : ""}`}
          onClick={() => handleModeChange("single")}
        >
          <IconFileText size={15} />
          <span>Single Document Q&A</span>
        </button>
        <button
          type="button"
          data-testid="tab-multi-mode"
          className={`qa-mode-tab-btn ${qaMode === "multi" ? "active" : ""}`}
          onClick={() => handleModeChange("multi")}
        >
          <IconBrain size={15} />
          <span>Multi-Document Synthesis</span>
          {documents.length > 1 && (
            <span className="qa-mode-count-badge">{documents.length} Docs Available</span>
          )}
        </button>
      </div>

      {/* Scope Selector: Single Target vs. Multi-Doc Checkboxes */}
      {qaMode === "single" ? (
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

          <div className="selector-right">
            {activeDoc && (
              <>
                <span className="active-doc-type-pill">{activeDoc.document_type || "Document"}</span>
                <span className={`active-doc-status-pill status-${activeDoc.status || "processed"}`}>
                  {activeDoc.status || "Processed"}
                </span>
                {multimodalMeta?.tables_detected > 0 && (
                  <span className="multimodal-stat-pill" title={`${multimodalMeta.tables_detected} tables detected`}>
                    📊 {multimodalMeta.tables_detected} {multimodalMeta.tables_detected === 1 ? "Table" : "Tables"}
                  </span>
                )}
                {multimodalMeta?.charts_detected > 0 && (
                  <span className="multimodal-stat-pill" title={`${multimodalMeta.charts_detected} visual diagrams detected`}>
                    📈 {multimodalMeta.charts_detected} {multimodalMeta.charts_detected === 1 ? "Chart" : "Charts"}
                  </span>
                )}
                {multimodalMeta?.ocr_pages?.length > 0 && (
                  <span className="multimodal-stat-pill" title={`OCR applied on page(s): ${multimodalMeta.ocr_pages.join(', ')}`}>
                    🔍 OCR Active
                  </span>
                )}
              </>
            )}
            <button
              type="button"
              className="mode-switch-inline-btn"
              onClick={() => handleModeChange("multi")}
              title="Switch to cross-document multi-synthesis mode"
            >
              <IconBrain size={14} />
              <span>Switch to Multi-Doc Mode &rarr;</span>
            </button>
          </div>
        </div>
      ) : (
        <div className="multi-doc-selector-bar">
          <div className="multi-doc-header-row">
            <div className="multi-doc-title-group">
              <IconBrain size={16} />
              <span>Multi-Document Synthesis Scope</span>
            </div>

            <div className="multi-doc-actions-group">
              <span className="active-doc-type-pill">
                {selectedMultiDocIds.length} of {documents.length} Selected
              </span>
              <button
                type="button"
                className="multi-doc-action-btn"
                onClick={handleSelectAll}
                disabled={documents.length === 0}
              >
                Select All
              </button>
              <button
                type="button"
                className="multi-doc-action-btn"
                onClick={handleClearAll}
                disabled={documents.length === 0}
              >
                Clear All
              </button>
              <button
                type="button"
                className="multi-doc-action-btn switch-single-btn"
                onClick={() => handleModeChange("single")}
                title="Switch back to single target document mode"
              >
                &larr; Single Document Mode
              </button>
            </div>
          </div>

          <div className="multi-doc-chips-grid">
            {documents.length === 0 ? (
              <span className="empty-hint-text">No documents uploaded yet.</span>
            ) : (
              documents.map((doc) => {
                const isChecked = selectedMultiDocIds.includes(doc.id);
                return (
                  <label
                    key={doc.id}
                    className={`multi-doc-chip ${isChecked ? "selected" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleMultiDoc(doc.id)}
                    />
                    <span>{doc.filename}</span>
                    <span className="chip-id-tag">#{doc.id}</span>
                  </label>
                );
              })
            )}
          </div>
        </div>
      )}

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
        ) : qaMode === "single" && !selectedDocId ? (
          <div className="qa-empty-state">
            <div className="qa-empty-orb">
              <IconFileText size={36} />
            </div>
            <h3>Select a Document to Start</h3>
            <p>Choose any processed document from the dropdown above to begin grounded single-document Q&A.</p>
          </div>
        ) : qaMode === "multi" && selectedMultiDocIds.length === 0 ? (
          <div className="qa-empty-state">
            <div className="qa-empty-orb">
              <IconBrain size={36} />
            </div>
            <h3>Select Documents for Synthesis</h3>
            <p>Check one or more documents above to synthesize cross-document information.</p>
          </div>
        ) : (
          <div className="qa-chat-stream">
            {/* Stream Header */}
            <div className="qa-stream-header">
              <div className="stream-badge">
                <IconSparkles size={14} />
                <span>
                  {qaMode === "single"
                    ? "Context-Aware Generative Q&A"
                    : "Cross-Document Agentic Synthesis"}
                </span>
              </div>
              <h4>
                {qaMode === "single"
                  ? `Querying "${activeDoc?.filename}"`
                  : `Synthesizing Across ${selectedMultiDocIds.length} Document${
                      selectedMultiDocIds.length === 1 ? "" : "s"
                    }`}
              </h4>
              <p>
                {qaMode === "single"
                  ? "Multi-passage grounded synthesis with verified page-level citations and hallucination prevention."
                  : "Cross-document passage retrieval with source document attribution, evidence grounding, and honest fallback."}
              </p>
            </div>

            {/* Conversation History: Single vs Multi */}
            {qaMode === "single" ? (
              /* ================= SINGLE DOCUMENT STREAM ================= */
              isLoadingHistory ? (
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
                      <div className="qa-user-bubble-row">
                        <div className="user-avatar-tag">You</div>
                        <div className="user-question-content">
                          <p>{item.question}</p>
                        </div>
                      </div>

                      <div className="qa-ai-bubble-row">
                        <div className="ai-avatar-tag">
                          <IconSparkles size={16} />
                        </div>
                        <div className="ai-answer-content">
                          <div className="ai-bubble-top">
                            <span className="ai-tag-name">DocuAI Grounded Response</span>
                          </div>

                          <MarkdownContent content={item.answer} />

                          {Array.isArray(item.citations) && item.citations.length > 0 && (
                            <div className="citations-wrapper">
                              <span className="citations-header">Supporting Passages & Citations:</span>
                              <div className="citations-list">
                                {item.citations.map((cite, cIdx) => (
                                  <CitationCard key={cIdx} cite={cite} index={cIdx} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Latest Question/Answer Turn */}
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

                            {qaAnswer.answer_mode === "generative" ? (
                              <span className="mode-badge generative-mode" title={`Model: ${qaAnswer.model_used || "Google Gemini"}`}>
                                <IconSparkles size={12} />
                                <span>Generative AI ({qaAnswer.model_used || "Gemini"})</span>
                              </span>
                            ) : (
                              <span className="mode-badge fallback-mode" title="Operating in extractive retrieval fallback mode.">
                                <IconFileText size={12} />
                                <span>Retrieval Fallback</span>
                              </span>
                            )}

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

                          <MarkdownContent content={qaAnswer.answer} />

                          {Array.isArray(qaAnswer.citations) && qaAnswer.citations.length > 0 && (
                            <div className="citations-wrapper">
                              <span className="citations-header">Supporting Passages & Citations:</span>
                              <div className="citations-list">
                                {qaAnswer.citations.map((cite, cIdx) => (
                                  <CitationCard key={cIdx} cite={cite} index={cIdx} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {isAsking && (
                    <div className="qa-ai-bubble-row loading-turn">
                      <div className="ai-avatar-tag pulse-anim">
                        <IconSparkles size={16} />
                      </div>
                      <div className="ai-answer-content">
                        <div className="thinking-row">
                          <span className="agent-radar-dot" />
                          <span>Retrieving multi-passage context and generating grounded answer...</span>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )
            ) : (
              /* ================= MULTI-DOCUMENT SYNTHESIS STREAM ================= */
              isLoadingMultiHistory ? (
                <div className="qa-history-loading">
                  <span className="spinner-dot" />
                  <span>Loading multi-document conversation history...</span>
                </div>
              ) : (
                <>
                  {multiQaHistory.length === 0 && !multiQaAnswer && (
                    <div className="qa-starter-prompts-container">
                      <span className="starter-label">Suggested Multi-Document Inquiries:</span>
                      <div className="starter-chips-grid">
                        {MULTI_STARTER_PROMPTS.map((prompt, i) => (
                          <button
                            key={i}
                            type="button"
                            className="starter-chip-btn"
                            onClick={() => handlePromptClick(prompt)}
                            disabled={isAskingMulti}
                          >
                            <IconBrain size={13} />
                            <span>{prompt}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {multiQaHistory.map((item) => (
                    <div className="qa-turn-container" key={item.id}>
                      <div className="qa-user-bubble-row">
                        <div className="user-avatar-tag">You</div>
                        <div className="user-question-content">
                          <p>{item.question}</p>
                        </div>
                      </div>

                      <div className="qa-ai-bubble-row">
                        <div className="ai-avatar-tag">
                          <IconBrain size={16} />
                        </div>
                        <div className="ai-answer-content">
                          <div className="ai-bubble-top">
                            <span className="ai-tag-name">DocuAI Multi-Document Synthesis</span>
                          </div>

                          {/* Documents Consulted Indicators */}
                          {Array.isArray(item.documents_consulted) && item.documents_consulted.length > 0 && (
                            <div className="documents-consulted-row">
                              <span className="consulted-label">Documents Consulted:</span>
                              <div className="consulted-pills-list">
                                {item.documents_consulted.map((docName, dIdx) => (
                                  <span key={dIdx} className="consulted-doc-pill">
                                    <IconFileText size={12} />
                                    <span>{docName}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          <MarkdownContent content={item.answer} />

                          {Array.isArray(item.citations) && item.citations.length > 0 && (
                            <div className="citations-wrapper">
                              <span className="citations-header">Cross-Document Supporting Citations:</span>
                              <div className="citations-list">
                                {item.citations.map((cite, cIdx) => (
                                  <CitationCard key={cIdx} cite={cite} index={cIdx} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  {/* Latest Multi-Document Turn */}
                  {multiQaAnswer && !isMultiAnswerInHistory && (
                    <div className="qa-turn-container new-turn">
                      <div className="qa-user-bubble-row">
                        <div className="user-avatar-tag">You</div>
                        <div className="user-question-content">
                          <p>{multiQaAnswer.question}</p>
                        </div>
                      </div>

                      <div className="qa-ai-bubble-row">
                        <div className="ai-avatar-tag">
                          <IconBrain size={16} />
                        </div>
                        <div className="ai-answer-content">
                          <div className="ai-bubble-top">
                            <span className="ai-tag-name">DocuAI Multi-Document Synthesis</span>

                            {multiQaAnswer.answer_mode === "generative" ? (
                              <span className="mode-badge generative-mode" title={`Model: ${multiQaAnswer.model_used || "Google Gemini"}`}>
                                <IconSparkles size={12} />
                                <span>Generative AI ({multiQaAnswer.model_used || "Gemini"})</span>
                              </span>
                            ) : (
                              <span className="mode-badge fallback-mode" title="Operating in extractive multi-document retrieval fallback mode.">
                                <IconFileText size={12} />
                                <span>Synthesis Fallback</span>
                              </span>
                            )}

                            <span
                              className={`evidence-status-pill ${
                                multiQaAnswer.has_sufficient_evidence ? "supported" : "insufficient"
                              }`}
                            >
                              {multiQaAnswer.has_sufficient_evidence ? (
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

                          {/* Documents Consulted Indicators */}
                          {Array.isArray(multiQaAnswer.documents_consulted) && multiQaAnswer.documents_consulted.length > 0 && (
                            <div className="documents-consulted-row">
                              <span className="consulted-label">Documents Consulted:</span>
                              <div className="consulted-pills-list">
                                {multiQaAnswer.documents_consulted.map((docName, dIdx) => (
                                  <span key={dIdx} className="consulted-doc-pill">
                                    <IconFileText size={12} />
                                    <span>{docName}</span>
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          <MarkdownContent content={multiQaAnswer.answer} />

                          {Array.isArray(multiQaAnswer.citations) && multiQaAnswer.citations.length > 0 && (
                            <div className="citations-wrapper">
                              <span className="citations-header">Cross-Document Supporting Citations:</span>
                              <div className="citations-list">
                                {multiQaAnswer.citations.map((cite, cIdx) => (
                                  <CitationCard key={cIdx} cite={cite} index={cIdx} />
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {isAskingMulti && (
                    <div className="qa-ai-bubble-row loading-turn">
                      <div className="ai-avatar-tag pulse-anim">
                        <IconBrain size={16} />
                      </div>
                      <div className="ai-answer-content">
                        <div className="thinking-row">
                          <span className="agent-radar-dot" />
                          <span>Retrieving cross-document evidence and synthesizing grounded multi-document response...</span>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              )
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* Error Banner */}
        {(qaMode === "single" ? qaError : multiQaError) && (
          <div className="qa-error-alert" role="alert">
            <IconAlertTriangle size={18} />
            <span>{qaMode === "single" ? qaError : multiQaError}</span>
          </div>
        )}

        {/* Input Bar */}
        {token && documents.length > 0 && (
          <form
            className="qa-input-bar"
            onSubmit={qaMode === "single" ? handleSingleSubmit : handleMultiSubmit}
          >
            <input
              type="text"
              className="qa-input-field"
              placeholder={
                qaMode === "single"
                  ? `Ask a question about "${activeDoc?.filename || "this document"}"...`
                  : `Ask a synthesized question across ${selectedMultiDocIds.length} selected documents...`
              }
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={qaMode === "single" ? isAsking : isAskingMulti}
            />

            <button
              type="submit"
              className="qa-send-btn"
              disabled={
                (qaMode === "single" ? isAsking || !selectedDocId : isAskingMulti || selectedMultiDocIds.length === 0) ||
                !question.trim()
              }
              title={qaMode === "single" ? "Submit question for this document" : "Submit cross-document synthesis query"}
            >
              <IconSend size={16} />
              <span>{qaMode === "single" ? "Ask Document" : "Synthesize All"}</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
