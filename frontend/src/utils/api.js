// api.js - CuraAI API Helper Library

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

export const getAuthHeaders = () => {
  const token = localStorage.getItem('curaai_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
  };
};

export const api = {
  // Auth Operations
  register: async (name, mobile_number, password, role) => {
    const res = await fetch(`${API_BASE_URL}/auth/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, mobile_number, password, role }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Registration failed');
    return data;
  },
  login: async (mobile_number, password) => {
    const res = await fetch(`${API_BASE_URL}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mobile_number, password }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Login failed');
    return data;
  },
  forgotPassword: async (mobile_number) => {
    const res = await fetch(`${API_BASE_URL}/auth/forgot-password`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mobile_number }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.message); return data;
  },
  verifyOtp: async (mobile_number, otp, new_password) => {
    const res = await fetch(`${API_BASE_URL}/auth/verify-otp`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ mobile_number, otp, new_password }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.message); return data;
  },

  // Patient Profile (Editable Records)
  getProfile: async () => {
    const res = await fetch(`${API_BASE_URL}/patient/profile`, { headers: getAuthHeaders() });
    const data = await res.json(); if (!res.ok) throw new Error(data.message); return data;
  },
  updateProfile: async (profileData) => {
    const res = await fetch(`${API_BASE_URL}/patient/profile`, { method: 'PUT', headers: getAuthHeaders(), body: JSON.stringify(profileData) });
    const data = await res.json(); if (!res.ok) throw new Error(data.message); return data;
  },

  // Patient Dashboard & Analytics
  getDashboardData: async () => {
    const res = await fetch(`${API_BASE_URL}/patient/dashboard`, {
      headers: getAuthHeaders()
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to fetch dashboard data');
    return data;
  },

  getHealthHistory: async () => {
    const res = await fetch(`${API_BASE_URL}/patient/health-records`, {
      headers: getAuthHeaders()
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to fetch health records');
    return data;
  },

  logHealthRecord: async (record) => {
    const res = await fetch(`${API_BASE_URL}/patient/health-records`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(record)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to log health vitals');
    return data;
  },

  // File Uploads
  uploadReport: async (file, reportType, isPrescription) => {
    const token = localStorage.getItem('curaai_token');
    const formData = new FormData();
    formData.append('file', file);
    formData.append('report_type', reportType);
    formData.append('is_prescription', isPrescription ? 'true' : 'false');

    const res = await fetch(`${API_BASE_URL}/patient/upload-report`, {
      method: 'POST',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'File upload failed');
    return data;
  },

  analyzeSymptoms: async (symptoms) => {
    const res = await fetch(`${API_BASE_URL}/symptom-analysis`, { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ symptoms }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.message); return data;
  },

  analyzeCustomSymptoms: async (symptomText, severity, durationDays, tagSymptoms) => {
    const res = await fetch(`${API_BASE_URL}/symptom-analysis/custom`, {
      method: 'POST', headers: getAuthHeaders(),
      body: JSON.stringify({ symptom_text: symptomText, severity, duration_days: durationDays, tag_symptoms: tagSymptoms })
    });
    const data = await res.json(); if (!res.ok) throw new Error(data.message); return data;
  },

  recommendDoctors: async (disease, symptoms) => {
    const res = await fetch(`${API_BASE_URL}/doctors/recommend`, { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ disease, symptoms }) });
    const data = await res.json(); if (!res.ok) throw new Error(data.message); return data;
  },

  getDrugRecommendations: async (disease, predictionId) => {
    const res = await fetch(`${API_BASE_URL}/drug-recommendations`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ disease, prediction_id: predictionId })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'AI Drug Recommender failed');
    return data;
  },

  getHealthRecommendations: async (disease) => {
    const res = await fetch(`${API_BASE_URL}/health-recommendations`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ disease })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'AI Health Advisor failed');
    return data;
  },

  // Doctor Connect
  getDoctors: async () => {
    const res = await fetch(`${API_BASE_URL}/doctors`, {
      headers: getAuthHeaders()
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to list doctors');
    return data;
  },

  bookAppointment: async (doctorId, date, time, type) => {
    const res = await fetch(`${API_BASE_URL}/appointments`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ doctor_id: doctorId, appointment_date: date, appointment_time: time, consultation_type: type })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to book appointment');
    return data;
  },

  getAppointments: async () => {
    const res = await fetch(`${API_BASE_URL}/appointments`, {
      headers: getAuthHeaders()
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to fetch appointments');
    return data;
  },

  // SOS Emergency & Reminders
  triggerSOS: async (location) => {
    const res = await fetch(`${API_BASE_URL}/emergency-alert`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ location })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to trigger SOS alert');
    return data;
  },

  setMedicineReminder: async (medicineName, reminderTime) => {
    const res = await fetch(`${API_BASE_URL}/medicine-reminder`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ medicine_name: medicineName, reminder_time: reminderTime })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to set reminder');
    return data;
  },

  // Messages
  sendMessage: async (receiverId, message) => {
    const res = await fetch(`${API_BASE_URL}/messages`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ receiver_id: receiverId, message })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Message dispatch failed');
    return data;
  },

  getMessages: async (counterpartyId) => {
    const res = await fetch(`${API_BASE_URL}/messages?counterparty_id=${counterpartyId}`, {
      headers: getAuthHeaders()
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to retrieve messages');
    return data;
  },

  // Admin dashboard
  getAdminDashboard: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/dashboard`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to fetch admin metrics');
    return data;
  },

  // Medicine Reminders (Full CRUD)
  getReminders: async () => {
    const res = await fetch(`${API_BASE_URL}/reminders`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to load reminders');
    return data;
  },
  addReminder: async (reminderData) => {
    const res = await fetch(`${API_BASE_URL}/reminders`, {
      method: 'POST', headers: getAuthHeaders(), body: JSON.stringify(reminderData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to add reminder');
    return data;
  },
  updateReminder: async (id, reminderData) => {
    const res = await fetch(`${API_BASE_URL}/reminders/${id}`, {
      method: 'PUT', headers: getAuthHeaders(), body: JSON.stringify(reminderData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to update reminder');
    return data;
  },
  deleteReminder: async (id) => {
    const res = await fetch(`${API_BASE_URL}/reminders/${id}`, {
      method: 'DELETE', headers: getAuthHeaders()
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to delete reminder');
    return data;
  },
  setMedicineReminder: async (medicineName, reminderTime) => {
    const res = await fetch(`${API_BASE_URL}/medicine-reminder`, {
      method: 'POST', headers: getAuthHeaders(),
      body: JSON.stringify({ medicine_name: medicineName, reminder_time: reminderTime })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message || 'Failed to set reminder');
    return data;
  },

  // Chatbot
  sendChatMessage: async (message) => {
    const res = await fetch(`${API_BASE_URL}/chat`, { method: 'POST', headers: getAuthHeaders(), body: JSON.stringify({ message }) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Chatbot error');
    return data;
  },
  getChatHistory: async () => {
    const res = await fetch(`${API_BASE_URL}/chat/history`, { headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message);
    return data;
  },
  clearChatHistory: async () => {
    const res = await fetch(`${API_BASE_URL}/chat/history`, { method: 'DELETE', headers: getAuthHeaders() });
    const data = await res.json();
    if (!res.ok) throw new Error(data.message);
    return data;
  },
};

