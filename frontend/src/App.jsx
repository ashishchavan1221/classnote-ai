import React, { useState, useEffect, useRef } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  useNavigate,
  useParams,
  Navigate,
} from "react-router-dom";
import {
  BookOpen,
  Calendar,
  CheckSquare,
  Clock,
  Download,
  ExternalLink,
  FileText,
  LayoutDashboard,
  Mic,
  MicOff,
  Plus,
  RefreshCw,
  Settings as SettingsIcon,
  LogOut,
  User,
  Users,
  Video,
  Database,
  ArrowRight,
  Loader2,
  CheckCircle,
  FileDown
} from "lucide-react";
import mermaid from "mermaid";
import { api } from "./services/api";

// Initialize Mermaid for flowcharts
mermaid.initialize({
  startOnLoad: true,
  theme: "neutral",
  securityLevel: "loose",
  themeVariables: {
    fontFamily: "Patrick Hand, sans-serif",
  }
});

// -------------------------------------------------------------
// Mermaid Component
// -------------------------------------------------------------
const MermaidDiagram = ({ chart }) => {
  const [svg, setSvg] = useState("");
  const [error, setError] = useState(false);
  const containerId = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

  useEffect(() => {
    const renderDiagram = async () => {
      try {
        setError(false);
        // Clear previous state
        const { svg: renderedSvg } = await mermaid.render(containerId, chart);
        setSvg(renderedSvg);
      } catch (err) {
        console.error("Mermaid parsing error:", err);
        setError(true);
      }
    };

    if (chart) {
      renderDiagram();
    }
  }, [chart]);

  if (error) {
    return (
      <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm font-handwriting border border-red-200">
        [Flowchart structure layout failed to draw. Displaying raw code:]
        <pre className="text-xs font-mono mt-2 overflow-x-auto whitespace-pre">{chart}</pre>
      </div>
    );
  }

  return (
    <div 
      className="mermaid-wrapper flex justify-center py-4 bg-amber-50/50 rounded-xl border border-dashed border-amber-200 my-4 overflow-x-auto"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

// -------------------------------------------------------------
// Authentication Context and Wrappers
// -------------------------------------------------------------
const AuthContext = React.createContext(null);

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    try {
      setLoading(true);
      const data = await api.getMe();
      setUser(data);
    } catch (e) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (localStorage.getItem("token")) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    await api.login(email, password);
    await fetchUser();
  };

  const register = async (name, email, password, role, institution) => {
    await api.register(name, email, password, role, institution);
    await fetchUser();
  };

  const logout = () => {
    api.logout();
    setUser(null);
  };

  const updateUserInfo = (updatedUser) => {
    setUser(updatedUser);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updateUserInfo }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => React.useContext(AuthContext);

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-10 w-10 animate-spin text-brand-600" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
};

// -------------------------------------------------------------
// Main Layout Frame Component
// -------------------------------------------------------------
const AppLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    if (!user) return;
    
    let seenMeetings = new Set();
    
    const checkNewMeetings = async () => {
      try {
        const meetingsList = await api.getMeetings();
        // Check for any meetings that are currently live
        const activeMeetings = meetingsList.filter(m => m.status === "live");
        
        activeMeetings.forEach(m => {
          if (!seenMeetings.has(m.id)) {
            setNotifications(prev => {
              if (prev.some(n => n.id === m.id)) return prev;
              return [...prev, {
                id: m.id,
                title: m.title,
                message: `Class "${m.title}" is now LIVE! Click here to join the call.`,
                link: `/meeting/${m.id}`
              }];
            });
            seenMeetings.add(m.id);
          }
        });
      } catch (err) {
        console.error("Failed to check active meetings for notifications:", err);
      }
    };
    
    checkNewMeetings();
    const interval = setInterval(checkNewMeetings, 7000);
    
    return () => clearInterval(interval);
  }, [user]);

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar navigation */}
      <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col justify-between p-4 shadow-xl">
        <div>
          {/* Logo */}
          <div className="flex items-center space-x-2 px-3 py-4 mb-6">
            <BookOpen className="h-7 w-7 text-brand-300" />
            <span className="font-sans font-bold text-lg tracking-wider bg-gradient-to-r from-brand-300 to-indigo-200 bg-clip-text text-transparent">
              ClassNote AI
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1">
            <Link
              to="/dashboard"
              className="flex items-center space-x-3 px-4 py-3 rounded-xl transition duration-150 hover:bg-slate-800 text-slate-300 hover:text-white"
            >
              <LayoutDashboard className="h-5 w-5 text-slate-400" />
              <span className="text-sm font-medium">Dashboard</span>
            </Link>

            <Link
              to="/tasks"
              className="flex items-center space-x-3 px-4 py-3 rounded-xl transition duration-150 hover:bg-slate-800 text-slate-300 hover:text-white"
            >
              <CheckSquare className="h-5 w-5 text-slate-400" />
              <span className="text-sm font-medium">Task Board</span>
            </Link>

            <Link
              to="/settings"
              className="flex items-center space-x-3 px-4 py-3 rounded-xl transition duration-150 hover:bg-slate-800 text-slate-300 hover:text-white"
            >
              <SettingsIcon className="h-5 w-5 text-slate-400" />
              <span className="text-sm font-medium">Settings</span>
            </Link>
          </nav>
        </div>

        {/* User Card & Logout */}
        <div className="border-t border-slate-800 pt-4">
          <div className="flex items-center space-x-3 px-3 py-2 mb-3 bg-slate-800/40 rounded-xl">
            <div className="h-10 w-10 rounded-full bg-brand-600 flex items-center justify-center text-white font-bold uppercase shadow-inner">
              {user?.name?.[0] || "U"}
            </div>
            <div className="overflow-hidden">
              <p className="text-sm font-semibold truncate text-slate-100">{user?.name}</p>
              <span className="text-xs uppercase bg-brand-700/60 px-2 py-0.5 rounded text-brand-200 border border-brand-500/30">
                {user?.role}
              </span>
            </div>
          </div>
          <button
            onClick={() => {
              logout();
              navigate("/");
            }}
            className="flex w-full items-center space-x-3 px-4 py-2.5 rounded-xl transition duration-150 hover:bg-red-950/40 text-red-400 hover:text-red-300 hover:border-red-900 border border-transparent"
          >
            <LogOut className="h-5 w-5" />
            <span className="text-sm font-medium">Log Out</span>
          </button>
        </div>
      </aside>

      {/* Main page content area */}
      <main className="flex-1 flex flex-col overflow-y-auto">
        <header className="bg-white border-b border-slate-100 h-16 flex items-center justify-between px-8 shadow-sm">
          <h1 className="text-xl font-semibold text-slate-800">
            Autonomous Notes & Action items
          </h1>
          <div className="flex items-center space-x-4">
            {user?.institution && (
              <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200">
                🏫 {user.institution}
              </span>
            )}
            <div className="text-sm text-slate-500 font-medium">
              Today: {new Date().toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
            </div>
          </div>
        </header>

        {/* Live Notification Banners */}
        {notifications.map(n => (
          <div key={n.id} className="bg-brand-50 border-b border-brand-100 px-8 py-3.5 flex items-center justify-between animate-slide-down">
            <div className="flex items-center space-x-3 text-sm text-brand-800 font-semibold">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-brand-500"></span>
              </span>
              <span>{n.message}</span>
            </div>
            <div className="flex items-center space-x-4">
              <button
                onClick={() => {
                  setNotifications(prev => prev.filter(item => item.id !== n.id));
                  navigate(n.link);
                }}
                className="bg-brand-600 hover:bg-brand-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg shadow-sm"
              >
                Join Now
              </button>
              <button
                onClick={() => setNotifications(prev => prev.filter(item => item.id !== n.id))}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>
          </div>
        ))}

        <div className="p-8 flex-1">
          {children}
        </div>
      </main>
    </div>
  );
};

// -------------------------------------------------------------
// Landing Page View
// -------------------------------------------------------------
const LandingPage = () => {
  return (
    <div className="min-h-screen bg-gradient-to-tr from-brand-900 via-indigo-950 to-slate-900 text-white flex flex-col justify-between">
      <header className="max-w-7xl mx-auto w-full px-6 h-20 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <BookOpen className="h-8 w-8 text-brand-300" />
          <span className="font-bold text-xl tracking-wider bg-gradient-to-r from-brand-300 to-indigo-100 bg-clip-text text-transparent">
            ClassNote AI
          </span>
        </div>
        <div className="space-x-4">
          <Link to="/login" className="px-4 py-2 text-slate-300 hover:text-white transition">
            Sign In
          </Link>
          <Link to="/register" className="bg-brand-600 hover:bg-brand-500 text-white px-5 py-2.5 rounded-full shadow-lg hover:shadow-brand-500/20 transition-all font-semibold">
            Register
          </Link>
        </div>
      </header>

      <main className="max-w-6xl mx-auto w-full px-6 flex-1 flex flex-col justify-center items-center text-center py-20">
        <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/30 mb-8 text-brand-300 text-sm font-semibold tracking-wide">
          <span>✨ Smart Autonomous Classroom Pipelines</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl font-sans font-bold leading-tight max-w-4xl bg-gradient-to-b from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
          Host Live Sessions. <br />
          Get Handwriting styled Notes & Notion Tasks.
        </h1>
        
        <p className="mt-6 text-lg md:text-xl text-slate-300 max-w-2xl font-light">
          Host class calls directly through Jitsi. The AI listens, references past lectures, extracts action items, syncs to Notion, and designs beautiful notes.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4 justify-center">
          <Link
            to="/register"
            className="group bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white px-8 py-4 rounded-full font-bold shadow-2xl hover:shadow-brand-500/35 transition-all flex items-center space-x-2"
          >
            <span>Get Started Free</span>
            <ArrowRight className="h-5 w-5 transform group-hover:translate-x-1 transition-transform" />
          </Link>
        </div>

        {/* Feature grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mt-24 max-w-5xl w-full">
          <div className="bg-slate-800/40 border border-slate-700/40 p-6 rounded-2xl text-left hover:border-brand-500/20 transition-all hover:bg-slate-800/60">
            <Mic className="h-10 w-10 text-brand-400 mb-4 bg-brand-500/10 p-2 rounded-xl" />
            <h3 className="text-lg font-bold text-slate-100">Live Transcription</h3>
            <p className="text-slate-400 mt-2 text-sm">
              Record class sessions in real-time. Streaming WebSockets render live voice logs straight to sidebars.
            </p>
          </div>

          <div className="bg-slate-800/40 border border-slate-700/40 p-6 rounded-2xl text-left hover:border-brand-500/20 transition-all hover:bg-slate-800/60">
            <Database className="h-10 w-10 text-accent-400 mb-4 bg-accent-500/10 p-2 rounded-xl" />
            <h3 className="text-lg font-bold text-slate-100">RAG Context</h3>
            <p className="text-slate-400 mt-2 text-sm">
              Retrieval Augmented Generation hooks past transcripts to current sessions, matching references for continuous learning.
            </p>
          </div>

          <div className="bg-slate-800/40 border border-slate-700/40 p-6 rounded-2xl text-left hover:border-brand-500/20 transition-all hover:bg-slate-800/60">
            <FileText className="h-10 w-10 text-emerald-400 mb-4 bg-emerald-500/10 p-2 rounded-xl" />
            <h3 className="text-lg font-bold text-slate-100">Handwriting styled PDFs</h3>
            <p className="text-slate-400 mt-2 text-sm">
              Get note sheets styled with Patrick Hand font. Flowcharts and tasks included in the downloadable print template.
            </p>
          </div>
        </div>
      </main>

      <footer className="h-16 flex items-center justify-center text-xs text-slate-500 border-t border-slate-800/50">
        © 2026 ClassNote AI. Built for modern classrooms.
      </footer>
    </div>
  );
};

// -------------------------------------------------------------
// Register Page
// -------------------------------------------------------------
const RegisterPage = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("student"); // "student" | "teacher"
  const [formData, setFormData] = useState({ name: "", email: "", password: "", role: "student", institution: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dbStatus, setDbStatus] = useState({ use_mongodb: false, mongodb_configured: false });

  useEffect(() => {
    const fetchDbStatus = async () => {
      const status = await api.getStatus();
      setDbStatus(status);
    };
    fetchDbStatus();
  }, []);

  const handleTabChange = (role) => {
    setActiveTab(role);
    setFormData(prev => ({ ...prev, role }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(formData.name, formData.email, formData.password, formData.role, formData.institution);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  const renderDbStatusPill = () => {
    if (dbStatus.use_mongodb) {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>MongoDB Atlas Connected</span>
        </div>
      );
    } else if (dbStatus.mongodb_configured) {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-red-500/10 border border-red-500/30 text-red-400">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
          <span>MongoDB Atlas Offline</span>
        </div>
      );
    } else {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/10 border border-amber-500/30 text-amber-400">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
          <span>Local JSON DB Fallback</span>
        </div>
      );
    }
  };

  const themeColor = activeTab === "student" ? "emerald" : "brand";

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center space-x-2 text-white">
          <BookOpen className="h-9 w-9 text-brand-400" />
          <span className="font-bold text-2xl tracking-wider">ClassNote AI</span>
        </Link>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-white">
          Create your account
        </h2>
        <div className="mt-3 flex justify-center">{renderDbStatusPill()}</div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-800 py-8 px-4 shadow-xl rounded-2xl sm:px-10 border border-slate-700/50">
          
          {/* Tab selector for Student / Teacher */}
          <div className="flex bg-slate-900 p-1 rounded-xl mb-6 border border-slate-700">
            <button
              onClick={() => handleTabChange("student")}
              className={`flex-1 text-center py-2.5 rounded-lg text-xs font-bold transition duration-200 ${
                activeTab === "student"
                  ? "bg-emerald-600 text-white shadow-md"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              🎓 Student Section
            </button>
            <button
              onClick={() => handleTabChange("teacher")}
              className={`flex-1 text-center py-2.5 rounded-lg text-xs font-bold transition duration-200 ${
                activeTab === "teacher"
                  ? "bg-brand-600 text-white shadow-md"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              💼 Teacher Section
            </button>
          </div>

          <form className="space-y-5" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-950/40 border border-red-900 text-red-200 p-3.5 rounded-xl text-sm font-medium">
                ⚠️ {error}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-300">
                {activeTab === "student" ? "Student Name" : "Teacher Name"}
              </label>
              <input
                type="text"
                required
                className={`mt-1.5 block w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 sm:text-sm ${
                  activeTab === "student" ? "focus:ring-emerald-500 focus:border-emerald-500" : "focus:ring-brand-500 focus:border-brand-500"
                }`}
                placeholder={activeTab === "student" ? "Full Name" : "Professor / Mentor Name"}
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300">Email Address</label>
              <input
                type="email"
                required
                className={`mt-1.5 block w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 sm:text-sm ${
                  activeTab === "student" ? "focus:ring-emerald-500 focus:border-emerald-500" : "focus:ring-brand-500 focus:border-brand-500"
                }`}
                placeholder="you@school.edu"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300">Password</label>
              <input
                type="password"
                required
                className={`mt-1.5 block w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 sm:text-sm ${
                  activeTab === "student" ? "focus:ring-emerald-500 focus:border-emerald-500" : "focus:ring-brand-500 focus:border-brand-500"
                }`}
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300">Institution / School Name</label>
              <input
                type="text"
                className={`mt-1.5 block w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 sm:text-sm ${
                  activeTab === "student" ? "focus:ring-emerald-500 focus:border-emerald-500" : "focus:ring-brand-500 focus:border-brand-500"
                }`}
                placeholder="e.g. Stanford University"
                value={formData.institution}
                onChange={(e) => setFormData({ ...formData, institution: e.target.value })}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full flex justify-center py-3 px-4 rounded-xl border border-transparent text-sm font-semibold text-white shadow-lg transition duration-150 ${
                activeTab === "student"
                  ? "bg-emerald-600 hover:bg-emerald-500 focus:ring-emerald-500 hover:shadow-emerald-500/20"
                  : "bg-brand-600 hover:bg-brand-500 focus:ring-brand-500 hover:shadow-brand-500/20"
              }`}
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Sign Up"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            Already registered?{" "}
            <Link to="/login" className={`font-semibold ${activeTab === "student" ? "text-emerald-400 hover:text-emerald-300" : "text-brand-400 hover:text-brand-300"}`}>
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("student"); // "student" | "teacher"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dbStatus, setDbStatus] = useState({ use_mongodb: false, mongodb_configured: false });
  const [portalAlert, setPortalAlert] = useState("");

  useEffect(() => {
    const fetchDbStatus = async () => {
      const status = await api.getStatus();
      setDbStatus(status);
    };
    fetchDbStatus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setPortalAlert("");
    setLoading(true);
    try {
      await login(email, password);
      // Fetch details to check role matching
      const userProfile = await api.getMe();
      if (userProfile.role !== activeTab) {
        setPortalAlert(`Note: You logged into the ${activeTab === "student" ? "Student" : "Teacher"} portal, but your account is registered as a ${userProfile.role === "student" ? "Student" : "Teacher"}. Redirecting you to the correct sections...`);
        setTimeout(() => {
          navigate("/dashboard");
        }, 2000);
      } else {
        navigate("/dashboard");
      }
    } catch (err) {
      setError(err.message || "Invalid credentials");
      setLoading(false);
    }
  };

  const renderDbStatusPill = () => {
    if (dbStatus.use_mongodb) {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>MongoDB Atlas Connected</span>
        </div>
      );
    } else if (dbStatus.mongodb_configured) {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-red-500/10 border border-red-500/30 text-red-400">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" />
          <span>MongoDB Atlas Offline</span>
        </div>
      );
    } else {
      return (
        <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-[11px] font-bold bg-amber-500/10 border border-amber-500/30 text-amber-400">
          <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" />
          <span>Local JSON DB Fallback</span>
        </div>
      );
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <Link to="/" className="inline-flex items-center space-x-2 text-white">
          <BookOpen className="h-9 w-9 text-brand-400" />
          <span className="font-bold text-2xl tracking-wider">ClassNote AI</span>
        </Link>
        <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-white">
          Sign in to your portal
        </h2>
        <div className="mt-3 flex justify-center">{renderDbStatusPill()}</div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-800 py-8 px-4 shadow-xl rounded-2xl sm:px-10 border border-slate-700/50">
          
          {/* Tab selector for Student / Teacher Portal */}
          <div className="flex bg-slate-900 p-1 rounded-xl mb-6 border border-slate-700">
            <button
              onClick={() => setActiveTab("student")}
              className={`flex-1 text-center py-2.5 rounded-lg text-xs font-bold transition duration-200 ${
                activeTab === "student"
                  ? "bg-emerald-600 text-white shadow-md"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              🎓 Student Portal
            </button>
            <button
              onClick={() => setActiveTab("teacher")}
              className={`flex-1 text-center py-2.5 rounded-lg text-xs font-bold transition duration-200 ${
                activeTab === "teacher"
                  ? "bg-brand-600 text-white shadow-md"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              💼 Teacher Portal
            </button>
          </div>

          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-950/40 border border-red-900 text-red-200 p-3.5 rounded-xl text-sm font-medium">
                ⚠️ {error}
              </div>
            )}
            
            {portalAlert && (
              <div className="bg-blue-950/40 border border-blue-950 text-blue-200 p-3.5 rounded-xl text-xs font-medium animate-pulse">
                ℹ️ {portalAlert}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-slate-300">Email Address</label>
              <input
                type="email"
                required
                className={`mt-1.5 block w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 sm:text-sm ${
                  activeTab === "student" ? "focus:ring-emerald-500 focus:border-emerald-500" : "focus:ring-brand-500 focus:border-brand-500"
                }`}
                placeholder="you@school.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300">Password</label>
              <input
                type="password"
                required
                className={`mt-1.5 block w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:ring-2 sm:text-sm ${
                  activeTab === "student" ? "focus:ring-emerald-500 focus:border-emerald-500" : "focus:ring-brand-500 focus:border-brand-500"
                }`}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full flex justify-center py-3 px-4 rounded-xl border border-transparent text-sm font-semibold text-white shadow-lg transition duration-150 ${
                activeTab === "student"
                  ? "bg-emerald-600 hover:bg-emerald-500 focus:ring-emerald-500 hover:shadow-emerald-500/20"
                  : "bg-brand-600 hover:bg-brand-500 focus:ring-brand-500 hover:shadow-brand-500/20"
              }`}
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : "Sign In"}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-400">
            Need an account?{" "}
            <Link to="/register" className={`font-semibold ${activeTab === "student" ? "text-emerald-400 hover:text-emerald-300" : "text-brand-400 hover:text-brand-300"}`}>
              Register Free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// Dashboard View
// -------------------------------------------------------------
const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [meetings, setMeetings] = useState([]);
  const [stats, setStats] = useState({ meetingsCount: 0, pendingTasks: 0 });
  const [showScheduleForm, setShowScheduleForm] = useState(false);
  const [newMeeting, setNewMeeting] = useState({ title: "", description: "", scheduledAt: "", participantEmails: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const list = await api.getMeetings();
      setMeetings(list);
      
      const tasks = await api.getTasks();
      const pendingCount = tasks.filter(t => t.status === "pending").length;
      
      setStats({
        meetingsCount: list.length,
        pendingTasks: pendingCount
      });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSchedule = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const emailsList = newMeeting.participantEmails
        .split(",")
        .map(e => e.trim())
        .filter(e => e !== "");
        
      await api.createMeeting(
        newMeeting.title,
        newMeeting.description,
        newMeeting.scheduledAt,
        emailsList
      );
      
      setNewMeeting({ title: "", description: "", scheduledAt: "", participantEmails: "" });
      setShowScheduleForm(false);
      loadData();
    } catch (err) {
      setError(err.message || "Failed to create session.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-brand-600" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-brand-600 to-indigo-700 text-white rounded-2xl p-6 shadow-lg relative overflow-hidden flex flex-col md:flex-row justify-between items-start md:items-center">
        <div>
          <h2 className="text-2xl font-bold font-sans">Welcome back, {user?.name}!</h2>
          <p className="mt-2 text-indigo-100 font-light text-sm max-w-md">
            {user?.role === "teacher" 
              ? "Host your live session classrooms, distribute handwriting notes, and push student projects to boards."
              : "Review upcoming courses, read handwriting-styled notes, and track your action item assignments."
            }
          </p>
        </div>
        {user?.role === "teacher" && (
          <button
            onClick={() => setShowScheduleForm(true)}
            className="mt-4 md:mt-0 bg-white hover:bg-brand-50 text-brand-700 px-5 py-3 rounded-xl font-semibold shadow-md flex items-center space-x-2 transition-all transform hover:-translate-y-0.5 active:translate-y-0"
          >
            <Plus className="h-5 w-5" />
            <span>Create Session</span>
          </button>
        )}
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex items-center space-x-4">
          <div className="p-3 bg-brand-50 rounded-xl text-brand-600">
            <Video className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block uppercase font-bold tracking-wider">Meetings Hosted</span>
            <p className="text-2xl font-bold text-slate-800 mt-1">{stats.meetingsCount}</p>
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex items-center space-x-4">
          <div className="p-3 bg-accent-50 rounded-xl text-accent-600">
            <CheckSquare className="h-6 w-6" />
          </div>
          <div>
            <span className="text-xs text-slate-400 block uppercase font-bold tracking-wider">Action Items</span>
            <p className="text-2xl font-bold text-slate-800 mt-1">{stats.pendingTasks} Pending</p>
          </div>
        </div>
      </div>

      {/* Meetings List */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-slate-800 flex items-center space-x-2">
            <Calendar className="h-5 w-5 text-brand-500" />
            <span>All Class Sessions</span>
          </h3>
        </div>

        {meetings.length === 0 ? (
          <div className="text-center py-12 border-2 border-dashed border-slate-100 rounded-xl">
            <Calendar className="mx-auto h-12 w-12 text-slate-300" />
            <h4 className="mt-4 text-sm font-semibold text-slate-600">No sessions scheduled</h4>
            <p className="mt-1 text-xs text-slate-400 max-w-xs mx-auto">
              Create a new meeting session above to initialize the pipeline.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-100 text-xs text-slate-400 uppercase font-bold">
                  <th className="pb-3 pl-2">Session Title</th>
                  <th className="pb-3">Date & Time</th>
                  <th className="pb-3">Session Status</th>
                  <th className="pb-3 pr-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm">
                {meetings.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50/50 transition">
                    <td className="py-4 pl-2 font-semibold text-slate-800">
                      <div>
                        {m.title}
                        <span className="text-xs text-slate-400 font-normal block mt-0.5">{m.description || "No description"}</span>
                      </div>
                    </td>
                    <td className="py-4 text-slate-600">
                      {new Date(m.scheduledAt).toLocaleString(undefined, {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </td>
                    <td className="py-4">
                      {m.status === "scheduled" && (
                        <span className="bg-slate-100 border border-slate-200 text-slate-700 px-2.5 py-1 rounded-full text-xs font-semibold uppercase">
                          Scheduled
                        </span>
                      )}
                      {m.status === "live" && (
                        <span className="bg-red-50 border border-red-200 text-red-600 px-2.5 py-1 rounded-full text-xs font-semibold uppercase flex items-center space-x-1.5 w-max">
                          <span className="h-2 w-2 rounded-full bg-red-600 recording-pulse" />
                          <span>Live Session</span>
                        </span>
                      )}
                      {m.status === "completed" && (
                        <span className="bg-emerald-50 border border-emerald-200 text-emerald-600 px-2.5 py-1 rounded-full text-xs font-semibold uppercase">
                          Completed
                        </span>
                      )}
                    </td>
                    <td className="py-4 pr-2 text-right">
                      {m.status === "live" ? (
                        <div className="flex justify-end items-center space-x-2">
                          <Link
                            to={`/meeting/${m.id}`}
                            className="inline-flex items-center space-x-1 bg-red-600 hover:bg-red-500 text-white text-xs font-bold px-3.5 py-2 rounded-lg shadow-sm"
                          >
                            <span>Join Session</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Link>
                          {m.meetingLink && (
                            <a
                              href={m.meetingLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold px-2.5 py-2 rounded-lg inline-flex items-center space-x-1"
                              title="Open Direct Video Call Link"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              <span>Call Link</span>
                            </a>
                          )}
                        </div>
                      ) : m.status === "completed" ? (
                        <div className="flex justify-end items-center space-x-2">
                          {m.transcriptText && (
                            <span className="text-[10px] text-slate-400 italic">
                              {m.transcriptText.split(" ").filter(Boolean).length} words captured
                            </span>
                          )}
                          <Link
                            to={`/notes/${m.id}`}
                            className="bg-brand-50 hover:bg-brand-100 text-brand-700 text-xs font-bold px-3 py-2 rounded-lg flex items-center space-x-1"
                          >
                            <FileText className="h-3.5 w-3.5" />
                            <span>View Notes</span>
                          </Link>
                        </div>
                      ) : (
                        <div className="flex justify-end items-center space-x-2">
                          {user?.role === "teacher" && (
                            <button
                              onClick={async () => {
                                await api.startMeeting(m.id);
                                loadData();
                                navigate(`/meeting/${m.id}`);
                              }}
                              className="bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold px-3.5 py-2 rounded-lg"
                            >
                              Start Session
                            </button>
                          )}
                          <Link
                            to={`/meeting/${m.id}`}
                            className="inline-flex items-center space-x-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold px-3 py-2 rounded-lg"
                          >
                            <span>Class Room</span>
                            <ArrowRight className="h-3.5 w-3.5" />
                          </Link>
                          {m.meetingLink && (
                            <a
                              href={m.meetingLink}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold px-2.5 py-2 rounded-lg inline-flex items-center space-x-1"
                              title="Open Direct Video Call Link"
                            >
                              <ExternalLink className="h-3.5 w-3.5" />
                              <span>Call Link</span>
                            </a>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Schedule Meeting Modal */}
      {showScheduleForm && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-100 max-w-md w-full p-6 relative">
            <h3 className="text-lg font-bold text-slate-800 mb-4">Create Session</h3>
            <form onSubmit={handleSchedule} className="space-y-4">
              {error && <div className="text-xs text-red-600 font-medium">⚠️ {error}</div>}
              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase">Title</label>
                <input
                  type="text"
                  required
                  className="mt-1 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
                  placeholder="e.g. Lecture 4: React Routing"
                  value={newMeeting.title}
                  onChange={(e) => setNewMeeting({ ...newMeeting, title: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase">Description</label>
                <textarea
                  className="mt-1 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
                  placeholder="Session description details"
                  rows={2}
                  value={newMeeting.description}
                  onChange={(e) => setNewMeeting({ ...newMeeting, description: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase">Scheduled Date & Time</label>
                <input
                  type="datetime-local"
                  required
                  className="mt-1 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
                  value={newMeeting.scheduledAt}
                  onChange={(e) => setNewMeeting({ ...newMeeting, scheduledAt: e.target.value })}
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-500 uppercase">Participant Emails (comma separated)</label>
                <input
                  type="text"
                  className="mt-1 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500"
                  placeholder="alex@school.edu, chloe@school.edu"
                  value={newMeeting.participantEmails}
                  onChange={(e) => setNewMeeting({ ...newMeeting, participantEmails: e.target.value })}
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowScheduleForm(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-500 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-xs font-semibold shadow-sm flex items-center space-x-1"
                >
                  {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Schedule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

const MeetingRoom = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [meeting, setMeeting] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [socket, setSocket] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [processingStep, setProcessingStep] = useState(0);
  const [callStarted, setCallStarted] = useState(false);
  const [speechError, setSpeechError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recognitionRef = useRef(null);
  const accumulatedTranscriptRef = useRef("");
  const socketRef = useRef(null);
  const isRecordingRef = useRef(false);

  const handleEndMeetingRef = useRef(null);

  // Fetch meeting on mount
  useEffect(() => {
    const fetchMeeting = async () => {
      try {
        const m = await api.getMeeting(id);
        setMeeting(m);
      } catch (e) {
        navigate("/dashboard");
      }
    };
    fetchMeeting();
  }, [id]);

  // Students: poll meeting status so they auto-redirect to notes when teacher ends meeting
  useEffect(() => {
    if (!meeting || user?.role !== "student") return;
    const pollInterval = setInterval(async () => {
      try {
        const m = await api.getMeeting(id);
        if (m.status === "completed") {
          clearInterval(pollInterval);
          navigate(`/notes/${id}`);
        }
      } catch (e) {}
    }, 4000);
    return () => clearInterval(pollInterval);
  }, [meeting, user]);

  // Start real SpeechRecognition
  const startSpeechRecognition = (currentSocket) => {
    setSpeechError(null);
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechError("Google Chrome or Web Speech API is required for live speech-to-text recording. Browser default recognition is not supported in this client.");
      console.warn("[Speech] SpeechRecognition API not available in this browser.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    recognitionRef.current = recognition;

    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          const spoken = event.results[i][0].transcript.trim();
          if (!spoken) continue;

          // Accumulate for notes generation
          accumulatedTranscriptRef.current += spoken + " ";

          const entry = {
            sender: user?.name || "Speaker",
            text: spoken,
            timestamp: new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          };

          setLiveTranscript(prev => [...prev, entry]);

          // Broadcast via WebSocket so other participants see live feed
          const ws = currentSocket || socketRef.current;
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(entry));
          }
        }
      }
    };

    recognition.onerror = (e) => {
       console.warn("[Speech] Recognition error:", e.error);
       if (e.error === "not-allowed") {
         setSpeechError("Microphone permission blocked or locked by another frame. Please allow microphone access in your browser search bar settings.");
         setIsRecording(false);
         isRecordingRef.current = false;
       } else if (e.error === "service-not-allowed") {
         setSpeechError("Speech recognition service not allowed.");
         setIsRecording(false);
         isRecordingRef.current = false;
       } else if (e.error === "no-speech" || e.error === "aborted" || e.error === "network") {
         setSpeechError(null);
         if (isRecordingRef.current) {
           setTimeout(() => {
             try { recognition.start(); } catch (_) {}
           }, 1000);
         }
       } else {
         setSpeechError(`Microphone issue detected: ${e.error}`);
       }
     };

    recognition.onend = () => {
      // Restart if still recording (continuous mode)
      if (isRecordingRef.current) {
        try { recognition.start(); } catch (_) {}
      }
    };

    try {
      recognition.start();
      setIsRecording(true);
      isRecordingRef.current = true;

      const ws = currentSocket || socketRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          sender: "System",
          text: "🎙️ Live speech recognition started. Speak clearly to capture notes.",
          timestamp: new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        }));
      }
    } catch (e) {
      console.error("[Speech] Could not start recognition:", e);
    }
  };

  const stopSpeechRecognition = () => {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (_) {}
      recognitionRef.current = null;
    }
    if (mediaRecorderRef.current) {
      try { mediaRecorderRef.current.stop(); } catch (_) {}
    }
    setIsRecording(false);
    isRecordingRef.current = false;
  };

  const toggleRecording = () => {
    if (isRecording) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition(socketRef.current);
    }
  };

  useEffect(() => {
    if (!meeting) return;

    const wsUrl = api.getMeetingSocketUrl(id);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;
    setSocket(ws);

    ws.onopen = () => {
      console.log("[WS] Connected to room:", id);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLiveTranscript(prev => [...prev, data]);
      } catch (e) {
        console.error("[WS] Error reading payload:", e);
      }
    };

    return () => {
      stopSpeechRecognition();
      ws.close();
    };
  }, [meeting]);

  const [showEndConfirm, setShowEndConfirm] = useState(false);

  const handleEndMeeting = async () => {
    stopSpeechRecognition();
    setShowEndConfirm(false);
    setProcessing(true);

    const fullTranscript = accumulatedTranscriptRef.current.trim();

    // Convert recorded audio chunks to base64 for fallback transcription on backend
    let audioBase64 = "";
    if (audioChunksRef.current && audioChunksRef.current.length > 0) {
      try {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        audioBase64 = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onloadend = () => {
            const base64data = reader.result.split(',')[1];
            resolve(base64data);
          };
          reader.readAsDataURL(audioBlob);
        });
      } catch (err) {
        console.error("Failed to convert audio to base64:", err);
      }
    }

    const steps = [
      "Capturing speech transcript...",
      "Analysing spoken content for key topics...",
      "Structuring notes from your speech...",
      "Generating action items from discussion...",
      "Compiling handwriting-style PDF...",
      "Finalising study guide..."
    ];

    let curStep = 0;
    const interval = setInterval(() => {
      if (curStep < steps.length - 1) {
        curStep++;
        setProcessingStep(curStep);
      } else {
        clearInterval(interval);
      }
    }, 2000);

    try {
      await api.endMeeting(id, fullTranscript, audioBase64);
      clearInterval(interval);
      setProcessing(false);
      navigate(`/notes/${id}`);
    } catch (e) {
      clearInterval(interval);
      setProcessing(false);
    }
  };

  useEffect(() => {
    handleEndMeetingRef.current = handleEndMeeting;
  });


  if (!meeting) {
    return (
      <div className="flex h-screen items-center justify-center bg-slate-50">
        <Loader2 className="h-8 w-8 animate-spin text-brand-600" />
      </div>
    );
  }

  if (processing) {
    return (
      <div className="h-full flex items-center justify-center p-6 bg-slate-900 rounded-3xl border border-slate-800 shadow-xl min-h-[400px]">
        <div className="text-center max-w-md space-y-6">
          <Loader2 className="h-10 w-10 animate-spin text-brand-400 mx-auto" />
          <h2 className="text-xl font-bold text-slate-100">Generating Class Study Guide...</h2>
          <p className="text-slate-400 text-sm">Processing your speech into structured notes and a handwriting PDF.</p>
          
          <div className="bg-slate-950 p-6 rounded-2xl border border-slate-800 text-left space-y-4">
            {[
              "Capturing speech transcript...",
              "Analysing spoken content for key topics...",
              "Structuring notes from your speech...",
              "Generating action items from discussion...",
              "Compiling handwriting-style PDF...",
              "Finalising study guide..."
            ].map((step, idx) => (
              <div key={idx} className="flex items-center space-x-3 text-sm">
                {idx < processingStep ? (
                  <CheckCircle className="h-5 w-5 text-emerald-400 flex-shrink-0" />
                ) : idx === processingStep ? (
                  <Loader2 className="h-5 w-5 animate-spin text-brand-400 flex-shrink-0" />
                ) : (
                  <div className="h-5 w-5 rounded-full border border-slate-700 flex-shrink-0" />
                )}
                <span className={idx <= processingStep ? "text-slate-200" : "text-slate-500"}>
                  {step}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  const jitsiRoomName = meeting.meetingLink ? meeting.meetingLink.split("/").pop() : id;
  const jitsiUrl = `https://jitsi.riot.im/${jitsiRoomName}`;

  return (
    <div className="h-full flex flex-col space-y-4">

      {/* Custom End Meeting Confirmation Modal */}
      {showEndConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full mx-4 space-y-5">
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0">
                <span className="text-red-600 text-lg">⚠</span>
              </div>
              <div>
                <h3 className="font-bold text-slate-800 text-lg">End Class Session?</h3>
                <p className="text-slate-500 text-sm">This will generate AI notes from everything you spoke.</p>
              </div>
            </div>

            <div className="bg-slate-50 rounded-xl p-4 text-sm text-slate-600 space-y-1">
              <p className="font-semibold text-slate-700">Speech captured so far:</p>
              <p className="text-xs text-slate-500 italic">
                {accumulatedTranscriptRef.current.trim()
                  ? `"${accumulatedTranscriptRef.current.trim().slice(0, 150)}${accumulatedTranscriptRef.current.length > 150 ? '...' : '"'}`
                  : "No speech captured yet. Speak into your mic before ending."}
              </p>
            </div>

            <div className="flex space-x-3 pt-1">
              <button
                onClick={() => setShowEndConfirm(false)}
                className="flex-1 px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition"
              >
                Cancel — Continue Session
              </button>
              <button
                onClick={handleEndMeeting}
                className="flex-1 px-4 py-2.5 rounded-xl bg-red-600 hover:bg-red-700 text-white font-bold text-sm transition"
              >
                End & Generate Notes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Top bar */}
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-slate-800">{meeting.title}</h2>
          <span className="text-xs text-slate-500">{meeting.description || "Classroom Session"}</span>
        </div>
        
        <div className="flex items-center space-x-3">
          {/* Toggle embedded Jitsi call */}
          <button
            onClick={() => {
              const nextCall = !callStarted;
              setCallStarted(nextCall);
              if (nextCall && !isRecording) {
                startSpeechRecognition(socket || socketRef.current);
              }
            }}
            className="px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-2 bg-brand-600 hover:bg-brand-500 text-white transition shadow-sm"
          >
            <span>🎥</span>
            <span>{callStarted ? "Close Video Call" : "Join Video Call"}</span>
          </button>

          <button
            onClick={toggleRecording}
            className={`px-4 py-2 rounded-lg text-xs font-bold flex items-center space-x-2 transition shadow-sm ${
              isRecording 
                ? "bg-red-500 hover:bg-red-600 text-white" 
                : "bg-slate-100 hover:bg-slate-200 text-slate-700"
            }`}
          >
            {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
            <span>{isRecording ? "Stop Recording" : "Record Mic Audio"}</span>
          </button>
          
          {user?.role === "teacher" && (
            <button
              onClick={() => setShowEndConfirm(true)}
              className="bg-red-600 hover:bg-red-700 text-white text-xs font-bold px-4 py-2 rounded-lg shadow-sm transition"
            >
              End Meeting
            </button>
          )}
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-4 min-h-[420px]">
        
        {/* Video Call Panel */}
        <div className="lg:col-span-3 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl border border-slate-700 shadow-inner flex flex-col items-center justify-center p-2 relative overflow-hidden min-h-[450px]">
          {callStarted ? (
            <iframe
              src={`${jitsiUrl}#userInfo.displayName="${encodeURIComponent(user?.name || 'User')}"&config.prejoinPageEnabled=false`}
              allow="camera; microphone; fullscreen; display-capture; autoplay"
              className="w-full h-full rounded-xl border-none min-h-[450px]"
              title="Jitsi Meeting"
            />
          ) : (
            <div className="flex flex-col items-center justify-center space-y-6 p-8 flex-1">
              <div className="flex items-center space-x-3">
                <span className="h-3 w-3 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-slate-300 text-sm font-medium">Session LIVE — {meeting.title}</span>
              </div>

              <div className="text-6xl">🎥</div>

              <div className="text-center space-y-2">
                <h3 className="text-white font-bold text-lg">Video Call Ready</h3>
                <p className="text-slate-400 text-sm max-w-xs">
                  Click the button below to join the call directly inside the app.
                </p>
              </div>

              <button
                onClick={() => {
                  setCallStarted(true);
                  if (!isRecording) {
                    startSpeechRecognition(socket || socketRef.current);
                  }
                }}
                className="bg-brand-600 hover:bg-brand-500 text-white font-bold px-8 py-3 rounded-xl shadow-lg text-sm transition transform hover:-translate-y-0.5 flex items-center space-x-2"
              >
                <span>🚀</span>
                <span>{user?.role === "teacher" ? "Start Video Call" : "Join Video Call"}</span>
              </button>

              <p className="text-slate-600 text-xs text-center">
                Room: <span className="text-slate-400 font-mono">{jitsiRoomName}</span>
              </p>
            </div>
          )}
        </div>

        {/* Live Audio Transcript Sidebar */}
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 flex flex-col justify-between">
          <div className="flex-1 overflow-hidden flex flex-col">
            <h3 className="font-bold text-slate-800 text-sm flex items-center space-x-2 mb-4">
              <span className={`h-2.5 w-2.5 rounded-full ${isRecording ? 'bg-red-500 recording-pulse' : 'bg-slate-300'}`} />
              <span>Live Transcription Feed</span>
            </h3>
            
            <div className="space-y-3 overflow-y-auto flex-1 pr-1">
              {speechError && (
                <div className="bg-red-50 text-red-700 text-xs p-2.5 rounded-xl border border-red-200 mb-3 font-semibold">
                  ⚠️ {speechError}
                </div>
              )}
              {liveTranscript.length === 0 ? (
                <div className="text-center py-10 text-xs text-slate-400 space-y-2">
                  <div className="text-2xl">🎙️</div>
                  <p>Click <strong>Record Mic Audio</strong> and speak — your words will appear here live.</p>
                </div>
              ) : (
                liveTranscript.map((t, idx) => (
                  <div key={idx} className="text-xs bg-slate-50 border border-slate-100 p-2.5 rounded-xl">
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-bold text-brand-700">{t.sender}</span>
                      <span className="text-[10px] text-slate-400">{t.timestamp}</span>
                    </div>
                    <p className="text-slate-600">{t.text}</p>
                  </div>
                ))
              )}
            </div>
          </div>
          
          <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-xl text-[10px] text-slate-500 mt-3">
            🔒 Speech is captured locally and used to generate your study notes.
          </div>
        </div>
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// Notes Viewer View (Patrick Hand handwriting font preview)
// -------------------------------------------------------------
const NotesViewer = () => {
  const { id } = useParams();
  const [notes, setNotes] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNotes = async () => {
      try {
        setLoading(true);
        const data = await api.getNotes(id);
        setNotes(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchNotes();
  }, [id]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-brand-600" />
      </div>
    );
  }

  if (!notes) {
    return (
      <div className="text-center py-12">
        <FileText className="mx-auto h-12 w-12 text-slate-300" />
        <h4 className="mt-4 text-sm font-semibold text-slate-600">No study notes found</h4>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Downloader toolbar */}
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-slate-800">
            {notes.meetingTitle ? `${notes.meetingTitle} — Session Notes` : "Generated Classroom Notes"}
          </h2>
          <div className="flex items-center space-x-3 mt-0.5">
            <span className="text-xs text-slate-400">Compiled on {new Date(notes.generatedAt).toLocaleString()}</span>
            {notes.transcriptText && (
              <span className="text-xs bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-0.5 rounded-full">
                🎙 {notes.transcriptText.split(" ").filter(Boolean).length} words from your speech
              </span>
            )}
          </div>
        </div>
        
        <a
          href={api.getNotesPdfUrl(id)}
          target="_blank"
          rel="noopener noreferrer"
          className="bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold px-4 py-2.5 rounded-xl shadow-md flex items-center space-x-1.5 transition-all transform hover:-translate-y-0.5"
        >
          <FileDown className="h-4.5 w-4.5" />
          <span>Download handwriting PDF</span>
        </a>
      </div>

      {/* Styled Notebook Sheet layout */}
      <div className="notebook-paper p-8 rounded-3xl min-h-[600px] border border-slate-200">
        <div className="notebook-margin-line" />
        
        {/* Margin shifted content */}
        <div className="pl-14 pr-4 py-2 select-text font-handwriting text-slate-800 text-lg">
          <h1 className="text-3xl font-bold text-slate-900 border-b border-indigo-200 pb-2 mb-6 tracking-wide">
            LECTURE STUDY NOTES GUIDE
          </h1>

          <div className="space-y-8">
            {notes.structuredContent.map((section, idx) => (
              <div key={idx} className="space-y-3">
                <h3 className="text-xl font-bold text-teal-800 flex items-center space-x-2">
                  <span># {section.heading}</span>
                </h3>
                
                <ul className="list-none space-y-2 pl-4">
                  {section.bullets.map((bullet, bulletIdx) => (
                    <li key={bulletIdx} className="flex items-start">
                      <span className="text-indigo-400 mr-2 flex-shrink-0">•</span>
                      <span>{bullet}</span>
                    </li>
                  ))}
                </ul>

                {/* Inline Mermaid Diagram flowchart */}
                {section.diagramMermaid && (
                  <div className="mt-4 max-w-lg mx-auto">
                    <MermaidDiagram chart={section.diagramMermaid} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// Task Board View (Kanban style tracking panel)
// -------------------------------------------------------------
const TaskBoard = () => {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncingId, setSyncingId] = useState(null);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const data = await api.getTasks();
      setTasks(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTasks();
  }, []);

  const handleSync = async (taskId) => {
    try {
      setSyncingId(taskId);
      await api.syncTask(taskId);
      loadTasks();
    } catch (e) {
      alert("Failed syncing task to connected board.");
    } finally {
      setSyncingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-brand-600" />
      </div>
    );
  }

  // Kanban Columns
  const pendingTasks = tasks.filter(t => t.status === "pending");
  const syncedTasks = tasks.filter(t => t.status === "synced");
  const completedTasks = tasks.filter(t => t.status === "completed");

  const renderCard = (t) => (
    <div key={t.id} className="bg-white p-4.5 rounded-xl border border-slate-100 shadow-sm space-y-3 hover:border-brand-200 transition">
      <div>
        <span className="text-[10px] font-bold text-brand-600 bg-brand-50 px-2.5 py-0.5 rounded-full uppercase border border-brand-200/20">
          {t.meetingTitle || "Class Task"}
        </span>
        <p className="text-sm font-semibold text-slate-800 mt-2 leading-relaxed">{t.description}</p>
      </div>

      <div className="border-t border-slate-50 pt-2.5 flex items-center justify-between text-xs">
        <div className="flex items-center space-x-1.5 text-slate-500">
          <User className="h-3.5 w-3.5" />
          <span className="font-medium">{t.assigneeName || "Unassigned"}</span>
        </div>

        {t.dueDate && (
          <div className="flex items-center space-x-1 text-slate-400">
            <Clock className="h-3.5 w-3.5" />
            <span>{new Date(t.dueDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>
          </div>
        )}
      </div>

      <div className="border-t border-slate-50 pt-2.5 flex items-center justify-between">
        {t.status === "pending" ? (
          <button
            onClick={() => handleSync(t.id)}
            disabled={syncingId === t.id}
            className="w-full bg-brand-600 hover:bg-brand-500 text-white text-[10px] font-bold py-2 rounded-lg flex items-center justify-center space-x-1 shadow-sm disabled:opacity-50"
          >
            {syncingId === t.id ? (
              <RefreshCw className="h-3 w-3 animate-spin" />
            ) : (
              <RefreshCw className="h-3 w-3" />
            )}
            <span>Sync to Notion / Jira</span>
          </button>
        ) : (
          <a
            href={t.externalTaskId || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="w-full border border-slate-100 hover:bg-slate-50 text-slate-500 text-[10px] font-semibold py-2 rounded-lg flex items-center justify-center space-x-1"
          >
            <span>Linked external ticket</span>
            <ExternalLink className="h-3 w-3" />
          </a>
        )}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-slate-100 shadow-sm">
        <div>
          <h2 className="text-lg font-bold text-slate-800">Action Items Task Board</h2>
          <span className="text-xs text-slate-400">Sync class assignments directly to external boards.</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Pending column */}
        <div className="bg-slate-100/50 p-4 rounded-2xl border border-slate-200/50 space-y-4 h-max min-h-[400px]">
          <h3 className="font-bold text-sm text-slate-700 flex justify-between items-center px-1">
            <span>Pending Sync</span>
            <span className="bg-slate-200 text-slate-700 px-2 py-0.5 rounded text-xs">{pendingTasks.length}</span>
          </h3>
          <div className="space-y-3">
            {pendingTasks.map(renderCard)}
          </div>
        </div>

        {/* Synced column */}
        <div className="bg-slate-100/50 p-4 rounded-2xl border border-slate-200/50 space-y-4 h-max min-h-[400px]">
          <h3 className="font-bold text-sm text-brand-700 flex justify-between items-center px-1">
            <span>Synced Boards</span>
            <span className="bg-brand-100 text-brand-700 px-2 py-0.5 rounded text-xs">{syncedTasks.length}</span>
          </h3>
          <div className="space-y-3">
            {syncedTasks.map(renderCard)}
          </div>
        </div>

        {/* Completed column */}
        <div className="bg-slate-100/50 p-4 rounded-2xl border border-slate-200/50 space-y-4 h-max min-h-[400px]">
          <h3 className="font-bold text-sm text-emerald-700 flex justify-between items-center px-1">
            <span>Completed</span>
            <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs">{completedTasks.length}</span>
          </h3>
          <div className="space-y-3">
            {completedTasks.map(renderCard)}
          </div>
        </div>
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// Settings Page (Integration setup)
// -------------------------------------------------------------
const Settings = () => {
  const { user, updateUserInfo } = useAuth();
  const [notionToken, setNotionToken] = useState("");
  const [notionDatabaseId, setNotionDatabaseId] = useState("");
  const [jiraHost, setJiraHost] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [jiraProjectKey, setJiraProjectKey] = useState("");
  
  const [notionSaving, setNotionSaving] = useState(false);
  const [jiraSaving, setJiraSaving] = useState(false);

  useEffect(() => {
    if (user?.connectedApps) {
      setNotionToken(user.connectedApps.notion?.token || "");
      setNotionDatabaseId(user.connectedApps.notion?.databaseId || "");
      
      setJiraHost(user.connectedApps.jira?.host || "");
      setJiraEmail(user.connectedApps.jira?.email || "");
      setJiraToken(user.connectedApps.jira?.token || "");
      setJiraProjectKey(user.connectedApps.jira?.projectKey || "");
    }
  }, [user]);

  const handleNotionSave = async (e) => {
    e.preventDefault();
    setNotionSaving(true);
    try {
      const updatedUser = await api.connectNotion(notionToken, notionDatabaseId);
      updateUserInfo(updatedUser);
      alert("Notion connection updated successfully!");
    } catch (err) {
      alert("Failed to save Notion integration details.");
    } finally {
      setNotionSaving(false);
    }
  };

  const handleJiraSave = async (e) => {
    e.preventDefault();
    setJiraSaving(true);
    try {
      const updatedUser = await api.connectJira(jiraHost, jiraEmail, jiraToken, jiraProjectKey);
      updateUserInfo(updatedUser);
      alert("Jira connection updated successfully!");
    } catch (err) {
      alert("Failed to save Jira integration details.");
    } finally {
      setJiraSaving(false);
    }
  };

  return (
    <div className="space-y-8 max-w-4xl">
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <h2 className="text-lg font-bold text-slate-800 flex items-center space-x-2">
          <SettingsIcon className="h-5 w-5 text-brand-500" />
          <span>Notion Integration Settings</span>
        </h2>
        <p className="text-slate-400 text-xs mt-1">
          Input your developer token and database details to allow task automation.
        </p>

        <form onSubmit={handleNotionSave} className="space-y-4 mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase">Integration Token</label>
              <input
                type="password"
                className="mt-1.5 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50"
                placeholder="secret_••••••••"
                value={notionToken}
                onChange={(e) => setNotionToken(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase">Database ID</label>
              <input
                type="text"
                className="mt-1.5 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50"
                placeholder="e.g. 1a2b3c4d..."
                value={notionDatabaseId}
                onChange={(e) => setNotionDatabaseId(e.target.value)}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={notionSaving}
            className="bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold px-4 py-2.5 rounded-lg flex items-center space-x-1"
          >
            {notionSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>Save Notion Settings</span>
          </button>
        </form>
      </div>

      <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
        <h2 className="text-lg font-bold text-slate-800 flex items-center space-x-2">
          <SettingsIcon className="h-5 w-5 text-brand-500" />
          <span>Jira Integration Settings</span>
        </h2>
        <p className="text-slate-400 text-xs mt-1">
          Provide your Atlassian Jira site host and access token details.
        </p>

        <form onSubmit={handleJiraSave} className="space-y-4 mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase">Jira Host URL</label>
              <input
                type="text"
                className="mt-1.5 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50"
                placeholder="e.g. your-domain.atlassian.net"
                value={jiraHost}
                onChange={(e) => setJiraHost(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase">Jira User Email</label>
              <input
                type="email"
                className="mt-1.5 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50"
                placeholder="jira-login@company.com"
                value={jiraEmail}
                onChange={(e) => setJiraEmail(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase">API Access Token</label>
              <input
                type="password"
                className="mt-1.5 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50"
                placeholder="ATATT••••••••"
                value={jiraToken}
                onChange={(e) => setJiraToken(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-500 uppercase">Jira Project Key</label>
              <input
                type="text"
                className="mt-1.5 block w-full px-3.5 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-1 focus:ring-brand-500 bg-slate-50"
                placeholder="e.g. PROJ"
                value={jiraProjectKey}
                onChange={(e) => setJiraProjectKey(e.target.value)}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={jiraSaving}
            className="bg-brand-600 hover:bg-brand-500 text-white text-xs font-bold px-4 py-2.5 rounded-lg flex items-center space-x-1"
          >
            {jiraSaving && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            <span>Save Jira Settings</span>
          </button>
        </form>
      </div>
    </div>
  );
};

// -------------------------------------------------------------
// App Core Routing Wrapper
// -------------------------------------------------------------
const App = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          {/* Landing / Auth pages */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <Dashboard />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/meeting/:id"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <MeetingRoom />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/notes/:id"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <NotesViewer />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/tasks"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <TaskBoard />
                </AppLayout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <AppLayout>
                  <Settings />
                </AppLayout>
              </ProtectedRoute>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default App;
