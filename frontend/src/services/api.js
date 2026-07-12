const isDev = window.location.port === "5173";
const API_BASE = import.meta.env.VITE_API_URL || (isDev ? "http://127.0.0.1:8000/api" : (window.location.origin + "/api"));

const getHeaders = () => {
  const token = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
};

export const api = {
  // Authentication
  async register(name, email, password, role, institution) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password, role, institution }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Registration failed");
    }
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    return data;
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Login failed");
    }
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    return data;
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      method: "GET",
      headers: getHeaders(),
    });
    if (!res.ok) {
      localStorage.removeItem("token");
      throw new Error("Session expired");
    }
    return res.json();
  },

  logout() {
    localStorage.removeItem("token");
  },

  // Meetings
  async getMeetings() {
    const res = await fetch(`${API_BASE}/meetings`, {
      method: "GET",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load meetings");
    return res.json();
  },

  async createMeeting(title, description, scheduledAt, participantEmails = []) {
    const res = await fetch(`${API_BASE}/meetings`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ title, description, scheduledAt, participantEmails }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create meeting");
    }
    return res.json();
  },

  async getMeeting(id) {
    const res = await fetch(`${API_BASE}/meetings/${id}`, {
      method: "GET",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load meeting details");
    return res.json();
  },

  async startMeeting(id) {
    const res = await fetch(`${API_BASE}/meetings/${id}/start`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to start meeting");
    return res.json();
  },

  async endMeeting(id, transcript = "", audioBase64 = "") {
    const res = await fetch(`${API_BASE}/meetings/${id}/end`, {
      method: "POST",
      headers: { ...getHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ transcript, audioBase64 }),
    });
    if (!res.ok) throw new Error("Failed to end meeting");
    return res.json();
  },

  // Notes
  async getNotes(meetingId) {
    const res = await fetch(`${API_BASE}/notes/${meetingId}`, {
      method: "GET",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load meeting study notes");
    return res.json();
  },

  getNotesPdfUrl(meetingId) {
    const token = localStorage.getItem("token");
    return `${API_BASE}/notes/${meetingId}/pdf?token=${token}`;
  },

  // Tasks
  async getTasks(meetingId = null) {
    let url = `${API_BASE}/tasks`;
    if (meetingId) {
      url += `?meetingId=${meetingId}`;
    }
    const res = await fetch(url, {
      method: "GET",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to load task board");
    return res.json();
  },

  async syncTask(taskId) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/sync`, {
      method: "POST",
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Sync failed");
    return res.json();
  },

  // Integrations
  async connectNotion(token, databaseId) {
    const res = await fetch(`${API_BASE}/integrations/notion/connect`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ token, databaseId }),
    });
    if (!res.ok) throw new Error("Notion update failed");
    return res.json();
  },

  async connectJira(host, email, token, projectKey) {
    const res = await fetch(`${API_BASE}/integrations/jira/connect`, {
      method: "POST",
      headers: getHeaders(),
      body: JSON.stringify({ host, email, token, projectKey }),
    });
    if (!res.ok) throw new Error("Jira update failed");
    return res.json();
  },

  getMeetingSocketUrl(meetingId) {
    const isDev = window.location.port === "5173";
    const wsProto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = isDev ? "127.0.0.1:8000" : window.location.host;
    return `${wsProto}://${host}/api/meetings/${meetingId}/websocket`;
  }
};
