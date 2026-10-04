import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
];

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB

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
   * Safely read JSON from the backend.
   */
  async function readResponse(response) {
    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      return await response.json();
    }

    const text = await response.text();

    return {
      detail: text || "The backend returned an unexpected response.",
    };
  }

  /*
   * Load previously processed documents.
   */
  async function loadDocuments() {
    try {
      setIsLoadingDocuments(true);
      setErrorMessage("");

      const response = await fetch(`${API_URL}/documents`);

      const data = await readResponse(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to load document history."
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
        `Unable to connect to the backend. Make sure FastAPI is running at ${API_URL}.`
      );
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  /*
   * Validate the selected file.
   */
  function validateFile(file) {
    if (!file) {
      return "Please select a document first.";
    }

    if (!ALLOWED_TYPES.includes(file.type)) {
      return "Unsupported file type. Please upload PDF, JPG, JPEG or PNG.";
    }

    if (file.size > MAX_FILE_SIZE) {
      return "File is too large. Maximum allowed size is 20 MB.";
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
   * Upload and process the document.
   */
  async function handleUpload() {
    if (!selectedFile) {
      setUploadStatus("Please select a document first.");
      return;
    }

    const validationError = validateFile(selectedFile);

    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    try {
      setIsProcessing(true);
      setUploadStatus("Processing your document...");
      setErrorMessage("");
      setDocumentResult(null);
      setSelectedDocument(null);

      const formData = new FormData();

      formData.append("file", selectedFile);

      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await readResponse(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Document upload failed."
        );
      }

      /*
       * Store the complete processing result.
       */
      setDocumentResult(data);

      setUploadStatus(
        "Document processed successfully!"
      );

      setSelectedFile(null);

      /*
       * Refresh document history.
       */
      await loadDocuments();
    } catch (error) {
      console.error("Upload error:", error);

      setUploadStatus("");

      if (
        error instanceof TypeError &&
        error.message.toLowerCase().includes("fetch")
      ) {
        setErrorMessage(
          `Cannot connect to the backend at ${API_URL}. Start the FastAPI server first.`
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

      const response = await fetch(
        `${API_URL}/documents/${documentId}`
      );

      const data = await readResponse(response);

      if (!response.ok) {
        throw new Error(
          data.detail || "Unable to load document."
        );
      }

      setSelectedDocument(data);

      setTimeout(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: "smooth",
        });
      }, 100);
    } catch (error) {
      console.error("Document error:", error);

      setErrorMessage(
        error.message || "Unable to load document."
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
      .replace(/\b\w/g, (character) =>
        character.toUpperCase()
      );
  }

  /*
   * Convert any value into something displayable.
   */
  function formatValue(value) {
    if (value === null || value === undefined) {
      return "N/A";
    }

    if (Array.isArray(value)) {
      return value.join(", ");
    }

    if (typeof value === "object") {
      return JSON.stringify(value, null, 2);
    }

    return String(value);
  }

  /*
   * Render extracted information safely.
   */
  function renderInformation(information) {
    if (
      !information ||
      typeof information !== "object" ||
      Object.keys(information).length === 0
    ) {
      return (
        <p>
          No structured information was returned for this
          document.
        </p>
      );
    }

    return (
      <div className="information-grid">
        {Object.entries(information).map(
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

  return (
    <main className="docuai-app">

      {/* =====================================================
          HERO
      ====================================================== */}

      <section className="hero">

        <div className="ai-icon">
          <div className="icon-orbit orbit-one"></div>
          <div className="icon-orbit orbit-two"></div>

          <span>✦</span>
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
            Enterprise Multimodal AI Document Intelligence
            Platform
          </p>

          <p className="description">
            Upload documents, extract information, classify
            content, and let autonomous AI agents transform
            unstructured data into intelligent insights.
          </p>

        </div>

      </section>


      {/* =====================================================
          ERROR MESSAGE
      ====================================================== */}

      {errorMessage && (
        <section className="upload-section">

          <div className="upload-status">
            ⚠️ {errorMessage}
          </div>

        </section>
      )}


      {/* =====================================================
          UPLOAD
      ====================================================== */}

      <section className="upload-section">

        <div className="section-title">

          <div className="section-icon">
            ⬆
          </div>

          <div>
            <h2>Upload Document</h2>

            <p>
              Start your Agentic AI-powered document analysis
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

              <div className="upload-ring ring-one"></div>

              <div className="upload-ring ring-two"></div>

              <div className="file-icon">
                📄
              </div>

            </div>


            {selectedFile ? (
              <>
                <h3 className="file-selected">
                  {selectedFile.name}
                </h3>

                <p>
                  File selected successfully ✓
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
            disabled={!selectedFile || isProcessing}
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


      {/* =====================================================
          CURRENT RESULT
      ====================================================== */}

      {documentResult && (
        <section className="result-section">

          <div className="workflow-header">

            <div className="section-icon">
              ✦
            </div>

            <div>
              <h2>AI Analysis Result</h2>

              <p>
                Your document was successfully processed
              </p>
            </div>

          </div>


          <div className="result-card">

            {/* BASIC INFORMATION */}

            <div className="result-row">

              <span>
                📄 Filename
              </span>

              <strong>
                {documentResult.filename || "N/A"}
              </strong>

            </div>


            <div className="result-row">

              <span>
                🏷 Document Type
              </span>

              <strong>
                {documentResult.document_type || "Unknown"}
              </strong>

            </div>


            <div className="result-row">

              <span>
                📌 Processing Status
              </span>

              <strong>
                {documentResult.status || "Processed"}
              </strong>

            </div>


            {/* EXTRACTED INFORMATION */}

            <div className="result-information">

              <h3>
                ✨ Extracted Information
              </h3>

              {renderInformation(
                documentResult.document_information
              )}

            </div>


            {/* ANALYSIS */}

            {documentResult.analysis && (
              <div className="result-information">

                <h3>
                  🧠 AI Analysis
                </h3>

                {documentResult.analysis.summary && (
                  <p>
                    {documentResult.analysis.summary}
                  </p>
                )}


                {Array.isArray(
                  documentResult.analysis.key_findings
                ) &&
                  documentResult.analysis.key_findings.length >
                    0 && (
                    <>
                      <h4>
                        Key Findings
                      </h4>

                      <ul>
                        {documentResult.analysis.key_findings.map(
                          (finding, index) => (
                            <li key={index}>
                              {finding}
                            </li>
                          )
                        )}
                      </ul>
                    </>
                  )}

              </div>
            )}


            {/* SUPERVISOR */}

            {documentResult.supervisor_decision && (
              <div className="result-information">

                <h3>
                  🤖 Supervisor Agent
                </h3>

                {renderInformation(
                  documentResult.supervisor_decision
                )}

              </div>
            )}


            {/* VERIFICATION */}

            {documentResult.verification && (
              <div className="result-information">

                <h3>
                  ✅ Verification
                </h3>

                <p>
                  Status:{" "}
                  <strong>
                    {
                      documentResult.verification
                        .status
                    }
                  </strong>
                </p>


                {Array.isArray(
                  documentResult.verification.issues
                ) &&
                  documentResult.verification.issues
                    .length > 0 && (
                    <>
                      <h4>
                        Verification Issues
                      </h4>

                      <ul>
                        {documentResult.verification.issues.map(
                          (issue, index) => (
                            <li key={index}>
                              {issue}
                            </li>
                          )
                        )}
                      </ul>
                    </>
                  )}

              </div>
            )}


            {/* AGENT TRACE */}

            {Array.isArray(
              documentResult.agent_trace
            ) &&
              documentResult.agent_trace.length > 0 && (
                <div className="result-information">

                  <h3>
                    🔗 Agent Execution Trace
                  </h3>

                  <div className="information-grid">

                    {documentResult.agent_trace.map(
                      (agent, index) => (
                        <div
                          className="information-item"
                          key={`${agent}-${index}`}
                        >
                          <span className="information-key">
                            Step {index + 1}
                          </span>

                          <span className="information-value">
                            {agent}
                          </span>
                        </div>
                      )
                    )}

                  </div>

                </div>
              )}


            {/* EXTRACTED TEXT */}

            {documentResult.extracted_text && (
              <div className="result-information">

                <h3>
                  📃 Extracted Text
                </h3>

                <div className="extracted-text">
                  {documentResult.extracted_text}
                </div>

              </div>
            )}

          </div>

        </section>
      )}


      {/* =====================================================
          DOCUMENT HISTORY
      ====================================================== */}

      <section className="workflow">

        <div className="workflow-header">

          <div className="section-icon">
            📚
          </div>

          <div>

            <h2>
              Document History
            </h2>

            <p>
              Previously processed enterprise documents
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

              <div className="file-icon">
                📄
              </div>

              <h3>
                No documents yet
              </h3>

              <p>
                Process your first document to see it here.
              </p>

            </div>

          ) : (

            <div className="history-grid">

              {documents.map((document) => (

                <div
                  className="history-card"
                  key={document.id}
                >

                  <div className="history-top">

                    <div className="history-file-icon">
                      📄
                    </div>

                    <span className="history-status">
                      {document.status || "Processed"}
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
                      viewDocument(document.id)
                    }
                    disabled={isLoadingDocument}
                  >
                    {isLoadingDocument
                      ? "Loading..."
                      : "View Document"}
                  </button>

                </div>

              ))}

            </div>

          )}

        </div>

      </section>


      {/* =====================================================
          SELECTED DOCUMENT
      ====================================================== */}

      {selectedDocument && (

        <section className="result-section">

          <div className="workflow-header">

            <div className="section-icon">
              📑
            </div>

            <div>

              <h2>
                Document Details
              </h2>

              <p>
                Stored document information
              </p>

            </div>

          </div>


          <div className="result-card">

            <div className="result-row">

              <span>
                📄 Filename
              </span>

              <strong>
                {selectedDocument.filename || "N/A"}
              </strong>

            </div>


            <div className="result-row">

              <span>
                🏷 Document Type
              </span>

              <strong>
                {selectedDocument.document_type ||
                  "Unknown"}
              </strong>

            </div>


            <div className="result-row">

              <span>
                📌 Status
              </span>

              <strong>
                {selectedDocument.status || "N/A"}
              </strong>

            </div>


            {/* STORED INFORMATION */}

            <div className="result-information">

              <h3>
                ✨ Extracted Information
              </h3>

              {selectedDocument.document_information ? (
                renderInformation(
                  selectedDocument.document_information
                )
              ) : (
                <p>
                  Structured information is not stored in
                  the current document-history response.
                </p>
              )}

            </div>


            {/* STORED ANALYSIS */}

            {selectedDocument.analysis && (
              <div className="result-information">

                <h3>
                  🧠 AI Analysis
                </h3>

                {typeof selectedDocument.analysis ===
                "string" ? (
                  <p>
                    {selectedDocument.analysis}
                  </p>
                ) : (
                  <>
                    {selectedDocument.analysis.summary && (
                      <p>
                        {
                          selectedDocument.analysis
                            .summary
                        }
                      </p>
                    )}

                    {Array.isArray(
                      selectedDocument.analysis
                        .key_findings
                    ) && (
                      <ul>
                        {selectedDocument.analysis.key_findings.map(
                          (finding, index) => (
                            <li key={index}>
                              {finding}
                            </li>
                          )
                        )}
                      </ul>
                    )}
                  </>
                )}

              </div>
            )}


            {/* EXTRACTED TEXT */}

            <div className="result-information">

              <h3>
                📃 Extracted Text
              </h3>

              <div className="extracted-text">
                {selectedDocument.extracted_text ||
                  "No extracted text available."}
              </div>

            </div>


            {/* AGENT TRACE */}

            {selectedDocument.agent_trace && (
              <div className="result-information">

                <h3>
                  🔗 Agent Execution Trace
                </h3>

                <div className="extracted-text">
                  {Array.isArray(
                    selectedDocument.agent_trace
                  )
                    ? selectedDocument.agent_trace.join(
                        " → "
                      )
                    : selectedDocument.agent_trace}
                </div>

              </div>
            )}

          </div>

        </section>

      )}


      {/* =====================================================
          FEATURES
      ====================================================== */}

      <section className="features">

        <div className="feature-card">

          <div className="feature-icon purple">
            ◈
          </div>

          <h3>
            Multimodal Processing
          </h3>

          <p>
            Process PDFs, scanned documents and images.
          </p>

        </div>


        <div className="feature-card">

          <div className="feature-icon cyan">
            ✦
          </div>

          <h3>
            Agentic AI
          </h3>

          <p>
            Autonomous agents classify, analyze and verify
            documents.
          </p>

        </div>


        <div className="feature-card">

          <div className="feature-icon purple">
            ⌘
          </div>

          <h3>
            Information Extraction
          </h3>

          <p>
            Extract meaningful structured enterprise
            information.
          </p>

        </div>

      </section>


      {/* =====================================================
          WORKFLOW
      ====================================================== */}

      <section className="workflow">

        <div className="workflow-header">

          <div className="section-icon">
            ⌁
          </div>

          <div>

            <h2>
              How DocuAI Works
            </h2>

            <p>
              Your intelligent Agentic AI document processing
              pipeline
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