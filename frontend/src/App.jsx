/**
 * App.jsx — root component.
 *
 * Auth gate → LoginScreen or MainLayout.
 * MainLayout: Sidebar + ChatView + RightPanel (when open).
 * SettingsProvider wraps everything so all components can read/write settings.
 */

import React, { useState, useEffect, useRef } from "react";
import { useAuth } from "./contexts/AuthContext.jsx";
import { SettingsProvider } from "./contexts/SettingsContext.jsx";
import { useIsMobile } from "./hooks/useIsMobile.js";
import LoginScreen from "./components/LoginScreen.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ChatView from "./components/ChatView.jsx";
import RightPanel from "./components/RightPanel.jsx";
import SettingsModal from "./components/SettingsModal.jsx";
import { fetchCourses, syncCourses } from "./api.js";

function LoadingSpinner() {
  return (
    <div style={{
      height: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "var(--color-text-muted)",
      fontSize: "14px",
      background: "var(--color-bg)",
    }}>
      Loading…
    </div>
  );
}

function MainLayout() {
  const { authFetch } = useAuth();
  const isMobile = useIsMobile();

  const [courses, setCourses]               = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null);
  const [syncing, setSyncing]               = useState(false);
  const [sidebarOpen, setSidebarOpen]       = useState(!isMobile);
  const [showRightPanel, setShowRightPanel] = useState(false);
  const [showSettings, setShowSettings]     = useState(false);
  const chatSendRef = useRef(null);  // receives fireQuickAction from ChatView

  useEffect(() => { loadCourses(); }, []);
  useEffect(() => { setShowRightPanel(false); }, [selectedCourse]);

  const loadCourses = async () => {
    try {
      const data = await fetchCourses(authFetch);
      const list = data.courses ?? [];
      setCourses(list);
      // Auto-select first course if nothing is selected
      if (list.length > 0) {
        setSelectedCourse(prev => prev ?? list[0]);
      } else {
        handleSync();
      }
    } catch (err) {
      console.error("Failed to load courses:", err);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncCourses(authFetch);
      await loadCourses();
    } catch (err) {
      console.error("Sync failed:", err);
    } finally {
      setSyncing(false);
    }
  };

  const handleToggleSidebar = () => {
    setSidebarOpen(p => !p);
    // On mobile, close right panel when sidebar opens (avoid double overlay)
    if (isMobile && !sidebarOpen) setShowRightPanel(false);
  };

  const handleToggleRightPanel = () => {
    setShowRightPanel(p => !p);
    // On mobile, close sidebar when right panel opens
    if (isMobile && !showRightPanel) setSidebarOpen(false);
  };

  return (
    <div style={styles.layout}>
      {/* ---- Mobile backdrop for sidebar ---- */}
      {isMobile && sidebarOpen && (
        <div
          style={styles.mobileBackdrop}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* ---- Mobile backdrop for right panel ---- */}
      {isMobile && showRightPanel && (
        <div
          style={styles.mobileBackdrop}
          onClick={() => setShowRightPanel(false)}
        />
      )}

      {/* ---- Left: Sidebar ---- */}
      <Sidebar
        open={sidebarOpen}
        courses={courses}
        selectedCourse={selectedCourse}
        onSelectCourse={(c) => { setSelectedCourse(c); if (isMobile) setSidebarOpen(false); }}
        onSync={handleSync}
        syncing={syncing}
        onToggle={handleToggleSidebar}
        onOpenSettings={() => setShowSettings(true)}
      />

      {/* ---- Centre: Chat ---- */}
      <div style={styles.centre}>
        <ChatView
          key={selectedCourse?.id ?? "all"}
          course={selectedCourse}
          onToggleSidebar={handleToggleSidebar}
          onToggleRightPanel={handleToggleRightPanel}
          rightPanelOpen={showRightPanel}
          syncing={syncing}
          registerSend={fn => { chatSendRef.current = fn; }}
        />
      </div>

      {/* ---- Right: Assignments + Mind Map panel ---- */}
      {showRightPanel && selectedCourse && (
        <RightPanel
          course={selectedCourse}
          onClose={() => setShowRightPanel(false)}
          onAskAI={prompt => {
            chatSendRef.current?.(prompt);
            setShowRightPanel(false); // close panel, show the answer in chat
          }}
        />
      )}

      {/* ---- Settings modal ---- */}
      {showSettings && (
        <SettingsModal onClose={() => setShowSettings(false)} />
      )}
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingSpinner />;
  return (
    <SettingsProvider>
      {!user ? <LoginScreen /> : <MainLayout />}
    </SettingsProvider>
  );
}

const styles = {
  layout: {
    display: "flex",
    height: "100vh",
    width: "100vw",
    overflow: "hidden",
    background: "var(--color-bg)",
    position: "relative",
  },
  centre: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    minWidth: 0,
  },
  mobileBackdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(0,0,0,0.4)",
    zIndex: 130,
    animation: "fadeInUp 0.15s ease",
  },
};
