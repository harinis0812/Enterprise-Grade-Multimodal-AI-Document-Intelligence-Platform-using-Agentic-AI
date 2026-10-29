import {
  IconUpload,
  IconMessageSquare,
  IconFileText,
  IconCheckCircle,
  IconAlertTriangle,
  IconShield,
  IconSparkles,
  IconArrowRight,
  IconBrain
} from "../components/Icons";

export default function DashboardView({
  user,
  documents = [],
  health,
  onNavigate,
  onViewDocument,
  onAskDocument
}) {
  const totalDocs = documents.length;
  const processedDocs = documents.filter((d) => {
    const s = (d.status || "").toLowerCase();
    return s === "verified" || s === "processed";
  }).length;
  const reviewDocs = documents.filter((d) => {
    const s = (d.status || "").toLowerCase();
    return (
      s === "needs_review" ||
      s === "failed" ||
      s === "error" ||
      (s && s !== "verified" && s !== "processed")
    );
  }).length;
  const recentDocs = documents.slice(0, 5);

  const displayName = user?.full_name || (user?.email ? user.email.split("@")[0] : null);

  return (
    <div className="view-content-wrapper dashboard-view">
      {/* Welcome Banner */}
      <div className="dashboard-hero-banner">
        <div className="hero-banner-content">
          <div className="hero-badge">
            <span className="pulse-dot"></span>
            <span>ENTERPRISE AGENTIC AI INTELLIGENCE</span>
          </div>

          <h2 className="hero-greeting">
            {displayName ? `Welcome back, ${displayName}` : "Enterprise Multimodal Document Intelligence"}
          </h2>

          <p className="hero-subtitle">
            Autonomous multi-agent platform for high-accuracy document classification,
            OCR extraction, intelligent verification, and grounded citation Q&A.
          </p>

          <div className="hero-action-buttons">
            <button
              type="button"
              className="btn-hero-primary"
              onClick={() => onNavigate("upload")}
            >
              <IconUpload size={18} />
              <span>Upload New Document</span>
            </button>

            <button
              type="button"
              className="btn-hero-secondary"
              onClick={() => onNavigate("ask")}
            >
              <IconMessageSquare size={18} />
              <span>Ask Document AI</span>
            </button>
          </div>
        </div>

        <div className="hero-banner-graphic">
          <div className="ai-brain-orb">
            <IconBrain size={56} className="orb-icon" />
            <div className="orb-ring ring-1" />
            <div className="orb-ring ring-2" />
          </div>
        </div>
      </div>

      {/* Real Metric Summary Cards */}
      <div className="metrics-summary-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Total Documents</span>
            <div className="metric-icon-badge icon-indigo">
              <IconFileText size={18} />
            </div>
          </div>
          <div className="metric-value">{totalDocs}</div>
          <div className="metric-footnote">
            <span>Stored in secure tenant repository</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Successfully Processed</span>
            <div className="metric-icon-badge icon-emerald">
              <IconCheckCircle size={18} />
            </div>
          </div>
          <div className="metric-value">{processedDocs}</div>
          <div className="metric-footnote">
            <span>Verified by Autonomous Agents</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Pending / Review</span>
            <div className="metric-icon-badge icon-amber">
              <IconAlertTriangle size={18} />
            </div>
          </div>
          <div className="metric-value">{reviewDocs}</div>
          <div className="metric-footnote">
            <span>Low-contrast or unverified items</span>
          </div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Backend Architecture</span>
            <div className="metric-icon-badge icon-sky">
              <IconShield size={18} />
            </div>
          </div>
          <div className="metric-value status-text">
            {health?.status === "healthy" ? "Operational" : "Standby"}
          </div>
          <div className="metric-footnote">
            <span>Database: {health?.database || "Connected"}</span>
          </div>
        </div>
      </div>

      {/* Main Grid: Recent Documents & Agent Pipeline Quick Overview */}
      <div className="dashboard-sections-grid">
        {/* Left Column: Recent Documents */}
        <div className="dashboard-panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <IconFileText size={18} className="text-accent" />
              <h3>Recent Enterprise Documents</h3>
            </div>
            {totalDocs > 5 && (
              <button
                type="button"
                className="panel-link-btn"
                onClick={() => onNavigate("history")}
              >
                <span>View All ({totalDocs})</span>
                <IconArrowRight size={14} />
              </button>
            )}
          </div>

          <div className="panel-body">
            {recentDocs.length === 0 ? (
              <div className="empty-panel-state">
                <div className="empty-icon-circle">
                  <IconFileText size={32} />
                </div>
                <h4>No documents uploaded yet</h4>
                <p>Upload a PDF, JPG, or PNG document to begin autonomous AI extraction.</p>
                <button
                  type="button"
                  className="btn-panel-action"
                  onClick={() => onNavigate("upload")}
                >
                  <IconUpload size={16} />
                  <span>Upload Your First Document</span>
                </button>
              </div>
            ) : (
              <div className="recent-docs-list">
                {recentDocs.map((doc) => (
                  <div className="recent-doc-row" key={doc.id}>
                    <div className="doc-avatar-pill">
                      <IconFileText size={16} />
                    </div>

                    <div className="doc-info-col">
                      <h4 className="doc-name-text" title={doc.filename}>
                        {doc.filename}
                      </h4>
                      <div className="doc-submeta">
                        <span className="doc-type-chip">{doc.document_type || "Document"}</span>
                        <span className="doc-date-chip">
                          {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : `ID #${doc.id}`}
                        </span>
                      </div>
                    </div>

                    <div className="doc-status-col">
                      <span className={`status-pill pill-${(doc.status || "processed").toLowerCase().replace(/[^a-z0-9]/g, "-")}`}>
                        {(doc.status === "processed" || doc.status === "verified") && <IconCheckCircle size={12} />}
                        {doc.status || "Processed"}
                      </span>
                    </div>

                    <div className="doc-actions-col">
                      <button
                        type="button"
                        className="doc-row-btn"
                        onClick={() => onViewDocument(doc.id)}
                        title="View Complete Intelligence Details"
                      >
                        Inspect
                      </button>
                      <button
                        type="button"
                        className="doc-row-btn primary-tint"
                        onClick={() => onAskDocument(doc)}
                        title="Ask Questions with AI Citations"
                      >
                        <IconMessageSquare size={13} />
                        <span>Query</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Agentic Architecture & Quick Capabilities */}
        <div className="dashboard-panel">
          <div className="panel-header">
            <div className="panel-title-group">
              <IconSparkles size={18} className="text-violet" />
              <h3>Autonomous Multi-Agent Pipeline</h3>
            </div>
            <span className="panel-tag">LangGraph Workflow</span>
          </div>

          <div className="panel-body">
            <div className="pipeline-steps-card">
              <div className="pipeline-item">
                <div className="step-badge">01</div>
                <div className="step-content">
                  <h5>Document Intake & OCR</h5>
                  <p>PyMuPDF for digital documents; PaddleOCR for scanned imagery.</p>
                </div>
              </div>

              <div className="pipeline-item">
                <div className="step-badge">02</div>
                <div className="step-content">
                  <h5>Classification Agent</h5>
                  <p>Invoices, receipts, legal contracts, reports, and identity records.</p>
                </div>
              </div>

              <div className="pipeline-item">
                <div className="step-badge">03</div>
                <div className="step-content">
                  <h5>Information Extraction Agent</h5>
                  <p>Structured schema mapping and field-level key-value identification.</p>
                </div>
              </div>

              <div className="pipeline-item">
                <div className="step-badge">04</div>
                <div className="step-content">
                  <h5>Supervisor & Verification Agents</h5>
                  <p>Validates text coherence, audits extraction, and logs cryptographic traces.</p>
                </div>
              </div>
            </div>

            <div className="quick-help-card">
              <IconShield size={20} className="text-emerald" />
              <div>
                <h6>Multi-Tenant Data Isolation</h6>
                <p>Every document is encrypted and accessible only by its authenticated owner.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
