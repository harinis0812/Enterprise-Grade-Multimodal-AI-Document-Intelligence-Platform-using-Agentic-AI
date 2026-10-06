import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
];

const MAX_FILE_SIZE = 20 * 1024 * 1024;

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

  useEffect(() => {
    loadDocuments();
  }, []);

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
      `${API_URL}/documents/${documentId}`
    );

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
    try {
      setIsLoadingDocuments(true);
      setErrorMessage("");

      const response = await fetch(
        `${API_URL}/documents`
      );

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
        `Unable to connect to the backend at ${API_URL}.`
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
        "File is too large. Maximum allowed size is 20 MB."
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

      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(
        `${API_URL}/upload`,
        {
          method: "POST",
          body: formData,
        }
      );

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

      const completeDocument =
        await fetchDocumentDetails(documentId);

      setSelectedDocument(completeDocument);

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

  return (
    <main className="docuai-app">

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

          {isLoadingDocuments ? (
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