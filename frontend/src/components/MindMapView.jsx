/**
 * MindMapView — interactive mind map for a course.
 *
 * Ported and adapted from School-AI v1 TopicMindMap.jsx.
 * Pure React SVG rendering — no d3 or external libraries.
 *
 * Props:
 *   course    — { id, name }
 *   onAskAI   — fn(prompt)  called when user clicks "Ask AI" on a node
 */

import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext.jsx";

const BASE = import.meta.env.VITE_API_BASE ?? "";

// ------------------------------------------------------------------ //
// Constants                                                           //
// ------------------------------------------------------------------ //

const MIN_SCALE = 0.25;
const MAX_SCALE = 1.8;
const ROOT_BRANCH_GAP = 320;
const LEVEL_GAP = 260;
const LEAF_SPACING = 140;
const STAGE_PADDING_X = 140;
const STAGE_PADDING_Y = 90;

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function genId() { return Math.random().toString(36).slice(2); }

// ------------------------------------------------------------------ //
// Layout algorithm (adapted from v1 buildGraphLayout)                //
// ------------------------------------------------------------------ //

function findRoot(topics) {
  return topics.find(t => t.isRoot)
    || topics.find(t => !t.parentId)
    || topics[0]
    || null;
}

function buildLayout(topics = []) {
  if (!topics.length) return { nodes: [], edges: [], viewBox: "0 0 800 600", activeWidth: 800, activeHeight: 600 };

  const topicMap = new Map(topics.map(t => [t.id, t]));
  const root = findRoot(topics);
  if (!root) return { nodes: [], edges: [], viewBox: "0 0 800 600", activeWidth: 800, activeHeight: 600 };

  const rootId = root.id;
  const levels = new Map([[rootId, 0]]);
  const sides  = new Map([[rootId, 0]]);
  const parents = new Map();
  const childrenOf = new Map();

  const addChild = (pid, cid) => {
    if (!childrenOf.has(pid)) childrenOf.set(pid, []);
    childrenOf.get(pid).push(cid);
  };

  topics.forEach(t => {
    if (!t || t.id === rootId) return;
    const pid = (t.parentId && t.parentId !== t.id && topicMap.has(t.parentId))
      ? t.parentId
      : rootId;
    parents.set(t.id, pid);
    addChild(pid, t.id);
  });

  function resolveLevel(id, depth = 0, seen = new Set()) {
    if (levels.has(id)) return levels.get(id);
    if (depth > topics.length || seen.has(id)) return 1;
    const pid = parents.get(id) || rootId;
    const ns = new Set(seen); ns.add(id);
    const pLevel = pid === rootId ? 0 : resolveLevel(pid, depth + 1, ns);
    const explicit = Number.isFinite(topicMap.get(id)?.level) ? topicMap.get(id).level : null;
    const resolved = Math.max(pLevel + 1, explicit || 1);
    levels.set(id, resolved);
    return resolved;
  }
  topics.forEach(t => { if (t.id !== rootId) resolveLevel(t.id); });

  const topLevel = childrenOf.get(rootId) || [];
  topLevel.forEach((cid, i) => sides.set(cid, i % 2 === 0 ? 1 : -1));

  function propagateSides(pid) {
    (childrenOf.get(pid) || []).forEach(cid => {
      sides.set(cid, sides.get(pid) || 1);
      propagateSides(cid);
    });
  }
  topLevel.forEach(cid => propagateSides(cid));

  const spanCache = new Map();
  function getSpan(id) {
    if (spanCache.has(id)) return spanCache.get(id);
    const children = childrenOf.get(id) || [];
    const span = children.length === 0 ? 1 : children.reduce((s, c) => s + getSpan(c), 0);
    spanCache.set(id, span);
    return span;
  }

  const stageCX = 1080;
  const stageCY = 900;
  const positions = new Map([[rootId, { x: stageCX, y: stageCY }]]);

  function nodeMetrics(level) {
    if (level === 0) return { w: 200, h: 72 };
    if (level === 1) return { w: 168, h: 60 };
    return { w: 140, h: 52 };
  }

  function placeGroup(pid, side, childIds, anchorY) {
    const pp = positions.get(pid);
    if (!pp || !childIds.length) return;
    const totalUnits = childIds.reduce((s, c) => s + getSpan(c), 0);
    let cursor = -totalUnits / 2;
    childIds.forEach(cid => {
      const span = getSpan(cid);
      const cy = anchorY + (cursor + span / 2) * LEAF_SPACING;
      const gap = pid === rootId ? ROOT_BRANCH_GAP : LEVEL_GAP;
      positions.set(cid, { x: pp.x + side * gap, y: cy });
      placeChildren(cid);
      cursor += span;
    });
  }

  function placeChildren(pid) {
    const children = childrenOf.get(pid) || [];
    if (!children.length) return;
    if (pid === rootId) {
      const left  = children.filter(c => (sides.get(c) || 1) < 0);
      const right = children.filter(c => (sides.get(c) || 1) >= 0);
      placeGroup(pid, -1, left,  stageCY);
      placeGroup(pid, 1,  right, stageCY);
      return;
    }
    const side = sides.get(pid) || 1;
    const py = positions.get(pid)?.y || stageCY;
    placeGroup(pid, side, children, py);
  }
  placeChildren(rootId);

  // Build node list
  const nodes = topics.map(t => {
    const pos = positions.get(t.id) || { x: stageCX, y: stageCY };
    const level = t.id === rootId ? 0 : (levels.get(t.id) || 1);
    const side  = level === 0 ? 0 : (sides.get(t.id) || 1);
    const { w, h } = nodeMetrics(level);
    return { ...t, x: pos.x, y: pos.y, width: w, height: h, level, side };
  });

  // Column packing to prevent overlap
  const columns = new Map();
  nodes.forEach(n => {
    const key = n.level === 0 ? "root" : `${n.level}:${n.side < 0 ? "L" : "R"}`;
    if (!columns.has(key)) columns.set(key, []);
    columns.get(key).push(n);
  });
  columns.forEach(col => {
    if (col.length < 2) return;
    const gap = 24;
    col.sort((a, b) => a.y - b.y);
    for (let i = 1; i < col.length; i++) {
      const prev = col[i - 1], curr = col[i];
      const minY = prev.y + (prev.height + curr.height) / 2 + gap;
      if (curr.y < minY) curr.y = minY;
    }
    col.reverse();
    for (let i = 1; i < col.length; i++) {
      const next = col[i - 1], curr = col[i];
      const maxY = next.y - (next.height + curr.height) / 2 - gap;
      if (curr.y > maxY) curr.y = maxY;
    }
    col.reverse();
    // Center column
    const top    = col[0].y    - col[0].height    / 2;
    const bottom = col[col.length - 1].y + col[col.length - 1].height / 2;
    const shift  = stageCY - (top + bottom) / 2;
    col.forEach(n => { n.y += shift; });
  });

  // Edges
  const edges = [...parents.entries()].map(([cid, pid]) => ({
    id: `${pid}::${cid}`,
    sourceId: pid,
    targetId: cid,
  }));

  // ViewBox
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  nodes.forEach(n => {
    minX = Math.min(minX, n.x - n.width  / 2 - STAGE_PADDING_X);
    maxX = Math.max(maxX, n.x + n.width  / 2 + STAGE_PADDING_X);
    minY = Math.min(minY, n.y - n.height / 2 - STAGE_PADDING_Y);
    maxY = Math.max(maxY, n.y + n.height / 2 + STAGE_PADDING_Y);
  });
  const aw = maxX - minX;
  const ah = maxY - minY;

  return { nodes, edges, viewBox: `${minX} ${minY} ${aw} ${ah}`, activeWidth: aw, activeHeight: ah };
}

function buildEdgePath(src, tgt) {
  const dir = tgt.x >= src.x ? 1 : -1;
  const sx = src.x + dir * Math.max(18, src.width / 2 - 14);
  const ex = tgt.x - dir * Math.max(18, tgt.width / 2 - 14);
  const curve = Math.max(80, Math.abs(ex - sx) * 0.4);
  return `M ${sx} ${src.y} C ${sx + curve * dir} ${src.y}, ${ex - curve * dir} ${tgt.y}, ${ex} ${tgt.y}`;
}

// ------------------------------------------------------------------ //
// Component                                                          //
// ------------------------------------------------------------------ //

export default function MindMapView({ course, onAskAI }) {
  const { authFetch } = useAuth();
  const shellRef = useRef(null);
  const dragRef  = useRef(null);

  const [topics, setTopics]           = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [selectedId, setSelectedId]   = useState(null);
  const [viewport, setViewport]       = useState({ x: 0, y: 0, scale: 0.7 });
  const [vpReady, setVpReady]         = useState(false);
  const [regenerating, setRegenerating] = useState(false);

  const graph   = useMemo(() => buildLayout(topics), [topics]);
  const nodeMap = useMemo(() => new Map(graph.nodes.map(n => [n.id, n])), [graph.nodes]);
  const selected = useMemo(() => nodeMap.get(selectedId) || null, [nodeMap, selectedId]);

  // ---- Fetch mind map ----
  useEffect(() => {
    if (!course?.id) return;
    setLoading(true);
    setError(null);
    authFetch(`${BASE}/api/mindmap/${course.id}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(d => {
        const t = (d.graph_data?.topics || []);
        setTopics(t);
        if (t.length) setSelectedId(t.find(x => x.isRoot)?.id || t[0].id);
      })
      .catch(e => setError(`Could not load mind map (${e})`))
      .finally(() => setLoading(false));
  }, [course?.id]);

  // ---- Default viewport (fit-to-shell) ----
  const getDefaultVp = useCallback(() => {
    const sw = shellRef.current?.clientWidth  || 600;
    const sh = shellRef.current?.clientHeight || 400;
    const lw = graph.activeWidth;
    const lh = graph.activeHeight;
    const fitScale = clamp(Math.min(sw / lw, sh / lh) * 0.88, MIN_SCALE, 1.0);
    return {
      x: Math.round((sw - lw * fitScale) / 2),
      y: Math.round((sh - lh * fitScale) / 2),
      scale: Number(fitScale.toFixed(2)),
    };
  }, [graph.activeWidth, graph.activeHeight]);

  useEffect(() => {
    if (!graph.nodes.length) return;
    const vp = getDefaultVp();
    setViewport(vp);
    setVpReady(true);
  }, [graph.nodes.length, getDefaultVp]);

  // Resize observer
  useEffect(() => {
    const shell = shellRef.current;
    if (!shell || typeof ResizeObserver === "undefined") return;
    const obs = new ResizeObserver(() => {
      if (!dragRef.current && vpReady) {
        setViewport(getDefaultVp());
      }
    });
    obs.observe(shell);
    return () => obs.disconnect();
  }, [vpReady, getDefaultVp]);

  // ---- Drag (pan) ----
  useEffect(() => {
    const onMove = e => {
      const d = dragRef.current;
      if (!d) return;
      setViewport(v => ({ ...v, x: d.ox + (e.clientX - d.sx), y: d.oy + (e.clientY - d.sy) }));
    };
    const onUp = () => { dragRef.current = null; };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup",   onUp);
    window.addEventListener("pointercancel", onUp);
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup",   onUp);
      window.removeEventListener("pointercancel", onUp);
    };
  }, []);

  const startDrag = e => {
    if (e.target.closest("[data-node]")) return; // don't pan when clicking node
    dragRef.current = { sx: e.clientX, sy: e.clientY, ox: viewport.x, oy: viewport.y };
    e.preventDefault();
  };

  // ---- Zoom ----
  const onWheel = e => {
    e.preventDefault();
    const delta = -e.deltaY * 0.001;
    setViewport(v => {
      const nextScale = clamp(v.scale + delta * v.scale, MIN_SCALE, MAX_SCALE);
      const shell = shellRef.current;
      const cx = shell ? e.clientX - shell.getBoundingClientRect().left : 0;
      const cy = shell ? e.clientY - shell.getBoundingClientRect().top  : 0;
      const wx = (cx - v.x) / v.scale;
      const wy = (cy - v.y) / v.scale;
      return { scale: nextScale, x: cx - wx * nextScale, y: cy - wy * nextScale };
    });
  };

  // ---- Regenerate ----
  async function handleRegenerate() {
    setRegenerating(true);
    try {
      const res = await authFetch(`${BASE}/api/mindmap/${course.id}/regenerate`, { method: "POST" });
      if (res.ok) {
        const d = await res.json();
        const t = d.graph_data?.topics || [];
        setTopics(t);
        setSelectedId(t.find(x => x.isRoot)?.id || t[0]?.id || null);
        setVpReady(false);
      }
    } finally { setRegenerating(false); }
  }

  // ---- Node colours ----
  function nodeColor(node) {
    if (node.level === 0) return { bg: "var(--color-primary)", text: "var(--color-primary-text)", border: "var(--color-primary)" };
    if (node.level === 1) return { bg: "var(--color-surface)", text: "var(--color-text)", border: "var(--color-primary)" };
    return { bg: "var(--color-surface-2)", text: "var(--color-text-muted)", border: "var(--color-border)" };
  }

  // ---- Render ----
  if (!course) {
    return (
      <div style={mm.empty}>
        <p style={{ color: "var(--color-text-muted)", fontSize: "13px" }}>Select a course to view its mind map.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={mm.empty}>
        <p style={{ color: "var(--color-text-faint)", fontSize: "13px" }}>Generating mind map…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={mm.empty}>
        <p style={{ color: "var(--pill-red-text)", fontSize: "13px" }}>{error}</p>
        <button style={mm.regenBtn} onClick={handleRegenerate} disabled={regenerating}>
          {regenerating ? "Regenerating…" : "Try again"}
        </button>
      </div>
    );
  }

  if (!topics.length) {
    return (
      <div style={mm.empty}>
        <p style={{ color: "var(--color-text-muted)", fontSize: "13px" }}>
          No content indexed yet. Sync your course first.
        </p>
      </div>
    );
  }

  return (
    <div style={mm.shell} ref={shellRef}
      onPointerDown={startDrag}
      onWheel={onWheel}
    >
      {/* Toolbar */}
      <div style={mm.toolbar}>
        <span style={mm.toolbarTitle}>{course.name}</span>
        <div style={{ display: "flex", gap: "6px" }}>
          <button style={mm.toolBtn} onClick={() => setViewport(v => ({ ...v, scale: clamp(v.scale + 0.15, MIN_SCALE, MAX_SCALE) }))}>+</button>
          <button style={mm.toolBtn} onClick={() => setViewport(v => ({ ...v, scale: clamp(v.scale - 0.15, MIN_SCALE, MAX_SCALE) }))}>−</button>
          <button style={mm.toolBtn} onClick={() => { setVpReady(false); setViewport(getDefaultVp()); setVpReady(true); }}>⊡</button>
          <button style={mm.toolBtn} onClick={handleRegenerate} disabled={regenerating} title="Regenerate">
            {regenerating ? "…" : "↺"}
          </button>
        </div>
      </div>

      {/* SVG canvas */}
      <svg
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", overflow: "visible", cursor: dragRef.current ? "grabbing" : "grab" }}
        preserveAspectRatio="none"
      >
        <g transform={`translate(${viewport.x},${viewport.y}) scale(${viewport.scale})`}>
          {/* Edges */}
          {graph.edges.map(edge => {
            const src = nodeMap.get(edge.sourceId);
            const tgt = nodeMap.get(edge.targetId);
            if (!src || !tgt) return null;
            const isSelected = edge.sourceId === selectedId || edge.targetId === selectedId;
            return (
              <path
                key={edge.id}
                d={buildEdgePath(src, tgt)}
                fill="none"
                stroke={isSelected ? "var(--color-primary)" : "var(--color-border)"}
                strokeWidth={isSelected ? 2 : 1.5}
                strokeOpacity={isSelected ? 0.9 : 0.5}
              />
            );
          })}

          {/* Nodes */}
          {graph.nodes.map(node => {
            const isSelected = node.id === selectedId;
            const colors = nodeColor(node);
            const rx = node.height / 2;
            return (
              <g
                key={node.id}
                data-node="true"
                transform={`translate(${node.x - node.width / 2},${node.y - node.height / 2})`}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedId(node.id)}
              >
                <rect
                  width={node.width}
                  height={node.height}
                  rx={rx}
                  ry={rx}
                  fill={isSelected ? "var(--color-primary)" : colors.bg}
                  stroke={isSelected ? "var(--color-primary)" : colors.border}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                  filter={isSelected ? "drop-shadow(0 4px 12px rgba(0,0,0,0.18))" : undefined}
                />
                <foreignObject x={8} y={0} width={node.width - 16} height={node.height}>
                  <div
                    xmlns="http://www.w3.org/1999/xhtml"
                    style={{
                      width: "100%",
                      height: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      textAlign: "center",
                      fontSize: node.level === 0 ? "13px" : node.level === 1 ? "12px" : "11px",
                      fontWeight: node.level === 0 ? "700" : node.level === 1 ? "600" : "500",
                      color: isSelected ? "var(--color-primary-text)" : colors.text,
                      lineHeight: "1.3",
                      padding: "4px",
                      wordBreak: "break-word",
                      overflow: "hidden",
                    }}
                  >
                    {node.label}
                  </div>
                </foreignObject>
              </g>
            );
          })}
        </g>
      </svg>

      {/* Selected node detail panel */}
      {selected && !selected.isRoot && (
        <div style={mm.detailPanel}>
          <div style={mm.detailLabel}>{selected.label}</div>
          {onAskAI && (
            <button
              style={mm.askBtn}
              onClick={() => onAskAI(`Tell me about "${selected.label}" from my ${course.name} course.`)}
            >
              💡 Ask AI about this
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---- Styles ----
const mm = {
  shell: {
    position: "relative",
    width: "100%",
    height: "100%",
    minHeight: "400px",
    background: "var(--color-bg)",
    overflow: "hidden",
    userSelect: "none",
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
    minHeight: "300px",
    gap: "12px",
    padding: "20px",
    textAlign: "center",
  },
  toolbar: {
    position: "absolute",
    top: "10px",
    left: "10px",
    right: "10px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    zIndex: 10,
    pointerEvents: "none",
  },
  toolbarTitle: {
    fontSize: "12px",
    fontWeight: "600",
    color: "var(--color-text-muted)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "9999px",
    padding: "4px 10px",
    pointerEvents: "auto",
  },
  toolBtn: {
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "8px",
    color: "var(--color-text-muted)",
    fontSize: "14px",
    fontWeight: "600",
    width: "28px",
    height: "28px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    pointerEvents: "auto",
  },
  regenBtn: {
    padding: "6px 14px",
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    border: "none",
    borderRadius: "9999px",
    fontSize: "12px",
    fontWeight: "600",
    cursor: "pointer",
  },
  detailPanel: {
    position: "absolute",
    bottom: "12px",
    left: "50%",
    transform: "translateX(-50%)",
    background: "var(--color-surface)",
    border: "1px solid var(--color-border)",
    borderRadius: "12px",
    padding: "10px 16px",
    boxShadow: "0 4px 16px rgba(0,0,0,0.12)",
    display: "flex",
    alignItems: "center",
    gap: "12px",
    maxWidth: "80%",
    zIndex: 20,
    pointerEvents: "auto",
  },
  detailLabel: {
    fontSize: "13px",
    fontWeight: "600",
    color: "var(--color-text)",
    flex: 1,
    minWidth: 0,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  askBtn: {
    padding: "5px 12px",
    background: "var(--color-primary)",
    color: "var(--color-primary-text)",
    border: "none",
    borderRadius: "9999px",
    fontSize: "12px",
    fontWeight: "600",
    cursor: "pointer",
    whiteSpace: "nowrap",
    flexShrink: 0,
  },
};
