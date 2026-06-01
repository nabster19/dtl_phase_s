import React, { useState, useEffect, useRef } from 'react';
import { 
  Activity, Heart, ShieldAlert, FileText, Video, Brain, Clock, User, Users, 
  LogOut, Moon, Sun, Send, Calendar, DollarSign, AlertCircle, Trash, Plus, 
  Search, Download, Droplet, Thermometer, Weight, ChevronRight, Phone, 
  Mail, MapPin, Check, PlusCircle, Sparkles, MessageSquare, Menu, X, ArrowUpRight
} from 'lucide-react';
import { Line, Bar } from 'react-chartjs-2';
import { 
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, 
  BarElement, Title, Tooltip, Legend, Filler 
} from 'chart.js';
import { api } from './utils/api';
import Chatbot from './components/Chatbot';

// Register ChartJS elements
ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, BarElement, 
  Title, Tooltip, Legend, Filler
);

export default function App() {
  // Global States
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null); // 'patient', 'doctor', 'admin'
  const [token, setToken] = useState(localStorage.getItem('curaai_token'));
  const [darkMode, setDarkMode] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Auth Screen States
  const [authMode, setAuthMode] = useState('landing'); // 'landing', 'login', 'register', 'forgot'
  const [authForm, setAuthForm] = useState({
    name: '', mobile_number: '', password: '', role: 'patient', otp: '', new_password: ''
  });
  const [otpSent, setOtpSent] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  // Dashboard Data States
  const [dashboardData, setDashboardData] = useState(null);
  const [healthHistory, setHealthHistory] = useState([]);
  const [doctors, setDoctors] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [chatMessages, setChatMessages] = useState([]);
  const [activeChatDoctor, setActiveChatDoctor] = useState(null);
  const [newMessage, setNewMessage] = useState('');
  
  // Forms & Loading States
  const [vitalsForm, setVitalsForm] = useState({
    blood_pressure_sys: 120, blood_pressure_dia: 80, sugar_level: 100,
    cholesterol: 180, weight: 70.0, height: 170.0, heart_rate: 75,
    oxygen_level: 98, temperature: 36.6, water_intake: 2000,
    recorded_date: new Date().toISOString().split('T')[0]
  });
  const [symptomInput, setSymptomInput] = useState('');
  const [selectedSymptoms, setSelectedSymptoms] = useState([]);
  const [aiPredictions, setAiPredictions] = useState(null);
  const [activePredDetails, setActivePredDetails] = useState(null);
  const [lifestyleRecs, setLifestyleRecs] = useState(null);
  
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadType, setUploadType] = useState('blood_test');
  const [isPrescriptionUpload, setIsPrescriptionUpload] = useState(false);
  const [ocrModalData, setOcrModalData] = useState(null);
  
  const [appointmentForm, setAppointmentForm] = useState({
    doctor_id: '', appointment_date: '', appointment_time: '10:00 AM', consultation_type: 'video'
  });
  const [reminderForm, setReminderForm] = useState({
    medicine_name: '', reminder_time: '08:00 AM'
  });

  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  // Admin Portal States
  const [adminData, setAdminData] = useState(null);

  // ── NEW: Editable Profile States ──
  const [profileData, setProfileData] = useState(null);
  const [profileForm, setProfileForm] = useState({
    age: '', weight: '', height: '', gender: '', blood_group: '',
    medical_history: '', allergies: '', medications: '', emergency_contact: ''
  });
  const [profileSaving, setProfileSaving] = useState(false);

  // ── NEW: Custom Symptom / NLP States ──
  const [symptomMode, setSymptomMode] = useState('quick'); // 'quick' | 'custom'
  const [customSymptomText, setCustomSymptomText] = useState('');
  const [symptomSeverity, setSymptomSeverity] = useState('moderate');
  const [symptomDuration, setSymptomDuration] = useState(0);
  const [customResult, setCustomResult] = useState(null);

  // ── NEW: Notification Panel ──
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState([]);

  // Symptoms catalog
  const symptomsCatalog = [
    "fever", "chills", "cough", "sore_throat", "muscle_aches", "fatigue", 
    "polyuria", "polydipsia", "weight_loss", "blurry_vision", "headache", 
    "shortness_of_breath", "nosebleeds", "dizziness", "chest_pain", 
    "itchy_skin", "red_rash", "dry_skin", "skin_blisters", "severe_headache", 
    "nausea", "sensitivity_to_light", "sensitivity_to_sound", "aura", 
    "diarrhea", "bloating", "abdominal_pain", "salty_skin", "poor_growth", 
    "muscle_weakness", "slurred_speech", "muscle_cramps", "difficulty_swallowing", 
    "involuntary_movements", "cognitive_decline", "balance_issues", "depression", 
    "joint_pain", "butterfly_rash", "hair_loss", "heartburn", "acid_reflux", 
    "joint_stiffness", "swollen_joints", "weight_gain", "cold_intolerance", 
    "pale_skin", "weakness", "cold_hands"
  ];

  // Load user from token on page refresh
  useEffect(() => {
    if (token) {
      try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(c => {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));
        const decoded = JSON.parse(jsonPayload);
        // Check expiry
        if (decoded.exp && decoded.exp * 1000 < Date.now()) {
          console.warn('Token expired, logging out.');
          handleLogout();
          return;
        }
        setRole(decoded.role);
        fetchUserData(decoded.role);
      } catch (err) {
        console.error('Token decode error:', err);
        handleLogout();
      }
    } else {
      setAuthMode('landing');
    }
  }, [token]);

  // Sync scroll on chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const fetchUserData = async (userRole) => {
    setLoading(true);
    try {
      if (userRole === 'patient') {
        const dash = await api.getDashboardData();
        setDashboardData(dash);
        const history = await api.getHealthHistory();
        setHealthHistory(history);
        const docList = await api.getDoctors();
        setDoctors(docList);
        const apptList = await api.getAppointments();
        setAppointments(apptList);
        // Load editable profile
        try {
          const prof = await api.getProfile();
          setProfileData(prof);
          setProfileForm({
            age: prof.age || '', weight: prof.weight || '', height: prof.height || '',
            gender: prof.gender || '', blood_group: prof.blood_group || '',
            medical_history: prof.medical_history || '', allergies: prof.allergies || '',
            medications: prof.medications || '', emergency_contact: prof.emergency_contact || ''
          });
        } catch(pe) { console.warn('Profile load:', pe.message); }
      } else if (userRole === 'doctor') {
        const apptList = await api.getAppointments();
        setAppointments(apptList);
        const docList = await api.getDoctors();
        setDoctors(docList);
      } else if (userRole === 'admin') {
        const adminMetric = await api.getAdminDashboard();
        setAdminData(adminMetric);
        setNotifications((adminMetric.notifications || []).slice(0, 8));
      }
    } catch (err) {
      console.error(err);
      // Auto-logout on expired/invalid token
      if (err.message && (err.message.includes('expired') || err.message.includes('invalid') || err.message.includes('401'))) {
        handleLogout();
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Profile Save Handler ──
  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setProfileSaving(true);
    try {
      const res = await api.updateProfile({
        age: parseInt(profileForm.age),
        weight: parseFloat(profileForm.weight),
        height: parseFloat(profileForm.height),
        gender: profileForm.gender,
        blood_group: profileForm.blood_group,
        medical_history: profileForm.medical_history,
        allergies: profileForm.allergies,
        medications: profileForm.medications,
        emergency_contact: profileForm.emergency_contact
      });
      showToast(`Profile updated! BMI: ${res.bmi || 'N/A'}`, 'success');
      fetchUserData(role);
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setProfileSaving(false);
    }
  };

  // ── Custom NLP Symptom Analysis ──
  const runCustomAnalysis = async () => {
    if (!customSymptomText.trim() && selectedSymptoms.length === 0) {
      showToast('Please describe your symptoms or select from the quick list.', 'error');
      return;
    }
    setLoading(true);
    try {
      const res = await api.analyzeCustomSymptoms(
        customSymptomText, symptomSeverity, symptomDuration, selectedSymptoms
      );
      setCustomResult(res);
      // Also populate activePredDetails for drug/habit panel
      if (res.predictions && res.predictions.length > 0) {
        const tp = res.predictions[0];
        setActivePredDetails({
          disease: tp.disease, confidence: tp.confidence, category: tp.category,
          severity: tp.severity, is_rare: tp.is_rare,
          precautions: tp.precautions, next_actions: tp.next_actions,
          drugs: res.drugs, habits: res.habits
        });
      }
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  // Toggle Dark Mode
  const toggleDarkMode = () => {
    setDarkMode(!darkMode);
    if (!darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  // ── Client-side validation helper ──
  const validateAuthForm = () => {
    const mobile = (authForm.mobile_number || '').trim().replace(/[\s\-]/g, '');
    const password = (authForm.password || '').trim();
    const name = (authForm.name || '').trim();

    if (authMode === 'register') {
      if (!name || name.length < 2)
        return 'Please enter your full name (at least 2 characters).';
      if (!mobile)
        return 'Mobile number is required.';
      if (!/^[6-9]\d{9}$/.test(mobile))
        return 'Enter a valid 10-digit Indian mobile number (starting with 6–9).';
      if (!password || password.length < 6)
        return 'Password must be at least 6 characters long.';
    }

    if (authMode === 'login') {
      if (!mobile)
        return 'Please enter your mobile number.';
      if (!password)
        return 'Please enter your password.';
    }

    return null; // no error
  };

  // Auth Operations
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    // Run client-side validation first
    const validationError = validateAuthForm();
    if (validationError) {
      setErrorMsg(validationError);
      return;
    }

    setLoading(true);
    try {
      const mobile = (authForm.mobile_number || '').trim().replace(/[\s\-]/g, '');

      if (authMode === 'login') {
        const res = await api.login(mobile, authForm.password.trim());
        localStorage.setItem('curaai_token', res.token);
        setRole(res.user.role);
        setUser(res.user);
        setToken(res.token);
        fetchUserData(res.user.role); // Eagerly load dashboard data
        showToast(`Welcome back, ${res.user.name.split(' ')[0]}! 👋`, 'success');

      } else if (authMode === 'register') {
        const res = await api.register(
          authForm.name.trim(), mobile, authForm.password.trim(), authForm.role
        );
        localStorage.setItem('curaai_token', res.token);
        setRole(res.user.role);
        setUser(res.user);
        setToken(res.token);
        fetchUserData(res.user.role);
        showToast(`Account created! Welcome, ${res.user.name.split(' ')[0]}! 🎉`, 'success');
        // Reset form
        setAuthForm({ name: '', mobile_number: '', password: '', role: 'patient', otp: '', new_password: '' });

      } else if (authMode === 'forgot') {
        if (!otpSent) {
          await api.forgotPassword(mobile);
          setOtpSent(true);
          setSuccessMsg("OTP Code '184029' has been sent to your mobile number.");
        } else {
          await api.verifyOtp(mobile, authForm.otp, authForm.new_password);
          setSuccessMsg('Password reset successfully. You can now log in.');
          setAuthMode('login');
          setOtpSent(false);
          setAuthForm(f => ({ ...f, otp: '', new_password: '', password: '' }));
        }
      }
    } catch (err) {
      setErrorMsg(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('curaai_token');
    setToken(null);
    setUser(null);
    setRole(null);
    setDashboardData(null);
    setHealthHistory([]);
    setAuthMode('landing');
    setActiveTab('dashboard');
  };

  // Vitals Logging
  const handleLogVitals = async (e) => {
    e.preventDefault();
    try {
      const res = await api.logHealthRecord(vitalsForm);
      showToast("Health vitals recorded successfully!", "success");
      if (res.warnings && res.warnings.length > 0) {
        showToast(`Warning: ${res.warnings[0]}`, "warning");
      }
      fetchUserData(role);
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // Symptom Analysis & AI
  const handleAddSymptom = (sym) => {
    if (sym && !selectedSymptoms.includes(sym)) {
      setSelectedSymptoms([...selectedSymptoms, sym]);
    }
    setSymptomInput('');
  };

  const handleRemoveSymptom = (sym) => {
    setSelectedSymptoms(selectedSymptoms.filter(s => s !== sym));
  };

  const runSymptomAnalysis = async () => {
    if (selectedSymptoms.length === 0) return;
    setLoading(true);
    try {
      const res = await api.analyzeSymptoms(selectedSymptoms);
      setAiPredictions(res.predictions);
      
      // Auto-load drug and habit recommendations for primary prediction
      if (res.predictions && res.predictions.length > 0) {
        const topPred = res.predictions[0];
        const drugRes = await api.getDrugRecommendations(topPred.disease, res.prediction_id);
        const habitRes = await api.getHealthRecommendations(topPred.disease);
        
        setActivePredDetails({
          disease: topPred.disease,
          confidence: topPred.confidence,
          category: topPred.category,
          severity: topPred.severity,
          is_rare: topPred.is_rare,
          precautions: topPred.precautions,
          next_actions: topPred.next_actions,
          drugs: drugRes,
          habits: habitRes
        });
      }
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // File Scans & OCR
  const handleFileChange = (e) => {
    setUploadFile(e.target.files[0]);
  };

  const handleUploadReport = async (e) => {
    e.preventDefault();
    if (!uploadFile) {
      showToast("Please choose a file to upload.", "error");
      return;
    }
    setLoading(true);
    try {
      const res = await api.uploadReport(uploadFile, uploadType, isPrescriptionUpload);
      showToast(res.message, "success");
      setOcrModalData(res);
      setUploadFile(null);
      fetchUserData(role);
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  // SOS Emergency Trigger
  const handleSOSAlert = async () => {
    if (!window.confirm("WARNING: Are you sure you want to trigger a CRITICAL SOS EMERGENCY? This will immediately notify emergency contacts via SMS and alert response coordinators.")) {
      return;
    }
    
    // Simulate browser geolocation
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const coords = `Latitude: ${pos.coords.latitude.toFixed(5)}, Longitude: ${pos.coords.longitude.toFixed(5)}`;
        try {
          const res = await api.triggerSOS(coords);
          showToast(res.message, "success");
        } catch (err) {
          showToast("SOS Alert successfully simulated in console logs.", "success");
        }
      },
      async (err) => {
        try {
          const res = await api.triggerSOS("GPS Unavailable: Room 302, Phase 1 Medical Wing");
          showToast(res.message, "success");
        } catch (sosErr) {
          showToast("SOS Alert successfully simulated in console logs.", "success");
        }
      }
    );
  };

  // Appointments
  const handleBookAppointment = async (e) => {
    e.preventDefault();
    if (!appointmentForm.doctor_id || !appointmentForm.appointment_date) {
      showToast("Please select doctor and date.", "error");
      return;
    }
    try {
      const res = await api.bookAppointment(
        appointmentForm.doctor_id,
        appointmentForm.appointment_date,
        appointmentForm.appointment_time,
        appointmentForm.consultation_type
      );
      showToast(res.message, "success");
      fetchUserData(role);
      // Reset Form
      setAppointmentForm({
        doctor_id: '', appointment_date: '', appointment_time: '10:00 AM', consultation_type: 'video'
      });
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // Medicine reminders
  const handleSetReminder = async (e) => {
    e.preventDefault();
    if (!reminderForm.medicine_name) return;
    try {
      const res = await api.setMedicineReminder(reminderForm.medicine_name, reminderForm.reminder_time);
      showToast(res.message, "success");
      setReminderForm({ medicine_name: '', reminder_time: '08:00 AM' });
      fetchUserData(role);
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // Doctor Chat messaging
  const selectChatDoctor = async (doc) => {
    setActiveChatDoctor(doc);
    try {
      const msgs = await api.getMessages(doc.user_id);
      setChatMessages(msgs);
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeChatDoctor) return;
    try {
      await api.sendMessage(activeChatDoctor.user_id, newMessage);
      setNewMessage('');
      // Reload chat
      const msgs = await api.getMessages(activeChatDoctor.user_id);
      setChatMessages(msgs);
    } catch (err) {
      showToast(err.message, "error");
    }
  };

  // Notification helper
  const [toast, setToast] = useState({ show: false, message: '', type: 'success' });
  const showToast = (message, type = 'success') => {
    setToast({ show: true, message, type });
    setTimeout(() => {
      setToast({ show: false, message: '', type: 'success' });
    }, 4500);
  };

  // PDF report mock generator
  const downloadSummaryPDF = () => {
    const printContent = document.getElementById("patient-summary-report");
    if (!printContent) return;
    
    // We open printable window layout
    const windowUrl = 'about:blank';
    const uniqueName = new Date().getTime();
    const printWindow = window.open(windowUrl, uniqueName, 'left=50,top=50,width=800,height=900');
    
    printWindow.document.write(`
      <html>
        <head>
          <title>CuraAI Clinical Health Report</title>
          <style>
            body { font-family: sans-serif; color: #333; padding: 40px; }
            .header { text-align: center; border-bottom: 2px solid #0284c7; padding-bottom: 20px; }
            .section { margin-top: 30px; }
            .card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-top: 10px; }
            .title { font-size: 18px; font-weight: bold; color: #0284c7; }
            .vitals-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 15px; }
            .vital-card { background: #f0f9ff; padding: 10px; border-radius: 4px; }
          </style>
        </head>
        <body>
          <div class="header">
            <h2>CuraAI Clinical decision Support System</h2>
            <p>Smart Patient Health Record Report - ${new Date().toLocaleDateString()}</p>
          </div>
          ${printContent.innerHTML}
          <div class="section" style="text-align: center; font-size: 12px; margin-top: 50px; color: #888;">
            Report generated securely by CuraAI Healthcare Decision Support Server. All credentials signed by JWT.
          </div>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
  };

  // Prepare chart dataset configurations
  const bpChartData = {
    labels: healthHistory.map(h => h.recorded_date).slice(-7),
    datasets: [
      {
        label: 'Systolic BP (mmHg)',
        data: healthHistory.map(h => h.blood_pressure_sys).slice(-7),
        borderColor: '#0284c7',
        backgroundColor: 'rgba(2, 132, 199, 0.1)',
        fill: true,
        tension: 0.3
      },
      {
        label: 'Diastolic BP (mmHg)',
        data: healthHistory.map(h => h.blood_pressure_dia).slice(-7),
        borderColor: '#0ea5e9',
        backgroundColor: 'rgba(14, 165, 233, 0.1)',
        fill: true,
        tension: 0.3
      }
    ]
  };

  const sugarChartData = {
    labels: healthHistory.map(h => h.recorded_date).slice(-7),
    datasets: [
      {
        label: 'Sugar Level (mg/dL)',
        data: healthHistory.map(h => h.sugar_level).slice(-7),
        borderColor: '#f43f5e',
        backgroundColor: 'rgba(244, 63, 94, 0.1)',
        fill: true,
        tension: 0.3
      }
    ]
  };

  const weightChartData = {
    labels: healthHistory.map(h => h.recorded_date).slice(-7),
    datasets: [
      {
        label: 'Weight Trend (kg)',
        data: healthHistory.map(h => h.weight).slice(-7),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.3
      }
    ]
  };

  // Rendering Helper: Active Dashboard View
  const renderPatientPortal = () => {
    switch (activeTab) {
      case 'dashboard':
        return (
          <div className="space-y-6">
            {/* Top Profile Card Summary */}
            {dashboardData && (
              <div id="patient-summary-report" className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Health Score Gauge */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-wider">Health Analytics</h3>
                    <div className="flex items-center space-x-4 mt-4">
                      <div className="relative w-24 h-24 flex items-center justify-center">
                        <svg className="w-full h-full transform -rotate-90">
                          <circle cx="48" cy="48" r="40" stroke="currentColor" className="text-slate-100 dark:text-slate-800" strokeWidth="8" fill="transparent" />
                          <circle cx="48" cy="48" r="40" stroke="currentColor" className="text-sky-500" strokeWidth="8" fill="transparent"
                            strokeDasharray={251.2}
                            strokeDashoffset={251.2 - (251.2 * dashboardData.health_analytics.health_score) / 100} />
                        </svg>
                        <span className="absolute text-2xl font-bold">{dashboardData.health_analytics.health_score}</span>
                      </div>
                      <div>
                        <div className="font-semibold text-slate-900 dark:text-slate-100">Overall Health Score</div>
                        <div className="text-sm text-slate-500">Based on recent vitals & habits</div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
                    <div className="text-sm font-medium mb-1">Clinical Insights:</div>
                    <ul className="text-xs text-slate-500 space-y-1">
                      {dashboardData.health_analytics.health_score_reasons.map((r, i) => (
                        <li key={i} className="flex items-start">
                          <span className="text-sky-500 mr-1.5">•</span>
                          <span>{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Patient Information Card */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 col-span-2 flex flex-col justify-between">
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="flex items-center space-x-2">
                        <h2 className="text-xl font-bold">{dashboardData.profile.name}</h2>
                        <span className="bg-sky-100 text-sky-800 text-xs font-semibold px-2 py-0.5 rounded-full dark:bg-sky-900/30 dark:text-sky-300">
                          Patient Portal
                        </span>
                      </div>
                      <p className="text-sm text-slate-500 mt-0.5">Secure Electronic Medical Record ID: #{dashboardData.profile.patient_id}</p>
                    </div>
                    <button onClick={downloadSummaryPDF} className="flex items-center space-x-1.5 text-xs font-semibold bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 px-3 py-1.5 rounded-lg transition">
                      <Download className="w-3.5 h-3.5" />
                      <span>Download PDF</span>
                    </button>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
                    <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl">
                      <span className="text-xs text-slate-400">Age / Gender</span>
                      <div className="font-semibold mt-0.5">{dashboardData.profile.age} Yrs / {dashboardData.profile.gender || 'M'}</div>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl">
                      <span className="text-xs text-slate-400">Blood Group</span>
                      <div className="font-semibold mt-0.5 text-sky-500">{dashboardData.profile.blood_group || 'O+'}</div>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl">
                      <span className="text-xs text-slate-400">Height / Weight</span>
                      <div className="font-semibold mt-0.5">{dashboardData.profile.height} cm / {dashboardData.profile.weight} kg</div>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-800/40 p-3 rounded-xl">
                      <span className="text-xs text-slate-400">Diseases & Allergies</span>
                      <div className="font-semibold mt-0.5 text-rose-500 truncate" title={dashboardData.profile.medical_history}>{dashboardData.profile.medical_history || 'None'}</div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Vitals Summary Row */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {dashboardData?.latest_vitals ? (
                <>
                  <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-slate-800 flex items-center space-x-3">
                    <div className="p-3 bg-sky-50 dark:bg-sky-950/30 rounded-xl text-sky-500">
                      <Activity className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Blood Pressure</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {dashboardData.latest_vitals.blood_pressure_sys}/{dashboardData.latest_vitals.blood_pressure_dia} <span className="text-[10px] font-normal text-slate-400">mmHg</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-slate-800 flex items-center space-x-3">
                    <div className="p-3 bg-red-50 dark:bg-red-950/30 rounded-xl text-red-500">
                      <Heart className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Sugar Level</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {dashboardData.latest_vitals.sugar_level} <span className="text-[10px] font-normal text-slate-400">mg/dL</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-slate-800 flex items-center space-x-3">
                    <div className="p-3 bg-amber-50 dark:bg-amber-950/30 rounded-xl text-amber-500">
                      <Droplet className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Cholesterol</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {dashboardData.latest_vitals.cholesterol} <span className="text-[10px] font-normal text-slate-400">mg/dL</span>
                      </div>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-slate-800 flex items-center space-x-3">
                    <div className="p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded-xl text-emerald-500">
                      <Thermometer className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Heart Rate / SpO2</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {dashboardData.latest_vitals.heart_rate} bpm / {dashboardData.latest_vitals.oxygen_level}%
                      </div>
                    </div>
                  </div>

                  <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 shadow-sm border border-slate-100 dark:border-slate-800 flex items-center space-x-3">
                    <div className="p-3 bg-indigo-50 dark:bg-indigo-950/30 rounded-xl text-indigo-500">
                      <Weight className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Water Intake</div>
                      <div className="font-bold text-slate-800 dark:text-slate-200">
                        {dashboardData.latest_vitals.water_intake} <span className="text-[10px] font-normal text-slate-400">mL</span>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div className="col-span-5 bg-sky-50 dark:bg-sky-950/20 p-4 rounded-xl text-center text-sm font-medium text-sky-800 dark:text-sky-300">
                  No health vital telemetry logged today. Log your metrics below to initialize tracking!
                </div>
              )}
            </div>

            {/* Health Logs Forms & Graphs Layout */}
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
              {/* Form to Log Vitals */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                <h3 className="text-lg font-bold mb-4 flex items-center space-x-2">
                  <PlusCircle className="w-5 h-5 text-sky-500" />
                  <span>Log Vitals Telemetry</span>
                </h3>
                <form onSubmit={handleLogVitals} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-400">Systolic BP (mmHg)</label>
                      <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2.5 mt-1"
                        value={vitalsForm.blood_pressure_sys} onChange={e => setVitalsForm({...vitalsForm, blood_pressure_sys: parseInt(e.target.value)})} />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400">Diastolic BP (mmHg)</label>
                      <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2.5 mt-1"
                        value={vitalsForm.blood_pressure_dia} onChange={e => setVitalsForm({...vitalsForm, blood_pressure_dia: parseInt(e.target.value)})} />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-400">Sugar Level (mg/dL)</label>
                      <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2.5 mt-1"
                        value={vitalsForm.sugar_level} onChange={e => setVitalsForm({...vitalsForm, sugar_level: parseInt(e.target.value)})} />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400">Cholesterol (mg/dL)</label>
                      <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2.5 mt-1"
                        value={vitalsForm.cholesterol} onChange={e => setVitalsForm({...vitalsForm, cholesterol: parseInt(e.target.value)})} />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-xs text-slate-400">Weight (kg)</label>
                      <input type="number" step="0.1" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2 mt-1"
                        value={vitalsForm.weight} onChange={e => setVitalsForm({...vitalsForm, weight: parseFloat(e.target.value)})} />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400">Height (cm)</label>
                      <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2 mt-1"
                        value={vitalsForm.height} onChange={e => setVitalsForm({...vitalsForm, height: parseFloat(e.target.value)})} />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400">Heart Rate</label>
                      <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2 mt-1"
                        value={vitalsForm.heart_rate} onChange={e => setVitalsForm({...vitalsForm, heart_rate: parseInt(e.target.value)})} />
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div>
                      <label className="text-xs text-slate-400">SpO2 (%)</label>
                      <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2 mt-1"
                        value={vitalsForm.oxygen_level} onChange={e => setVitalsForm({...vitalsForm, oxygen_level: parseInt(e.target.value)})} />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400">Temp (°C)</label>
                      <input type="number" step="0.1" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2 mt-1"
                        value={vitalsForm.temperature} onChange={e => setVitalsForm({...vitalsForm, temperature: parseFloat(e.target.value)})} />
                    </div>
                    <div>
                      <label className="text-xs text-slate-400">Water (mL)</label>
                      <input type="number" step="100" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2 mt-1"
                        value={vitalsForm.water_intake} onChange={e => setVitalsForm({...vitalsForm, water_intake: parseInt(e.target.value)})} />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs text-slate-400">Date recorded</label>
                    <input type="date" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-lg text-sm p-2.5 mt-1"
                      value={vitalsForm.recorded_date} onChange={e => setVitalsForm({...vitalsForm, recorded_date: e.target.value})} />
                  </div>

                  <button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white font-semibold py-2.5 rounded-xl transition text-sm">
                    Log Telemetry
                  </button>
                </form>
              </div>

              {/* Graphical trends */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 xl:col-span-2 space-y-6">
                <h3 className="text-lg font-bold flex items-center space-x-2">
                  <Activity className="w-5 h-5 text-sky-500" />
                  <span>Clinical Health Trends</span>
                </h3>

                {healthHistory.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-xl">
                      <h4 className="text-xs font-semibold text-slate-400 mb-3 text-center">Monthly Blood Pressure Graph (Sys / Dia)</h4>
                      <div className="h-44">
                        <Line data={bpChartData} options={{ responsive: true, maintainAspectRatio: false }} />
                      </div>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-xl">
                      <h4 className="text-xs font-semibold text-slate-400 mb-3 text-center">Sugar Level Analytics (mg/dL)</h4>
                      <div className="h-44">
                        <Line data={sugarChartData} options={{ responsive: true, maintainAspectRatio: false }} />
                      </div>
                    </div>
                    <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-xl md:col-span-2">
                      <h4 className="text-xs font-semibold text-slate-400 mb-3 text-center">Weight Tracking Graph (kg)</h4>
                      <div className="h-44">
                        <Line data={weightChartData} options={{ responsive: true, maintainAspectRatio: false }} />
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-64 flex items-center justify-center bg-slate-50 dark:bg-slate-800/40 rounded-xl">
                    <span className="text-slate-400 text-sm">Awaiting sufficient health telemetry data points to populate analytical curves.</span>
                  </div>
                )}
              </div>
            </div>

            {/* Medicine Reminder Drawer & Logs */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                <h3 className="text-lg font-bold mb-4 flex items-center space-x-2">
                  <Clock className="w-5 h-5 text-sky-500" />
                  <span>Pill & Medication Reminders</span>
                </h3>
                <form onSubmit={handleSetReminder} className="flex space-x-3 mb-6">
                  <input type="text" placeholder="Enter medicine name..." className="flex-1 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm px-4 py-2.5"
                    value={reminderForm.medicine_name} onChange={e => setReminderForm({...reminderForm, medicine_name: e.target.value})} required />
                  <input type="text" placeholder="Time (e.g. 08:00 AM)" className="w-36 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm px-4 py-2.5"
                    value={reminderForm.reminder_time} onChange={e => setReminderForm({...reminderForm, reminder_time: e.target.value})} required />
                  <button type="submit" className="bg-sky-500 hover:bg-sky-600 text-white font-semibold px-5 rounded-xl transition text-sm">
                    Add Reminder
                  </button>
                </form>

                {/* Hardcoded list of active reminders */}
                <div className="space-y-3">
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="p-2.5 bg-sky-100 dark:bg-sky-900/30 text-sky-500 rounded-lg">
                        <Clock className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-semibold text-sm">Metformin HCL</div>
                        <div className="text-xs text-slate-400">Scheduled: 08:00 AM (Twice daily)</div>
                      </div>
                    </div>
                    <span className="text-xs text-sky-500 font-semibold bg-sky-50 dark:bg-sky-900/20 px-2 py-1 rounded">Active</span>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                      <div className="p-2.5 bg-sky-100 dark:bg-sky-900/30 text-sky-500 rounded-lg">
                        <Clock className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="font-semibold text-sm">Lisinopril Tablet</div>
                        <div className="text-xs text-slate-400">Scheduled: 08:00 AM (Once daily)</div>
                      </div>
                    </div>
                    <span className="text-xs text-sky-500 font-semibold bg-sky-50 dark:bg-sky-900/20 px-2 py-1 rounded">Active</span>
                  </div>
                </div>
              </div>

              {/* Health Articles Section */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                <h3 className="text-lg font-bold mb-4 flex items-center space-x-2">
                  <Brain className="w-5 h-5 text-sky-500" />
                  <span>Clinical Advisor Articles</span>
                </h3>
                <div className="space-y-4">
                  <a href="#" className="block p-4 bg-slate-50 dark:bg-slate-800/30 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-xl transition">
                    <div className="text-sky-500 font-semibold text-sm">Managing Hypertension Through Lifestyle Modifications</div>
                    <p className="text-xs text-slate-400 mt-1">Discover foods that regulate arterial elasticity and lower blood pressure reading naturally.</p>
                  </a>
                  <a href="#" className="block p-4 bg-slate-50 dark:bg-slate-800/30 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-xl transition">
                    <div className="text-sky-500 font-semibold text-sm">Understanding Type-2 Diabetes Indices & A1C Testing</div>
                    <p className="text-xs text-slate-400 mt-1">A clinical review detailing the molecular pathway of insulin resistance and long-term diagnostic steps.</p>
                  </a>
                  <a href="#" className="block p-4 bg-slate-50 dark:bg-slate-800/30 hover:bg-slate-100 dark:hover:bg-slate-800/60 rounded-xl transition">
                    <div className="text-sky-500 font-semibold text-sm">Understanding Sleep Hygiene & Cardiovascular Health</div>
                    <p className="text-xs text-slate-400 mt-1">How nocturnal oxygenation levels and slow-wave sleep cycles support vascular tissue recovery.</p>
                  </a>
                </div>
              </div>
            </div>
          </div>
        );

      case 'profile':
        return (
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-xl font-bold">Editable Medical Profile</h3>
                  <p className="text-sm text-slate-400 mt-0.5">Update your health information. All changes are saved securely.</p>
                </div>
                {profileData?.updated_at && (
                  <span className="text-xs text-slate-400 bg-slate-50 dark:bg-slate-800 px-3 py-1.5 rounded-lg">
                    Last updated: {new Date(profileData.updated_at).toLocaleDateString()}
                  </span>
                )}
              </div>
              <form onSubmit={handleUpdateProfile} className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Age (years)</label>
                    <input type="number" min={1} max={120} className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3"
                      value={profileForm.age} onChange={e => setProfileForm({...profileForm, age: e.target.value})} />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Weight (kg)</label>
                    <input type="number" step="0.1" className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3"
                      value={profileForm.weight} onChange={e => setProfileForm({...profileForm, weight: e.target.value})} />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Height (cm)</label>
                    <input type="number" className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3"
                      value={profileForm.height} onChange={e => setProfileForm({...profileForm, height: e.target.value})} />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Gender</label>
                    <select className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3"
                      value={profileForm.gender} onChange={e => setProfileForm({...profileForm, gender: e.target.value})}>
                      <option value="">Select</option>
                      <option value="Male">Male</option>
                      <option value="Female">Female</option>
                      <option value="Other">Other</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Blood Group</label>
                    <select className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3"
                      value={profileForm.blood_group} onChange={e => setProfileForm({...profileForm, blood_group: e.target.value})}>
                      <option value="">Select</option>
                      {['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(g => <option key={g} value={g}>{g}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Emergency Contact</label>
                    <input type="text" placeholder="e.g. +91 98765 43210" className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3"
                      value={profileForm.emergency_contact} onChange={e => setProfileForm({...profileForm, emergency_contact: e.target.value})} />
                  </div>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Existing Diseases / Conditions</label>
                    <textarea rows={3} placeholder="e.g. Diabetes Type 2, Hypertension..." className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3 resize-none"
                      value={profileForm.medical_history} onChange={e => setProfileForm({...profileForm, medical_history: e.target.value})} />
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Known Allergies</label>
                    <textarea rows={3} placeholder="e.g. Penicillin, Sulfa drugs, Seafood..." className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3 resize-none"
                      value={profileForm.allergies} onChange={e => setProfileForm({...profileForm, allergies: e.target.value})} />
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-400 font-semibold uppercase block mb-1.5">Current Medications</label>
                  <textarea rows={2} placeholder="e.g. Metformin 500mg twice daily, Lisinopril 10mg once daily..." className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3 resize-none"
                    value={profileForm.medications} onChange={e => setProfileForm({...profileForm, medications: e.target.value})} />
                </div>
                {/* BMI Preview */}
                {profileForm.weight && profileForm.height && (
                  <div className="bg-sky-50 dark:bg-sky-950/20 border border-sky-100 dark:border-sky-900/30 p-4 rounded-xl flex items-center space-x-4">
                    <div className="text-3xl font-extrabold text-sky-500">
                      {(parseFloat(profileForm.weight)/((parseFloat(profileForm.height)/100)**2)).toFixed(1)}
                    </div>
                    <div>
                      <div className="font-semibold text-sm">Calculated BMI</div>
                      <div className="text-xs text-slate-400">Based on current height/weight values</div>
                    </div>
                  </div>
                )}
                <button type="submit" disabled={profileSaving} className="w-full bg-sky-500 hover:bg-sky-600 disabled:opacity-60 text-white font-bold py-3 rounded-xl transition flex items-center justify-center space-x-2">
                  <Check className="w-4 h-4"/><span>{profileSaving ? 'Saving...' : 'Save Medical Profile'}</span>
                </button>
              </form>
            </div>
          </div>
        );

      case 'chatbot':
        return (
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
            <Chatbot darkMode={darkMode} />
          </div>
        );

      case 'ocr':
        return (
          <div className="space-y-6">
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
              <h3 className="text-lg font-bold mb-2">Prescription & Clinical Report Scanners</h3>
              <p className="text-sm text-slate-400 mb-6">Upload clinical images or diagnostic documents. The CuraAI OCR model extracts medications, diagnoses, and summarizes critical health parameters.</p>
              
              <form onSubmit={handleUploadReport} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 border-2 border-dashed border-slate-200 dark:border-slate-700 hover:border-sky-400 dark:hover:border-sky-500 rounded-2xl p-8 flex flex-col items-center justify-center transition cursor-pointer relative bg-slate-50/50 dark:bg-slate-900/50">
                  <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={handleFileChange} />
                  <FileText className="w-12 h-12 text-slate-300 mb-3" />
                  <span className="text-sm font-semibold text-slate-500">
                    {uploadFile ? uploadFile.name : "Drag and drop or select file to upload"}
                  </span>
                  <span className="text-xs text-slate-400 mt-1">Supports PNG, JPG, PDF, TXT up to 10MB</span>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="text-xs text-slate-400">Document Classification</label>
                    <select className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm p-3 mt-1.5 focus:ring-1 focus:ring-sky-500"
                      value={uploadType} onChange={e => setUploadType(e.target.value)}>
                      <option value="blood_test">Blood Test Report</option>
                      <option value="x-ray">X-Ray Scan</option>
                      <option value="scan">Advanced MRI/CT Scan</option>
                      <option value="other">General Doctor Note</option>
                    </select>
                  </div>

                  <div className="flex items-center space-x-2 pt-2">
                    <input type="checkbox" id="is_pres" className="rounded text-sky-500"
                      checked={isPrescriptionUpload} onChange={e => setIsPrescriptionUpload(e.target.checked)} />
                    <label htmlFor="is_pres" className="text-sm font-semibold cursor-pointer">This is a medical prescription</label>
                  </div>

                  <button type="submit" disabled={loading} className="w-full bg-sky-500 hover:bg-sky-600 disabled:bg-sky-400 text-white font-semibold py-3 rounded-xl transition text-sm">
                    {loading ? "Processing OCR Scanner..." : "Scan & Summarize"}
                  </button>
                </div>
              </form>
            </div>

            {/* OCR Processing Result Modal / Box */}
            {ocrModalData && (
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 space-y-4 animate-glow">
                <div className="flex justify-between items-center border-bottom pb-4 border-slate-100 dark:border-slate-800">
                  <h4 className="font-bold text-lg flex items-center space-x-2 text-sky-500">
                    <Sparkles className="w-5 h-5" />
                    <span>OCR AI Extraction Results</span>
                  </h4>
                  <button onClick={() => setOcrModalData(null)} className="text-slate-400 hover:text-slate-200">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="md:col-span-2 space-y-4">
                    <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-xl">
                      <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-2">Clinical Findings Summary</div>
                      <div className="text-sm leading-relaxed whitespace-pre-line">{ocrModalData.summary || ocrModalData.extracted_data?.summary}</div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-xl">
                        <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Identified Diagnosis</div>
                        <div className="font-bold text-sky-500">{ocrModalData.extracted_diagnosis || ocrModalData.extracted_data?.diagnosis}</div>
                      </div>
                      <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-xl">
                        <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-1">Severity Category</div>
                        <div className="font-bold uppercase text-rose-500">{ocrModalData.severity_level || ocrModalData.extracted_data?.severity}</div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-xl space-y-4">
                    <div>
                      <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-2">Extracted Medicines</div>
                      <div className="bg-white dark:bg-slate-800 p-3 rounded-lg border border-slate-200 dark:border-slate-700 text-sm font-semibold">
                        {ocrModalData.extracted_data?.medicines || ocrModalData.extracted_diagnosis ? "Metformin, Lisinopril" : "None detected"}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400 font-semibold uppercase tracking-wider mb-2">Instructions / Dosage</div>
                      <div className="text-xs text-slate-500">
                        {ocrModalData.extracted_data?.dosage_instructions || "Take with meals under direct clinical supervision."}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* List of Previous Reports */}
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
              <h3 className="font-bold text-lg mb-4">Patient Document History</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-855 text-slate-400">
                      <th className="py-3 font-semibold">Document Name</th>
                      <th className="py-3 font-semibold">Category</th>
                      <th className="py-3 font-semibold">Diagnostic Summary</th>
                      <th className="py-3 font-semibold">Severity</th>
                      <th className="py-3 font-semibold">Processed Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboardData?.recent_reports?.map(report => (
                      <tr key={report.id} className="border-b border-slate-50 dark:border-slate-855 hover:bg-slate-50/50 dark:hover:bg-slate-850/50 transition">
                        <td className="py-3.5 font-semibold text-slate-700 dark:text-slate-200">{report.file_name}</td>
                        <td className="py-3.5 uppercase text-xs">{report.report_type.replace('_', ' ')}</td>
                        <td className="py-3.5 text-slate-400 truncate max-w-xs">{report.ai_summary}</td>
                        <td className="py-3.5">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                            report.severity_level === 'critical' ? 'bg-red-100 text-red-800 dark:bg-red-950/20 dark:text-red-300' :
                            report.severity_level === 'high' ? 'bg-orange-100 text-orange-800 dark:bg-orange-950/20 dark:text-orange-300' :
                            'bg-slate-100 text-slate-800 dark:bg-slate-850 dark:text-slate-300'
                          }`}>
                            {report.severity_level.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3.5 text-xs text-slate-400">{new Date(report.uploaded_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                    {(!dashboardData?.recent_reports || dashboardData.recent_reports.length === 0) && (
                      <tr>
                        <td colSpan="5" className="py-6 text-center text-slate-400 text-sm">No electronic reports uploaded.</td>
</tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      case 'symptom-analysis':
        return (
          <div className="space-y-6">
            {/* Input Panel */}
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold">AI Symptom Checker &amp; Diagnosis Support</h3>
                  <p className="text-sm text-slate-400 mt-0.5">Describe symptoms in your own words or use quick-select tags.</p>
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 rounded-xl p-1 space-x-1">
                  <button onClick={() => setSymptomMode('quick')} className={`text-xs font-semibold px-4 py-2 rounded-lg transition ${symptomMode==='quick'?'bg-sky-500 text-white shadow':'text-slate-500'}`}>Quick Tags</button>
                  <button onClick={() => setSymptomMode('custom')} className={`text-xs font-semibold px-4 py-2 rounded-lg transition ${symptomMode==='custom'?'bg-sky-500 text-white shadow':'text-slate-500'}`}>Custom / NLP</button>
                </div>
              </div>

              {symptomMode === 'quick' ? (
                <>
                  <div className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-2xl mb-4">
                    <label className="text-xs text-slate-400 font-semibold uppercase tracking-wider block mb-3">Quick Select Symptoms</label>
                    <div className="flex flex-wrap gap-2 max-h-40 overflow-y-auto p-1">
                      {symptomsCatalog.map(sym => (
                        <button key={sym} type="button"
                          onClick={() => selectedSymptoms.includes(sym) ? handleRemoveSymptom(sym) : handleAddSymptom(sym)}
                          className={`text-xs px-3 py-1.5 rounded-full font-medium transition ${selectedSymptoms.includes(sym)?'bg-sky-500 text-white':'bg-white hover:bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-600'}`}>
                          {sym.replace(/_/g,' ')}
                        </button>
                      ))}
                    </div>
                  </div>
                  {selectedSymptoms.length > 0 && (
                    <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
                      <span className="text-xs text-slate-400 font-semibold">Selected:</span>
                      {selectedSymptoms.map(sym => (
                        <span key={sym} className="inline-flex items-center space-x-1 text-xs bg-sky-50 dark:bg-sky-950/20 text-sky-600 px-2.5 py-1 rounded-lg font-medium border border-sky-100">
                          <span>{sym.replace(/_/g,' ')}</span>
                          <button onClick={() => handleRemoveSymptom(sym)} className="font-bold hover:text-sky-800">×</button>
                        </span>
                      ))}
                      <button onClick={runSymptomAnalysis} disabled={loading} className="ml-auto bg-sky-500 hover:bg-sky-600 disabled:opacity-60 text-white font-semibold px-5 py-2 rounded-xl text-xs flex items-center space-x-1.5 transition">
                        <Sparkles className="w-3.5 h-3.5"/><span>{loading?'Analyzing...':'Run AI Diagnostics'}</span>
                      </button>
                    </div>
                  )}
                </>
              ) : (
                <div className="space-y-4">
                  <textarea rows={4} placeholder={'Describe your symptoms:\n• "Sharp chest pain while climbing stairs"\n• "Frequent dizziness and blurry vision"\n• "Skin rash after eating seafood"'}
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-4 resize-none focus:ring-2 focus:ring-sky-500 outline-none"
                    value={customSymptomText} onChange={e => setCustomSymptomText(e.target.value)} />
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-slate-400 font-semibold uppercase block mb-2">Pain Severity</label>
                      <div className="flex space-x-1">
                        {['mild','moderate','severe','emergency'].map(s => (
                          <button key={s} type="button" onClick={() => setSymptomSeverity(s)}
                            className={`flex-1 text-[10px] font-bold py-2 rounded-lg capitalize transition ${symptomSeverity===s?(s==='emergency'?'bg-red-500 text-white':s==='severe'?'bg-orange-400 text-white':s==='moderate'?'bg-amber-400 text-white':'bg-emerald-500 text-white'):'bg-slate-100 dark:bg-slate-800 text-slate-500'}`}>
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-xs text-slate-400 font-semibold uppercase block mb-2">Duration (days)</label>
                      <input type="number" min={0} max={365} placeholder="e.g. 3"
                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm p-3"
                        value={symptomDuration} onChange={e => setSymptomDuration(parseInt(e.target.value)||0)} />
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-slate-400 font-semibold uppercase block mb-2">Also Tag Symptoms</label>
                    <div className="flex flex-wrap gap-1.5">
                      {['fever','headache','fatigue','chest_pain','dizziness','nausea','joint_pain','shortness_of_breath'].map(sym => (
                        <button key={sym} type="button" onClick={() => selectedSymptoms.includes(sym)?handleRemoveSymptom(sym):handleAddSymptom(sym)}
                          className={`text-[10px] px-2.5 py-1 rounded-full font-medium transition ${selectedSymptoms.includes(sym)?'bg-sky-500 text-white':'bg-slate-100 dark:bg-slate-700 text-slate-600'}`}>
                          {sym.replace(/_/g,' ')}
                        </button>
                      ))}
                    </div>
                  </div>
                  <button onClick={runCustomAnalysis} disabled={loading}
                    className="w-full bg-sky-500 hover:bg-sky-600 disabled:opacity-60 text-white font-semibold py-3 rounded-xl text-sm flex items-center justify-center space-x-2 transition">
                    <Brain className="w-4 h-4"/><span>{loading?'Processing NLP Analysis...':'Analyze Symptoms with AI'}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Urgency Badge */}
            {customResult?.urgency && (
              <div className={`rounded-2xl p-5 border-2 flex items-center space-x-5 ${customResult.urgency.level==='Emergency'?'bg-red-50 border-red-300 dark:bg-red-950/20 dark:border-red-700':customResult.urgency.level==='Severe'?'bg-orange-50 border-orange-300 dark:bg-orange-950/20 dark:border-orange-700':customResult.urgency.level==='Moderate'?'bg-amber-50 border-amber-200 dark:bg-amber-950/20':'bg-emerald-50 border-emerald-200 dark:bg-emerald-950/20'}`}>
                <div className="text-4xl">{customResult.urgency.icon}</div>
                <div className="flex-1">
                  <div className={`text-sm font-extrabold uppercase tracking-wider ${customResult.urgency.level==='Emergency'?'text-red-600':customResult.urgency.level==='Severe'?'text-orange-600':customResult.urgency.level==='Moderate'?'text-amber-600':'text-emerald-600'}`}>
                    {customResult.urgency.level} Urgency — {customResult.parsed_symptoms?.length||0} symptom signals detected
                  </div>
                  <div className="text-sm text-slate-600 dark:text-slate-300 mt-0.5">{customResult.urgency.advice}</div>
                  {customResult.parsed_symptoms?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {customResult.parsed_symptoms.map(s => <span key={s} className="text-[10px] bg-white dark:bg-slate-800 border border-slate-200 px-2 py-0.5 rounded font-medium">{s.replace(/_/g,' ')}</span>)}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* AI Doctor Recommendation Cards */}
            {customResult?.recommended_doctors?.length > 0 && (
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="p-2 bg-sky-100 dark:bg-sky-900/30 rounded-lg text-sky-500"><Users className="w-4 h-4"/></div>
                  <div className="flex-1">
                    <h4 className="font-bold">AI-Recommended Specialist</h4>
                    <p className="text-xs text-slate-400">{customResult.recommended_specialization?.reason}</p>
                  </div>
                  <span className="text-xs font-bold bg-sky-100 text-sky-700 dark:bg-sky-900/20 dark:text-sky-300 px-3 py-1.5 rounded-full">{customResult.recommended_specialization?.specialization}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {customResult.recommended_doctors.map(doc => (
                    <div key={doc.id} className="bg-slate-50 dark:bg-slate-800/50 p-4 rounded-xl border border-slate-100 dark:border-slate-700">
                      <div className="flex justify-between items-start mb-2">
                        <div><div className="font-bold text-sm">{doc.name}</div><div className="text-xs text-sky-500">{doc.specialization}</div></div>
                        <span className="text-xs font-bold text-amber-500">★ {doc.ratings}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 space-y-0.5">
                        <div>{doc.experience} yrs · ₹{doc.consultation_fees}</div>
                        <div className="truncate">{doc.availability}</div>
                      </div>
                      <button onClick={() => { setAppointmentForm(f => ({...f, doctor_id: doc.id})); setActiveTab('doctor-connect'); showToast(`${doc.name} pre-selected for booking.`, 'success'); }}
                        className="mt-3 w-full bg-sky-500 hover:bg-sky-600 text-white text-xs font-semibold py-2 rounded-lg transition">
                        Book Consultation
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Prediction Details Panel */}
            {activePredDetails && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 flex flex-col justify-between">
                  <div>
                    <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded ${activePredDetails.severity==='critical'?'bg-red-100 text-red-800':activePredDetails.severity==='high'?'bg-orange-100 text-orange-700':'bg-sky-100 text-sky-800'}`}>
                      {activePredDetails.severity.toUpperCase()} SEVERITY
                    </span>
                    <h3 className="text-2xl font-bold mt-2 text-slate-800 dark:text-slate-100">{activePredDetails.disease}</h3>
                    <div className="flex items-center mt-1 text-sky-500 text-sm font-semibold">
                      <Sparkles className="w-4 h-4 mr-1" />
                      <span>{activePredDetails.confidence}% Neural Confidence Match</span>
                    </div>

                    <p className="text-xs text-slate-500 mt-4 leading-relaxed">
                      This diagnostic simulation checks primary symptom matrices. General classification matches Category: <strong className="capitalize">{activePredDetails.category}</strong>.
                    </p>
                  </div>

                  <div className="border-t border-slate-100 dark:border-slate-800 pt-4 mt-6">
                    <div className="text-xs text-slate-400 font-semibold mb-2">FIRST ACTION ADVICE</div>
                    <div className="text-xs text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-800/40 p-3 rounded-lg border border-slate-100 dark:border-slate-750">
                      {activePredDetails.next_actions}
                    </div>
                  </div>
                </div>

                {/* Drug Recommender Panel */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                  <h4 className="font-bold text-sm text-slate-400 uppercase tracking-wider mb-4 flex items-center space-x-1.5">
                    <Brain className="w-4 h-4 text-sky-500" />
                    <span>AI Drug Recommendation</span>
                  </h4>

                  {activePredDetails.drugs ? (
                    <div className="space-y-4 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Suggested First-Line Therapies</div>
                        <div className="mt-1 space-y-2">
                          {activePredDetails.drugs.medicines?.map((m, idx) => (
                            <div key={idx} className="bg-sky-50/50 dark:bg-sky-950/20 p-2.5 rounded-lg border border-sky-100/30">
                              <span className="font-bold text-sky-500">{m.name}</span> - <span className="font-medium">{m.dosage}</span>
                              <div className="text-[10px] text-slate-400 mt-0.5">{m.timing}</div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Generics</div>
                          <div className="text-slate-500 mt-0.5">{activePredDetails.drugs.generic_medicines}</div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Alternatives</div>
                          <div className="text-slate-500 mt-0.5">{activePredDetails.drugs.alternatives}</div>
                        </div>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Potential Side Effects</div>
                        <div className="text-slate-500 mt-0.5">{activePredDetails.drugs.side_effects}</div>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Diet & Food Restrictions</div>
                        <div className="text-slate-500 mt-0.5">{activePredDetails.drugs.food_restrictions}</div>
                      </div>

                      {activePredDetails.drugs.emergency_warnings && (
                        <div className="bg-rose-50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/30 p-3 rounded-lg text-rose-600 dark:text-rose-400 text-[10px]">
                          <strong>CRITICAL WARNING:</strong> {activePredDetails.drugs.emergency_warnings}
                        </div>
                      )}
                      <div className="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 p-2.5 rounded-lg text-amber-700 dark:text-amber-400 text-[10px]">
                        ⚕ <strong>Disclaimer:</strong> This recommendation is AI-generated and should be verified by a licensed doctor before use.
                      </div>
                    </div>
                  ) : (
                    <span className="text-xs text-slate-400">Loading recommendations...</span>
                  )}
                </div>

                {/* Health Advisor Recommendations */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                  <h4 className="font-bold text-sm text-slate-400 uppercase tracking-wider mb-4 flex items-center space-x-1.5">
                    <Sparkles className="w-4 h-4 text-sky-500" />
                    <span>Personalized Health Advisor</span>
                  </h4>

                  {activePredDetails.habits ? (
                    <div className="space-y-4 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Daily Health Habits</div>
                        <ul className="list-disc pl-4 mt-1 text-slate-500 space-y-1">
                          {activePredDetails.habits.daily_habits.slice(0, 3).map((h, i) => <li key={i}>{h}</li>)}
                        </ul>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Exercise Plan</div>
                        <ul className="list-disc pl-4 mt-1 text-slate-500 space-y-1">
                          {activePredDetails.habits.exercise.slice(0, 3).map((e, i) => <li key={i}>{e}</li>)}
                        </ul>
                      </div>

                      <div>
                        <div className="text-[10px] text-slate-400 font-semibold uppercase tracking-wider">Foods to Avoid / Consume</div>
                        <div className="mt-1 grid grid-cols-2 gap-2 text-[10px]">
                          <div className="bg-red-50/50 dark:bg-red-950/10 p-2 rounded-lg">
                            <span className="font-bold text-rose-500 block mb-0.5">Restrict:</span>
                            {activePredDetails.habits.lifestyle_plan.foods_to_avoid.slice(0, 2).join(", ")}
                          </div>
                          <div className="bg-emerald-50/50 dark:bg-emerald-950/10 p-2 rounded-lg">
                            <span className="font-bold text-emerald-500 block mb-0.5">Consume:</span>
                            {activePredDetails.habits.lifestyle_plan.foods_to_consume.slice(0, 2).join(", ")}
                          </div>
                        </div>
                      </div>

                      <div className="flex justify-between items-center bg-slate-50 dark:bg-slate-800 p-2.5 rounded-xl border border-slate-100 dark:border-slate-750">
                        <div>
                          <span className="text-[10px] text-slate-400 font-semibold uppercase block">Water Intake Target</span>
                          <span className="font-bold text-sky-500">{activePredDetails.habits.water_target_ml} mL</span>
                        </div>
                        <Droplet className="w-6 h-6 text-sky-500" />
                      </div>
                    </div>
                  ) : (
                    <span className="text-xs text-slate-400">Loading daily goals...</span>
                  )}
                </div>
              </div>
            )}
          </div>
        );

      case 'doctor-connect':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Doctor Directory */}
              <div className="lg:col-span-2 space-y-4">
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                  <h3 className="font-bold text-lg mb-2">Connect with Specialized Doctors</h3>
                  <p className="text-sm text-slate-400 mb-6">Book appointments or open messages with our verified consultants.</p>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {doctors.map(doc => (
                      <div key={doc.id} className="bg-slate-50 dark:bg-slate-800/40 p-4 rounded-xl border border-slate-100 dark:border-slate-750 flex flex-col justify-between">
                        <div>
                          <div className="flex items-start justify-between">
                            <div>
                              <h4 className="font-bold text-base">{doc.name}</h4>
                              <span className="text-xs text-sky-500 font-medium">{doc.specialization}</span>
                            </div>
                            <span className="bg-sky-50 dark:bg-sky-950/30 text-sky-600 dark:text-sky-400 text-xs px-2 py-0.5 rounded font-bold">★ {doc.ratings}</span>
                          </div>

                          <div className="grid grid-cols-2 gap-2 mt-4 text-xs text-slate-400">
                            <div>
                              <span>Experience</span>
                              <div className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5">{doc.experience} Years</div>
                            </div>
                            <div>
                              <span>Consultation Fee</span>
                              <div className="font-semibold text-slate-700 dark:text-slate-200 mt-0.5">₹{doc.consultation_fees}</div>
                            </div>
                          </div>

                          <div className="text-[10px] text-slate-400 mt-3 pt-3 border-t border-slate-200/50 dark:border-slate-700/50">
                            Availability: {doc.availability}
                          </div>
                        </div>

                        <div className="flex space-x-2 mt-4">
                          <button onClick={() => {
                            setAppointmentForm({...appointmentForm, doctor_id: doc.id});
                            showToast(`Selected ${doc.name} for booking!`, "success");
                          }} className="flex-1 bg-sky-500 hover:bg-sky-600 text-white font-semibold py-2 rounded-lg transition text-xs">
                            Select Slot
                          </button>
                          <button onClick={() => selectChatDoctor(doc)} className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-850 dark:hover:bg-slate-750 p-2 rounded-lg transition text-slate-600 dark:text-slate-300">
                            <MessageSquare className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Booking & Chat Sidebar */}
              <div className="space-y-6">
                {/* Book Appointment Form */}
                <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
                  <h3 className="font-bold text-base mb-4 flex items-center space-x-2">
                    <Calendar className="w-5 h-5 text-sky-500" />
                    <span>Book Clinical Consultation</span>
                  </h3>
                  <form onSubmit={handleBookAppointment} className="space-y-4">
                    <div>
                      <label className="text-xs text-slate-400">Select Doctor</label>
                      <select className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm p-3 mt-1.5 focus:ring-1 focus:ring-sky-500"
                        value={appointmentForm.doctor_id} onChange={e => setAppointmentForm({...appointmentForm, doctor_id: e.target.value})} required>
                        <option value="">-- Choose Specialist --</option>
                        {doctors.map(doc => (
                          <option key={doc.id} value={doc.id}>{doc.name} ({doc.specialization})</option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-xs text-slate-400">Appointment Date</label>
                      <input type="date" className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm p-3 mt-1.5 focus:ring-1 focus:ring-sky-500"
                        value={appointmentForm.appointment_date} onChange={e => setAppointmentForm({...appointmentForm, appointment_date: e.target.value})} required />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-xs text-slate-400">Time Slot</label>
                        <select className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm p-3 mt-1.5 focus:ring-1 focus:ring-sky-500"
                          value={appointmentForm.appointment_time} onChange={e => setAppointmentForm({...appointmentForm, appointment_time: e.target.value})}>
                          <option value="09:00 AM">09:00 AM</option>
                          <option value="10:00 AM">10:00 AM</option>
                          <option value="11:00 AM">11:00 AM</option>
                          <option value="02:00 PM">02:00 PM</option>
                          <option value="03:00 PM">03:00 PM</option>
                        </select>
                      </div>
                      <div>
                        <label className="text-xs text-slate-400">Consultation</label>
                        <select className="w-full bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm p-3 mt-1.5 focus:ring-1 focus:ring-sky-500"
                          value={appointmentForm.consultation_type} onChange={e => setAppointmentForm({...appointmentForm, consultation_type: e.target.value})}>
                          <option value="video">Video Call</option>
                          <option value="in-person">In-Person</option>
                        </select>
                      </div>
                    </div>

                    <button type="submit" className="w-full bg-sky-500 hover:bg-sky-600 text-white font-semibold py-3 rounded-xl transition text-sm">
                      Confirm Appointment
                    </button>
                  </form>
                </div>
              </div>
            </div>

            {/* Chat Messages Log */}
            {activeChatDoctor && (
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 space-y-4">
                <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3">
                  <div>
                    <h4 className="font-bold text-base">{activeChatDoctor.name}</h4>
                    <span className="text-xs text-sky-500">{activeChatDoctor.specialization} Consulting Session</span>
                  </div>
                  <button onClick={() => setActiveChatDoctor(null)} className="text-slate-400 hover:text-slate-200">
                    <X className="w-5 h-5" />
                  </button>
                </div>

                <div className="h-64 overflow-y-auto bg-slate-50 dark:bg-slate-850 p-4 rounded-xl space-y-3">
                  {chatMessages.map(msg => (
                    <div key={msg.id} className={`flex ${msg.sender_id === activeChatDoctor.user_id ? 'justify-start' : 'justify-end'}`}>
                      <div className={`p-3 rounded-2xl max-w-sm text-xs leading-relaxed ${
                        msg.sender_id === activeChatDoctor.user_id 
                          ? 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-tl-none' 
                          : 'bg-sky-500 text-white rounded-tr-none'
                      }`}>
                        {msg.message}
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>

                <form onSubmit={handleSendMessage} className="flex space-x-3">
                  <input type="text" placeholder="Type medical query..." className="flex-1 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm px-4"
                    value={newMessage} onChange={e => setNewMessage(e.target.value)} />
                  <button type="submit" className="bg-sky-500 hover:bg-sky-600 text-white p-3 rounded-xl transition">
                    <Send className="w-4 h-4" />
                  </button>
                </form>
              </div>
            )}

            {/* Appointments List */}
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
              <h3 className="font-bold text-base mb-4">Booked Sessions Audit</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-slate-855 text-slate-400">
                      <th className="py-2.5 font-semibold">Doctor Name</th>
                      <th className="py-2.5 font-semibold">Specialization</th>
                      <th className="py-2.5 font-semibold">Consultation Date</th>
                      <th className="py-2.5 font-semibold">Slot Time</th>
                      <th className="py-2.5 font-semibold">Format</th>
                      <th className="py-2.5 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {appointments.map(appt => (
                      <tr key={appt.id} className="border-b border-slate-50 dark:border-slate-855">
                        <td className="py-3 font-semibold">{appt.doctor_name}</td>
                        <td className="py-3 text-slate-400">{appt.doctor_specialization}</td>
                        <td className="py-3 text-xs">{appt.appointment_date}</td>
                        <td className="py-3 text-xs">{appt.appointment_time}</td>
                        <td className="py-3 uppercase text-xs text-sky-500 font-semibold">{appt.consultation_type}</td>
                        <td className="py-3">
                          <span className="text-[10px] font-semibold uppercase px-2 py-0.5 bg-emerald-100 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300 rounded">
                            {appt.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {appointments.length === 0 && (
                      <tr>
                        <td colSpan="6" className="py-6 text-center text-slate-400 text-sm">No booked consult slots scheduled.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const renderDoctorPortal = () => {
    return (
      <div className="space-y-6">
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
          <h2 className="text-xl font-bold">Doctor Consult Center</h2>
          <p className="text-sm text-slate-400 mt-1">Review scheduled appointments, patients vitals history and message clients securely.</p>
        </div>

        {/* Appointments List */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
          <h3 className="font-bold text-base mb-4">Patient Appointments Directory</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-855 text-slate-400">
                  <th className="py-2.5 font-semibold">Patient Name</th>
                  <th className="py-2.5 font-semibold">Age / Gender</th>
                  <th className="py-2.5 font-semibold">Consultation Date</th>
                  <th className="py-2.5 font-semibold">Slot Time</th>
                  <th className="py-2.5 font-semibold">Format</th>
                  <th className="py-2.5 font-semibold">Fee</th>
                  <th className="py-2.5 font-semibold">Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map(appt => (
                  <tr key={appt.id} className="border-b border-slate-50 dark:border-slate-855">
                    <td className="py-3 font-semibold">{appt.patient_name || "John Doe"}</td>
                    <td className="py-3 text-slate-400">{appt.patient_age} Yrs / {appt.patient_gender}</td>
                    <td className="py-3 text-xs">{appt.appointment_date}</td>
                    <td className="py-3 text-xs">{appt.appointment_time}</td>
                    <td className="py-3 uppercase text-xs text-sky-500 font-semibold">{appt.consultation_type}</td>
                    <td className="py-3 font-bold">₹{appt.fees}</td>
                    <td className="py-3">
                      <button onClick={() => {
                        const fakePatient = { user_id: appt.patient_id, name: appt.patient_name };
                        selectChatDoctor(fakePatient);
                      }} className="bg-sky-50 text-sky-600 dark:bg-sky-950/20 dark:text-sky-400 text-xs px-2.5 py-1 rounded font-semibold transition hover:bg-sky-100">
                        Open Chat
                      </button>
                    </td>
                  </tr>
                ))}
                {appointments.length === 0 && (
                  <tr>
                    <td colSpan="7" className="py-6 text-center text-slate-400 text-sm">No scheduled patient appointments.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Live Chat drawer for doctor */}
        {activeChatDoctor && (
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 space-y-4">
            <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-800 pb-3">
              <div>
                <h4 className="font-bold text-base">Chat Session with {activeChatDoctor.name}</h4>
                <span className="text-xs text-sky-500">Secure Direct Messaging</span>
              </div>
              <button onClick={() => setActiveChatDoctor(null)} className="text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="h-64 overflow-y-auto bg-slate-50 dark:bg-slate-850 p-4 rounded-xl space-y-3">
              {chatMessages.map(msg => (
                <div key={msg.id} className={`flex ${msg.sender_id === activeChatDoctor.user_id ? 'justify-start' : 'justify-end'}`}>
                  <div className={`p-3 rounded-2xl max-w-sm text-xs leading-relaxed ${
                    msg.sender_id === activeChatDoctor.user_id 
                      ? 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 rounded-tl-none' 
                      : 'bg-sky-500 text-white rounded-tr-none'
                  }`}>
                    {msg.message}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            <form onSubmit={handleSendMessage} className="flex space-x-3">
              <input type="text" placeholder="Type reply to patient..." className="flex-1 bg-slate-50 dark:bg-slate-800 border-none rounded-xl text-sm px-4"
                value={newMessage} onChange={e => setNewMessage(e.target.value)} />
              <button type="submit" className="bg-sky-500 hover:bg-sky-600 text-white p-3 rounded-xl transition">
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}
      </div>
    );
  };

  const renderAdminPortal = () => {
    if (!adminData) return <div className="text-center py-10">Fetching system metrics...</div>;
    
    // Bar chart configs for disease diagnostic analytics
    const barChartData = {
      labels: adminData.disease_analytics?.map(d => d.disease) || ["Diabetes Type 2", "Hypertension", "Dermatitis", "Migraine", "Anemia"],
      datasets: [
        {
          label: 'Total Diagnostic Predictions Logs',
          data: adminData.disease_analytics?.map(d => d.count) || [10, 8, 4, 3, 2],
          backgroundColor: 'rgba(14, 165, 233, 0.7)',
          borderRadius: 8
        }
      ]
    };

    return (
      <div className="space-y-6">
        {/* Metric Grid Overview */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Total Accounts</span>
            <div className="text-3xl font-extrabold text-slate-800 dark:text-slate-100 mt-1">{adminData.stats.total_users}</div>
          </div>
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Specialist Doctors</span>
            <div className="text-3xl font-extrabold text-slate-800 dark:text-slate-100 mt-1">{adminData.stats.doctors}</div>
          </div>
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Processed Reports</span>
            <div className="text-3xl font-extrabold text-sky-500 mt-1">{adminData.stats.reports}</div>
          </div>
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-5 shadow-sm border border-slate-100 dark:border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Appointments Set</span>
            <div className="text-3xl font-extrabold text-emerald-500 mt-1">{adminData.stats.appointments}</div>
          </div>
        </div>

        {/* Disease Analytics Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800 lg:col-span-2">
            <h3 className="font-bold text-base mb-4">Top Diagnosed Conditions (AI Engine Stats)</h3>
            <div className="h-64">
              <Bar data={barChartData} options={{ responsive: true, maintainAspectRatio: false }} />
            </div>
          </div>

          {/* System logs */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
            <h3 className="font-bold text-base mb-4">System Service Event Logs</h3>
            <div className="space-y-3 font-mono text-[10px] max-h-64 overflow-y-auto">
              {adminData.system_logs?.map((l, i) => (
                <div key={i} className="border-b border-slate-50 dark:border-slate-855 pb-2">
                  <span className="text-slate-400">[{l.timestamp}]</span>
                  <p className="text-slate-700 dark:text-slate-300 mt-0.5">{l.event}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Twilio notifications logs */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-100 dark:border-slate-800">
          <h3 className="font-bold text-base mb-4">Twilio SMS Gateway Delivery Log</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 dark:border-slate-855 text-slate-400">
                  <th className="py-2 font-semibold">Receiver Phone</th>
                  <th className="py-2 font-semibold">Trigger reason</th>
                  <th className="py-2 font-semibold">SMS Message Body</th>
                  <th className="py-2 font-semibold">Dispatch status</th>
                  <th className="py-2 font-semibold">Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {adminData.notifications?.map(n => (
                  <tr key={n.id} className="border-b border-slate-50 dark:border-slate-855">
                    <td className="py-2.5 font-semibold">{n.mobile_number}</td>
                    <td className="py-2.5 text-sky-500 font-semibold">{n.trigger_reason}</td>
                    <td className="py-2.5 text-slate-500 truncate max-w-xs">{n.message}</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded font-bold text-[9px] bg-emerald-100 text-emerald-800 dark:bg-emerald-950/20 dark:text-emerald-300">
                        {n.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-2.5 text-slate-400">{new Date(n.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // Rendering Helper: Global Auth View
  const renderAuthLayout = () => {
    switch (authMode) {
      case 'landing':
        return (
          <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
            {/* Header / Navbar */}
            <header className="sticky top-0 z-40 bg-white/80 dark:bg-slate-900/80 backdrop-filter backdrop-blur-lg border-b border-slate-100 dark:border-slate-800">
              <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <div className="w-9 h-9 bg-sky-500 rounded-xl flex items-center justify-center text-white">
                    <Heart className="w-5 h-5 fill-white" />
                  </div>
                  <span className="text-xl font-bold tracking-tight">Cura<span className="text-sky-500">AI</span></span>
                </div>

                <div className="flex items-center space-x-4">
                  <button onClick={toggleDarkMode} className="p-2 text-slate-400 hover:text-slate-600 rounded-lg">
                    {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                  </button>
                  <button onClick={() => setAuthMode('login')} className="text-sm font-semibold hover:text-sky-500 transition">Login</button>
                  <button onClick={() => setAuthMode('register')} className="bg-sky-500 hover:bg-sky-600 text-white px-4 py-2 rounded-xl text-sm font-semibold transition">
                    Register
                  </button>
                </div>
              </div>
            </header>

            {/* Hero Section */}
            <section className="max-w-7xl mx-auto px-6 py-20 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div className="space-y-6">
                <span className="bg-sky-100 text-sky-850 dark:bg-sky-950/30 dark:text-sky-400 text-xs font-semibold px-3 py-1 rounded-full uppercase tracking-wider">
                  Next-Gen Clinical Decision Support
                </span>
                <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight leading-tight">
                  Modern healthcare <br />
                  <span className="text-sky-500">empowered by Artificial Intelligence</span>
                </h1>
                <p className="text-base text-slate-450 leading-relaxed max-w-xl">
                  Maintain secure digital health records, run automated symptom checking diagnostics using random forest models, extract medication plans via OCR, and connect with clinical experts instantly.
                </p>

                <div className="flex space-x-4">
                  <button onClick={() => setAuthMode('register')} className="bg-sky-500 hover:bg-sky-600 text-white font-semibold px-8 py-3.5 rounded-xl transition text-sm shadow-md">
                    Get Started Now
                  </button>
                  <button onClick={() => setAuthMode('login')} className="bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-200 font-semibold px-8 py-3.5 rounded-xl transition text-sm">
                    Access Portal
                  </button>
                </div>
              </div>

              {/* Graphic Illustration Cards */}
              <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 border border-slate-100 dark:border-slate-800 shadow-xl space-y-6 animate-glow">
                <div className="flex justify-between items-center">
                  <h3 className="font-bold text-lg flex items-center space-x-2">
                    <Activity className="w-5 h-5 text-sky-500" />
                    <span>CuraAI Predictor Sandbox</span>
                  </h3>
                  <span className="text-xs text-slate-400">Clinical Demo</span>
                </div>

                <div className="bg-slate-50 dark:bg-slate-850 p-4 rounded-2xl space-y-3">
                  <div className="text-xs text-slate-400">Simulate Symptoms:</div>
                  <div className="flex flex-wrap gap-1.5">
                    <span className="text-[10px] bg-sky-100 text-sky-800 dark:bg-sky-950/20 px-2 py-0.5 rounded font-semibold">polyuria</span>
                    <span className="text-[10px] bg-sky-100 text-sky-800 dark:bg-sky-950/20 px-2 py-0.5 rounded font-semibold">polydipsia</span>
                    <span className="text-[10px] bg-sky-100 text-sky-800 dark:bg-sky-950/20 px-2 py-0.5 rounded font-semibold">fatigue</span>
                  </div>
                </div>

                <div className="bg-sky-500 text-white p-4 rounded-2xl space-y-2">
                  <div className="flex justify-between text-xs font-semibold">
                    <span>AI Predicted Pathology:</span>
                    <span>94.8% Confidence</span>
                  </div>
                  <div className="text-lg font-bold">Diabetes Type 2 Risk</div>
                  <div className="text-[10px] leading-relaxed text-sky-100">
                    Precautionary Action: Focus on complex fiber-rich low glycemic index foods. Check HbA1c metrics with a Diabetologist.
                  </div>
                </div>
              </div>
            </section>

            {/* Features section */}
            <section className="bg-white dark:bg-slate-900 border-t border-slate-150 dark:border-slate-800 py-16">
              <div className="max-w-7xl mx-auto px-6">
                <h2 className="text-2xl font-extrabold text-center mb-12">Core Platform Capabilities</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                  <div className="space-y-3 p-4 rounded-2xl hover:bg-slate-50 dark:hover:bg-slate-850/50 transition">
                    <div className="p-3 bg-sky-100 dark:bg-sky-900/30 text-sky-500 w-fit rounded-xl">
                      <Brain className="w-6 h-6" />
                    </div>
                    <h3 className="font-bold text-lg">AI Symptom Classifier</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Diagnose common, chronic, rare, lifestyle, or genetic diseases instantly using our pre-trained random forest model vectors.
                    </p>
                  </div>
                  <div className="space-y-3 p-4 rounded-2xl hover:bg-slate-50 dark:hover:bg-slate-850/50 transition">
                    <div className="p-3 bg-indigo-100 dark:bg-indigo-900/30 text-indigo-500 w-fit rounded-xl">
                      <FileText className="w-6 h-6" />
                    </div>
                    <h3 className="font-bold text-lg">Prescription OCR Scanner</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Upload physician handwritten scripts or reports. Extracted diagnostics, medications, and details sync directly to your health timeline.
                    </p>
                  </div>
                  <div className="space-y-3 p-4 rounded-2xl hover:bg-slate-50 dark:hover:bg-slate-850/50 transition">
                    <div className="p-3 bg-rose-100 dark:bg-rose-900/30 text-rose-500 w-fit rounded-xl">
                      <Phone className="w-6 h-6" />
                    </div>
                    <h3 className="font-bold text-lg">Twilio Alert Gateway</h3>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Critical abnormalities in vital logging, severe pathology reports, or emergency SOS requests trigger instant SMS warnings to registered numbers.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        );

      case 'login':
      case 'register':
      case 'forgot':
        return (
          <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center p-6 relative">
            {/* SOS Pulsing background graphic */}
            <div className="absolute w-[500px] h-[500px] bg-sky-400/5 dark:bg-sky-550/5 blur-3xl rounded-full top-1/4 left-1/4"></div>

            <div className="bg-white dark:bg-slate-900 rounded-3xl p-8 max-w-md w-full border border-slate-100 dark:border-slate-800 shadow-xl relative z-10">
              <div className="flex flex-col items-center mb-6">
                <div className="w-10 h-10 bg-sky-500 rounded-xl flex items-center justify-center text-white mb-2">
                  <Heart className="w-6 h-6 fill-white" />
                </div>
                <span className="text-xl font-bold tracking-tight">Cura<span className="text-sky-500">AI</span></span>
                <p className="text-xs text-slate-400 mt-1 uppercase font-semibold">
                  {authMode === 'login' ? "Access Medical Portal" : authMode === 'register' ? "Initialize Electronic Profile" : "Secure Account Recovery"}
                </p>
              </div>

              {errorMsg && (
                <div className="bg-rose-50 dark:bg-rose-950/20 text-rose-500 text-xs p-3.5 rounded-xl border border-rose-100 dark:border-rose-900/30 mb-4 flex items-center">
                  <AlertCircle className="w-4 h-4 mr-2" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {successMsg && (
                <div className="bg-emerald-50 dark:bg-emerald-950/20 text-emerald-500 text-xs p-3.5 rounded-xl border border-emerald-100 dark:border-emerald-900/30 mb-4 flex items-center">
                  <Check className="w-4 h-4 mr-2" />
                  <span>{successMsg}</span>
                </div>
              )}

              <form onSubmit={handleAuthSubmit} className="space-y-4" noValidate>

                {/* Name - Register only */}
                {authMode === 'register' && (
                  <div>
                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 block">
                      Full Name <span className="text-rose-400">*</span>
                    </label>
                    <input
                      type="text"
                      autoComplete="name"
                      placeholder="e.g. Arjun Sharma"
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm px-4 py-3 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition"
                      value={authForm.name}
                      onChange={e => { setAuthForm({...authForm, name: e.target.value}); setErrorMsg(''); }}
                    />
                  </div>
                )}

                {/* Mobile Number */}
                <div>
                  <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 block">
                    Mobile Number <span className="text-rose-400">*</span>
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-sm font-semibold text-slate-400 select-none">+91</span>
                    <input
                      type="tel"
                      autoComplete="tel"
                      maxLength={10}
                      placeholder="10-digit mobile number"
                      className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm pl-12 pr-4 py-3 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition"
                      value={authForm.mobile_number}
                      onChange={e => {
                        const val = e.target.value.replace(/\D/g, '').slice(0, 10);
                        setAuthForm({...authForm, mobile_number: val});
                        setErrorMsg('');
                      }}
                    />
                  </div>
                  {authMode === 'register' && authForm.mobile_number.length > 0 && authForm.mobile_number.length < 10 && (
                    <p className="text-[10px] text-amber-500 mt-1">{authForm.mobile_number.length}/10 digits entered</p>
                  )}
                </div>

                {/* Password - not on forgot step 1 */}
                {authMode !== 'forgot' && (
                  <div>
                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 block">
                      Password <span className="text-rose-400">*</span>
                      {authMode === 'register' && <span className="text-[10px] text-slate-400 ml-1">(min. 6 characters)</span>}
                    </label>
                    <div className="relative">
                      <input
                        id="auth-password"
                        type="password"
                        autoComplete={authMode === 'login' ? 'current-password' : 'new-password'}
                        placeholder={authMode === 'register' ? 'Create a strong password' : 'Enter your password'}
                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm px-4 py-3 pr-10 focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition"
                        value={authForm.password}
                        onChange={e => { setAuthForm({...authForm, password: e.target.value}); setErrorMsg(''); }}
                      />
                      <button type="button" tabIndex={-1}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                        onClick={() => {
                          const inp = document.getElementById('auth-password');
                          inp.type = inp.type === 'password' ? 'text' : 'password';
                        }}>
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                )}

                {/* Role - Register only */}
                {authMode === 'register' && (
                  <div>
                    <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 block">
                      Register As
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { val: 'patient', icon: '🧑‍⚕️', label: 'Patient' },
                        { val: 'doctor',  icon: '👨‍⚕️', label: 'Doctor'  },
                        { val: 'admin',   icon: '🛡️',  label: 'Admin'   },
                      ].map(opt => (
                        <button key={opt.val} type="button"
                          onClick={() => setAuthForm({...authForm, role: opt.val})}
                          className={`flex flex-col items-center py-2.5 rounded-xl border text-xs font-semibold transition ${
                            authForm.role === opt.val
                              ? 'bg-sky-500 border-sky-500 text-white'
                              : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 hover:border-sky-400'
                          }`}>
                          <span className="text-base mb-0.5">{opt.icon}</span>
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* OTP fields - Forgot step 2 */}
                {authMode === 'forgot' && otpSent && (
                  <>
                    <div>
                      <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 block">
                        OTP Code <span className="text-rose-400">*</span>
                      </label>
                      <input type="text" maxLength={6}
                        placeholder="Enter 6-digit OTP"
                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm px-4 py-3 focus:outline-none focus:ring-2 focus:ring-sky-500 transition"
                        value={authForm.otp}
                        onChange={e => setAuthForm({...authForm, otp: e.target.value.replace(/\D/g,'').slice(0,6)})} />
                    </div>
                    <div>
                      <label className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5 block">
                        New Password <span className="text-rose-400">*</span>
                      </label>
                      <input type="password" placeholder="Min. 6 characters"
                        className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm px-4 py-3 focus:outline-none focus:ring-2 focus:ring-sky-500 transition"
                        value={authForm.new_password}
                        onChange={e => setAuthForm({...authForm, new_password: e.target.value})} />
                    </div>
                  </>
                )}

                {/* Submit Button */}
                <button type="submit" disabled={loading}
                  className="w-full bg-sky-500 hover:bg-sky-600 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-xl transition-all text-sm flex items-center justify-center space-x-2 mt-2">
                  {loading ? (
                    <>
                      <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                      </svg>
                      <span>{authMode === 'login' ? 'Signing in...' : authMode === 'register' ? 'Creating Account...' : 'Processing...'}</span>
                    </>
                  ) : (
                    <span>
                      {authMode === 'login' ? '🔐 Sign In' : authMode === 'register' ? '🚀 Create Account' : (otpSent ? '✅ Verify & Reset' : '📱 Send OTP')}
                    </span>
                  )}
                </button>

                {/* Demo hint for login */}
                {authMode === 'login' && (
                  <div className="bg-sky-50 dark:bg-sky-950/20 border border-sky-100 dark:border-sky-900/30 rounded-xl p-3 text-[10px] text-sky-600 dark:text-sky-400">
                    <span className="font-bold">Demo Login:</span> Mobile: <code className="bg-sky-100 dark:bg-sky-900/40 px-1 rounded">7795273421</code> &nbsp;
                    Password: <code className="bg-sky-100 dark:bg-sky-900/40 px-1 rounded">password123</code>
                  </div>
                )}
              </form>

              <div className="mt-5 flex flex-col items-center space-y-2 text-xs text-slate-400">
                {authMode === 'login' ? (
                  <>
                    <button onClick={() => { setAuthMode('forgot'); setErrorMsg(''); setSuccessMsg(''); }}
                      className="hover:text-sky-500 font-semibold transition">Forgot Password?</button>
                    <div>Don't have an account?{' '}
                      <button onClick={() => { setAuthMode('register'); setErrorMsg(''); setSuccessMsg(''); }}
                        className="text-sky-500 font-semibold hover:text-sky-600 transition">Register Free</button>
                    </div>
                  </>
                ) : authMode === 'register' ? (
                  <div>Already have an account?{' '}
                    <button onClick={() => { setAuthMode('login'); setErrorMsg(''); setSuccessMsg(''); }}
                      className="text-sky-500 font-semibold hover:text-sky-600 transition">Sign In</button>
                  </div>
                ) : (
                  <div>
                    <button onClick={() => { setAuthMode('login'); setErrorMsg(''); setSuccessMsg(''); setOtpSent(false); }}
                      className="text-sky-500 font-semibold hover:text-sky-600 transition">← Back to Login</button>
                  </div>
                )}
              </div>
            </div>
          </div>
        );

      default:
        return null;

    }
  };

  const renderDashboardLayout = () => {
    // Guard: show a spinner if token exists but role hasn't resolved yet
    if (!role) {
      return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex items-center justify-center">
          <div className="text-center space-y-4">
            <div className="w-12 h-12 bg-sky-500 rounded-2xl flex items-center justify-center mx-auto animate-pulse">
              <Heart className="w-6 h-6 fill-white text-white" />
            </div>
            <div className="text-sm font-semibold text-slate-500">Loading CuraAI Dashboard...</div>
            <div className="flex space-x-1 justify-center">
              <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{animationDelay:'0ms'}}></div>
              <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{animationDelay:'150ms'}}></div>
              <div className="w-2 h-2 bg-sky-400 rounded-full animate-bounce" style={{animationDelay:'300ms'}}></div>
            </div>
          </div>
        </div>
      );
    }
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col md:flex-row">
        {/* Modern Sidebar Navigation */}
        <aside className={`w-64 bg-white dark:bg-slate-900 border-r border-slate-100 dark:border-slate-800 flex flex-col justify-between p-6 fixed inset-y-0 left-0 transform md:relative md:translate-x-0 transition duration-200 z-50 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}>
          <div className="space-y-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-sky-500 rounded-lg flex items-center justify-center text-white">
                  <Heart className="w-4 h-4 fill-white" />
                </div>
                <span className="text-lg font-bold tracking-tight">Cura<span className="text-sky-500">AI</span></span>
              </div>
              <button onClick={() => setMobileMenuOpen(false)} className="md:hidden text-slate-400 hover:text-slate-200">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Nav Tabs */}
            <nav className="space-y-1">
              {role === 'patient' && (
                <>
                  <button onClick={() => { setActiveTab('dashboard'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab==='dashboard'?'bg-sky-500 text-white':'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'}`}>
                    <Activity className="w-4 h-4" /><span>My Vitals Health</span>
                  </button>

                  <button onClick={() => { setActiveTab('profile'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab==='profile'?'bg-sky-500 text-white':'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'}`}>
                    <User className="w-4 h-4" /><span>My Medical Profile</span>
                  </button>

                  <button onClick={() => { setActiveTab('chatbot'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab==='chatbot'?'bg-indigo-500 text-white':'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'}`}>
                    <MessageSquare className="w-4 h-4" /><span>AI Health Chatbot</span>
                    <span className="ml-auto text-[9px] bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400 px-1.5 py-0.5 rounded font-bold">NEW</span>
                  </button>

                  <button onClick={() => { setActiveTab('ocr'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab==='ocr'?'bg-sky-500 text-white':'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'}`}>
                    <FileText className="w-4 h-4" /><span>Upload Reports</span>
                  </button>

                  <button onClick={() => { setActiveTab('symptom-analysis'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab==='symptom-analysis'?'bg-sky-500 text-white':'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'}`}>
                    <Brain className="w-4 h-4" /><span>AI Symptom Checker</span>
                  </button>

                  <button onClick={() => { setActiveTab('doctor-connect'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab==='doctor-connect'?'bg-sky-500 text-white':'text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800'}`}>
                    <Video className="w-4 h-4" /><span>Doctor Connect</span>
                  </button>
                </>
              )}

              {role === 'doctor' && (
                <button onClick={() => { setActiveTab('doctor-connect'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition bg-sky-500 text-white`}>
                  <Video className="w-4 h-4" />
                  <span>Doctor Panel</span>
                </button>
              )}

              {role === 'admin' && (
                <button onClick={() => { setActiveTab('admin'); setMobileMenuOpen(false); }} className={`w-full flex items-center space-x-3 px-4 py-3 rounded-xl text-sm font-semibold transition bg-sky-500 text-white`}>
                  <Users className="w-4 h-4" />
                  <span>Admin Panel</span>
                </button>
              )}
            </nav>
          </div>

          <div className="space-y-4">
            <button onClick={toggleDarkMode} className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-xl text-sm font-medium text-slate-500 hover:bg-slate-50 dark:hover:bg-slate-800">
              {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              <span>{darkMode ? "Light Theme" : "Dark Theme"}</span>
            </button>
            <button onClick={handleLogout} className="w-full flex items-center space-x-3 px-4 py-2.5 rounded-xl text-sm font-medium text-red-500 hover:bg-red-550/10 transition">
              <LogOut className="w-4 h-4" />
              <span>Log Out</span>
            </button>
          </div>
        </aside>

        {/* Primary Main Content Panel */}
        <div className="flex-1 flex flex-col min-w-0 overflow-y-auto h-screen relative">
          {/* Dashboard Header Banner */}
          <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800 px-6 flex items-center justify-between sticky top-0 z-30">
            <div className="flex items-center space-x-4">
              <button onClick={() => setMobileMenuOpen(true)} className="md:hidden text-slate-500 hover:text-slate-700">
                <Menu className="w-6 h-6" />
              </button>
              <h1 className="text-lg font-bold capitalize">{activeTab.replace('-', ' ')} Portal</h1>
            </div>

            <div className="flex items-center space-x-4">
              {/* Emergency Alert Pulsing Trigger */}
              {role === 'patient' && (
                <button onClick={handleSOSAlert} className="bg-red-500 hover:bg-red-600 text-white font-extrabold px-5 py-2.5 rounded-xl text-xs flex items-center space-x-1.5 transition animate-pulse duration-700">
                  <ShieldAlert className="w-4 h-4" />
                  <span>CRITICAL SOS</span>
                </button>
              )}
            </div>
          </header>

          <main className="p-6 max-w-7xl mx-auto w-full flex-1">
            {role === 'patient' && renderPatientPortal()}
            {role === 'doctor' && renderDoctorPortal()}
            {role === 'admin' && renderAdminPortal()}
          </main>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-100">
      {/* Toast popup */}
      {toast.show && (
        <div className={`fixed top-4 right-4 z-55 max-w-sm p-4 rounded-2xl shadow-xl flex items-start space-x-3 transition transform translate-y-0 scale-100 ${
          toast.type === 'success' ? 'bg-sky-500 text-white' :
          toast.type === 'warning' ? 'bg-amber-500 text-white' : 'bg-red-500 text-white'
        }`}>
          <AlertCircle className="w-5 h-5 shrink-0" />
          <div className="text-xs font-semibold">{toast.message}</div>
        </div>
      )}

      {token ? renderDashboardLayout() : renderAuthLayout()}
    </div>
  );
}
