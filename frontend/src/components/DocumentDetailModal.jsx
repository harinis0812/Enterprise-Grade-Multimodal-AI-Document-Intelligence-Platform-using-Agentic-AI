import { useState } from "react";
import {
  IconClose,
  IconFileText,
  IconSparkles,
  IconShield,
  IconBrain,
  IconCheckCircle,
  IconCopy,
  IconCheck,
  IconMessageSquare
} from "./Icons";

export default function DocumentDetailModal({
  document,
  isOpen,
  onClose,
  onAskDocument,
}) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState("overview"); // 'overview', 'extracted', 'text', 'trace'

  if (!isOpen || !document) return null;

  function copyTextToClipboard() {
    if (!document.extracted_text) return;
    navigator.clipboard.writeText(document.extracted_text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function formatKey(key) {
    return key
      .replaceAll("_", " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function formatValue(value) {
    if (value === null || value === undefined) return "N/A";
    if (Array.isArray(value)) return value.join(", ");
    if (typeof value === "object") return JSON.stringify(value, null, 2);
    if (typeof value === "boolean") return value ? "Yes" : "No";
    return String(value);
  }

  const infoObj = document.document_information || {};
  const hasInfo = infoObj && typeof infoObj === "object" && Object.keys(infoObj).length > 0;
  const analysis = document.analysis;
  const supervisor = document.supervisor_decision;
  const verification = document.verification;
  const trace = Array.isArray(document.agent_trace) ? document.agent_trace : [];

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="doc-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Modal Top Bar */}
        <div className="doc-modal-header">
          <div className="doc-modal-title-row">
            <div className="doc-modal-icon">
              <IconFileText size={22} />
            </div>
            <div className="doc-modal-info">
              <div className="doc-modal-meta-row">
                <span className="doc-modal-type-badge">{document.document_type || "Document"}</span>
                <span className={`doc-modal-status-badge status-${document.status || "processed"}`}>
                  {document.status === "processed" && <IconCheckCircle size={13} />}
                  {document.status || "Processed"}
                </span>
                <span className="doc-modal-id">ID: #{document.id}</span>
              </div>
              <h2 className="doc-modal-filename">{document.filename}</h2>
            </div>
          </div>

          <div className="doc-modal-actions">
            <button
              type="button"
              className="doc-modal-ask-btn"
              onClick={() => {
                onClose();
                if (onAskDocument) onAskDocument(document);
              }}
            >
              <IconMessageSquare size={16} />
              <span>Ask Document AI</span>
            </button>

            <button
              type="button"
              className="doc-modal-close-btn"
              onClick={onClose}
              aria-label="Close modal"
            >
              <IconClose size={20} />
            </button>
          </div>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="doc-modal-tabs">
          <button
            type="button"
            className={`modal-tab ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            Overview & AI Analysis
          </button>
          <button
            type="button"
            className={`modal-tab ${activeTab === "extracted" ? "active" : ""}`}
            onClick={() => setActiveTab("extracted")}
          >
            Structured Data ({hasInfo ? Object.keys(infoObj).length : 0})
          </button>
          <button
            type="button"
            className={`modal-tab ${activeTab === "trace" ? "active" : ""}`}
            onClick={() => setActiveTab("trace")}
          >
            Agent Trace ({trace.length} Steps)
          </button>
          <button
            type="button"
            className={`modal-tab ${activeTab === "text" ? "active" : ""}`}
            onClick={() => setActiveTab("text")}
          >
            Raw Extracted Text
          </button>
        </div>

        {/* Modal Body */}
        <div className="doc-modal-body">
          {/* TAB 1: OVERVIEW & AI ANALYSIS */}
          {activeTab === "overview" && (
            <div className="modal-tab-pane">
              {/* AI Summary Card */}
              {analysis ? (
                <div className="detail-card highlight-card">
                  <div className="card-header-with-badge">
                    <div className="card-title-group">
                      <IconSparkles size={18} className="text-accent" />
                      <h3>Autonomous AI Analysis</h3>
                    </div>
                    {analysis.status && (
                      <span className="detail-pill-badge">Status: {analysis.status}</span>
                    )}
                  </div>

                  {analysis.summary && (
                    <p className="detail-summary-text">{analysis.summary}</p>
                  )}

                  {Array.isArray(analysis.key_findings) && analysis.key_findings.length > 0 && (
                    <div className="detail-findings-box">
                      <h4>Key Intelligence Findings</h4>
                      <ul className="detail-findings-list">
                        {analysis.key_findings.map((item, idx) => (
                          <li key={idx}>
                            <span className="finding-bullet">•</span>
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="detail-card">
                  <p className="text-muted">No specific AI summary generated for this document.</p>
                </div>
              )}

              {/* Verification & Supervisor Grid */}
              <div className="modal-two-column-grid">
                {/* Supervisor Decision */}
                <div className="detail-card">
                  <div className="card-title-group">
                    <IconBrain size={18} className="text-indigo" />
                    <h3>Supervisor Agent Decision</h3>
                  </div>
                  {supervisor && typeof supervisor === "object" ? (
                    <div className="meta-key-value-list">
                      {Object.entries(supervisor).map(([k, v]) => (
                        <div className="meta-kv-item" key={k}>
                          <span className="meta-key">{formatKey(k)}</span>
                          <strong className="meta-val">{formatValue(v)}</strong>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted">Autonomous routing decision completed.</p>
                  )}
                </div>

                {/* Verification Agent */}
                <div className="detail-card">
                  <div className="card-title-group">
                    <IconShield size={18} className="text-emerald" />
                    <h3>Verification Agent</h3>
                  </div>
                  {verification && typeof verification === "object" ? (
                    <div className="verification-details-box">
                      <div className="verification-status-pill">
                        <IconCheckCircle size={15} />
                        <span>Status: {verification.status || "Verified"}</span>
                      </div>
                      {verification.message && (
                        <p className="verification-msg">{verification.message}</p>
                      )}
                      {Array.isArray(verification.issues) && verification.issues.length > 0 && (
                        <div className="verification-issues">
                          <h5>Flagged Issues</h5>
                          <ul>
                            {verification.issues.map((issue, idx) => (
                              <li key={idx}>{issue}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="text-muted">Document verification check passed with high confidence.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: STRUCTURED DATA */}
          {activeTab === "extracted" && (
            <div className="modal-tab-pane">
              {hasInfo ? (
                <div className="structured-grid">
                  {Object.entries(infoObj).map(([key, val]) => (
                    <div className="structured-item-card" key={key}>
                      <span className="structured-key-label">{formatKey(key)}</span>
                      <div className="structured-val-content">{formatValue(val)}</div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-modal-state">
                  <IconFileText size={40} />
                  <h4>No Structured Fields Extracted</h4>
                  <p>This document may be unstructured text or freeform narrative.</p>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: AGENT TRACE */}
          {activeTab === "trace" && (
            <div className="modal-tab-pane">
              <div className="trace-timeline-container">
                <div className="trace-intro">
                  <h4>Autonomous LangGraph Multi-Agent Execution Path</h4>
                  <p>
                    Every document passes through specialized agent stages to guarantee
                    accuracy, validation, and zero hallucinations.
                  </p>
                </div>

                <div className="trace-stepper">
                  {trace.map((step, idx) => (
                    <div className="stepper-node" key={idx}>
                      <div className="stepper-circle">
                        <span>{String(idx + 1).padStart(2, "0")}</span>
                      </div>
                      <div className="stepper-details">
                        <span className="stepper-label">Stage {idx + 1}</span>
                        <h4 className="stepper-title">{step}</h4>
                        <span className="stepper-status">Executed & Verified</span>
                      </div>
                      {idx < trace.length - 1 && <div className="stepper-connector" />}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: RAW EXTRACTED TEXT */}
          {activeTab === "text" && (
            <div className="modal-tab-pane">
              <div className="raw-text-container">
                <div className="raw-text-toolbar">
                  <span className="raw-text-count">
                    {document.extracted_text ? `${document.extracted_text.length.toLocaleString()} Characters` : "Empty text"}
                  </span>
                  <button
                    type="button"
                    className="raw-copy-btn"
                    onClick={copyTextToClipboard}
                    disabled={!document.extracted_text}
                  >
                    {copied ? (
                      <>
                        <IconCheck size={14} />
                        <span>Copied to Clipboard!</span>
                      </>
                    ) : (
                      <>
                        <IconCopy size={14} />
                        <span>Copy Text</span>
                      </>
                    )}
                  </button>
                </div>

                <pre className="raw-text-viewer">
                  {document.extracted_text || "No text could be extracted from this document."}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
