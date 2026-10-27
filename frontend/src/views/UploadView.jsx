import { useState, useRef } from "react";
import {
  IconUpload,
  IconFileText,
  IconCheckCircle,
  IconAlertTriangle,
  IconSparkles,
  IconMessageSquare,
  IconArrowRight,
  IconRefresh,
  IconBrain
} from "../components/Icons";

const ALLOWED_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export default function UploadView({
  token,
  onUpload,
  isProcessing,
  uploadStatus,
  errorMessage,
  lastResult,
  onViewDocument,
  onAskDocument,
  onOpenAuth
}) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState("");
  const fileInputRef = useRef(null);

  function validateFile(file) {
    if (!file) return "Please choose a file to upload.";
    const name = file.name.toLowerCase();
    const hasValidExt = ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
    if (!hasValidExt) {
      return "Unsupported file format. Please upload PDF, JPG, JPEG, or PNG.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return "File exceeds the 10 MB limit. Please select a smaller document.";
    }
    return "";
  }

  function handleFileSelected(file) {
    const error = validateFile(file);
    if (error) {
      setFileError(error);
      setSelectedFile(null);
      return;
    }
    setFileError("");
    setSelectedFile(file);
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  }

  function handleTriggerSubmit() {
    if (!token) {
      onOpenAuth("login");
      return;
    }
    if (!selectedFile) {
      setFileError("Please select a document first.");
      return;
    }
    onUpload(selectedFile);
  }

  return (
    <div className="view-content-wrapper upload-view">
      {/* View Header */}
      <div className="view-section-header">
        <div>
          <h2>Document Upload & Multimodal Ingestion</h2>
          <p>
            Upload business documents to trigger autonomous OCR, classification,
            information extraction, supervisor validation, and verification agents.
          </p>
        </div>
      </div>

      {/* Unauthenticated notice */}
      {!token && (
        <div className="auth-prompt-card">
          <div className="prompt-icon-bubble">
            <IconBrain size={24} />
          </div>
          <div className="prompt-text">
            <h4>Authentication Required</h4>
            <p>
              Please sign in or create an enterprise account to upload documents,
              access your isolated database repository, and query with grounded AI citations.
            </p>
          </div>
          <button
            type="button"
            className="btn-prompt-auth"
            onClick={() => onOpenAuth("login")}
          >
            Sign In to Upload
          </button>
        </div>
      )}

      {/* Main Upload Area */}
      <div className="upload-container-card">
        {/* Drag and Drop Zone */}
        <div
          className={`dropzone-box ${dragActive ? "drag-active" : ""} ${selectedFile ? "has-file" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.jpg,.jpeg,.png"
            style={{ display: "none" }}
            onChange={(e) => {
              if (e.target.files && e.target.files[0]) {
                handleFileSelected(e.target.files[0]);
              }
            }}
          />

          <div className="dropzone-inner">
            <div className={`dropzone-icon-orb ${isProcessing ? "pulse-anim" : ""}`}>
              <IconUpload size={32} />
            </div>

            {selectedFile ? (
              <div className="selected-file-details">
                <span className="file-ready-badge">Ready for Ingestion</span>
                <h4 className="file-name-title">{selectedFile.name}</h4>
                <p className="file-size-subtitle">
                  {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • {selectedFile.type || "Document"}
                </p>
                <button
                  type="button"
                  className="btn-change-file"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                >
                  Change Document
                </button>
              </div>
            ) : (
              <div className="dropzone-idle-details">
                <h4>Drag and drop your document here</h4>
                <p>Or click anywhere to browse your files from your computer</p>
                <div className="supported-formats-pills">
                  <span>PDF</span>
                  <span>JPG</span>
                  <span>JPEG</span>
                  <span>PNG</span>
                  <span className="pill-limit">Max 10 MB</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Validation or Error messages */}
        {(fileError || errorMessage) && (
          <div className="upload-error-alert" role="alert">
            <IconAlertTriangle size={18} />
            <span>{fileError || errorMessage}</span>
          </div>
        )}

        {/* Processing State with Agent Progression */}
        {isProcessing && (
          <div className="upload-processing-tracker">
            <div className="tracker-spinner-row">
              <span className="agent-radar-dot"></span>
              <h4>{uploadStatus || "Autonomous Multi-Agent Ingestion in progress..."}</h4>
            </div>

            <div className="agent-phases-row">
              <div className="phase-chip active">
                <span className="phase-num">1</span>
                <span>PyMuPDF / OCR</span>
              </div>
              <div className="phase-connector active" />
              <div className="phase-chip active">
                <span className="phase-num">2</span>
                <span>Classification</span>
              </div>
              <div className="phase-connector active" />
              <div className="phase-chip active">
                <span className="phase-num">3</span>
                <span>Extraction</span>
              </div>
              <div className="phase-connector active" />
              <div className="phase-chip active">
                <span className="phase-num">4</span>
                <span>Verification</span>
              </div>
            </div>
          </div>
        )}

        {/* Action Button */}
        <div className="upload-actions-bar">
          <button
            type="button"
            className="btn-submit-upload"
            onClick={handleTriggerSubmit}
            disabled={!selectedFile || isProcessing}
          >
            {isProcessing ? (
              <>
                <IconRefresh size={18} className="spin-icon" />
                <span>Processing Document with Agents...</span>
              </>
            ) : (
              <>
                <IconSparkles size={18} />
                <span>Process Document with Agentic AI</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Latest Upload Result Card */}
      {lastResult && (
        <div className="upload-result-container">
          <div className="result-success-banner">
            <div className="banner-left">
              <div className="success-badge-circle">
                <IconCheckCircle size={22} />
              </div>
              <div>
                <span className="result-label">PROCESSING SUCCEEDED</span>
                <h3>{lastResult.filename}</h3>
                <div className="result-chips-row">
                  <span className="doc-type-chip">{lastResult.document_type || "Document"}</span>
                  <span className="doc-status-chip">{lastResult.status || "Processed"}</span>
                  <span className="doc-id-chip">ID: #{lastResult.id}</span>
                </div>
              </div>
            </div>

            <div className="banner-actions">
              <button
                type="button"
                className="btn-result-action"
                onClick={() => onViewDocument(lastResult.id)}
              >
                <IconFileText size={16} />
                <span>Inspect Intelligence Details</span>
              </button>

              <button
                type="button"
                className="btn-result-action primary"
                onClick={() => onAskDocument(lastResult)}
              >
                <IconMessageSquare size={16} />
                <span>Ask Questions (AI Q&A)</span>
                <IconArrowRight size={14} />
              </button>
            </div>
          </div>

          {/* Quick Extracted Summary */}
          {lastResult.analysis?.summary && (
            <div className="result-quick-summary-card">
              <h4>Executive AI Summary</h4>
              <p>{lastResult.analysis.summary}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
