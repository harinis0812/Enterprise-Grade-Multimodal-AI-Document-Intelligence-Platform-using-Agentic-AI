import { useState, useMemo } from "react";
import {
  IconSearch,
  IconFileText,
  IconCheckCircle,
  IconMessageSquare,
  IconUpload,
  IconFilter,
  IconShield
} from "../components/Icons";

export default function HistoryView({
  documents = [],
  isLoading = false,
  token,
  onViewDocument,
  onAskDocument,
  onNavigate,
  onOpenAuth
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTypeFilter, setSelectedTypeFilter] = useState("all");
  const [selectedStatusFilter, setSelectedStatusFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest"); // 'newest', 'oldest', 'name'

  // Extract unique document types from available data
  const documentTypes = useMemo(() => {
    const types = new Set();
    documents.forEach((d) => {
      if (d.document_type) types.add(d.document_type);
    });
    return Array.from(types);
  }, [documents]);

  // Filtered and sorted documents
  const filteredDocuments = useMemo(() => {
    return documents
      .filter((doc) => {
        // Search query
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchName = doc.filename?.toLowerCase().includes(q);
          const matchType = doc.document_type?.toLowerCase().includes(q);
          if (!matchName && !matchType) return false;
        }

        // Type filter
        if (selectedTypeFilter !== "all" && doc.document_type !== selectedTypeFilter) {
          return false;
        }

        // Status filter
        if (selectedStatusFilter !== "all" && doc.status !== selectedStatusFilter) {
          return false;
        }

        return true;
      })
      .sort((a, b) => {
        if (sortBy === "newest") return (b.id || 0) - (a.id || 0);
        if (sortBy === "oldest") return (a.id || 0) - (b.id || 0);
        if (sortBy === "name") return (a.filename || "").localeCompare(b.filename || "");
        return 0;
      });
  }, [documents, searchQuery, selectedTypeFilter, selectedStatusFilter, sortBy]);

  return (
    <div className="view-content-wrapper history-view">
      {/* View Header */}
      <div className="view-section-header">
        <div>
          <h2>Document Repository & Intelligence History</h2>
          <p>
            Browse, search, and inspect your processed enterprise documents.
            Data is strictly isolated to your authenticated tenant session.
          </p>
        </div>

        {token && documents.length > 0 && (
          <button
            type="button"
            className="btn-header-cta"
            onClick={() => onNavigate("upload")}
          >
            <IconUpload size={16} />
            <span>Upload Document</span>
          </button>
        )}
      </div>

      {!token ? (
        <div className="history-empty-card">
          <div className="empty-icon-orb">
            <IconShield size={36} />
          </div>
          <h3>Enterprise Authentication Required</h3>
          <p>Sign in to view your multi-tenant document repository and intelligence history.</p>
          <button
            type="button"
            className="btn-hero-primary"
            onClick={() => onOpenAuth("login")}
          >
            Sign In to Access
          </button>
        </div>
      ) : isLoading ? (
        <div className="history-loading-grid">
          {[1, 2, 3, 4].map((n) => (
            <div className="skeleton-doc-card" key={n}>
              <div className="skeleton-line shimmer" style={{ width: "40%", height: "20px" }} />
              <div className="skeleton-line shimmer" style={{ width: "80%", height: "24px", margin: "12px 0" }} />
              <div className="skeleton-line shimmer" style={{ width: "60%", height: "16px" }} />
            </div>
          ))}
        </div>
      ) : documents.length === 0 ? (
        <div className="history-empty-card">
          <div className="empty-icon-orb">
            <IconFileText size={36} />
          </div>
          <h3>No Documents in Your Repository</h3>
          <p>You haven't uploaded any documents yet. Upload a PDF or image to begin analysis.</p>
          <button
            type="button"
            className="btn-hero-primary"
            onClick={() => onNavigate("upload")}
          >
            <IconUpload size={18} />
            <span>Upload First Document</span>
          </button>
        </div>
      ) : (
        <>
          {/* Controls Bar: Search, Filters, Sorting */}
          <div className="history-controls-card">
            {/* Search Input */}
            <div className="search-input-wrapper">
              <IconSearch size={18} className="search-icon" />
              <input
                type="text"
                placeholder="Search by filename or document category..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <button
                  type="button"
                  className="clear-search-btn"
                  onClick={() => setSearchQuery("")}
                >
                  Clear
                </button>
              )}
            </div>

            {/* Filter by Category */}
            <div className="filter-select-wrapper">
              <span className="filter-icon-tag"><IconFilter size={14} /></span>
              <select
                value={selectedTypeFilter}
                onChange={(e) => setSelectedTypeFilter(e.target.value)}
              >
                <option value="all">All Document Types ({documents.length})</option>
                {documentTypes.map((type) => (
                  <option key={type} value={type}>
                    {type} ({documents.filter((d) => d.document_type === type).length})
                  </option>
                ))}
              </select>
            </div>

            {/* Filter by Status */}
            <div className="filter-select-wrapper">
              <select
                value={selectedStatusFilter}
                onChange={(e) => setSelectedStatusFilter(e.target.value)}
              >
                <option value="all">All Statuses</option>
                <option value="processed">Processed</option>
                <option value="needs_review">Needs Review</option>
              </select>
            </div>

            {/* Sort by */}
            <div className="filter-select-wrapper">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
              >
                <option value="newest">Sort: Newest First</option>
                <option value="oldest">Sort: Oldest First</option>
                <option value="name">Sort: Filename (A–Z)</option>
              </select>
            </div>
          </div>

          {/* Results Count Bar */}
          <div className="results-count-bar">
            <span>
              Showing <strong>{filteredDocuments.length}</strong> of <strong>{documents.length}</strong> enterprise documents
            </span>
            {(searchQuery || selectedTypeFilter !== "all" || selectedStatusFilter !== "all") && (
              <button
                type="button"
                className="reset-filters-link"
                onClick={() => {
                  setSearchQuery("");
                  setSelectedTypeFilter("all");
                  setSelectedStatusFilter("all");
                }}
              >
                Reset all filters
              </button>
            )}
          </div>

          {/* Documents Table / Grid */}
          {filteredDocuments.length === 0 ? (
            <div className="no-matches-card">
              <IconSearch size={32} />
              <h4>No matching documents found</h4>
              <p>Try refining your search term or selecting a different document category.</p>
            </div>
          ) : (
            <div className="history-table-container">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Document Type</th>
                    <th>Status</th>
                    <th>Date / Record</th>
                    <th className="text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocuments.map((doc) => (
                    <tr key={doc.id} className="history-row">
                      <td className="doc-main-cell">
                        <div className="doc-cell-content">
                          <div className="doc-file-icon-badge">
                            <IconFileText size={18} />
                          </div>
                          <div>
                            <span className="doc-filename-link" onClick={() => onViewDocument(doc.id)}>
                              {doc.filename}
                            </span>
                            <span className="doc-id-subtext">ID: #{doc.id}</span>
                          </div>
                        </div>
                      </td>

                      <td>
                        <span className="doc-type-badge">{doc.document_type || "Unknown"}</span>
                      </td>

                      <td>
                        <span className={`status-pill pill-${doc.status || "processed"}`}>
                          {doc.status === "processed" && <IconCheckCircle size={12} />}
                          {doc.status || "Processed"}
                        </span>
                      </td>

                      <td className="doc-date-cell">
                        {doc.created_at
                          ? new Date(doc.created_at).toLocaleString()
                          : `Document #${doc.id}`}
                      </td>

                      <td className="doc-actions-cell text-right">
                        <div className="actions-button-group">
                          <button
                            type="button"
                            className="btn-action-inspect"
                            onClick={() => onViewDocument(doc.id)}
                            title="Inspect complete extracted intelligence"
                          >
                            Inspect
                          </button>
                          <button
                            type="button"
                            className="btn-action-qa"
                            onClick={() => onAskDocument(doc)}
                            title="Query this document with grounded Q&A"
                          >
                            <IconMessageSquare size={13} />
                            <span>Ask AI</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
