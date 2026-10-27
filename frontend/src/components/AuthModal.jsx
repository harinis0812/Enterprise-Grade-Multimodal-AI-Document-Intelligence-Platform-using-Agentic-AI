import { useState } from "react";
import {
  IconClose,
  IconEye,
  IconEyeOff,
  IconShield,
  IconBrain,
  IconCheck,
  IconAlertTriangle
} from "./Icons";

export default function AuthModal({
  isOpen,
  onClose,
  initialMode = "login",
  onSubmit,
  loading = false,
  error = "",
}) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [validationError, setValidationError] = useState("");

  if (!isOpen) return null;

  function handleSubmit(e) {
    e.preventDefault();
    setValidationError("");

    if (!email.trim()) {
      setValidationError("Please enter your corporate email address.");
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setValidationError("Please enter a valid email format (e.g. user@enterprise.com).");
      return;
    }

    if (!password) {
      setValidationError("Please enter your password.");
      return;
    }
    if (password.length < 8) {
      setValidationError("Password must be at least 8 characters long.");
      return;
    }

    if (mode === "register" && !fullName.trim()) {
      setValidationError("Please enter your full name.");
      return;
    }

    onSubmit({
      mode,
      email: email.trim(),
      password,
      fullName: fullName.trim(),
    });
  }

  return (
    <div className="auth-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="auth-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Close Button */}
        <button
          type="button"
          className="auth-modal-close"
          onClick={onClose}
          aria-label="Close authentication modal"
        >
          <IconClose size={20} />
        </button>

        {/* Modal Split View */}
        <div className="auth-modal-split">
          {/* Left Hero / Branding Panel */}
          <div className="auth-modal-brand-panel">
            <div className="auth-brand-header">
              <div className="auth-brand-badge">
                <IconBrain size={24} />
              </div>
              <h3>Docu<span>AI</span></h3>
            </div>

            <div className="auth-brand-content">
              <h4>Enterprise-Grade Document Intelligence</h4>
              <p>
                Autonomously process, verify, and extract deep structured intelligence
                from enterprise contracts, invoices, and records using Agentic AI.
              </p>

              <div className="auth-feature-list">
                <div className="auth-feature-item">
                  <div className="feature-check"><IconCheck size={14} /></div>
                  <span>Multi-agent autonomous classification & OCR</span>
                </div>
                <div className="auth-feature-item">
                  <div className="feature-check"><IconCheck size={14} /></div>
                  <span>Grounded AI question answering with citations</span>
                </div>
                <div className="auth-feature-item">
                  <div className="feature-check"><IconCheck size={14} /></div>
                  <span>Multi-tenant data isolation & audit compliance</span>
                </div>
              </div>
            </div>

            <div className="auth-brand-footer">
              <IconShield size={14} />
              <span>AES-256 Multi-Tenant Secured</span>
            </div>
          </div>

          {/* Right Form Panel */}
          <div className="auth-modal-form-panel">
            {/* Mode Switch Tabs */}
            <div className="auth-tabs-container">
              <button
                type="button"
                className={`auth-tab-btn ${mode === "login" ? "active" : ""}`}
                onClick={() => {
                  setMode("login");
                  setValidationError("");
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-tab-btn ${mode === "register" ? "active" : ""}`}
                onClick={() => {
                  setMode("register");
                  setValidationError("");
                }}
              >
                Create Account
              </button>
            </div>

            <div className="auth-form-intro">
              <h3>{mode === "login" ? "Welcome back" : "Get started with DocuAI"}</h3>
              <p>
                {mode === "login"
                  ? "Enter your credentials to access your document repository"
                  : "Register a secure account to upload and analyze business documents"}
              </p>
            </div>

            {/* Error Message */}
            {(validationError || error) && (
              <div className="auth-error-alert" role="alert">
                <IconAlertTriangle size={18} />
                <span>{validationError || error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form-body">
              {mode === "register" && (
                <div className="form-group">
                  <label htmlFor="auth-fullname">Full Name</label>
                  <input
                    id="auth-fullname"
                    type="text"
                    placeholder="e.g. Sarah Jenkins"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    disabled={loading}
                    autoComplete="name"
                    required
                  />
                </div>
              )}

              <div className="form-group">
                <label htmlFor="auth-email">Corporate Email Address</label>
                <input
                  id="auth-email"
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={loading}
                  autoComplete="email"
                  required
                />
              </div>

              <div className="form-group">
                <div className="label-row">
                  <label htmlFor="auth-password">Password</label>
                  <span className="field-hint">Min. 8 characters</span>
                </div>
                <div className="password-input-wrapper">
                  <input
                    id="auth-password"
                    type={showPassword ? "text" : "password"}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={loading}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <IconEyeOff size={18} /> : <IconEye size={18} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                className="auth-submit-action-btn"
                disabled={loading}
              >
                {loading ? (
                  <span className="btn-spinner-row">
                    <span className="spinner-dot"></span>
                    <span>Authenticating...</span>
                  </span>
                ) : mode === "login" ? (
                  "Sign In to Enterprise Workspace"
                ) : (
                  "Create Enterprise Account"
                )}
              </button>
            </form>

            <div className="auth-form-switch-prompt">
              {mode === "login" ? (
                <span>
                  Don't have an enterprise account?{" "}
                  <button
                    type="button"
                    className="switch-link"
                    onClick={() => {
                      setMode("register");
                      setValidationError("");
                    }}
                  >
                    Register here
                  </button>
                </span>
              ) : (
                <span>
                  Already registered?{" "}
                  <button
                    type="button"
                    className="switch-link"
                    onClick={() => {
                      setMode("login");
                      setValidationError("");
                    }}
                  >
                    Sign in
                  </button>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
