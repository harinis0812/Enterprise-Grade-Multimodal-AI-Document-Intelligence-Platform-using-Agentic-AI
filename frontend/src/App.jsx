import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import AuthModal from "./components/AuthModal";
import DocumentDetailModal from "./components/DocumentDetailModal";

import DashboardView from "./views/DashboardView";
import UploadView from "./views/UploadView";
import AskView from "./views/AskView";
import HistoryView from "./views/HistoryView";
import SecurityView from "./views/SecurityView";

import { api } from "./services/api";
import "./App.css";

export default function App() {
  // Navigation & View state
  const [activeTab, setActiveTab] = useState("dashboard"); // 'dashboard', 'upload', 'ask', 'history', 'security'
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState("login");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // Document repository & selection
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [uploadError, setUploadError] = useState("");
  const [lastUploadResult, setLastUploadResult] = useState(null);

  // Q&A state
  const [qaDocId, setQaDocId] = useState("");
  const [qaHistory, setQaHistory] = useState([]);
  const [isLoadingQAHistory, setIsLoadingQAHistory] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [qaAnswer, setQaAnswer] = useState(null);
  const [qaError, setQaError] = useState("");

  // Health state
  const [health, setHealth] = useState({
    status: "connecting",
    service: "DocuAI",
    database: "standby"
  });

  // Global Toast / Feedback Banner
  const [toastMessage, setToastMessage] = useState(null);

  function showToast(message, type = "success") {
    setToastMessage({ message, type });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  }

  // Check backend health periodically
  useEffect(() => {
    let mounted = true;
    async function checkHealth() {
      const h = await api.getHealth();
      if (mounted) setHealth(h);
    }
    checkHealth();
    const timer = setInterval(checkHealth, 30000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  // Logout handler
  const handleLogout = useCallback(() => {
    if (token) {
      api.logout(token).catch(() => {});
    }
    localStorage.removeItem("docuai_token");
    localStorage.removeItem("docuai_user");
    setToken("");
    setUser(null);
    setDocuments([]);
    setSelectedDocument(null);
    setQaHistory([]);
    setQaAnswer(null);
    setQaDocId("");
    showToast("You have been signed out successfully.", "info");
  }, [token]);

  // Load documents for current user on token change
  useEffect(() => {
    let ignore = false;
    async function fetchDocs() {
      if (!token) {
        setDocuments([]);
        return;
      }
      try {
        setIsLoadingDocuments(true);
        const docs = await api.getDocuments(token);
        if (!ignore) {
          setDocuments(docs);
          if (docs.length > 0 && !qaDocId) {
            setQaDocId(String(docs[0].id));
          }
        }
      } catch (err) {
        console.warn("Error fetching documents:", err);
        if (err.message?.includes("401") || err.message?.includes("Unauthorized")) {
          handleLogout();
        }
      } finally {
        if (!ignore) setIsLoadingDocuments(false);
      }
    }
    fetchDocs();
    return () => {
      ignore = true;
    };
  }, [token, qaDocId, handleLogout]);

  // Reload QA history whenever target document changes
  useEffect(() => {
    let ignore = false;
    async function fetchHistory() {
      if (!qaDocId || !token) {
        setQaHistory([]);
        return;
      }
      try {
        setIsLoadingQAHistory(true);
        const history = await api.getDocumentQAHistory(qaDocId, token);
        if (!ignore) setQaHistory(history);
      } catch (err) {
        console.warn("Error fetching QA history:", err);
        if (!ignore) setQaHistory([]);
      } finally {
        if (!ignore) setIsLoadingQAHistory(false);
      }
    }
    fetchHistory();
    return () => {
      ignore = true;
    };
  }, [qaDocId, token]);

  // Explicit reload helper after uploads
  async function refreshDocuments() {
    if (!token) return;
    try {
      const docs = await api.getDocuments(token);
      setDocuments(docs);
    } catch (err) {
      console.warn("Error reloading documents:", err);
    }
  }

  // Explicit reload helper after Q&A
  async function refreshQAHistory(docId) {
    if (!docId || !token) return;
    try {
      const history = await api.getDocumentQAHistory(docId, token);
      setQaHistory(history);
    } catch (err) {
      console.warn("Error reloading QA history:", err);
    }
  }

  // Auth Submit handler (Login or Register)
  async function handleAuthSubmit({ mode, email, password, fullName }) {
    setAuthLoading(true);
    setAuthError("");
    try {
      let data;
      if (mode === "login") {
        data = await api.login(email, password);
      } else {
        data = await api.register(email, password, fullName);
      }

      if (data.access_token) {
        localStorage.setItem("docuai_token", data.access_token);
        if (data.user) {
          localStorage.setItem("docuai_user", JSON.stringify(data.user));
          setUser(data.user);
        }
        setToken(data.access_token);
        setAuthModalOpen(false);
        showToast(
          mode === "login"
            ? `Welcome back, ${data.user?.full_name || email}!`
            : "Enterprise account registered successfully!",
          "success"
        );
      }
    } catch (err) {
      setAuthError(err.message || "Authentication failed.");
    } finally {
      setAuthLoading(false);
    }
  }

  // Open Document Detail modal
  async function handleViewDocument(docId) {
    try {
      const fullDoc = await api.getDocumentDetails(docId, token);
      setSelectedDocument(fullDoc);
      setIsDetailModalOpen(true);
    } catch (err) {
      showToast(err.message || "Failed to load document details.", "error");
    }
  }

  // Ask Question on Document
  async function handleAskQuestion(docId, questionText) {
    if (!token) {
      setAuthModalMode("login");
      setAuthModalOpen(true);
      return;
    }
    try {
      setIsAsking(true);
      setQaError("");
      setQaAnswer(null);

      const res = await api.askDocumentQuestion(docId, questionText, token);
      setQaAnswer(res);
      await refreshQAHistory(docId);
    } catch (err) {
      setQaError(err.message || "Failed to generate answer for this document.");
    } finally {
      setIsAsking(false);
    }
  }

  // Navigate to Q&A with document selected
  function handleNavigateToQA(doc) {
    if (doc?.id) {
      setQaDocId(String(doc.id));
    }
    setActiveTab("ask");
  }

  // Handle Document Upload
  async function handleUpload(file) {
    if (!token) {
      setAuthModalMode("login");
      setAuthModalOpen(true);
      return;
    }
    try {
      setIsUploading(true);
      setUploadError("");
      setUploadStatus("Ingesting document and executing autonomous agents...");

      const result = await api.uploadDocument(file, token);
      setLastUploadResult(result);
      setUploadStatus("Processing completed successfully.");
      showToast(`Document "${file.name}" processed successfully!`, "success");

      await refreshDocuments();
      if (result?.id) {
        setQaDocId(String(result.id));
      }
    } catch (err) {
      setUploadError(err.message || "Document processing failed.");
      setUploadStatus("");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <div className="docuai-enterprise-app">
      {/* Toast Alert */}
      {toastMessage && (
        <div className={`app-toast toast-${toastMessage.type}`} role="status">
          <span>{toastMessage.message}</span>
        </div>
      )}

      {/* Main Persistent Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        documentCount={documents.length}
        health={health}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        token={token}
      />

      {/* Main App Content Area */}
      <div className="app-main-layout">
        {/* Top Header */}
        <Header
          activeTab={activeTab}
          user={user}
          token={token}
          onOpenAuth={(mode) => {
            setAuthModalMode(mode);
            setAuthError("");
            setAuthModalOpen(true);
          }}
          onLogout={handleLogout}
          onOpenSidebar={() => setSidebarOpen(true)}
          setActiveTab={setActiveTab}
        />

        {/* View Switcher Container */}
        <main className="app-view-container">
          {activeTab === "dashboard" && (
            <DashboardView
              user={user}
              documents={documents}
              health={health}
              onNavigate={setActiveTab}
              onViewDocument={handleViewDocument}
              onAskDocument={handleNavigateToQA}
              onOpenAuth={(mode) => {
                setAuthModalMode(mode);
                setAuthError("");
                setAuthModalOpen(true);
              }}
            />
          )}

          {activeTab === "upload" && (
            <UploadView
              token={token}
              onUpload={handleUpload}
              isProcessing={isUploading}
              uploadStatus={uploadStatus}
              errorMessage={uploadError}
              lastResult={lastUploadResult}
              onViewDocument={handleViewDocument}
              onAskDocument={handleNavigateToQA}
              onOpenAuth={(mode) => {
                setAuthModalMode(mode);
                setAuthError("");
                setAuthModalOpen(true);
              }}
            />
          )}

          {activeTab === "ask" && (
            <AskView
              documents={documents}
              selectedDocId={qaDocId}
              setSelectedDocId={setQaDocId}
              token={token}
              qaHistory={qaHistory}
              isLoadingHistory={isLoadingQAHistory}
              isAsking={isAsking}
              qaAnswer={qaAnswer}
              qaError={qaError}
              onAskQuestion={handleAskQuestion}
              onOpenAuth={(mode) => {
                setAuthModalMode(mode);
                setAuthError("");
                setAuthModalOpen(true);
              }}
              onNavigate={setActiveTab}
            />
          )}

          {activeTab === "history" && (
            <HistoryView
              documents={documents}
              isLoading={isLoadingDocuments}
              token={token}
              onViewDocument={handleViewDocument}
              onAskDocument={handleNavigateToQA}
              onNavigate={setActiveTab}
              onOpenAuth={(mode) => {
                setAuthModalMode(mode);
                setAuthError("");
                setAuthModalOpen(true);
              }}
            />
          )}

          {activeTab === "security" && (
            <SecurityView
              token={token}
              user={user}
              onOpenAuth={(mode) => {
                setAuthModalMode(mode);
                setAuthError("");
                setAuthModalOpen(true);
              }}
            />
          )}
        </main>
      </div>

      {/* Deep Document Inspection Modal */}
      <DocumentDetailModal
        document={selectedDocument}
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        onAskDocument={handleNavigateToQA}
      />

      {/* Enterprise Authentication Modal */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        initialMode={authModalMode}
        onSubmit={handleAuthSubmit}
        loading={authLoading}
        error={authError}
      />
    </div>
  );
}