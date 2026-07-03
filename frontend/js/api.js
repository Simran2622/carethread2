// api.js — Shared API helper used by every page
// This file does 3 things:
// 1. Stores the backend URL in one place
// 2. Manages JWT tokens in localStorage
// 3. Provides a fetch() wrapper that automatically adds the auth header

const API_BASE_URL = "http://127.0.0.1:8000";

// ─── TOKEN MANAGEMENT ────────────────────────────────

function saveSession(token, role) {
    localStorage.setItem("carethread_token", token);
    localStorage.setItem("carethread_role", role);
}

function getToken() {
    return localStorage.getItem("carethread_token");
}

function getRole() {
    return localStorage.getItem("carethread_role");
}

function clearSession() {
    localStorage.removeItem("carethread_token");
    localStorage.removeItem("carethread_role");
}

function logout() {
    clearSession();
    window.location.href = "../pages/login.html";
}

function requireAuth() {
    const token = getToken();
    if (!token) {
        window.location.href = "../pages/login.html";
        return false;
    }
    return true;
}

// ─── API FETCH WRAPPER ───────────────────────────────

async function apiFetch(path, options = {}) {
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    const token = getToken();
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers
    });

    let data = null;
    try {
        data = await response.json();
    } catch (_) {
        // no JSON body
    }

    if (!response.ok) {
        const message = (data && data.detail) || `Request failed (${response.status})`;
        throw new Error(message);
    }

    return data;
}

// ─── UI HELPERS ──────────────────────────────────────

function formatDateTime(isoString) {
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit"
    });
}

function formatTime(isoString) {
    const d = new Date(isoString);
    return d.toLocaleTimeString(undefined, {
        hour: "numeric",
        minute: "2-digit"
    });
}

function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.textContent = message;
        el.style.display = "block";
    }
}

function hideError(elementId) {
    const el = document.getElementById(elementId);
    if (el) {
        el.style.display = "none";
    }
}