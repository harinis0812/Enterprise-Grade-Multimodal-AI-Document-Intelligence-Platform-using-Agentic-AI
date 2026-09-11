import { useState } from "react";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState("");
  const [documentResult, setDocumentResult] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  function handleFileChange(event) {
    const file = event.target.files[0];

    if (!file) return;

    setSelectedFile(file);
    setUploadStatus("");
    setDocumentResult(null);
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

      const response = await fetch(
        "http://127.0.0.1:8000/upload",
        {
          method: "POST",
          body: formData,
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || "Document upload failed"
        );
      }

      setDocumentResult(data);
      setUploadStatus(
        "Document processed successfully!"
      );
    } catch (error) {
      console.error(error);

      setUploadStatus(
        error.message ||
          "Error processing document."
      );
    } finally {
      setIsProcessing(false);
    }
  }

  return (
    <main className="docuai-app">

      {/* ================= HERO ================= */}

      <section className="hero">

        <div className="ai-icon">
          <div className="icon-orbit orbit-one"></div>
          <div className="icon-orbit orbit-two"></div>
          <span>✦</span>
        </div>

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

      </section>


      {/* ================= UPLOAD ================= */}

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


      {/* ================= FEATURES ================= */}

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


      {/* ================= RESULT ================= */}

      {documentResult && (

        <section className="result-section">

          <div className="workflow-header">

            <div className="section-icon">
              ✦
            </div>

            <div>
              <h2>
                AI Analysis Result
              </h2>

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


            {/* EXTRACTED INFORMATION */}

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
                      {key
                        .replaceAll("_", " ")
                        .replace(/\b\w/g, c =>
                          c.toUpperCase()
                        )}
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


            {/* AI ANALYSIS */}

            {documentResult.analysis && (

              <div className="ai-result-block">

                <h3>
                  🧠 AI Analysis
                </h3>

                <div className="analysis-card">

                  <p className="analysis-summary">
                    {documentResult.analysis.summary}
                  </p>

                  {documentResult.analysis.key_findings && (

                    <div className="key-findings">

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

                    </div>

                  )}

                </div>

              </div>

            )}


            {/* SUPERVISOR */}

            {documentResult.supervisor_decision && (

              <div className="ai-result-block">

                <h3>
                  🤖 Supervisor Agent
                </h3>

                <div className="supervisor-card">

                  <div className="result-row">

                    <span>
                      Next Agent
                    </span>

                    <strong>
                      {
                        documentResult
                          .supervisor_decision
                          .next_agent
                      }
                    </strong>

                  </div>


                  <div className="result-row">

                    <span>
                      Decision
                    </span>

                    <strong>
                      {
                        documentResult
                          .supervisor_decision
                          .reason
                      }
                    </strong>

                  </div>


                  <div className="result-row">

                    <span>
                      Verification Required
                    </span>

                    <strong>
                      {
                        documentResult
                          .supervisor_decision
                          .requires_verification
                          ? "Yes"
                          : "No"
                      }
                    </strong>

                  </div>

                </div>

              </div>

            )}


            {/* VERIFICATION */}

            {documentResult.verification && (

              <div className="ai-result-block">

                <h3>
                  ✅ Verification
                </h3>

                <div className="verification-card">

                  <div className="verification-status">

                    {documentResult.verification.status ===
                    "verified"
                      ? "✓ Document Verified"
                      : "⚠ Needs Review"}

                  </div>


                  <div className="verification-grid">

                    <div>
                      <span>
                        Document Type
                      </span>

                      <strong>
                        {
                          documentResult
                            .verification
                            .document_type_valid
                            ? "✓ Valid"
                            : "✗ Invalid"
                        }
                      </strong>
                    </div>


                    <div>
                      <span>
                        Information
                      </span>

                      <strong>
                        {
                          documentResult
                            .verification
                            .information_valid
                            ? "✓ Valid"
                            : "✗ Invalid"
                        }
                      </strong>
                    </div>


                    <div>
                      <span>
                        Analysis
                      </span>

                      <strong>
                        {
                          documentResult
                            .verification
                            .analysis_valid
                            ? "✓ Valid"
                            : "✗ Invalid"
                        }
                      </strong>
                    </div>

                  </div>

                </div>

              </div>

            )}


            {/* WORKFLOW STATUS */}

            <div className="ai-result-block">

              <h3>
                ⚙ Processing Status
              </h3>

              <div className="status-card">

                <span>
                  Workflow Status
                </span>

                <strong>
                  {documentResult.workflow_status ||
                    documentResult.status ||
                    "Completed"}
                </strong>

              </div>

            </div>


            {/* TEXT */}

            {documentResult.text && (

              <div className="ai-result-block">

                <h3>
                  📃 Extracted Text
                </h3>

                <div className="extracted-text">
                  {documentResult.text}
                </div>

              </div>

            )}

          </div>

        </section>

      )}


      {/* ================= WORKFLOW ================= */}

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