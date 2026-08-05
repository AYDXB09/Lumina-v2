/**
 * Lumina API client.
 * All calls go through authFetch (from AuthContext) for auto-refresh.
 */

const BASE = import.meta.env.VITE_API_BASE ?? "";

// ------------------------------------------------------------------ //
// Canvas                                                              //
// ------------------------------------------------------------------ //

export async function fetchCourses(authFetch) {
  const res = await authFetch(`${BASE}/api/canvas/courses`);
  if (!res.ok) throw new Error("Failed to fetch courses");
  return res.json();
}

export async function syncCourses(authFetch) {
  const res = await authFetch(`${BASE}/api/canvas/courses/sync`, { method: "POST" });
  if (!res.ok) throw new Error("Sync failed");
  return res.json();
}

export async function fetchAssignments(authFetch, courseId) {
  const res = await authFetch(`${BASE}/api/canvas/courses/${courseId}/assignments`);
  if (!res.ok) throw new Error("Failed to fetch assignments");
  return res.json();
}

export async function fetchAnnouncements(authFetch, courseId) {
  const res = await authFetch(`${BASE}/api/canvas/courses/${courseId}/announcements`);
  if (!res.ok) throw new Error("Failed to fetch announcements");
  return res.json();
}

export async function fetchQuizzes(authFetch, courseId) {
  const res = await authFetch(`${BASE}/api/canvas/courses/${courseId}/quizzes`);
  if (!res.ok) throw new Error("Failed to fetch quizzes");
  return res.json();
}

export async function fetchFeedback(authFetch, courseId) {
  const res = await authFetch(`${BASE}/api/canvas/courses/${courseId}/feedback`);
  if (!res.ok) throw new Error("Failed to fetch feedback");
  return res.json();
}

// ------------------------------------------------------------------ //
// Calendar                                                            //
// ------------------------------------------------------------------ //

export async function fetchCalendarSources(authFetch) {
  const res = await authFetch(`${BASE}/api/calendar/sources`);
  if (!res.ok) throw new Error("Failed to fetch calendar sources");
  return res.json();
}

export async function fetchCalendarEvents(authFetch, fetchWindow = "1week", syncFrequency = "query") {
  const res = await authFetch(
    `${BASE}/api/calendar/events?fetch_window=${fetchWindow}&sync_frequency=${syncFrequency}`
  );
  if (!res.ok) throw new Error("Failed to fetch calendar events");
  return res.json();
}

export async function syncCalendars(authFetch, fetchWindow = "1week") {
  const res = await authFetch(`${BASE}/api/calendar/sync?fetch_window=${fetchWindow}`, { method: "POST" });
  if (!res.ok) throw new Error("Calendar sync failed");
  return res.json();
}

// ------------------------------------------------------------------ //
// Student materials                                                   //
// ------------------------------------------------------------------ //

export async function fetchMaterials(authFetch) {
  const res = await authFetch(`${BASE}/api/materials`);
  if (!res.ok) throw new Error("Failed to fetch materials");
  return res.json();
}

/**
 * Upload one or more files.
 * @param {File|File[]} files  - single File or array of Files
 * @returns {Promise<{results, total, ok_count}>}
 */
export async function uploadMaterial(authFetch, files, courseId = null) {
  const form = new FormData();
  const fileList = Array.isArray(files) ? files : [files];
  fileList.forEach(f => form.append("files", f));
  if (courseId) form.append("course_id", courseId);
  const res = await authFetch(`${BASE}/api/materials/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const d = await res.json().catch(() => ({}));
    throw new Error(d.detail || "Upload failed");
  }
  return res.json();
}

export async function deleteMaterial(authFetch, filename) {
  const res = await authFetch(`${BASE}/api/materials/${encodeURIComponent(filename)}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Delete failed");
  return res.json();
}

// ------------------------------------------------------------------ //
// Mind map                                                            //
// ------------------------------------------------------------------ //

export async function fetchMindMap(authFetch, courseId) {
  const res = await authFetch(`${BASE}/api/mindmap/${courseId}`);
  if (!res.ok) throw new Error("Failed to fetch mind map");
  return res.json();
}

export async function regenerateMindMap(authFetch, courseId) {
  const res = await authFetch(`${BASE}/api/mindmap/${courseId}/regenerate`, { method: "POST" });
  if (!res.ok) throw new Error("Regeneration failed");
  return res.json();
}

// ------------------------------------------------------------------ //
// Study plan (cross-course — not scoped to a single course)          //
// ------------------------------------------------------------------ //

export async function fetchStudyPlan(authFetch) {
  const res = await authFetch(`${BASE}/api/studyplan`);
  if (!res.ok) throw new Error("Failed to fetch study plan");
  return res.json();
}

export async function regenerateStudyPlan(authFetch) {
  const res = await authFetch(`${BASE}/api/studyplan/regenerate`, { method: "POST" });
  if (!res.ok) throw new Error("Regeneration failed");
  return res.json();
}

// ------------------------------------------------------------------ //
// Adaptive quiz                                                       //
// ------------------------------------------------------------------ //

export async function startQuiz(authFetch, courseId, topic) {
  const res = await authFetch(`${BASE}/api/quiz/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ course_id: courseId, topic }),
  });
  if (!res.ok) throw new Error("Failed to start quiz");
  return res.json();
}

export async function answerQuiz(authFetch, attemptId, selectedIndex) {
  const res = await authFetch(`${BASE}/api/quiz/${attemptId}/answer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ selected_index: selectedIndex }),
  });
  if (!res.ok) throw new Error("Failed to submit answer");
  return res.json();
}

export async function nextQuizQuestion(authFetch, attemptId) {
  const res = await authFetch(`${BASE}/api/quiz/${attemptId}/next`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to load next question");
  return res.json();
}

export async function finishQuiz(authFetch, attemptId) {
  const res = await authFetch(`${BASE}/api/quiz/${attemptId}/finish`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to finish quiz");
  return res.json();
}

// ------------------------------------------------------------------ //
// Admin knowledge base                                                //
// ------------------------------------------------------------------ //

export async function fetchAdminMaterials(authFetch) {
  const res = await authFetch(`${BASE}/api/admin/materials`);
  if (!res.ok) throw new Error("Failed to fetch admin materials");
  return res.json();
}

export async function deleteAdminMaterial(authFetch, materialId) {
  const res = await authFetch(`${BASE}/api/admin/materials/${materialId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Delete failed");
  return res.json();
}

// ------------------------------------------------------------------ //
// Chat sessions                                                       //
// ------------------------------------------------------------------ //

export async function fetchSessions(authFetch, courseId = null) {
  const url = courseId
    ? `${BASE}/api/chat/sessions?course_id=${courseId}`
    : `${BASE}/api/chat/sessions`;
  const res = await authFetch(url);
  if (!res.ok) throw new Error("Failed to fetch sessions");
  return res.json();
}

export async function fetchMessages(authFetch, sessionId) {
  const res = await authFetch(`${BASE}/api/chat/sessions/${sessionId}/messages`);
  if (!res.ok) throw new Error("Failed to fetch messages");
  return res.json();
}

export async function deleteSession(authFetch, sessionId) {
  const res = await authFetch(`${BASE}/api/chat/sessions/${sessionId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete session");
  return res.json();
}

// ------------------------------------------------------------------ //
// Streaming chat                                                      //
// ------------------------------------------------------------------ //

/**
 * Stream a chat response via SSE.
 *
 * @param {Function} authFetch    - from AuthContext
 * @param {Array}    messages     - [{ role, content }]
 * @param {Object}   opts         - { sessionId, courseId }
 * @param {Function} onChunk      - called with each text chunk string
 * @param {Function} onToolCall   - called with { name, args }
 * @returns {Promise<string>}     - full assembled response
 */
export async function streamChat(authFetch, messages, opts = {}, onChunk, onToolCall, onSessionId) {
  const controller = new AbortController();
  opts.signal?.(controller);   // hand the abort fn to the caller

  const res = await authFetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      session_id: opts.sessionId ?? null,
      course_id:  opts.courseId  ?? null,
    }),
    signal: controller.signal,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Chat request failed");
  }

  const reader  = res.body.getReader();
  const decoder = new TextDecoder();
  let   buffer  = "";
  let   full    = "";

  while (true) {
    let done, value;
    try {
      ({ done, value } = await reader.read());
    } catch (e) {
      if (e.name === "AbortError") return full;  // user stopped — return what we have
      throw e;
    }
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // keep incomplete last line

    for (const line of lines) {
      if (!line.startsWith("data:")) continue;
      const raw = line.slice(5).trim();
      if (raw === "[DONE]") return full;

      try {
        const event = JSON.parse(raw);
        if (event.type === "session_id") {
          onSessionId?.(event.session_id);
        } else if (event.type === "content" && event.text) {
          full += event.text;
          onChunk?.(event.text);
        } else if (event.type === "tool_call") {
          onToolCall?.(event);
        } else if (event.type === "error") {
          throw new Error(event.message ?? "AI provider error");
        }
      } catch {
        // Ignore malformed chunks
      }
    }
  }

  return full;
}
