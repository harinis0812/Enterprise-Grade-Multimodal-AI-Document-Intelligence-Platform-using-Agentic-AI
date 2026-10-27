import { useState, useEffect } from "react";
import {
  IconShield,
  IconCheckCircle,
  IconAlertTriangle,
  IconSearch,
  IconRefresh,
  IconFileText
} from "../components/Icons";
import { api } from "../services/api";

export default function SecurityView({
  token,
  onOpenAuth
}) {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [eventTypeFilter, setEventTypeFilter] = useState("all");

  async function loadAuditLogs() {
    if (!token) return;
    try {
      setLoading(true);
      setError("");
      const data = await api.getAuditLogs(token);
      setLogs(data);
    } catch (err) {
      setError(err.message || "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let ignore = false;
    async function fetchLogs() {
      if (!token) return;
      try {
        setLoading(true);
        setError("");
        const data = await api.getAuditLogs(token);
        if (!ignore) setLogs(data);
      } catch (err) {
        if (!ignore) setError(err.message || "Failed to load audit logs.");
      } finally {
        if (!ignore) setLoading(false);
      }
    }
    fetchLogs();
    return () => {
      ignore = true;
    };
  }, [token]);

  function getEventBadge(eventType) {
    if (eventType.includes("SUCCESS") || eventType.includes("ACCESS")) {
      return <span className="audit-pill pill-success">{eventType}</span>;
    }
    if (eventType.includes("DENIED") || eventType.includes("FAILED") || eventType.includes("INACTIVE")) {
      return <span className="audit-pill pill-danger">{eventType}</span>;
    }
    return <span className="audit-pill pill-info">{eventType}</span>;
  }

  const uniqueEventTypes = Array.from(new Set(logs.map((l) => l.event_type))).filter(Boolean);

  const filteredLogs = logs.filter((log) => {
    if (eventTypeFilter !== "all" && log.event_type !== eventTypeFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchType = log.event_type?.toLowerCase().includes(q);
      const matchDetails = log.details?.toLowerCase().includes(q);
      const matchIp = log.ip_address?.toLowerCase().includes(q);
      if (!matchType && !matchDetails && !matchIp) return false;
    }
    return true;
  });

  return (
    <div className="view-content-wrapper security-view">
      {/* View Header */}
      <div className="view-section-header">
        <div>
          <h2>Security Controls & Audit Activity</h2>
          <p>
            Real-time cryptographic audit trail of user sessions, document operations,
            and autonomous agent actions strictly isolated to your tenant.
          </p>
        </div>

        {token && (
          <button
            type="button"
            className="btn-header-cta secondary"
            onClick={loadAuditLogs}
            disabled={loading}
          >
            <IconRefresh size={16} className={loading ? "spin-icon" : ""} />
            <span>Refresh Audit Logs</span>
          </button>
        )}
      </div>

      {!token ? (
        <div className="history-empty-card">
          <div className="empty-icon-orb">
            <IconShield size={36} />
          </div>
          <h3>Enterprise Authentication Required</h3>
          <p>Please sign in to view your account's cryptographic security audit log.</p>
          <button
            type="button"
            className="btn-hero-primary"
            onClick={() => onOpenAuth("login")}
          >
            Sign In
          </button>
        </div>
      ) : (
        <>
          {/* Security Features Overview */}
          <div className="security-cards-grid">
            <div className="security-spec-card">
              <div className="spec-icon-box icon-emerald">
                <IconCheckCircle size={20} />
              </div>
              <h4>Multi-Tenant Document Isolation</h4>
              <p>Every SQL query strictly scopes documents and Q&A history to your user ID.</p>
            </div>

            <div className="security-spec-card">
              <div className="spec-icon-box icon-sky">
                <IconShield size={20} />
              </div>
              <h4>Zero Data Leakage Protection</h4>
              <p>Passwords are hashed via Argon2/Bcrypt; JWT access tokens expire automatically.</p>
            </div>

            <div className="security-spec-card">
              <div className="spec-icon-box icon-indigo">
                <IconFileText size={20} />
              </div>
              <h4>Immutable Audit Logging</h4>
              <p>Every login attempt, document upload, and AI query turn is recorded with IP trace.</p>
            </div>
          </div>

          {/* Audit Trail Section */}
          <div className="audit-table-card">
            <div className="audit-table-header">
              <div className="audit-title-group">
                <IconShield size={18} className="text-emerald" />
                <h3>Cryptographic Audit Trail ({logs.length} Total Events)</h3>
              </div>

              {/* Filters */}
              <div className="audit-filters-row">
                <div className="search-input-wrapper small">
                  <IconSearch size={14} className="search-icon" />
                  <input
                    type="text"
                    placeholder="Filter audit events..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>

                <div className="filter-select-wrapper small">
                  <select
                    value={eventTypeFilter}
                    onChange={(e) => setEventTypeFilter(e.target.value)}
                  >
                    <option value="all">All Events ({logs.length})</option>
                    {uniqueEventTypes.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {error && (
              <div className="upload-error-alert" role="alert">
                <IconAlertTriangle size={18} />
                <span>{error}</span>
              </div>
            )}

            {loading ? (
              <div className="qa-history-loading">
                <span className="spinner-dot" />
                <span>Fetching latest security audit records from database...</span>
              </div>
            ) : filteredLogs.length === 0 ? (
              <div className="no-matches-card">
                <IconShield size={32} />
                <h4>No Audit Records Found</h4>
                <p>No activity has matched your filter criteria yet.</p>
              </div>
            ) : (
              <div className="history-table-container">
                <table className="history-table audit-table">
                  <thead>
                    <tr>
                      <th>Event ID</th>
                      <th>Event Type</th>
                      <th>IP Address</th>
                      <th>Details</th>
                      <th>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredLogs.map((log) => (
                      <tr key={log.id} className="history-row">
                        <td className="font-mono text-muted">#{log.id}</td>
                        <td>{getEventBadge(log.event_type)}</td>
                        <td className="font-mono">{log.ip_address || "127.0.0.1"}</td>
                        <td className="audit-details-cell">{log.details}</td>
                        <td className="doc-date-cell">
                          {log.created_at ? new Date(log.created_at).toLocaleString() : "Just now"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
