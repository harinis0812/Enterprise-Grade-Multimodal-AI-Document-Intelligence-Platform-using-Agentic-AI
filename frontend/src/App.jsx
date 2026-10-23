import { useEffect, useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8001";

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
];

const MAX_FILE_SIZE = 10 * 1024 * 1024;

function App() {
  const [selectedFile, setSelectedFile] = useState(null);

  const [uploadStatus, setUploadStatus] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  const [documentResult, setDocumentResult] = useState(null);
  const [documents, setDocuments] = useState([]);

  const [selectedDocument, setSelectedDocument] = useState(null);

  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [isLoadingDocument, setIsLoadingDocument] = useState(false);

  // Authentication state
  const [token, setToken] = useState(() => localStorage.getItem("docuai_token") || "");
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("docuai_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authFullName, setAuthFullName] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // Document Q&A state
  const [qaQuestion, setQaQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [qaAnswer, setQaAnswer] = useState(null);
  const [qaHistory, setQaHistory] = useState([]);
  const [isLoadingQAHistory, setIsLoadingQAHistory] = useState(false);
  const [qaError, setQaError] = useState("");

  useEffect(() => {
    if (token) {
      loadDocuments();
    } else {
      setDocuments([]);
    }
  }, [token]);

  function getAuthHeaders(hasBody = false) {
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    if (hasBody) {
      headers["Content-Type"] = "application/json";
    }
    return headers;
  }

  function handleLogout() {
    if (token) {
      fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders(false),
      }).catch(() => {});
    }
    localStorage.removeItem("docuai_token");
    localStorage.removeItem("docuai_user");
    setToken("");
    setUser(null);
    setDocuments([]);
    setDocumentResult(null);
    setSelectedDocument(null);
    setQaHistory([]);
    setQaAnswer(null);
  }

  async function handleAuthSubmit(e) {
    e?.preventDefault();
    setAuthLoading(true);
    setAuthError("");

    try {
      const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
      const payload = {
        email: authEmail.trim(),
        password: authPassword,
      };
      if (authMode === "register" && authFullName.trim()) {
        payload.full_name = authFullName.trim();
      }

      const response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await readResponse(response);

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed. Please verify your credentials.");
      }

      if (data.access_token) {
        localStorage.setItem("docuai_token", data.access_token);
        if (data.user) {
          localStorage.setItem("docuai_user", JSON.stringify(data.user));
          setUser(data.user);
        }
        setToken(data.access_token);
        setShowAuthModal(false);
        setAuthPassword("");
        setErrorMessage("");
      }
    } catch (err) {
      setAuthError(err.message || "Authentication error.");
    } finally {
      setAuthLoading(false);
    }
  }

  async function loadQAHistory(documentId) {
    if (!documentId || !token) {
      setQaHistory([]);
      return;
    }
    try {
      setIsLoadingQAHistory(true);
      const response = await fetch(`${API_URL}/documents/${documentId}/qa/history`, {
        headers: getAuthHeaders(false),
      });

      if (response.status === 401) {
        handleLogout();
        setShowAuthModal(true);
        return;
      }
      if (response.status === 403) {
        setQaHistory([]);
        return;
      }

      const data = await readResponse(response);
      if (response.ok && data.history) {
        setQaHistory(data.history);
      }
    } catch (err) {
      console.warn("Could not load Q&A history:", err);
    } finally {
      setIsLoadingQAHistory(false);
    }
  }

  async function handleAskQuestion(e, documentId) {
    e?.preventDefault();
    if (!token) {
      setShowAuthModal(true);
      setErrorMessage("Please sign in to query enterprise documents.");
      return;
    }
    if (!qaQuestion.trim()) {
      setQaError("Please enter a question.");
      return;
    }
    if (!documentId) {
      setQaError("No document selected.");
      return;
    }

    try {
      setIsAsking(true);
      setQaError("");
      setQaAnswer(null);

      const response = await fetch(`${API_URL}/documents/${documentId}/qa`, {
        method: "POST",
        headers: getAuthHeaders(true),
        body: JSON.stringify({ question: qaQuestion.trim() }),
      });

      if (response.status === 401) {
        handleLogout();
        setShowAuthModal(true);
        throw new Error("Session expired. Please sign in again.");
      }

      if (response.status === 403) {
        throw new Error("Access denied: You do not have permission to query this document.");
      }

      const data = await readResponse(response);

      if (!response.ok) {
        throw new Error(data.detail || "Unable to retrieve question answer.");
      }

      setQaAnswer(data);
      setQaQuestion("");
      await loadQAHistory(documentId);
    } catch (err) {
      setQaError(err.message || "An error occurred during document question answering.");
    } finally {
      setIsAsking(false);
    }
  }


  /*
   * Safely read a backend response.
   */
  async function readResponse(response) {
    const contentType =
      response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      return await response.json();
    }

    const text = await response.text();

    return {
      detail:
        text || "The backend returned an unexpected response.",
    };
  }

  /*
   * Parse the JSON stored by the backend in the
   * analysis database column.
   */
  function parseStoredAnalysis(data) {
    let parsedAnalysis = {};

    if (
      typeof data.analysis === "string" &&
      data.analysis.trim()
    ) {
      try {
        parsedAnalysis = JSON.parse(data.analysis);
      } catch (error) {
        console.error(
          "Unable to parse stored analysis:",
          error
        );
      }
    } else if (
      data.analysis &&
      typeof data.analysis === "object"
    ) {
      parsedAnalysis = data.analysis;
    }

    let parsedTrace = data.agent_trace;

    if (
      typeof parsedTrace === "string" &&
      parsedTrace.trim()
    ) {
      try {
        parsedTrace = JSON.parse(parsedTrace);
      } catch (error) {
        console.warn(
          "Unable to parse agent trace:",
          error
        );
      }
    }

    return {
      ...data,

      document_information:
        data.document_information ||
        parsedAnalysis.document_information ||
        {},

      analysis:
        parsedAnalysis.analysis ||
        (
          data.analysis &&
          typeof data.analysis === "object"
            ? data.analysis
            : null
        ),

      verification:
        data.verification ||
        parsedAnalysis.verification ||
        {},

      supervisor_decision:
        data.supervisor_decision ||
        parsedAnalysis.supervisor_decision ||
        null,

      agent_trace: parsedTrace || [],
    };
  }

  /*
   * Fetch complete document details.
   */
  async function fetchDocumentDetails(documentId) {
    const response = await fetch(
      `${API_URL}/documents/${documentId}`,
      {
        headers: getAuthHeaders(false),
      }
    );

    if (response.status === 401) {
      handleLogout();
      setShowAuthModal(true);
      throw new Error("Authentication required. Please sign in.");
    }

    if (response.status === 403) {
      throw new Error("Access denied: You do not have permission to view this document.");
    }

    const data = await readResponse(response);

    if (!response.ok) {
      throw new Error(
        data.detail || "Unable to load document details."
      );
    }

    return parseStoredAnalysis(data);
  }

  /*
   * Load previously processed documents.
   */
  async function loadDocuments() {
    if (!token) {
      setDocuments([]);
      return;
    }

    try {
      setIsLoadingDocuments(true);
      setErrorMessage("");

      const response = await fetch(
        `${API_URL}/documents`,
        {
          headers: getAuthHeaders(false),
        }
      );

      if (response.status === 401) {
        handleLogout();
        setShowAuthModal(true);
        return;
      }

      const data = await readResponse(response);

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "Unable to load document history."
        );
      }

      if (Array.isArray(data)) {
        setDocuments(data);
      } else if (Array.isArray(data.documents)) {
        setDocuments(data.documents);
      } else {
        setDocuments([]);
      }
    } catch (error) {
      console.error("History error:", error);

      setDocuments([]);

      setErrorMessage(
        error.message || `Unable to connect to the backend at ${API_URL}.`
      );
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  /*
   * Validate selected file.
   */
  function validateFile(file) {
    if (!file) {
      return "Please select a document first.";
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      return (
        "Unsupported file type. Please upload " +
        "PDF, JPG, JPEG or PNG."
      );
    }

    if (file.size > MAX_FILE_SIZE) {
      return (
        "File is too large. Maximum allowed size is 10 MB."
      );
    }

    return "";
  }

  /*
   * File selection.
   */
  function handleFileChange(event) {
    const file = event.target.files?.[0];

    if (!file) {
      return;
    }

    const validationError = validateFile(file);

    if (validationError) {
      setSelectedFile(null);
      setUploadStatus("");
      setErrorMessage(validationError);
      return;
    }

    setSelectedFile(file);
    setUploadStatus("");
    setErrorMessage("");
    setDocumentResult(null);
    setSelectedDocument(null);
  }

  /*
   * Upload and process document.
   *
   * Important:
   * /upload returns a summary response.
   * We then request /documents/{id} to retrieve
   * the complete extracted information.
   */
  async function handleUpload() {
    if (!token) {
      setErrorMessage("Please sign in or create an account to upload documents.");
      setShowAuthModal(true);
      return;
    }

    if (!selectedFile) {
      setUploadStatus(
        "Please select a document first."
      );
      return;
    }

    const validationError =
      validateFile(selectedFile);

    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    try {
      setIsProcessing(true);
      setUploadStatus(
        "Processing document through AI agents..."
      );
      setErrorMessage("");
      setDocumentResult(null);
      setSelectedDocument(null);
      setQaAnswer(null);
      setQaHistory([]);
      setQaError("");

      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(
        `${API_URL}/upload`,
        {
          method: "POST",
          headers: getAuthHeaders(false),
          body: formData,
        }
      );

      if (response.status === 401) {
        handleLogout();
        setShowAuthModal(true);
        throw new Error("Session expired. Please sign in again.");
      }

      const data = await readResponse(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Document upload failed."
        );
      }

      /*
       * Retrieve the complete processed document.
       */
      let completeDocument = data;

      if (data.id) {
        completeDocument =
          await fetchDocumentDetails(data.id);
        loadQAHistory(data.id);
      }

      setDocumentResult(completeDocument);

      setUploadStatus(
        "Document processed successfully."
      );

      setSelectedFile(null);

      await loadDocuments();

      /*
       * Scroll to the result section.
       */
      setTimeout(() => {
        const resultElement =
          document.getElementById(
            "current-result"
          );

        if (resultElement) {
          resultElement.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
      }, 150);

    } catch (error) {
      console.error("Upload error:", error);

      setUploadStatus("");

      if (
        error instanceof TypeError &&
        error.message
          .toLowerCase()
          .includes("fetch")
      ) {
        setErrorMessage(
          `Cannot connect to the backend at ${API_URL}.`
        );
      } else {
        setErrorMessage(
          error.message ||
            "Error processing document. Please try again."
        );
      }
    } finally {
      setIsProcessing(false);
    }
  }

  /*
   * View a previously processed document.
   */
  async function viewDocument(documentId) {
    try {
      setIsLoadingDocument(true);
      setErrorMessage("");
      setSelectedDocument(null);
      setQaAnswer(null);
      setQaHistory([]);
      setQaError("");

      const completeDocument =
        await fetchDocumentDetails(documentId);

      setSelectedDocument(completeDocument);
      loadQAHistory(documentId);

      setTimeout(() => {
        const element =
          document.getElementById(
            "selected-document"
          );

        if (element) {
          element.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }
      }, 150);

    } catch (error) {
      console.error(
        "Document error:",
        error
      );

      setErrorMessage(
        error.message ||
          "Unable to load document."
      );
    } finally {
      setIsLoadingDocument(false);
    }
  }

  /*
   * Convert object keys into readable labels.
   */
  function formatKey(key) {
    return key
      .replaceAll("_", " ")
      .replace(
        /\b\w/g,
        (character) =>
          character.toUpperCase()
      );
  }

  /*
   * Convert values into readable display text.
   */
  function formatValue(value) {
    if (
      value === null ||
      value === undefined
    ) {
      return "N/A";
    }

    if (Array.isArray(value)) {
      return value.join(", ");
    }

    if (
      typeof value === "object"
    ) {
      return JSON.stringify(
        value,
        null,
        2
      );
    }

    if (typeof value === "boolean") {
      return value ? "Yes" : "No";
    }

    return String(value);
  }

  /*
   * Render extracted information.
   */
  function renderInformation(
    information
  ) {
    if (
      !information ||
      typeof information !==
        "object" ||
      Object.keys(information)
        .length === 0
    ) {
      return (
        <div className="empty-result">
          <span className="empty-result-icon">
            --
          </span>
          <p>
            No structured information was
            returned for this document.
          </p>
        </div>
      );
    }

    return (
      <div className="information-grid">
        {Object.entries(
          information
        ).map(
          ([key, value]) => (
            <div
              className="information-item"
              key={key}
            >
              <span className="information-key">
                {formatKey(key)}
              </span>

              <span className="information-value">
                {formatValue(value)}
              </span>
            </div>
          )
        )}
      </div>
    );
  }

  /*
   * Render AI analysis.
   */
  function renderAnalysis(
    analysis
  ) {
    if (
      !analysis ||
      typeof analysis !== "object"
    ) {
      return null;
    }

    return (
      <div className="analysis-card">
        {analysis.summary && (
          <p className="analysis-summary">
            {analysis.summary}
          </p>
        )}

        {Array.isArray(
          analysis.key_findings
        ) &&
          analysis.key_findings.length >
            0 && (
            <div className="key-findings">
              <h4>
                Key Findings
              </h4>

              <ul>
                {analysis.key_findings.map(
                  (
                    finding,
                    index
                  ) => (
                    <li
                      key={index}
                    >
                      {finding}
                    </li>
                  )
                )}
              </ul>
            </div>
          )}

        {analysis.status && (
          <div className="analysis-status">
            <span>
              Analysis Status
            </span>

            <strong>
              {formatValue(
                analysis.status
              )}
            </strong>
          </div>
        )}
      </div>
    );
  }

  /*
   * Render verification.
   */
  function renderVerification(
    verification
  ) {
    if (
      !verification ||
      typeof verification !==
        "object" ||
      Object.keys(verification)
        .length === 0
    ) {
      return null;
    }

    return (
      <div className="verification-card">
        <div className="verification-status">
          {verification.status ||
            "Verified"}
        </div>

        {Array.isArray(
          verification.issues
        ) &&
          verification.issues.length >
            0 && (
            <div className="key-findings">
              <h4>
                Verification Issues
              </h4>

              <ul>
                {verification.issues.map(
                  (
                    issue,
                    index
                  ) => (
                    <li
                      key={index}
                    >
                      {issue}
                    </li>
                  )
                )}
              </ul>
            </div>
          )}

        {verification.message && (
          <p className="analysis-summary">
            {verification.message}
          </p>
        )}
      </div>
    );
  }

  /*
   * Render agent execution trace.
   */
  function renderAgentTrace(
    trace
  ) {
    if (
      !Array.isArray(trace) ||
      trace.length === 0
    ) {
      return null;
    }

    return (
      <div className="agent-trace">
        {trace.map(
          (agent, index) => (
            <div
              className="trace-step"
              key={`${agent}-${index}`}
            >
              <div className="trace-number">
                {String(
                  index + 1
                ).padStart(2, "0")}
              </div>

              <div className="trace-content">
                <span className="trace-label">
                  Agent
                </span>

                <strong>
                  {agent}
                </strong>
              </div>

              {index <
                trace.length - 1 && (
                <div className="trace-arrow">
                  →
                </div>
              )}
            </div>
          )
        )}
      </div>
    );
  }

  /*
   * Render Document Q&A Panel with citations and history.
   */
  function renderQAPanel(doc) {
    if (!doc || !doc.id) {
      return null;
    }

    return (
      <div className="qa-section" id={`qa-panel-${doc.id}`}>
        <div className="qa-header">
          <div className="qa-title-group">
            <span className="qa-icon-badge">Q&A</span>
            <div>
              <h3>Document Intelligence Q&A</h3>
              <p>
                Ask questions about &ldquo;{doc.filename}&rdquo; grounded in extracted content
              </p>
            </div>
          </div>
        </div>

        {/* Question form */}
        <form
          className="qa-form"
          onSubmit={(e) => handleAskQuestion(e, doc.id)}
        >
          <input
            type="text"
            className="qa-input"
            placeholder="Ask a question about this document (e.g. 'What is the total amount?')..."
            value={qaQuestion}
            onChange={(e) => setQaQuestion(e.target.value)}
            disabled={isAsking}
          />
          <button
            type="submit"
            className="qa-submit-btn"
            disabled={isAsking || !qaQuestion.trim()}
          >
            {isAsking ? "Analyzing..." : "Ask Document"}
          </button>
        </form>

        {qaError && (
          <div className="auth-error-banner" style={{ marginBottom: "16px" }}>
            {qaError}
          </div>
        )}

        {/* Latest Q&A Response */}
        {qaAnswer && qaAnswer.document_id === doc.id && (
          <div className="qa-result-box">
            <div className="qa-result-header">
              <span className="qa-question-display">
                Q: {qaAnswer.question}
              </span>
              <span
                className={`qa-evidence-pill ${
                  qaAnswer.has_sufficient_evidence
                    ? "supported"
                    : "insufficient"
                }`}
              >
                {qaAnswer.has_sufficient_evidence
                  ? "✓ Evidence Grounded"
                  : "⚠ Insufficient Evidence"}
              </span>
            </div>

            <p className="qa-answer-text">{qaAnswer.answer}</p>

            {/* Citations List */}
            {Array.isArray(qaAnswer.citations) &&
              qaAnswer.citations.length > 0 && (
                <div className="qa-citations-section">
                  <div className="qa-citations-heading">
                    Supporting Citations & Evidence
                  </div>
                  {qaAnswer.citations.map((cite, index) => (
                    <div className="qa-citation-card" key={index}>
                      <p className="qa-citation-quote">
                        &ldquo;{cite.quote}&rdquo;
                      </p>
                      <div className="qa-citation-meta">
                        {cite.page_number && (
                          <span className="qa-meta-chip page">
                            Page {cite.page_number}
                          </span>
                        )}
                        <span className="qa-meta-chip conf">
                          {Math.round((cite.confidence || 1.0) * 100)}% Match Confidence
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
          </div>
        )}

        {/* Q&A Conversation History */}
        {qaHistory.length > 0 && (
          <div className="qa-history-container" style={{ marginTop: "20px" }}>
            <h4
              style={{
                fontSize: "13px",
                color: "#94a3b8",
                marginBottom: "12px",
                textTransform: "uppercase",
                letterSpacing: "0.5px",
              }}
            >
              Conversation History ({qaHistory.length})
            </h4>

            {qaHistory.map((turn) => (
              <div className="qa-history-card" key={turn.id}>
                <div className="qa-history-q">
                  <span className="qa-history-badge-q">Q</span>
                  <strong>{turn.question}</strong>
                </div>

                <p className="qa-history-a">{turn.answer}</p>

                {Array.isArray(turn.citations) && turn.citations.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      gap: "8px",
                      marginTop: "8px",
                      paddingLeft: "24px",
                      flexWrap: "wrap",
                    }}
                  >
                    {turn.citations.map((c, i) => (
                      <span
                        key={i}
                        className="qa-meta-chip page"
                        style={{ fontSize: "10px" }}
                      >
                        {c.page_number ? `Page ${c.page_number}` : "Evidence cited"}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <main className="docuai-app">

      {/* TOP NAVIGATION & ENTERPRISE AUTH BAR */}
      <header className="top-nav">
        <div className="nav-brand">
          <span className="nav-logo-badge">DocuAI</span>
          <span className="nav-title">Enterprise Platform</span>
        </div>

        <div className="nav-auth">
          {token && user ? (
            <div className="user-profile-badge">
              <div className="user-avatar">
                {(user.full_name || user.email || "U")[0].toUpperCase()}
              </div>
              <span className="user-name">
                {user.full_name || user.email}
              </span>
              <button
                type="button"
                className="logout-nav-btn"
                onClick={handleLogout}
                title="Log out of DocuAI"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "10px" }}>
              <button
                type="button"
                className="auth-nav-btn secondary"
                onClick={() => {
                  setAuthMode("login");
                  setAuthError("");
                  setShowAuthModal(true);
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                className="auth-nav-btn primary"
                onClick={() => {
                  setAuthMode("register");
                  setAuthError("");
                  setShowAuthModal(true);
                }}
              >
                Create Account
              </button>
            </div>
          )}
        </div>
      </header>

      {/* AUTHENTICATION MODAL */}
      {showAuthModal && (
        <div className="auth-overlay" onClick={() => setShowAuthModal(false)}>
          <div className="auth-card" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="auth-close-btn"
              onClick={() => setShowAuthModal(false)}
            >
              ×
            </button>

            <div className="auth-header">
              <h2>{authMode === "login" ? "Enterprise Login" : "Create Account"}</h2>
              <p>
                {authMode === "login"
                  ? "Access your secured multimodal document intelligence repository"
                  : "Register a new enterprise user account to start analyzing documents"}
              </p>
            </div>

            <div className="auth-tabs">
              <button
                type="button"
                className={`auth-tab ${authMode === "login" ? "active" : ""}`}
                onClick={() => {
                  setAuthMode("login");
                  setAuthError("");
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-tab ${authMode === "register" ? "active" : ""}`}
                onClick={() => {
                  setAuthMode("register");
                  setAuthError("");
                }}
              >
                Register
              </button>
            </div>

            {authError && (
              <div className="auth-error-banner" style={{ marginBottom: "16px" }}>
                {authError}
              </div>
            )}

            <form className="auth-form" onSubmit={handleAuthSubmit}>
              {authMode === "register" && (
                <div className="auth-field">
                  <label htmlFor="auth-full-name">Full Name</label>
                  <input
                    id="auth-full-name"
                    type="text"
                    placeholder="Jane Doe"
                    value={authFullName}
                    onChange={(e) => setAuthFullName(e.target.value)}
                    required
                  />
                </div>
              )}

              <div className="auth-field">
                <label htmlFor="auth-email">Email Address</label>
                <input
                  id="auth-email"
                  type="email"
                  placeholder="employee@enterprise.com"
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  required
                />
              </div>

              <div className="auth-field">
                <label htmlFor="auth-password">Password</label>
                <input
                  id="auth-password"
                  type="password"
                  placeholder="•••••••• (min. 8 characters)"
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  required
                  minLength={8}
                />
              </div>

              <button
                type="submit"
                className="auth-submit-btn"
                disabled={authLoading}
              >
                {authLoading
                  ? "Authenticating..."
                  : authMode === "login"
                  ? "Sign In"
                  : "Register Account"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* HERO */}

      <section className="hero">

        <div className="ai-icon">
          <div className="ai-core">
            <span>AI</span>
          </div>

          <div className="ai-ring ai-ring-one"></div>
          <div className="ai-ring ai-ring-two"></div>
        </div>

        <div className="hero-content">

          <div className="badge">
            <span className="pulse-dot"></span>
            AI DOCUMENT INTELLIGENCE
          </div>

          <h1>
            Docu<span>AI</span>
          </h1>

          <p className="subtitle">
            Enterprise Multimodal AI
            Document Intelligence Platform
          </p>

          <p className="description">
            Upload documents, extract information,
            classify content, and let autonomous
            AI agents transform unstructured data
            into intelligent insights.
          </p>

        </div>

      </section>


      {/* ERROR */}

      {errorMessage && (
        <section className="error-section">
          <div className="error-message">
            <span>!</span>
            {errorMessage}
          </div>
        </section>
      )}


      {/* UPLOAD */}

      <section className="upload-section">

        <div className="section-title">

          <div className="section-icon">
            UP
          </div>

          <div>
            <h2>
              Upload Document
            </h2>

            <p>
              Start your Agentic AI-powered
              document analysis
            </p>
          </div>

        </div>

        {!token && (
          <div className="auth-notice-card">
            <h3>Enterprise Authentication Required</h3>
            <p>
              Please sign in or create an account to upload documents, access your private document repository, and query documents with grounded AI citations.
            </p>
            <button
              type="button"
              className="auth-nav-btn primary"
              onClick={() => {
                setAuthMode("login");
                setAuthError("");
                setShowAuthModal(true);
              }}
            >
              Sign In to Get Started
            </button>
          </div>
        )}

        <div className="upload-card">

          <input
            id="document-file"
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            onChange={handleFileChange}
          />

          <label
            htmlFor="document-file"
            className="file-selector"
          >

            <div className="upload-animation">

              <div className="upload-glow"></div>

              <div className="document-icon">
                <div className="document-fold"></div>

                <div className="document-lines">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>

              <div className="processing-dot dot-one"></div>
              <div className="processing-dot dot-two"></div>
              <div className="processing-dot dot-three"></div>

            </div>


            {selectedFile ? (
              <>
                <h3 className="file-selected">
                  {selectedFile.name}
                </h3>

                <p>
                  File selected successfully
                </p>

                <span className="choose-file">
                  Change File
                </span>
              </>
            ) : (
              <>
                <h3>
                  Drop your document here
                </h3>

                <p>
                  PDF, JPG, JPEG or PNG
                </p>

                <span className="choose-file">
                  Choose File
                </span>
              </>
            )}

          </label>


          <button
            type="button"
            className="upload-button"
            onClick={handleUpload}
            disabled={
              !selectedFile ||
              isProcessing
            }
          >
            {isProcessing
              ? "Processing..."
              : "Process Document"}
          </button>

        </div>


        {uploadStatus && (
          <p className="upload-status">
            {uploadStatus}
          </p>
        )}

      </section>


      {/* CURRENT RESULT */}

      {documentResult && (
        <section
          className="result-section"
          id="current-result"
        >

          <div className="workflow-header">

            <div className="section-icon">
              AI
            </div>

            <div>
              <h2>
                AI Analysis Result
              </h2>

              <p>
                Autonomous document
                processing completed
              </p>
            </div>

          </div>


          <div className="result-card">

            <div className="result-header">
              <div>
                <span className="result-label">
                  PROCESSING COMPLETE
                </span>

                <h3>
                  {documentResult.filename ||
                    "Document"}
                </h3>
              </div>

              <span className="verified-badge">
                {documentResult.status ||
                  "Processed"}
              </span>
            </div>


            {/* BASIC INFORMATION */}

            <div className="result-grid">

              <div className="result-stat">
                <span>
                  Document Type
                </span>

                <strong>
                  {documentResult.document_type ||
                    "Unknown"}
                </strong>
              </div>

              <div className="result-stat">
                <span>
                  Processing Status
                </span>

                <strong>
                  {documentResult.status ||
                    "Processed"}
                </strong>
              </div>

              <div className="result-stat">
                <span>
                  Document ID
                </span>

                <strong>
                  {documentResult.id ||
                    "N/A"}
                </strong>
              </div>

            </div>


            {/* EXTRACTED INFORMATION */}

            <div className="result-information">

              <div className="result-heading">
                <span className="heading-number">
                  01
                </span>

                <div>
                  <h3>
                    Extracted Information
                  </h3>

                  <p>
                    Structured information
                    identified by the
                    processing agents
                  </p>
                </div>
              </div>

              {renderInformation(
                documentResult.document_information
              )}

            </div>


            {/* AI ANALYSIS */}

            {documentResult.analysis && (
              <div className="result-information">

                <div className="result-heading">
                  <span className="heading-number">
                    02
                  </span>

                  <div>
                    <h3>
                      AI Analysis
                    </h3>

                    <p>
                      Analysis generated
                      from the extracted
                      document content
                    </p>
                  </div>
                </div>

                {renderAnalysis(
                  documentResult.analysis
                )}

              </div>
            )}


            {/* SUPERVISOR */}

            {documentResult.supervisor_decision && (
              <div className="result-information">

                <div className="result-heading">
                  <span className="heading-number">
                    03
                  </span>

                  <div>
                    <h3>
                      Supervisor Agent
                    </h3>

                    <p>
                      Workflow decision
                      and routing
                    </p>
                  </div>
                </div>

                <div className="analysis-card">
                  {renderInformation(
                    documentResult.supervisor_decision
                  )}
                </div>

              </div>
            )}


            {/* VERIFICATION */}

            {documentResult.verification &&
              Object.keys(
                documentResult.verification
              ).length > 0 && (
                <div className="result-information">

                  <div className="result-heading">
                    <span className="heading-number">
                      04
                    </span>

                    <div>
                      <h3>
                        Verification
                      </h3>

                      <p>
                        Final validation
                        performed by the
                        verification agent
                      </p>
                    </div>
                  </div>

                  {renderVerification(
                    documentResult.verification
                  )}

                </div>
              )}


            {/* AGENT TRACE */}

            {documentResult.agent_trace &&
              documentResult.agent_trace.length >
                0 && (
                <div className="result-information">

                  <div className="result-heading">
                    <span className="heading-number">
                      05
                    </span>

                    <div>
                      <h3>
                        Agent Execution Trace
                      </h3>

                      <p>
                        Autonomous processing
                        workflow
                      </p>
                    </div>
                  </div>

                  {renderAgentTrace(
                    documentResult.agent_trace
                  )}

                </div>
              )}


            {/* EXTRACTED TEXT */}

            {documentResult.extracted_text && (
              <div className="result-information">

                <div className="result-heading">
                  <span className="heading-number">
                    06
                  </span>

                  <div>
                    <h3>
                      Extracted Text
                    </h3>

                    <p>
                      Raw text recovered
                      from the document
                    </p>
                  </div>
                </div>

                <div className="extracted-text">
                  {documentResult.extracted_text}
                </div>

              </div>
            )}

            {renderQAPanel(documentResult)}

          </div>

        </section>
      )}


      {/* DOCUMENT HISTORY */}

      <section className="workflow">

        <div className="workflow-header">

          <div className="section-icon">
            DB
          </div>

          <div>
            <h2>
              Document History
            </h2>

            <p>
              Previously processed enterprise
              documents
            </p>
          </div>

        </div>


        <div className="history-container">

          {!token ? (
            <div className="history-empty">
              <div className="empty-document-icon">
                AUTH
              </div>
              <h3>Sign in to view your documents</h3>
              <p>Your document repository is protected by multi-tenant enterprise encryption.</p>
              <button
                type="button"
                className="auth-nav-btn primary"
                style={{ marginTop: "12px" }}
                onClick={() => {
                  setAuthMode("login");
                  setAuthError("");
                  setShowAuthModal(true);
                }}
              >
                Sign In
              </button>
            </div>
          ) : isLoadingDocuments ? (
            <p className="upload-status">
              Loading document history...
            </p>
          ) : documents.length === 0 ? (

            <div className="history-empty">

              <div className="empty-document-icon">
                DOC
              </div>

              <h3>
                No documents yet
              </h3>

              <p>
                Process your first document
                to see it here.
              </p>

            </div>

          ) : (

            <div className="history-grid">

              {documents.map(
                (document) => (

                  <div
                    className="history-card"
                    key={document.id}
                  >

                    <div className="history-top">

                      <div className="history-file-icon">
                        DOC
                      </div>

                      <span className="history-status">
                        {document.status ||
                          "Processed"}
                      </span>

                    </div>


                    <h3>
                      {document.filename}
                    </h3>


                    <p>
                      {document.document_type ||
                        "Unknown Document"}
                    </p>


                    <button
                      type="button"
                      className="view-button"
                      onClick={() =>
                        viewDocument(
                          document.id
                        )
                      }
                      disabled={
                        isLoadingDocument
                      }
                    >
                      {isLoadingDocument
                        ? "Loading..."
                        : "View Document"}
                    </button>

                  </div>

                )
              )}

            </div>

          )}

        </div>

      </section>


      {/* SELECTED DOCUMENT */}

      {selectedDocument && (

        <section
          className="result-section"
          id="selected-document"
        >

          <div className="workflow-header">

            <div className="section-icon">
              DOC
            </div>

            <div>

              <h2>
                Document Details
              </h2>

              <p>
                Complete stored processing
                information
              </p>

            </div>

          </div>


          <div className="result-card">

            <div className="result-header">
              <div>
                <span className="result-label">
                  STORED DOCUMENT
                </span>

                <h3>
                  {selectedDocument.filename ||
                    "Document"}
                </h3>
              </div>

              <span className="verified-badge">
                {selectedDocument.status ||
                  "Processed"}
              </span>
            </div>


            <div className="result-grid">

              <div className="result-stat">
                <span>
                  Document Type
                </span>

                <strong>
                  {selectedDocument.document_type ||
                    "Unknown"}
                </strong>
              </div>

              <div className="result-stat">
                <span>
                  Status
                </span>

                <strong>
                  {selectedDocument.status ||
                    "N/A"}
                </strong>
              </div>

              <div className="result-stat">
                <span>
                  Document ID
                </span>

                <strong>
                  {selectedDocument.id ||
                    "N/A"}
                </strong>
              </div>

            </div>


            {/* STORED INFORMATION */}

            <div className="result-information">

              <div className="result-heading">
                <span className="heading-number">
                  01
                </span>

                <div>
                  <h3>
                    Extracted Information
                  </h3>

                  <p>
                    Structured information
                    stored for this document
                  </p>
                </div>
              </div>

              {renderInformation(
                selectedDocument.document_information
              )}

            </div>


            {/* STORED ANALYSIS */}

            {selectedDocument.analysis && (
              <div className="result-information">

                <div className="result-heading">
                  <span className="heading-number">
                    02
                  </span>

                  <div>
                    <h3>
                      AI Analysis
                    </h3>

                    <p>
                      Stored document analysis
                    </p>
                  </div>
                </div>

                {renderAnalysis(
                  selectedDocument.analysis
                )}

              </div>
            )}


            {/* VERIFICATION */}

            {selectedDocument.verification &&
              Object.keys(
                selectedDocument.verification
              ).length > 0 && (
                <div className="result-information">

                  <div className="result-heading">
                    <span className="heading-number">
                      03
                    </span>

                    <div>
                      <h3>
                        Verification
                      </h3>

                      <p>
                        Verification result
                      </p>
                    </div>
                  </div>

                  {renderVerification(
                    selectedDocument.verification
                  )}

                </div>
              )}


            {/* EXTRACTED TEXT */}

            <div className="result-information">

              <div className="result-heading">
                <span className="heading-number">
                  04
                </span>

                <div>
                  <h3>
                    Extracted Text
                  </h3>

                  <p>
                    Text recovered from the
                    stored document
                  </p>
                </div>
              </div>

              <div className="extracted-text">
                {selectedDocument.extracted_text ||
                  "No extracted text available."}
              </div>

            </div>


            {/* AGENT TRACE */}

            {selectedDocument.agent_trace &&
              selectedDocument.agent_trace.length >
                0 && (
                <div className="result-information">

                  <div className="result-heading">
                    <span className="heading-number">
                      05
                    </span>

                    <div>
                      <h3>
                        Agent Execution Trace
                      </h3>

                      <p>
                        Stored autonomous
                        workflow trace
                      </p>
                    </div>
                  </div>

                  {renderAgentTrace(
                    selectedDocument.agent_trace
                  )}

                </div>
              )}

            {renderQAPanel(selectedDocument)}

          </div>

        </section>
      )}


      {/* FEATURES */}

      <section className="features">

        <div className="feature-card">

          <div className="feature-icon purple">
            PDF
          </div>

          <h3>
            Multimodal Processing
          </h3>

          <p>
            Process PDFs, scanned documents
            and images using document
            extraction and OCR.
          </p>

        </div>


        <div className="feature-card">

          <div className="feature-icon cyan">
            AI
          </div>

          <h3>
            Agentic AI
          </h3>

          <p>
            Autonomous agents classify,
            extract, analyze, supervise
            and verify documents.
          </p>

        </div>


        <div className="feature-card">

          <div className="feature-icon purple">
            NLP
          </div>

          <h3>
            Information Extraction
          </h3>

          <p>
            Convert unstructured enterprise
            documents into structured
            information.
          </p>

        </div>

      </section>


      {/* WORKFLOW */}

      <section className="workflow">

        <div className="workflow-header">

          <div className="section-icon">
            FLOW
          </div>

          <div>

            <h2>
              How DocuAI Works
            </h2>

            <p>
              Intelligent Agentic AI document
              processing pipeline
            </p>

          </div>

        </div>


        <div className="workflow-steps">

          <div className="step">
            <div className="step-number">
              01
            </div>

            <span>
              Upload
            </span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">
              02
            </div>

            <span>
              Classify
            </span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">
              03
            </div>

            <span>
              Extract
            </span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">
              04
            </div>

            <span>
              Analyze
            </span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">
              05
            </div>

            <span>
              Supervise
            </span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">
              06
            </div>

            <span>
              Verify
            </span>
          </div>

        </div>

      </section>

    </main>
  );
}

export default App;