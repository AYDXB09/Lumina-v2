/**
 * App.jsx — root component.
 *
 * Auth gate → LoginScreen or main layout.
 * Main layout: Sidebar (courses) + ChatView (right panel).
 */

import React, { useState, useEffect } from "react";
import { useAuth } from "./contexts/AuthContext.jsx";
import LoginScreen from "./components/LoginScreen.jsx";
import Sidebar from "./components/Sidebar.jsx";
import ChatView from "./components/ChatView.jsx";
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
    }}>
      Loading…
    </div>
  );
}

function MainLayout() {
  const { authFetch } = useAuth();
  const [courses, setCourses]               = useState([]);
  const [selectedCourse, setSelectedCourse] = useState(null); // null = all courses
  const [syncing, setSyncing]               = useState(false);

  // Load courses on mount
  useEffect(() => {
    loadCourses();
  }, []);

  const loadCourses = async () => {
    try {
      const data = await fetchCourses(authFetch);
      setCourses(data.courses ?? []);
      // Auto-sync if no courses yet
      if ((data.courses ?? []).length === 0) {
        handleSync();
      }
    } catch (err) {
      console.error("Failed to load courses:", err);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const data = await syncCourses(authFetch);
      // Reload after sync
      await loadCourses();
    } catch (err) {
      console.error("Sync failed:", err);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div style={styles.layout}>
      <Sidebar
        courses={courses}
        selectedCourse={selectedCourse}
        onSelectCourse={setSelectedCourse}
        onSync={handleSync}
        syncing={syncing}
      />
      <main style={styles.main}>
        <ChatView
          key={selectedCourse?.id ?? "all"}   // remount on course switch
          course={selectedCourse}
        />
      </main>
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();
  if (loading)  return <LoadingSpinner />;
  if (!user)    return <LoginScreen />;
  return <MainLayout />;
}

const styles = {
  layout: {
    display: "flex",
    height: "100vh",
    overflow: "hidden",
  },
  main: {
    flex: 1,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
};
