/**
 * QuizView — adaptive quiz for the active course.
 *
 * Ported from v1's QuizView.jsx concept (one question at a time, difficulty
 * tied to a running mastery score) with a key fix: mastery now persists to
 * Supabase (mastery_scores table) via the backend, instead of living only
 * in React state and resetting on every refresh like v1 did.
 *
 * Props:
 *   course — { id, name }
 */

import React, { useState } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";
import { startQuiz, answerQuiz, nextQuizQuestion, finishQuiz } from "../api.js";

const DEFAULT_COUNT = 5;

export default function QuizView({ course }) {
  const { authFetch } = useAuth();

  const [topic, setTopic] = useState("");
  const [count, setCount] = useState(DEFAULT_COUNT);
  const [phase, setPhase] = useState("setup"); // setup | loading | question | feedback | summary
  const [error, setError] = useState(null);

  const [attemptId, setAttemptId] = useState(null);
  const [questionNumber, setQuestionNumber] = useState(0);
  const [question, setQuestion] = useState(null);
  const [mastery, setMastery] = useState(0.5);
  const [selected, setSelected] = useState(null);
  const [feedback, setFeedback] = useState(null); // { correct, correct_index, hint }
  const [summary, setSummary] = useState(null);

  async function handleStart() {
    if (!topic.trim() || !course?.id) return;
    setPhase("loading");
    setError(null);
    try {
      const res = await startQuiz(authFetch, course.id, topic.trim());
      setAttemptId(res.attempt_id);
      setQuestionNumber(res.question_number);
      setQuestion(res.question);
      setMastery(res.mastery);
      setSelected(null);
      setFeedback(null);
      setPhase("question");
    } catch (e) {
      setError(e.message);
      setPhase("setup");
    }
  }

  async function handleSelect(index) {
    if (feedback) return; // already answered
    setSelected(index);
    setPhase("loading");
    try {
      const res = await answerQuiz(authFetch, attemptId, index);
      setFeedback(res);
      setMastery(res.mastery);
      setPhase("feedback");
    } catch (e) {
      setError(e.message);
      setPhase("question");
    }
  }

  async function handleNext() {
    if (questionNumber >= count) {
      await handleFinish();
      return;
    }
    setPhase("loading");
    setError(null);
    try {
      const res = await nextQuizQuestion(authFetch, attemptId);
      setQuestionNumber(res.question_number);
      setQuestion(res.question);
      setMastery(res.mastery);
      setSelected(null);
      setFeedback(null);
      setPhase("question");
    } catch (e) {
      setError(e.message);
      setPhase("feedback");
    }
  }

  async function handleFinish() {
    setPhase("loading");
    try {
      const res = await finishQuiz(authFetch, attemptId);
      setSummary(res);
      setPhase("summary");
    } catch (e) {
      setError(e.message);
      setPhase("feedback");
    }
  }

  function handleRestart() {
    setPhase("setup");
    setTopic("");
    setAttemptId(null);
    setQuestionNumber(0);
    setQuestion(null);
    setSelected(null);
    setFeedback(null);
    setSummary(null);
    setError(null);
  }

  if (!course?.id) {
    return <div style={s.centered}><p style={{ color: "var(--color-text-muted)", fontSize: "13px" }}>Select a course to start a quiz.</p></div>;
  }

  return (
    <div style={s.wrap}>
      {phase === "setup" && (
        <div style={s.setupForm}>
          <label style={s.label}>What topic do you want to be quizzed on?</label>
          <input
            style={s.input}
            value={topic}
            onChange={e => setTopic(e.target.value)}
            placeholder="e.g. Le Chatelier's principle"
            onKeyDown={e => e.key === "Enter" && handleStart()}
          />
          <label style={s.label}>Number of questions</label>
          <input
            style={{ ...s.input, width: "80px" }}
            type="number"
            min={1}
            max={20}
            value={count}
            onChange={e => setCount(Math.max(1, Math.min(20, Number(e.target.value) || DEFAULT_COUNT)))}
          />
          {error && <p style={s.error}>{error}</p>}
          <button style={s.primaryBtn} onClick={handleStart} disabled={!topic.trim()}>
            Start Quiz
          </button>
        </div>
      )}

      {phase === "loading" && (
        <div style={s.centered}><p style={{ color: "var(--color-text-faint)", fontSize: "13px" }}>Thinking…</p></div>
      )}

      {(phase === "question" || phase === "feedback") && question && (
        <div style={s.quizBody}>
          <div style={s.progressRow}>
            <span style={s.progressText}>Question {questionNumber} of {count}</span>
            <MasteryBar mastery={mastery} />
          </div>

          <p style={s.questionText}>{question.question}</p>

          <div style={s.options}>
            {question.options.map((opt, i) => {
              const isSelected = selected === i;
              const isCorrectAnswer = feedback && i === feedback.correct_index;
              const isWrongSelected = feedback && isSelected && !feedback.correct;
              return (
                <button
                  key={i}
                  style={{
                    ...s.option,
                    ...(isSelected ? s.optionSelected : {}),
                    ...(isCorrectAnswer ? s.optionCorrect : {}),
                    ...(isWrongSelected ? s.optionWrong : {}),
                  }}
                  onClick={() => handleSelect(i)}
                  disabled={!!feedback}
                >
                  {opt}
                </button>
              );
            })}
          </div>

          {feedback && (
            <div style={s.feedbackBox}>
              <p style={{ ...s.feedbackText, color: feedback.correct ? "var(--pill-green-text)" : "var(--pill-red-text)" }}>
                {feedback.correct ? "Correct!" : "Not quite."}
              </p>
              {!feedback.correct && feedback.hint && (
                <p style={s.hintText}>Hint: {feedback.hint}</p>
              )}
              <button style={s.primaryBtn} onClick={handleNext}>
                {questionNumber >= count ? "Finish Quiz" : "Next Question"}
              </button>
            </div>
          )}

          {!feedback && question.hint && (
            <p style={s.hintTextMuted}>Hint available after you answer.</p>
          )}

          {error && <p style={s.error}>{error}</p>}
        </div>
      )}

      {phase === "summary" && summary && (
        <div style={s.summaryBox}>
          <h3 style={s.summaryScore}>{summary.correct_count} / {summary.total}</h3>
          <p style={s.summaryPct}>{Math.round(summary.score * 100)}% correct</p>
          <button style={s.primaryBtn} onClick={handleRestart}>Start a New Quiz</button>
        </div>
      )}
    </div>
  );
}

function MasteryBar({ mastery }) {
  const pct = Math.round(mastery * 100);
  const color = mastery < 0.3 ? "var(--pill-red-text)" : mastery < 0.7 ? "var(--pill-amber-text)" : "var(--pill-green-text)";
  return (
    <div style={s.masteryWrap} title={`Mastery: ${pct}%`}>
      <div style={s.masteryTrack}>
        <div style={{ ...s.masteryFill, width: `${pct}%`, background: color }} />
      </div>
      <span style={{ ...s.masteryLabel, color }}>{pct}%</span>
    </div>
  );
}

const s = {
  wrap: { display: "flex", flexDirection: "column", height: "100%", overflowY: "auto", padding: "16px" },
  centered: { display: "flex", alignItems: "center", justifyContent: "center", height: "100%" },
  setupForm: { display: "flex", flexDirection: "column", gap: "8px" },
  label: { fontSize: "12px", color: "var(--color-text-muted)", marginTop: "8px" },
  input: {
    padding: "8px 10px", borderRadius: "8px", border: "1px solid var(--color-border)",
    background: "var(--color-surface)", color: "var(--color-text)", fontSize: "13px",
  },
  primaryBtn: {
    marginTop: "10px", padding: "8px 16px", borderRadius: "8px", border: "none",
    background: "var(--color-primary)", color: "var(--color-primary-text)",
    fontSize: "13px", fontWeight: 600, cursor: "pointer", alignSelf: "flex-start",
  },
  error: { fontSize: "12px", color: "var(--pill-red-text)" },
  quizBody: { display: "flex", flexDirection: "column", gap: "12px" },
  progressRow: { display: "flex", justifyContent: "space-between", alignItems: "center" },
  progressText: { fontSize: "12px", color: "var(--color-text-faint)" },
  masteryWrap: { display: "flex", alignItems: "center", gap: "6px" },
  masteryTrack: { width: "60px", height: "6px", borderRadius: "3px", background: "var(--color-surface-2)", overflow: "hidden" },
  masteryFill: { height: "100%", borderRadius: "3px", transition: "width 0.3s" },
  masteryLabel: { fontSize: "11px", fontWeight: 600 },
  questionText: { fontSize: "14px", color: "var(--color-text)", lineHeight: 1.5 },
  options: { display: "flex", flexDirection: "column", gap: "8px" },
  option: {
    textAlign: "left", padding: "10px 12px", borderRadius: "8px",
    border: "1px solid var(--color-border)", background: "var(--color-surface)",
    color: "var(--color-text)", fontSize: "13px", cursor: "pointer",
  },
  optionSelected: { borderColor: "var(--color-primary)" },
  optionCorrect: { borderColor: "var(--pill-green-text)", background: "var(--pill-green-bg)" },
  optionWrong: { borderColor: "var(--pill-red-text)", background: "var(--pill-red-bg)" },
  feedbackBox: { display: "flex", flexDirection: "column", gap: "6px", paddingTop: "8px", borderTop: "1px solid var(--color-border)" },
  feedbackText: { fontSize: "13px", fontWeight: 600, margin: 0 },
  hintText: { fontSize: "12px", color: "var(--color-text-muted)", margin: 0 },
  hintTextMuted: { fontSize: "11px", color: "var(--color-text-faint)", fontStyle: "italic" },
  summaryBox: { display: "flex", flexDirection: "column", alignItems: "center", gap: "6px", padding: "24px 0" },
  summaryScore: { fontSize: "32px", margin: 0, color: "var(--color-text)" },
  summaryPct: { fontSize: "13px", color: "var(--color-text-muted)", margin: 0 },
};
