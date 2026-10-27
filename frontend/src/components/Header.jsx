import {
  IconMenu,
  IconLogOut,
  IconShield,
  IconUpload,
  IconSparkles
} from "./Icons";

export default function Header({
  activeTab,
  user,
  token,
  onOpenAuth,
  onLogout,
  onOpenSidebar,
  setActiveTab
}) {
  const titles = {
    dashboard: "Enterprise Overview",
    upload: "Document Upload & Processing",
    ask: "Document Intelligence Q&A",
    history: "Document Repository & History",
    security: "Security & Audit Activity",
  };

  const breadcrumbs = {
    dashboard: "Platform / Dashboard",
    upload: "Platform / Upload & Agents",
    ask: "Platform / AI Q&A Workspace",
    history: "Platform / Repository",
    security: "Platform / Compliance & Security",
  };

  const initial = user?.full_name
    ? user.full_name[0].toUpperCase()
    : user?.email
    ? user.email[0].toUpperCase()
    : "U";

  return (
    <header className="app-header">
      {/* Mobile Menu & Page Title */}
      <div className="header-left">
        <button
          type="button"
          className="mobile-menu-btn"
          onClick={onOpenSidebar}
          aria-label="Open navigation menu"
        >
          <IconMenu size={22} />
        </button>

        <div className="header-breadcrumbs">
          <span className="breadcrumb-path">{breadcrumbs[activeTab] || "Platform"}</span>
          <h1 className="header-title">{titles[activeTab] || "Enterprise Platform"}</h1>
        </div>
      </div>

      {/* Header Actions & User Profile */}
      <div className="header-right">
        {/* Quick Upload CTA (if not on upload page) */}
        {activeTab !== "upload" && (
          <button
            type="button"
            className="header-quick-action"
            onClick={() => setActiveTab("upload")}
            title="Upload a new document"
          >
            <IconUpload size={16} />
            <span>Upload Document</span>
          </button>
        )}

        {/* User state */}
        {token && user ? (
          <div className="header-user-group">
            <div className="user-profile-card">
              <div className="user-avatar-bubble">
                <span>{initial}</span>
              </div>
              <div className="user-text-info">
                <span className="user-display-name">
                  {user.full_name || user.email.split("@")[0]}
                </span>
                <span className="user-role-badge">
                  <IconShield size={11} />
                  Enterprise User
                </span>
              </div>
            </div>

            <button
              type="button"
              className="header-logout-btn"
              onClick={onLogout}
              title="Sign Out of DocuAI"
            >
              <IconLogOut size={16} />
              <span>Sign Out</span>
            </button>
          </div>
        ) : (
          <div className="header-auth-buttons">
            <button
              type="button"
              className="auth-btn-ghost"
              onClick={() => onOpenAuth("login")}
            >
              Sign In
            </button>
            <button
              type="button"
              className="auth-btn-primary"
              onClick={() => onOpenAuth("register")}
            >
              <IconSparkles size={15} />
              <span>Create Account</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
