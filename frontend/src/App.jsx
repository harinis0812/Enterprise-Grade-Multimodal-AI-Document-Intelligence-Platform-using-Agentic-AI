import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [documentResult, setDocumentResult] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      setIsLoadingDocuments(true);

      const response = await fetch(`${API_URL}/documents`);

      if (!response.ok) {
        throw new Error("Unable to load document history");
      }

      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.error("History error:", error);
    } finally {
      setIsLoadingDocuments(false);
    }
  }

  function handleFileChange(event) {
    const file = event.target.files[0];

    if (!file) {
      return;
    }

    setSelectedFile(file);
    setUploadStatus("");
    setDocumentResult(null);
    setSelectedDocument(null);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setUploadStatus("Please select a document first.");
      return;
    }

    try {
      setIsProcessing(true);
      setUploadStatus("Processing your document...");
      setDocumentResult(null);

      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Document upload failed");
      }

      setDocumentResult(data);
      setUploadStatus("Document processed successfully!");
      setSelectedFile(null);

      await loadDocuments();
    } catch (error) {
      console.error("Upload error:", error);

      setUploadStatus(
        error.message ||
          "Error processing document. Please try again."
      );
    } finally {
      setIsProcessing(false);
    }
  }

  async function viewDocument(documentId) {
    try {
      const response = await fetch(
        `${API_URL}/documents/${documentId}`
      );

      if (!response.ok) {
        throw new Error("Unable to load document");
      }

      const data = await response.json();

      setSelectedDocument(data);

      window.scrollTo({
        top: document.body.scrollHeight,
        behavior: "smooth",
      });
    } catch (error) {
      console.error("Document error:", error);
    }
  }

  return (
    <main className="docuai-app">

      {/* HERO */}

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
            Enterprise Multimodal AI Document Intelligence Platform
          </p>

          <p className="description">
            Upload documents, extract information, classify content,
            and transform unstructured data into intelligent insights.
          </p>

        </div>

      </section>


      {/* UPLOAD */}

      <section className="upload-section">

        <div className="section-title">

          <div className="section-icon">
            ⬆
          </div>

          <div>
            <h2>Upload Document</h2>

            <p>
              Start your AI-powered document analysis
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


      {/* CURRENT RESULT */}

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

            <div className="result-row">

              <span>
                📄 Filename
              </span>

              <strong>
                {documentResult.filename}
              </strong>

            </div>


            <div className="result-row">

              <span>
                🏷 Document Type
              </span>

              <strong>
                {documentResult.document_type}
              </strong>

            </div>


            <div className="result-information">

              <h3>
                ✨ Extracted Information
              </h3>

              <div className="information-grid">

                {Object.entries(
                  documentResult.document_information || {}
                ).map(([key, value]) => (

                  <div
                    className="information-item"
                    key={key}
                  >

                    <span className="information-key">
                      {key.replaceAll("_", " ")}
                    </span>

                    <span className="information-value">

                      {Array.isArray(value)
                        ? value.join(", ")
                        : String(value)}

                    </span>

                  </div>

                ))}

              </div>

            </div>


            {/* ANALYSIS */}

            {documentResult.analysis && (
              <div className="result-information">

                <h3>
                  🧠 AI Analysis
                </h3>

                <p>
                  {documentResult.analysis.summary}
                </p>

                {documentResult.analysis.key_findings && (
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

                <div className="information-grid">

                  <div className="information-item">

                    <span className="information-key">
                      Next Agent
                    </span>

                    <span className="information-value">
                      {documentResult.supervisor_decision.next_agent}
                    </span>

                  </div>

                  <div className="information-item">

                    <span className="information-key">
                      Decision
                    </span>

                    <span className="information-value">
                      {documentResult.supervisor_decision.reason}
                    </span>

                  </div>

                </div>

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
                    {documentResult.verification.status}
                  </strong>
                </p>

              </div>
            )}

          </div>

        </section>
      )}


      {/* DOCUMENT HISTORY */}

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
                      ✓ Verified
                    </span>

                  </div>


                  <h3>
                    {document.filename}
                  </h3>


                  <p>
                    {document.document_type}
                  </p>


                  <button
                    type="button"
                    className="view-button"
                    onClick={() =>
                      viewDocument(document.id)
                    }
                  >
                    View Document
                  </button>

                </div>

              ))}

            </div>

          )}

        </div>

      </section>


      {/* SELECTED DOCUMENT */}

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
                {selectedDocument.filename}
              </strong>

            </div>


            <div className="result-row">

              <span>
                🏷 Document Type
              </span>

              <strong>
                {selectedDocument.document_type}
              </strong>

            </div>


            <div className="result-information">

              <h3>
                ✨ Extracted Information
              </h3>


              <div className="information-grid">

                {Object.entries(
                  selectedDocument.document_information || {}
                ).map(([key, value]) => (

                  <div
                    className="information-item"
                    key={key}
                  >

                    <span className="information-key">
                      {key.replaceAll("_", " ")}
                    </span>

                    <span className="information-value">

                      {Array.isArray(value)
                        ? value.join(", ")
                        : String(value)}

                    </span>

                  </div>

                ))}

              </div>

            </div>


            <div className="result-information">

              <h3>
                📃 Extracted Text
              </h3>

              <div className="extracted-text">
                {selectedDocument.extracted_text}
              </div>

            </div>

          </div>

        </section>

      )}


      {/* FEATURES */}

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
            Autonomous agents classify, analyze and verify documents.
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
            Extract meaningful structured enterprise information.
          </p>

        </div>

      </section>


      {/* WORKFLOW */}

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
              Your intelligent Agentic AI document processing pipeline
            </p>

          </div>

        </div>


        <div className="workflow-steps">

          <div className="step">
            <div className="step-number">01</div>
            <span>Upload</span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">02</div>
            <span>Extract</span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">03</div>
            <span>Classify</span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">04</div>
            <span>Analyze</span>
          </div>

          <div className="step-line"></div>

          <div className="step">
            <div className="step-number">05</div>
            <span>Verify</span>
          </div>

        </div>

      </section>

    </main>
  );
}

export default App;