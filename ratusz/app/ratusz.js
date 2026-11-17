// Ratusz: what the village did not have. The Port takes events from other machines (the Windows
// PC, Codex, the cloud) and turns them into agents on the island; every estate gets a charter
// (karta); agents file petitions (decisions) that you answer here, on the phone or from a push
// notification; the herald (ntfy) carries the push; the digest is what you read when you come home.
//
// Everything lives in ~/.claude/agent-quest next to todos and plans, so a plugin update never
// loses it:  events.json  charters.json  decisions.json  ratusz.json (config).
//
// ratusz.json: { "token": "<long secret other machines send as Bearer>",
//                "publicBase": "http://mac.tailnet:4791",        // how the phone reaches this server
//                "ntfy": { "url": "https://ntfy.sh", "topic": "ratusz-abc123", "token": "" } }

const fs = require("fs");
const os = require("os");
const path = require("path");
const crypto = require("crypto");

const DATA = path.join(os.homedir(), ".claude", "agent-quest");
const FILE = { events: "events.json", charters: "charters.json", decisions: "decisions.json", config: "ratusz.json" };
const readJson = (file, fallback) => { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; } };
const load = key => readJson(path.join(DATA, FILE[key]), {});
const save = (key, value) => { fs.mkdirSync(DATA, { recursive: true }); fs.writeFileSync(path.join(DATA, FILE[key]), JSON.stringify(value, null, 2)); };
const newId = () => Date.now().toString(36) + crypto.randomBytes(3).toString("hex");
const clip = (s, n) => String(s ?? "").replace(/\s+/g, " ").trim().slice(0, n);
const nowIso = () => new Date().toISOString();
const config = () => load("config");

// ---------- the Port: events from adapters on other machines (and this one) ----------
const EVENT_TYPES = new Set(["session_started", "turn_started", "turn_finished", "needs_decision", "blocked", "session_ended", "pr_opened", "ci_failed", "ci_passed", "repo_dirty", "note"]);
const KEEP_EVENTS = 3000;
const SHOW_HOURS = 12;

function addEvents(input) {
  const list = Array.isArray(input) ? input : [input];
  const all = load("events"); const events = Array.isArray(all.list) ? all.list : [];
  const added = [];
  for (const e of list) {
    if (!e || typeof e !== "object" || !EVENT_TYPES.has(e.type)) continue;
    const ev = {
      id: newId(), ts: /^\d{4}-\d{2}-\d{2}T/.test(e.ts || "") ? e.ts : nowIso(),
      type: e.type, source: clip(e.source || "unknown", 30), machine: clip(e.machine || "unknown", 40),
      project: clip(e.project || "", 80), root: clip(e.root || "", 300), session: clip(e.session || "", 80),
      title: clip(e.title || "", 200), verb: clip(e.verb || "", 60), role: ["backend", "testers", "marketing", "finance"].includes(e.role) ? e.role : null,
      payload: e.payload && typeof e.payload === "object" ? JSON.parse(JSON.stringify(e.payload).slice(0, 4000)) : null,
    };
    events.push(ev); added.push(ev);
  }
  if (added.length) save("events", { list: events.slice(-KEEP_EVENTS) });
  return added;
}
const events = (limit = 200) => (load("events").list ?? []).slice(-limit).reverse();

// Agents of other machines: the last event of every (machine, session) says what the agent does.
// Shaped like scanner/scan.js agents, plus `machine`, so the village draws them the same way.
function remoteAgents(localMachine = os.hostname()) {
  const since = Date.now() - SHOW_HOURS * 3600_000;
  const bySession = new Map();
  for (const e of load("events").list ?? []) {
    if (!e.session || e.machine === localMachine || Date.parse(e.ts) < since) continue;
    const key = `${e.machine}:${e.session}`;
    const s = bySession.get(key) ?? { key, feed: [], firstAt: e.ts };
    s.last = e; s.feed.push({ at: e.ts, tool: e.type, detail: e.title }); bySession.set(key, s);
  }
  const out = [];
  for (const s of bySession.values()) {
    const e = s.last, age = Date.now() - Date.parse(e.ts);
    if (e.type === "session_ended" && age > 10 * 60000) continue;
    const place = {
      session_started: ["working", "forge", "zaczyna"], turn_started: ["working", "forge", "pracuje"],
      turn_finished: ["waiting", "tavern", "skończył turę"], needs_decision: ["waiting", "castle", "petycja"],
      blocked: ["waiting", "tavern", "zablokowany"], session_ended: ["done", "tavern", "skończył"],
    }[e.type] ?? ["working", "chapel", e.verb || "pracuje"];
    const [state, building, verb] = place;
    // a session that said "started" long ago and nothing since is resting, not working
    const stale = state === "working" && age > 60 * 60000;
    out.push({
      id: s.key, kind: "session", name: clip(e.payload?.name || e.title || e.session, 40), project: e.project || e.machine, root: e.root || null,
      role: e.role || "backend", state: stale ? "resting" : state, building: stale ? "tavern" : building, verb: e.verb || verb,
      lastAt: e.ts, feed: s.feed.slice(-6), tests: [], plans: [], parent: null, lastPrompt: null, lastText: e.type === "turn_finished" ? clip(e.payload?.text, 500) || null : null,
      machine: e.machine, source: e.source,
    });
  }
  return out;
}

// ---------- charters: the estate's contract ----------
const CHARTER_FIELDS = ["goal", "inScope", "outScope", "done", "autonomy", "rules", "machine", "budget", "deadline", "notes"];
const AUTONOMY = { 1: "Pyta o wszystko", 2: "Pracuje sam, pyta o ryzyko", 3: "Pełna swoboda w repo" };
const DEFAULT_RULES = ["git push --force", "rm -rf", "DROP TABLE", "deploy", "migrate"];
const charterOf = root => (load("charters")[root] ?? null);
const charterByName = name => Object.entries(load("charters")).find(([root]) => path.basename(root.replace(/\\/g, "/")) === name)?.[1] ?? null;
const lines = v => Array.isArray(v) ? v.map(x => clip(x, 200)).filter(Boolean).slice(0, 40) : String(v ?? "").split(/\r?\n/).map(x => clip(x, 200)).filter(Boolean).slice(0, 40);
function setCharter(root, input) {
  if (!root || typeof input !== "object" || !input) return null;
  const old = charterOf(root) ?? {};
  const c = { ...old };
  for (const f of CHARTER_FIELDS) if (f in input) c[f] = ["done", "rules", "inScope", "outScope"].includes(f) ? lines(input[f]) : f === "autonomy" ? (AUTONOMY[input[f]] ? Number(input[f]) : 2) : clip(input[f], 2000);
  c.autonomy ??= 2; c.rules ??= DEFAULT_RULES.slice(); c.updatedAt = nowIso();
  const all = load("charters"); all[root] = c; save("charters", all);
  return c;
}
function charterMarkdown(name, c) {
  const list = (title, v) => (v?.length ? `\n## ${title}\n${v.map(x => `- ${x}`).join("\n")}\n` : "");
  return `# Karta posiadłości: ${name}\n\nTa karta jest umową między właścicielem a agentami tego projektu. Czytaj ją na starcie każdej sesji.\n` +
    (c.goal ? `\n## Cel\n${c.goal}\n` : "") + list("W zakresie", c.inScope) + list("Poza zakresem", c.outScope) + list("Wymagania ukończenia", c.done) +
    `\n## Swoboda agentów\nPoziom ${c.autonomy}: ${AUTONOMY[c.autonomy]}.\n` +
    (c.rules?.length ? `Zanim wykonasz którąkolwiek z tych operacji, złóż petycję (zatrzymaj się i poproś o zgodę):\n${c.rules.map(r => `- ${r}`).join("\n")}\n` : "") +
    (c.machine ? `\n## Zasoby\n- Maszyna domyślna: ${c.machine}\n` : "\n## Zasoby\n") + (c.budget ? `- Budżet: ${c.budget}\n` : "") + (c.deadline ? `- Termin: ${c.deadline}\n` : "") +
    (c.notes ? `\n## Uwagi\n${c.notes}\n` : "");
}
// KARTA.md in the project, imported from CLAUDE.md with an @ line, so agents read it on start.
function exportCharter(root, name) {
  const c = charterOf(root); if (!c || !fs.existsSync(root)) return { ok: false, reason: "brak karty albo folderu" };
  fs.writeFileSync(path.join(root, "KARTA.md"), charterMarkdown(name, c));
  const claudeMd = path.join(root, "CLAUDE.md");
  const existing = fs.existsSync(claudeMd) ? fs.readFileSync(claudeMd, "utf8") : "";
  if (!/^@KARTA\.md\s*$/m.test(existing)) fs.writeFileSync(claudeMd, (existing ? existing.replace(/\s*$/, "\n\n") : "") + "@KARTA.md\n");
  return { ok: true, files: ["KARTA.md", "CLAUDE.md"] };
}

// ---------- petitions (decisions) ----------
const KEEP_DECISIONS = 500;
const EXPIRE_MIN = 60;
const decisions = () => { const d = load("decisions"); return Array.isArray(d.list) ? d.list : []; };
function tidy(list) {
  const cut = Date.now() - EXPIRE_MIN * 60000;
  for (const d of list) if (d.status === "pending" && Date.parse(d.at) < cut) { d.status = "expired"; d.answeredAt = nowIso(); }
  return list.slice(-KEEP_DECISIONS);
}
function decisionsView() {
  const list = tidy(decisions());
  return { pending: list.filter(d => d.status === "pending").sort((a, b) => a.at.localeCompare(b.at)), recent: list.filter(d => d.status !== "pending").slice(-30).reverse() };
}
const decisionById = id => decisions().find(d => d.id === id) ?? null;
async function createDecision(input) {
  if (!input || typeof input !== "object" || !clip(input.title, 1)) return null;
  const d = {
    id: newId(), at: nowIso(), status: "pending", kind: ["approval", "review", "question"].includes(input.kind) ? input.kind : "approval",
    machine: clip(input.machine || "unknown", 40), source: clip(input.source || "unknown", 30), project: clip(input.project || "", 80), session: clip(input.session || "", 80),
    agent: clip(input.agent || "", 60), title: clip(input.title, 200), command: clip(input.command || "", 500), rule: clip(input.rule || "", 100),
    url: /^https?:\/\//.test(input.url || "") ? clip(input.url, 300) : "", note: "", answeredAt: null,
  };
  const list = tidy(decisions()); list.push(d); save("decisions", { list });
  void herald(d).catch(() => {});
  return d;
}
function answerDecision(id, { status, note }) {
  if (!["approved", "rejected"].includes(status)) return null;
  const list = tidy(decisions()); const d = list.find(x => x.id === id);
  if (!d) return null;
  if (d.status === "pending") { d.status = status; d.note = clip(note, 300); d.answeredAt = nowIso(); save("decisions", { list }); }
  return d;
}

// ---------- the herald: a push with buttons, through ntfy ----------
async function herald(d) {
  const { ntfy, publicBase, token } = config();
  if (!ntfy?.url || !ntfy?.topic) return false;
  const base = (publicBase || "").replace(/\/$/, "");
  const act = (label, status) => ({ action: "http", label, url: `${base}/api/decisions/${d.id}`, method: "POST", clear: true,
    headers: token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" }, body: JSON.stringify({ status }) });
  const title = `${d.project || d.machine}: ${d.kind === "review" ? "do odbioru" : d.kind === "question" ? "pytanie" : "prośba o zgodę"}`;
  const message = `${d.agent || d.source} (${d.machine}): ${d.title}${d.command ? `\n${d.command}` : ""}`;
  const actions = d.kind === "approval" && base ? [act("Zatwierdź", "approved"), act("Odrzuć", "rejected")] : [];
  if (d.url) actions.push({ action: "view", label: "Otwórz", url: d.url });
  const r = await fetch(ntfy.url, { method: "POST", headers: ntfy.token ? { Authorization: `Bearer ${ntfy.token}` } : {},
    body: JSON.stringify({ topic: ntfy.topic, title, message, priority: d.kind === "approval" ? 4 : 3, tags: ["scroll"], actions }) });
  return r.ok;
}
async function heraldTest() {
  const { ntfy } = config();
  if (!ntfy?.url || !ntfy?.topic) return { ok: false, reason: "brak ntfy.url lub ntfy.topic w ratusz.json" };
  const r = await fetch(ntfy.url, { method: "POST", headers: ntfy.token ? { Authorization: `Bearer ${ntfy.token}` } : {},
    body: JSON.stringify({ topic: ntfy.topic, title: "Ratusz", message: "Herold działa. Powiadomienia o petycjach będą przychodzić tutaj.", tags: ["scroll"] }) });
  return { ok: r.ok, status: r.status };
}

// ---------- the digest: three numbers and the list behind them ----------
function digest(world) {
  const { pending } = decisionsView();
  const dirty = new Map();
  for (const e of load("events").list ?? []) if (e.type === "repo_dirty" && Date.now() - Date.parse(e.ts) < 24 * 3600_000) dirty.set(`${e.machine}:${e.project}`, e);
  const waiting = world.agents.filter(a => a.state === "waiting" && a.kind === "session");
  const working = world.agents.filter(a => a.state === "working");
  const unfinished = [
    ...pending.map(d => ({ project: d.project, what: `petycja: ${d.title}`, since: d.at })),
    ...waiting.map(a => ({ project: a.project, what: `${a.name} czeka na Ciebie`, since: a.lastAt })),
    ...[...dirty.values()].map(e => ({ project: e.project, what: `${e.title} (${e.machine})`, since: e.ts })),
  ].sort((a, b) => a.since.localeCompare(b.since));
  return { at: nowIso(), petitions: pending.length, working: working.length, waiting: waiting.length, unfinished: unfinished.length,
    text: `${pending.length} petycje · ${working.length} pracuje · ${unfinished.length} niedokończonych`, list: unfinished.slice(0, 30) };
}

// ---------- access from other machines ----------
const tokenOk = req => {
  const want = config().token; if (!want) return false;
  const given = (req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  const a = Buffer.from(given), b = Buffer.from(want);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
};
// routes an adapter on another machine may call with the token (nothing that changes the server itself)
const REMOTE_PATHS = /^\/api\/(events|decisions(\/[\w-]+)?|digest|charter|world)$/;
function status() {
  const c = config();
  return { token: Boolean(c.token), publicBase: c.publicBase || "", ntfy: Boolean(c.ntfy?.url && c.ntfy?.topic), topic: c.ntfy?.topic || "", machine: os.hostname(), file: path.join(DATA, FILE.config) };
}

module.exports = { addEvents, events, remoteAgents, charterOf, charterByName, setCharter, exportCharter, AUTONOMY, DEFAULT_RULES,
  decisionsView, decisionById, createDecision, answerDecision, herald, heraldTest, digest, tokenOk, REMOTE_PATHS, status, config };
