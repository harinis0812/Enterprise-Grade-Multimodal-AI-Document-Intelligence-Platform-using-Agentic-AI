export const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8010";

export const ALLOWED_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/jpg"
];

export const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

/**
 * Builds HTTP headers with Bearer token if provided.
 */
export function getAuthHeaders(token, hasBody = false) {
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (hasBody) {
    headers["Content-Type"] = "application/json";
  }
  return headers;
}

/**
 * Safely parse HTTP responses, extracting JSON detail or fallback text.
 */
export async function readResponse(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return await response.json();
  }
  const text = await response.text();
  return { detail: text || "An unexpected server response occurred." };
}

/**
 * Safely unpacks nested and stringified analysis JSON from backend Document model.
 */
export function parseStoredAnalysis(data) {
  if (!data) return null;

  let parsedAnalysis = {};
  if (typeof data.analysis === "string" && data.analysis.trim()) {
    try {
      parsedAnalysis = JSON.parse(data.analysis);
    } catch (e) {
      console.warn("Unable to parse stored analysis JSON:", e);
    }
  } else if (data.analysis && typeof data.analysis === "object") {
    parsedAnalysis = data.analysis;
  }

  let parsedTrace = data.agent_trace;
  if (typeof parsedTrace === "string" && parsedTrace.trim()) {
    try {
      parsedTrace = JSON.parse(parsedTrace);
    } catch (e) {
      console.warn("Unable to parse agent trace JSON:", e);
    }
  }

  return {
    ...data,
    document_information:
      data.document_information ||
      parsedAnalysis.document_information ||
      {},
    analysis:
      parsedAnalysis.analysis ||
      (data.analysis && typeof data.analysis === "object" ? data.analysis : null),
    verification:
      data.verification ||
      parsedAnalysis.verification ||
      {},
    supervisor_decision:
      data.supervisor_decision ||
      parsedAnalysis.supervisor_decision ||
      null,
    agent_trace: Array.isArray(parsedTrace) ? parsedTrace : [],
  };
}

/**
 * API client methods.
 */
export const api = {
  async getHealth() {
    try {
      const res = await fetch(`${API_URL}/health`);
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.warn("Health check error:", err);
    }
    return { status: "disconnected", service: "DocuAI", database: "disconnected" };
  },

  async login(email, password) {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: email.trim(), password }),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Authentication failed.");
    }
    return data;
  },

  async register(email, password, full_name) {
    const payload = { email: email.trim(), password };
    if (full_name?.trim()) {
      payload.full_name = full_name.trim();
    }
    const res = await fetch(`${API_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Registration failed.");
    }
    return data;
  },

  async logout(token) {
    if (!token) return;
    try {
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: getAuthHeaders(token, false),
      });
    } catch (err) {
      console.warn("Logout error:", err);
    }
  },

  async getProfile(token) {
    const res = await fetch(`${API_URL}/auth/me`, {
      headers: getAuthHeaders(token, false),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Failed to load profile.");
    }
    return data;
  },

  async getDocuments(token) {
    const res = await fetch(`${API_URL}/documents`, {
      headers: getAuthHeaders(token, false),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Failed to fetch documents.");
    }
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.documents)) return data.documents;
    return [];
  },

  async getDocumentDetails(documentId, token) {
    const res = await fetch(`${API_URL}/documents/${documentId}`, {
      headers: getAuthHeaders(token, false),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || `Failed to fetch document #${documentId}.`);
    }
    return parseStoredAnalysis(data);
  },

  async uploadDocument(file, token) {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_URL}/upload`, {
      method: "POST",
      headers: getAuthHeaders(token, false),
      body: formData,
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Upload failed.");
    }

    // Retrieve detailed result
    if (data.id) {
      try {
        const fullDoc = await this.getDocumentDetails(data.id, token);
        return fullDoc;
      } catch (err) {
        console.warn("Could not fetch full doc after upload:", err);
      }
    }
    return data;
  },

  async askDocumentQuestion(documentId, question, token) {
    const res = await fetch(`${API_URL}/documents/${documentId}/qa`, {
      method: "POST",
      headers: getAuthHeaders(token, true),
      body: JSON.stringify({ question: question.trim() }),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Failed to answer question.");
    }
    return data;
  },

  async getDocumentQAHistory(documentId, token) {
    const res = await fetch(`${API_URL}/documents/${documentId}/qa/history`, {
      headers: getAuthHeaders(token, false),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Failed to load conversation history.");
    }
    return data.history || [];
  },

  async getAuditLogs(token) {
    const res = await fetch(`${API_URL}/audit-logs`, {
      headers: getAuthHeaders(token, false),
    });
    const data = await readResponse(res);
    if (!res.ok) {
      throw new Error(data.detail || "Failed to fetch audit logs.");
    }
    return data.logs || [];
  },
};
