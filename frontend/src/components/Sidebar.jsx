import {
  IconDashboard,
  IconUpload,
  IconMessageSquare,
  IconHistory,
  IconShield,
  IconBrain,
  IconClose
} from "./Icons";

export default function Sidebar({
  activeTab,
  setActiveTab,
  documentCount = 0,
  health,
  isOpen,
  onClose,
  token
}) {
  const navItems = [
    {
      id: "dashboard",
      label: "Dashboard",
      icon: IconDashboard,
      badge: null,
    },
    {
      id: "upload",
      label: "Upload & Process",
      icon: IconUpload,
      badge: null,
    },
    {
      id: "ask",
      label: "Ask Documents",
      icon: IconMessageSquare,
      badge: "AI",
    },
    {
      id: "history",
      label: "Document History",
      icon: IconHistory,
      badge: token ? documentCount : null,
    },
    {
      id: "security",
      label: "Security & Activity",
      icon: IconShield,
      badge: null,
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && <div className="sidebar-backdrop" onClick={onClose} />}

      <aside className={`app-sidebar ${isOpen ? "open" : ""}`}>
        {/* Brand Header */}
        <div className="sidebar-brand">
          <div className="brand-logo-container">
            <div className="brand-icon-gem">
              <IconBrain size={22} className="brand-icon" />
            </div>
            <div className="brand-text">
              <div className="brand-title">
                Docu<span>AI</span>
              </div>
              <div className="brand-tagline">Multimodal Agentic AI</div>
            </div>
          </div>
          <button
            type="button"
            className="sidebar-close-btn"
            onClick={onClose}
            aria-label="Close sidebar"
          >
            <IconClose size={20} />
          </button>
        </div>

        {/* Section Label */}
        <div className="sidebar-section-label">PLATFORM NAVIGATION</div>

        {/* Navigation list */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                type="button"
                className={`sidebar-nav-item ${isActive ? "active" : ""}`}
                onClick={() => {
                  setActiveTab(item.id);
                  if (onClose) onClose();
                }}
              >
                <div className="nav-item-icon-wrapper">
                  <Icon size={18} />
                </div>
                <span className="nav-item-label">{item.label}</span>
                {item.badge !== null && (
                  <span className={`nav-item-badge ${item.badge === "AI" ? "ai-badge" : ""}`}>
                    {item.badge}
                  </span>
                )}
                {isActive && <div className="active-pill-indicator" />}
              </button>
            );
          })}
        </nav>

        {/* System Health / Status Badge */}
        <div className="sidebar-footer">
          <div className="system-health-card">
            <div className="health-header">
              <span className={`health-dot ${health?.status === "healthy" ? "healthy" : "offline"}`} />
              <span className="health-title">System Status</span>
            </div>
            <div className="health-detail">
              <span>FastAPI & Agents:</span>
              <strong>{health?.status === "healthy" ? "Operational" : "Checking..."}</strong>
            </div>
            <div className="health-detail">
              <span>Database:</span>
              <strong>{health?.database === "connected" ? "Connected" : "Standby"}</strong>
            </div>
          </div>
          <div className="sidebar-version-tag">DocuAI v1.0.0 Enterprise</div>
        </div>
      </aside>
    </>
  );
}
