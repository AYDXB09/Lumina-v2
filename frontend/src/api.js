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
  const res = await authFetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages,
      session_id: opts.sessionId ?? null,
      course_id:  opts.courseId  ?? null,
    }),
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
    const { done, value } = await reader.read();
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
        }
      } catch {
        // Ignore malformed chunks
      }
    }
  }

  return full;
}
