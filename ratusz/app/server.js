// Agent Quest 3D server. Started in the background by the Agent Quest plugin; the village opens in
// Claude's own browser pane. Listens on 127.0.0.1 only, unless phone access is turned on (then also
// on the home network, with a secret key). GET/POST /api/phone switches it.
//
// GET  /                       the game          GET  /models/<file>        3D model modules
// GET  /api/world              projects (with level and growth), agents, other AI tools
// GET  /api/project?root=      one project: git, PRs, sessions, docs, tasks, plan tree, tech, level
// GET  /api/doc?root=&file=    a Markdown file of a project
// GET  /api/guild?kind=        barracks | testers | tech | marketing | treasury
// GET  /api/plans              plans agents wrote in plan mode, and plan documents
// POST /api/todos  /api/plan  /api/role  /api/marketing  /api/treasury
//
// Ratusz (app/ratusz.js):
// GET/POST /api/events          the Port: events from adapters on other machines
// GET/POST /api/decisions[/id]  petitions: list, create (adapters), answer (you, the phone, ntfy)
// GET/POST /api/charter          an estate's charter (?root= or ?name=); POST { root, charter, export }
// GET  /api/digest              what you read when you come home
// GET/POST /api/ratusz          the Port's status; POST sends a test push through ntfy

const http = require("http");
const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFile } = require("child_process");
const crypto = require("crypto");
const { scan } = require("../scanner/scan");
const treasurySync = require("./treasury-sync");
const ratusz = require("./ratusz");

const PORT = Number(process.env.AGENT_QUEST_PORT) || 4791; // 4791: the original Agent Quest keeps 4790
// Everything you add in the game lives outside the plugin folder, so an update never loses it.
const DATA = path.join(os.homedir(), ".claude", "agent-quest");
const FILES = { todos: "todos.json", plans: "plans.json", roles: "roles.json", treasury: "treasury.json", history: "history.json", phone: "phone.json" };
const MARKETING = path.join(DATA, "marketing");
const PROJECT_DAYS = 60;

const readJson = (file, fallback) => { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; } };
const load = key => readJson(path.join(DATA, FILES[key]), {});
const save = (key, value) => { fs.mkdirSync(DATA, { recursive: true }); fs.writeFileSync(path.join(DATA, FILES[key]), JSON.stringify(value, null, 2)); };
const isScratch = root => /Claude-Data.+scratch-workspaces/i.test(root || "");
const nameOf = root => (isScratch(root) ? "Sesje bez folderu" : path.basename(root));
const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

function run(cmd, args, cwd, timeout = 8000) {
  return new Promise(resolve => {
    execFile(cmd, args, { cwd, timeout, windowsHide: true, maxBuffer: 4 << 20 }, (err, stdout) => resolve(err ? null : stdout));
  });
}

// ---------- scans, cached: the map needs the last 12 hours often, the projects 60 days rarely ----------
let nowCache = { at: 0, value: null }, longCache = { at: 0, value: null };
const recent = () => (Date.now() - nowCache.at < 2000 ? nowCache.value : (nowCache = { at: Date.now(), value: scan() }).value);
const longScan = () => (Date.now() - longCache.at < 15000 ? longCache.value : (longCache = { at: Date.now(), value: scan(PROJECT_DAYS * 24) }).value);

// ---------- level and progress of a project ----------
// XP: every commit 2, merged PR 15, finished task 10, finished milestone 25, session 5.
// Level L is reached at 40·(L-1)² XP, up to 10.
const levelOf = xp => Math.min(10, 1 + Math.floor(Math.sqrt(xp / 40)));
const xpForLevel = l => 40 * (l - 1) ** 2;
const statsCache = new Map();
async function gitStats(root) {
  const hit = statsCache.get(root);
  if (hit && Date.now() - hit.at < 60000) return hit.value;
  let value = { commitsTotal: 0, merged: 0 };
  if (fs.existsSync(path.join(root, ".git"))) {
    const [count, prs] = await Promise.all([
      run("git", ["-C", root, "rev-list", "--count", "HEAD"], root),
      run("gh", ["pr", "list", "--state", "merged", "--limit", "200", "--json", "number"], root, 15000),
    ]);
    let merged = 0; try { merged = prs ? JSON.parse(prs).length : 0; } catch {}
    value = { commitsTotal: Number((count || "0").trim()) || 0, merged };
  }
  statsCache.set(root, { at: Date.now(), value });
  return value;
}
function progressOf(root, sessions, stats) {
  const todos = load("todos")[root] ?? [], plan = load("plans")[root] ?? [];
  const todosDone = todos.filter(t => t.done).length, nodesDone = plan.filter(n => n.status === "done").length;
  const xp = (stats?.commitsTotal ?? 0) * 2 + (stats?.merged ?? 0) * 15 + todosDone * 10 + nodesDone * 25 + sessions * 5;
  const level = levelOf(xp);
  // the garden grows with the plan when there is one, else with the tasks, else with the level
  const growth = plan.length ? nodesDone / plan.length : todos.length ? todosDone / todos.length : (level - 1) / 9;
  return { xp, level, levelFrom: xpForLevel(level), levelTo: level >= 10 ? xp : xpForLevel(level + 1), growth: Math.round(growth * 100) / 100,
    todos: { done: todosDone, total: todos.length }, plan: { done: nodesDone, total: plan.length } };
}

// ---------- the world ----------
let worldCache = { at: 0, value: null };
function world() {
  if (Date.now() - worldCache.at < 1500 && worldCache.value) return worldCache.value;
  const long = longScan(), now = recent();
  const projects = new Map();
  for (const a of long.agents) {
    if (!a.root || a.kind !== "session") continue;
    const p = projects.get(a.root) ?? { root: a.root, name: a.machine ? a.project : nameOf(a.root), sessions: 0, lastAt: a.lastAt, active: 0, machines: [] };
    if (a.machine && !p.machines.includes(a.machine)) p.machines.push(a.machine);
    p.sessions++;
    if (a.lastAt > p.lastAt) p.lastAt = a.lastAt;
    projects.set(a.root, p);
  }
  for (const a of now.agents) if (a.state === "working" && projects.has(a.root)) projects.get(a.root).active++;
  const money = moneyByProject();
  const list = [...projects.values()].map(p => {
    const cached = statsCache.get(p.root)?.value;
    if (!cached || Date.now() - statsCache.get(p.root).at > 60000) void gitStats(p.root); // fills in on a later call
    const progress = progressOf(p.root, p.sessions, cached);
    if (cached) remember(p.root, progress);
    return { ...p, isScratch: isScratch(p.root), ...progress, money: money.get(p.root) ?? { income: 0, cost: 0, profit: 0 } };
  }).sort((a, b) => (a.isScratch - b.isScratch) || b.lastAt.localeCompare(a.lastAt));
  const totals = [...money.values()].reduce((t, m) => ({ income: t.income + m.income, cost: t.cost + m.cost, profit: t.profit + m.profit }), { income: 0, cost: 0, profit: 0 });
  worldCache = { at: Date.now(), value: { now: now.now, projects: list, agents: now.agents, tools: now.tools, treasury: totals } };
  return worldCache.value;
}

// ---------- progress over time: one snapshot per project per day ----------
let history = null, historyDirty = false;
function remember(root, progress) {
  history ??= load("history");
  const today = new Date().toISOString().slice(0, 10);
  const list = history[root] ?? [];
  const snap = { date: today, xp: progress.xp, level: progress.level, growth: progress.growth, plan: progress.plan.done, todos: progress.todos.done };
  const last = list[list.length - 1];
  if (last?.date === today && JSON.stringify(last) === JSON.stringify(snap)) return;
  if (last?.date === today) list[list.length - 1] = snap; else list.push(snap);
  history[root] = list.slice(-365);
  historyDirty = true;
}
// the history file is written at most once a minute, for all projects together
setInterval(() => { if (historyDirty) { historyDirty = false; save("history", history); } }, 60000).unref();

// ---------- treasury: income and costs per project, kept in treasury.json ----------
const entries = () => { const t = load("treasury"); return Array.isArray(t.entries) ? t.entries : []; };
function moneyByProject() {
  const m = new Map();
  for (const e of entries()) {
    if (!e.root) continue; // imported but not yet assigned to a project
    const r = m.get(e.root) ?? { income: 0, cost: 0, profit: 0 };
    if (e.kind === "income") r.income += e.amount; else r.cost += e.amount;
    r.profit = r.income - r.cost;
    m.set(e.root, r);
  }
  return m;
}
function treasuryView() {
  const list = entries().sort((a, b) => b.date.localeCompare(a.date));
  const months = [];
  for (let i = 11; i >= 0; i--) { const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - i); months.push(d.toISOString().slice(0, 7)); }
  const byMonth = months.map(month => {
    const inMonth = list.filter(e => e.date.startsWith(month));
    const income = inMonth.filter(e => e.kind === "income").reduce((s, e) => s + e.amount, 0), cost = inMonth.filter(e => e.kind !== "income").reduce((s, e) => s + e.amount, 0);
    return { month, income, cost, profit: income - cost };
  });
  const w = world();
  return { entries: list.filter(e => e.root).slice(0, 200), unassigned: list.filter(e => !e.root).slice(0, 200), byMonth,
    projects: w.projects.filter(p => !p.isScratch).map(p => ({ root: p.root, name: p.name, ...p.money })),
    totals: w.treasury, treasurers: w.agents.filter(a => a.role === "finance"), sources: treasurySync.status() };
}
function changeTreasury({ action, id, root, kind, amount, date, category, note }) {
  const t = load("treasury"); let list = Array.isArray(t.entries) ? t.entries : [];
  if (action === "add") {
    const value = Math.round(Number(String(amount).replace(",", ".")) * 100) / 100;
    if (!isProject(root) || !(value > 0) || !["income", "cost"].includes(kind)) return null;
    const day = /^\d{4}-\d{2}-\d{2}$/.test(date || "") ? date : new Date().toISOString().slice(0, 10);
    list.push({ id: newId(), root, kind, amount: value, date: day, category: String(category ?? "").slice(0, 60), note: String(note ?? "").slice(0, 300) });
  }
  if (action === "delete") list = list.filter(e => e.id !== id);
  if (action === "assign" && isProject(root)) list.forEach(e => { if (e.id === id) e.root = root; });
  save("treasury", { ...t, entries: list });
  // "remember": entries whose title contains this text go to this project from now on
  if (action === "assign" && isProject(root) && typeof note === "string" && note.trim()) treasurySync.addRule(note.trim().slice(0, 80), root);
  worldCache.at = 0; projectCache.clear();
  return treasuryView();
}
// imports run 15 s after start and then every 15 minutes; the Treasury can also ask for one now
setTimeout(() => void treasurySync.syncAll().then(() => { worldCache.at = 0; }).catch(() => {}), 15000).unref();
setInterval(() => void treasurySync.syncAll().then(() => { worldCache.at = 0; }).catch(() => {}), 15 * 60000).unref();

// ---------- plans: written by agents in plan mode, and plan documents in the projects ----------
const isNew = iso => Date.now() - Date.parse(iso) < 7 * 86400_000;
function plansView() {
  const w = world();
  const agentPlans = longScan().agents.filter(a => a.plans?.length).flatMap(a => a.plans.map(p => ({
    at: p.at, text: p.text, title: (p.text.match(/^#+\s*(.+)$/m)?.[1] ?? p.text.split("\n")[0]).slice(0, 120),
    who: a.name, project: a.project, root: a.root, isNew: isNew(p.at) })))
    .sort((x, y) => y.at.localeCompare(x.at)).slice(0, 40);
  const docs = w.projects.filter(p => !p.isScratch).flatMap(p => docsOf(p.root, PLAN_DOC, 30)
    .map(d => ({ ...d, root: p.root, project: p.name, isNew: isNew(d.mtime) })))
    .sort((x, y) => y.mtime.localeCompare(x.mtime));
  return { agentPlans, docs };
}
const isProject = root => world().projects.some(p => p.root === root);

// ---------- technologies, read from the project's own manifests ----------
const TECH = [
  [/^react$/, "React"], [/^next$/, "Next.js"], [/^vue$/, "Vue"], [/^svelte$/, "Svelte"], [/^@angular\/core$/, "Angular"],
  [/^express$/, "Express"], [/^@nestjs\/core$/, "NestJS"], [/^fastify$/, "Fastify"], [/^typescript$/, "TypeScript"],
  [/^vite$/, "Vite"], [/^tailwindcss$/, "Tailwind"], [/^prisma$|^@prisma\/client$/, "Prisma"], [/^three$/, "three.js"],
  [/^jest$/, "Jest"], [/^vitest$/, "Vitest"], [/^@playwright\/test$|^playwright$/, "Playwright"], [/^electron$/, "Electron"],
  [/^fastapi$/, "FastAPI"], [/^django$/, "Django"], [/^flask$/, "Flask"], [/^pandas$/, "pandas"], [/^sqlalchemy$/, "SQLAlchemy"],
  [/^pytest$/, "pytest"], [/^openpyxl$/, "openpyxl"], [/^anthropic$|^@anthropic-ai\/sdk$/, "Claude API"], [/^openai$/, "OpenAI API"],
  [/^flutter_riverpod$|^riverpod$/, "Riverpod"], [/^drift$/, "Drift"], [/^go_router$/, "go_router"], [/^supabase|supabase_flutter$/, "Supabase"],
];
const techCache = new Map();
function techOf(root) {
  const hit = techCache.get(root);
  if (hit && Date.now() - hit.at < 300000) return hit.value;
  const found = new Set();
  const look = dir => {
    const has = f => fs.existsSync(path.join(dir, f));
    const deps = names => names.forEach(n => TECH.forEach(([re, label]) => { if (re.test(n.toLowerCase())) found.add(label); }));
    if (has("package.json")) { found.add("Node.js"); const p = readJson(path.join(dir, "package.json"), {}); deps(Object.keys({ ...p.dependencies, ...p.devDependencies })); }
    if (has("pubspec.yaml")) { found.add("Flutter / Dart"); const t = fs.readFileSync(path.join(dir, "pubspec.yaml"), "utf8"); deps([...t.matchAll(/^\s{2}([a-z_]+):/gm)].map(m => m[1])); }
    for (const f of ["requirements.txt", "pyproject.toml"]) if (has(f)) { found.add("Python"); deps(fs.readFileSync(path.join(dir, f), "utf8").split(/[\r\n"',\[\]=<>~ ]+/).filter(Boolean)); }
    if (has("go.mod")) found.add("Go");
    if (has("Cargo.toml")) found.add("Rust");
    if (fs.readdirSync(dir).some(f => /\.(csproj|sln)$/.test(f))) found.add(".NET");
    if (has("Dockerfile") || has("docker-compose.yml") || has("compose.yaml")) found.add("Docker");
    if (has(".github/workflows")) found.add("GitHub Actions");
  };
  try {
    look(root);
    for (const e of fs.readdirSync(root, { withFileTypes: true }))
      if (e.isDirectory() && !/^(node_modules|\.git|build|dist|\.dart_tool|venv|\.venv)$/.test(e.name)) { try { look(path.join(root, e.name)); } catch {} }
  } catch {}
  const value = [...found].sort();
  techCache.set(root, { at: Date.now(), value });
  return value;
}

// ---------- one project ----------
const projectCache = new Map();
async function project(root) {
  const hit = projectCache.get(root);
  if (hit && Date.now() - hit.at < 20000) return hit.value;
  const known = world().projects.find(p => p.root === root);
  if (!known) return null;
  const git = fs.existsSync(path.join(root, ".git"));
  const [log, branch, status, week, prs, stats, dates] = await Promise.all(git ? [
    run("git", ["-C", root, "log", "-15", "--date=relative", "--pretty=%h\x1f%an\x1f%ad\x1f%s"], root),
    run("git", ["-C", root, "rev-parse", "--abbrev-ref", "HEAD"], root),
    run("git", ["-C", root, "status", "--porcelain"], root),
    run("git", ["-C", root, "rev-list", "--count", "--since=7.days", "HEAD"], root),
    run("gh", ["pr", "list", "--state", "all", "--limit", "20", "--json", "number,title,state,updatedAt,mergedAt,url,headRefName"], root, 15000),
    gitStats(root),
    run("git", ["-C", root, "log", "--all", "--since=84.days", "--format=%ad", "--date=short"], root),
  ] : [null, null, null, null, null, gitStats(root), null]);
  // commits per week for the last 12 weeks, oldest first
  const weeks = Array.from({ length: 12 }, (_, i) => { const d = new Date(Date.now() - (11 - i) * 7 * 86400_000); return { from: d.toISOString().slice(0, 10), commits: 0 }; });
  for (const day of (dates || "").split("\n").filter(Boolean)) {
    const age = Math.floor((Date.now() - Date.parse(day)) / (7 * 86400_000));
    if (age >= 0 && age < 12) weeks[11 - age].commits++;
  }
  const commits = (log || "").trim().split("\n").filter(Boolean).map(l => { const [hash, author, when, subject] = l.split("\x1f"); return { hash, author, when, subject }; });
  let pulls = []; try { pulls = prs ? JSON.parse(prs) : []; } catch {}
  const agents = longScan().agents.filter(a => a.root === root);
  const sessions = agents.filter(a => a.kind === "session")
    .map(a => ({ id: a.id, name: a.name, state: a.state, verb: a.verb, lastAt: a.lastAt, lastPrompt: a.lastPrompt, lastText: a.lastText }));
  const tests = agents.flatMap(a => (a.tests ?? []).map(t => ({ ...t, who: a.name }))).sort((x, y) => y.at.localeCompare(x.at));
  const value = {
    ...known, ...progressOf(root, known.sessions, stats), git, stats,
    branch: (branch || "").trim() || null,
    changed: status ? status.split("\n").filter(Boolean).length : 0,
    commitsThisWeek: Number((week || "0").trim()) || 0,
    commits, pulls, sessions, tests: tests.slice(0, 15), tech: techOf(root),
    docs: docsOf(root), todoList: load("todos")[root] ?? [], planTree: load("plans")[root] ?? [],
    posts: postsOf(root), weeks, history: (history ?? load("history"))[root] ?? [],
    finance: { entries: entries().filter(e => e.root === root).sort((a, b) => b.date.localeCompare(a.date)), ...(moneyByProject().get(root) ?? { income: 0, cost: 0, profit: 0 }) },
    plans: plansView().agentPlans.filter(p => p.root === root), planDocs: docsOf(root, PLAN_DOC, 30),
    charter: ratusz.charterOf(root),
  };
  value.marketing = marketingAdvice(value);
  projectCache.set(root, { at: Date.now(), value });
  return value;
}

const PLAN_DOC = /plan|roadmap|strategi|harmonogram/i;

// Markdown a person would read: top-level notes, docs/, plans, CLAUDE.md. Never inside dependencies.
// `only` keeps just the paths it matches, so a search for plans is not crowded out by other notes.
function docsOf(root, only = null, cap = 60) {
  const out = [];
  const skip = /^(node_modules|\.git|\.venv|venv|build|dist|\.dart_tool|Pods|\.gradle|\.next|coverage)$/i;
  const walk = (dir, rel, depth) => {
    let entries; try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (out.length >= cap) return;
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) { if (depth < 2 && !skip.test(e.name)) walk(path.join(dir, e.name), r, depth + 1); }
      else if (/\.md$/i.test(e.name) && (!only || only.test(r))) {
        const st = fs.statSync(path.join(dir, e.name));
        out.push({ file: r, size: st.size, mtime: st.mtime.toISOString() });
      }
    }
  };
  walk(root, "", 0);
  const rank = f => (/^readme/i.test(f) ? 0 : /^claude\.md$/i.test(f) ? 1 : f.includes("/") ? 3 : 2);
  return out.sort((a, b) => rank(a.file) - rank(b.file) || b.mtime.localeCompare(a.mtime));
}

function readDoc(root, file) {
  if (!isProject(root)) return null;
  const full = path.resolve(root, file);
  if (!full.toLowerCase().startsWith(path.resolve(root).toLowerCase() + path.sep) || !/\.md$/i.test(full)) return null;
  try { const st = fs.statSync(full); if (st.size > 400 * 1024) return "(Ten plik jest za duży, żeby go tu pokazać.)"; return fs.readFileSync(full, "utf8"); } catch { return null; }
}

// ---------- marketing: posts are Markdown files with a small front matter ----------
function parsePost(file, text) {
  const meta = {};
  const fm = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
  if (fm) for (const line of fm[1].split(/\r?\n/)) { const m = line.match(/^(\w+):\s*(.*)$/); if (m) meta[m[1]] = m[2].replace(/^["']|["']$/g, ""); }
  const body = text.replace(/^---[\s\S]*?---\s*/, "");
  return { file, title: meta.title || path.basename(file, ".md"), channel: meta.channel || "—", status: (meta.status || "draft").toLowerCase(),
    project: meta.project || null, date: meta.date || null, planned: /^\d{4}-\d{2}-\d{2}$/.test(meta.planned || "") ? meta.planned : null, body: body.slice(0, 4000) };
}

// What the heralds should say next: news from the project (merged PRs, finished milestones, a new
// level), when the last post went out and what is planned, as one plain suggestion.
function marketingAdvice(p) {
  const today = new Date().toISOString().slice(0, 10);
  const since = Date.now() - 21 * 86400_000;
  const ideas = [
    ...p.pulls.filter(x => x.state === "MERGED" && x.mergedAt && Date.parse(x.mergedAt) > since)
      .map(x => ({ source: `PR #${x.number}`, at: x.mergedAt, title: `Nowość w ${p.name}: ${x.title.replace(/^\w+(\([^)]*\))?:\s*/, "")}` })),
    ...p.planTree.filter(n => n.status === "done" && n.doneAt && Date.parse(n.doneAt) > since)
      .map(n => ({ source: "kamień milowy", at: n.doneAt, title: `${p.name} osiąga kamień milowy: ${n.title}` })),
  ];
  const levelThen = p.history.find(h => Date.parse(h.date) > since)?.level;
  if (levelThen && levelThen < p.level) ideas.push({ source: "poziom", at: today, title: `${p.name} wskoczył na poziom ${p.level} — co się zmieniło` });
  ideas.sort((a, b) => String(b.at).localeCompare(String(a.at)));
  const published = p.posts.filter(x => x.status === "published" && x.date).sort((a, b) => b.date.localeCompare(a.date));
  const last = published[0]?.date ?? null;
  const daysSince = last ? Math.floor((Date.now() - Date.parse(last)) / 86400_000) : null;
  const next = p.posts.filter(x => x.status !== "published" && x.planned && x.planned >= today).sort((a, b) => a.planned.localeCompare(b.planned))[0] ?? null;
  let advice;
  if (next) advice = `Następny post zaplanowany na ${next.planned}: „${next.title}”.`;
  else if (!p.posts.length) advice = `Projekt nie ma jeszcze żadnego posta. Zacznij od przedstawienia projektu${ideas[0] ? ` albo od: „${ideas[0].title}”` : ""}.`;
  else if (daysSince === null || daysSince > 7) advice = `${daysSince === null ? "Nic jeszcze nie opublikowano" : `Od ostatniego posta minęło ${daysSince} dni`}. ${ideas[0] ? `Pomysł: „${ideas[0].title}”.` : "Zaplanuj datę dla któregoś szkicu."}`;
  else advice = `Ostatni post ${daysSince === 0 ? "dzisiaj" : `${daysSince} dni temu`}. Zaplanuj kolejny za kilka dni.`;
  return { ideas: ideas.slice(0, 8), lastPublished: last, daysSince, next, advice,
    docs: docsOf(p.root, /marketing|kampani|social|brand/i, 30) };
}
function allPosts() {
  if (!fs.existsSync(MARKETING)) return [];
  return fs.readdirSync(MARKETING).filter(f => f.endsWith(".md")).map(f => parsePost(f, fs.readFileSync(path.join(MARKETING, f), "utf8")))
    .sort((a, b) => String(b.date).localeCompare(String(a.date)));
}
const postsOf = root => allPosts().filter(p => p.project === root);
function changeMarketing({ action, root, title, channel, text, file, status, planned }) {
  const day = /^\d{4}-\d{2}-\d{2}$/.test(planned || "") ? planned : "";
  fs.mkdirSync(MARKETING, { recursive: true });
  if (action === "add") {
    if (!title || !String(title).trim()) return null;
    const name = `${new Date().toISOString().slice(0, 10)}-${newId()}.md`;
    const clean = s => String(s ?? "").replace(/\r?\n/g, " ").slice(0, 200);
    fs.writeFileSync(path.join(MARKETING, name), `---\ntitle: ${clean(title)}\nchannel: ${clean(channel || "LinkedIn")}\nstatus: draft\nproject: ${clean(root || "")}\ndate: ${new Date().toISOString().slice(0, 10)}\nplanned: ${day}\n---\n\n${String(text ?? "").slice(0, 8000)}\n`);
  }
  if (action === "plan" && /^[\w.-]+\.md$/.test(file || "")) {
    const full = path.join(MARKETING, file);
    if (fs.existsSync(full)) {
      const t = fs.readFileSync(full, "utf8");
      fs.writeFileSync(full, /^planned:.*$/m.test(t) ? t.replace(/^planned:.*$/m, `planned: ${day}`) : t.replace(/^---\r?\n/, `---\nplanned: ${day}\n`));
    }
  }
  if (action === "status" && /^[\w.-]+\.md$/.test(file || "") && ["draft", "approved", "published"].includes(status)) {
    const full = path.join(MARKETING, file);
    if (fs.existsSync(full)) fs.writeFileSync(full, fs.readFileSync(full, "utf8").replace(/^status:.*$/m, `status: ${status}`));
  }
  if (action === "delete" && /^[\w.-]+\.md$/.test(file || "")) { try { fs.unlinkSync(path.join(MARKETING, file)); } catch {} }
  projectCache.clear();
  return allPosts();
}

// ---------- guilds ----------
function guild(kind) {
  const w = world(), long = longScan();
  if (kind === "barracks") return { agents: w.agents, roles: load("roles") };
  if (kind === "testers") {
    return w.projects.map(p => {
      const runs = long.agents.filter(a => a.root === p.root).flatMap(a => (a.tests ?? []).map(t => ({ ...t, who: a.name }))).sort((x, y) => y.at.localeCompare(x.at));
      return { root: p.root, name: p.name, passed: runs.filter(r => !r.failed).length, failed: runs.filter(r => r.failed).length, last: runs.slice(0, 6) };
    }).filter(p => p.passed + p.failed > 0);
  }
  if (kind === "tech") return w.projects.filter(p => !p.isScratch).map(p => ({ root: p.root, name: p.name, tech: techOf(p.root) }));
  if (kind === "marketing") return marketingView();
  if (kind === "treasury") return treasuryView();
  return null;
}
// the heralds' overview: every project's news, last and next post, and the advice for it
async function marketingView() {
  const w = world();
  const projectsAdvice = [];
  for (const p of w.projects.filter(x => !x.isScratch)) {
    const full = await project(p.root);
    if (full) projectsAdvice.push({ root: p.root, name: p.name, level: p.level, growth: p.growth, ...full.marketing });
  }
  return { posts: allPosts(), projects: projectsAdvice, agents: w.agents.filter(a => a.role === "marketing") };
}

// ---------- changes from the game ----------
function changeTodos({ root, action, id, text }) {
  if (!isProject(root)) return null;
  const all = load("todos"); let list = all[root] ?? [];
  if (action === "add" && typeof text === "string" && text.trim()) list.push({ id: newId(), text: text.trim().slice(0, 300), done: false, at: new Date().toISOString() });
  if (action === "toggle") list.forEach(t => { if (t.id === id) t.done = !t.done; });
  if (action === "delete") list = list.filter(t => t.id !== id);
  all[root] = list; save("todos", all);
  projectCache.delete(root); worldCache.at = 0;
  return list;
}
// The development tree: milestones with a parent; a milestone's status cycles todo → doing → done.
function changePlan({ root, action, id, title, parent }) {
  if (!isProject(root)) return null;
  const all = load("plans"); let tree = all[root] ?? [];
  if (action === "add" && typeof title === "string" && title.trim()) tree.push({ id: newId(), title: title.trim().slice(0, 120), parent: tree.some(n => n.id === parent) ? parent : null, status: "todo" });
  if (action === "cycle") tree.forEach(n => {
    if (n.id !== id) return;
    n.status = { todo: "doing", doing: "done", done: "todo" }[n.status] ?? "todo";
    n.doneAt = n.status === "done" ? new Date().toISOString() : undefined; // the heralds announce fresh milestones
  });
  if (action === "rename" && typeof title === "string" && title.trim()) tree.forEach(n => { if (n.id === id) n.title = title.trim().slice(0, 120); });
  if (action === "delete") {
    const gone = new Set([id]); let grew = true;
    while (grew) { grew = false; for (const n of tree) if (n.parent && gone.has(n.parent) && !gone.has(n.id)) { gone.add(n.id); grew = true; } }
    tree = tree.filter(n => !gone.has(n.id));
  }
  all[root] = tree; save("plans", all);
  projectCache.delete(root); worldCache.at = 0;
  return tree;
}
function changeRole({ id, role }) {
  if (!/^[\w-]{6,64}$/.test(id || "") || !["backend", "testers", "marketing", "finance", null].includes(role ?? null)) return null;
  const roles = load("roles");
  if (role) roles[id] = role; else delete roles[id];
  save("roles", roles); nowCache.at = 0; longCache.at = 0; worldCache.at = 0;
  return roles;
}

// ---------- http ----------
const send = (res, code, type, body) => { res.writeHead(code, { "Content-Type": type, "Cache-Control": "no-store" }); res.end(body); };
const json = (res, value) => (value == null ? send(res, 404, "text/plain", "Not found") : send(res, 200, "application/json", JSON.stringify(value)));
const bodyOf = async req => { let b = ""; for await (const c of req) { b += c; if (b.length > 16384) break; } return JSON.parse(b || "{}"); };
const POSTS = { "/api/todos": changeTodos, "/api/plan": changePlan, "/api/role": changeRole, "/api/marketing": changeMarketing, "/api/treasury": changeTreasury };

// ---------- phone access: off by default; when the person turns it on in the village, the server
// also listens on the home network, and every request that does not come from this computer must
// carry the secret key (from the QR code once, then from a cookie). ----------
const PHONE = path.join(DATA, "phone.json");
const phone = () => readJson(PHONE, { enabled: false, key: "" });
const isLocal = req => ["127.0.0.1", "::1", "::ffff:127.0.0.1"].includes(req.socket.remoteAddress);
const keyOk = (given, key) => { const a = Buffer.from(String(given || "")), b = Buffer.from(key || "-"); return a.length === b.length && crypto.timingSafeEqual(a, b); };
const cookieKey = req => (req.headers.cookie || "").match(/(?:^|;\s*)aq_k=([\w-]+)/)?.[1];
// the home network first (Wi-Fi, then cable); virtual adapters (VirtualBox, Hyper-V, WSL, Docker) last
function lanAddresses() {
  const rank = (name, i) => /vethernet|virtual|vbox|vmware|hyper-v|wsl|docker/i.test(name) || /^0a:00:27|^08:00:27/i.test(i.mac) || i.address.startsWith("192.168.56.") ? 2 : /wi-?fi|wlan|wireless/i.test(name) ? 0 : 1;
  return Object.entries(os.networkInterfaces()).flatMap(([name, list]) => (list ?? []).map(i => ({ ...i, r: rank(name, i) })))
    .filter(i => i.family === "IPv4" && !i.internal && /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(i.address))
    .sort((a, b) => a.r - b.r).map(i => i.address);
}
function phoneView() {
  const p = phone();
  return { enabled: p.enabled, urls: p.enabled ? lanAddresses().map(ip => `http://${ip}:${PORT}/?k=${p.key}`) : [] };
}
function setPhone(enabled) {
  const p = phone();
  save("phone", { enabled: Boolean(enabled), key: enabled ? (p.key || crypto.randomBytes(18).toString("base64url")) : "" }); // off forgets the key: old QR codes stop working
  relisten();
  return phoneView();
}
const host = () => (phone().enabled || ratusz.config().token ? "0.0.0.0" : "127.0.0.1");
function relisten() { if (server.listening && server.address().address !== host()) server.close(() => server.listen(PORT, host())); }

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://127.0.0.1");
  // From this computer: only under the village's own address, so a web page can't reach it through
  // a look-alike domain. From the network: only with the key, and never the server controls.
  if (isLocal(req)) {
    if (!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(req.headers.host || "")) return send(res, 403, "text/plain", "Forbidden");
  } else if (ratusz.tokenOk(req) && ratusz.REMOTE_PATHS.test(url.pathname)) {
    // an adapter from the Port: the token opens the Ratusz routes and nothing else
  } else {
    const p = phone();
    if (!p.enabled) return send(res, 403, "text/plain", "Forbidden");
    if (keyOk(url.searchParams.get("k"), p.key)) {
      res.writeHead(302, { "Set-Cookie": `aq_k=${p.key}; Path=/; Max-Age=31536000; HttpOnly; SameSite=Strict`, Location: "/" });
      return res.end();
    }
    if (!keyOk(cookieKey(req), p.key)) return send(res, 403, "text/plain; charset=utf-8", "Zeskanuj kod QR z wioski na komputerze (przycisk Telefon).");
    if (/^\/api\/(shutdown|phone)$/.test(url.pathname)) return send(res, 403, "text/plain", "Forbidden");
  }
  try {
    if (url.pathname === "/api/phone") return json(res, req.method === "POST" ? setPhone((await bodyOf(req)).enabled) : phoneView());
    if (url.pathname === "/" || url.pathname === "/index.html") return send(res, 200, "text/html; charset=utf-8", fs.readFileSync(path.join(__dirname, "index.html")));
    const model = url.pathname.match(/^\/models\/([\w-]+\.(js|html))$/);
    if (model && fs.existsSync(path.join(__dirname, "models", model[1])))
      return send(res, 200, model[2] === "js" ? "text/javascript; charset=utf-8" : "text/html; charset=utf-8", fs.readFileSync(path.join(__dirname, "models", model[1])));
    if (url.pathname === "/api/version") return json(res, { version: VERSION });
    // a NEWER village server asks this one to step aside; an older one (or one that says no version) is refused
    if (url.pathname === "/api/shutdown" && req.method === "POST") {
      const asker = (await bodyOf(req)).version;
      if (!asker || compareVersions(asker, VERSION) <= 0) return send(res, 409, "text/plain", `this server is ${VERSION}`);
      if (historyDirty) save("history", history);
      send(res, 200, "text/plain", "bye"); return void setTimeout(() => process.exit(0), 100);
    }
    if (req.method === "POST" && POSTS[url.pathname]) return json(res, POSTS[url.pathname](await bodyOf(req)));
    if (url.pathname === "/api/world") return json(res, world());
    if (url.pathname === "/api/project") return json(res, await project(url.searchParams.get("root")));
    if (url.pathname === "/api/guild") return json(res, await guild(url.searchParams.get("kind")));
    if (url.pathname === "/api/plans") return json(res, plansView());
    if (url.pathname === "/api/treasury-sources") return json(res, treasurySync.status());
    if (url.pathname === "/api/treasury-sync" && req.method === "POST") { const s = await treasurySync.syncAll(); worldCache.at = 0; projectCache.clear(); return json(res, s); }
    // ---------- Ratusz ----------
    if (url.pathname === "/api/events") {
      if (req.method !== "POST") return json(res, ratusz.events(Number(url.searchParams.get("limit")) || 200));
      const added = ratusz.addEvents(await bodyOf(req)); nowCache.at = 0; longCache.at = 0; worldCache.at = 0; return json(res, { added: added.length });
    }
    if (url.pathname === "/api/decisions") {
      if (req.method === "POST") { const d = await ratusz.createDecision(await bodyOf(req)); worldCache.at = 0; return json(res, d); }
      return json(res, ratusz.decisionsView());
    }
    const dec = url.pathname.match(/^\/api\/decisions\/([\w-]+)$/);
    if (dec) {
      if (req.method === "POST") { const d = ratusz.answerDecision(dec[1], await bodyOf(req)); worldCache.at = 0; return json(res, d); }
      return json(res, ratusz.decisionById(dec[1]));
    }
    if (url.pathname === "/api/charter") {
      if (req.method === "POST") {
        const b = await bodyOf(req); if (!b.root) return json(res, null);
        const charter = ratusz.setCharter(b.root, b.charter ?? b);
        const exported = b.export ? ratusz.exportCharter(b.root, world().projects.find(p => p.root === b.root)?.name ?? nameOf(b.root)) : null;
        projectCache.delete(b.root); return json(res, { charter, export: exported });
      }
      const root = url.searchParams.get("root"), name = url.searchParams.get("name");
      return json(res, root ? (ratusz.charterOf(root) ?? {}) : name ? (ratusz.charterByName(name) ?? {}) : null);
    }
    if (url.pathname === "/api/digest") return json(res, ratusz.digest(world()));
    if (url.pathname === "/api/ratusz") return json(res, req.method === "POST" ? await ratusz.heraldTest() : ratusz.status());
    if (url.pathname === "/api/doc") { const t = readDoc(url.searchParams.get("root"), url.searchParams.get("file") || ""); return t == null ? json(res, null) : send(res, 200, "text/plain; charset=utf-8", t); }
    send(res, 404, "text/plain", "Not found");
  } catch (e) { send(res, 500, "text/plain", String(e.stack || e)); }
});
// The port may be held by a village server of another plugin version that outlived its session.
// The same or a newer version keeps the port and this one leaves; an older one is asked to stop
// (or, from before versions existed, stopped) and this one takes the port, so updates arrive.
const VERSION = readJson(path.join(__dirname, "..", ".claude-plugin", "plugin.json"), {}).version ?? "0";
function compareVersions(a, b) {
  const pa = String(a).split(".").map(Number), pb = String(b).split(".").map(Number);
  for (let i = 0; i < 3; i++) { const d = (pa[i] || 0) - (pb[i] || 0); if (d) return Math.sign(d); }
  return 0;
}
let retried = false;
async function takeOver() {
  let theirs = null, answered = false;
  try { const r = await fetch(`http://127.0.0.1:${PORT}/api/version`); answered = true; if (r.ok) theirs = (await r.json()).version; } catch {}
  if (retried || (theirs && compareVersions(theirs, VERSION) >= 0)) { console.log(`already running (${theirs ?? "unknown"})`); process.exit(0); }
  retried = true;
  console.log(`replacing village server ${theirs ?? "(old)"} with ${VERSION}`);
  try { await fetch(`http://127.0.0.1:${PORT}/api/shutdown`, { method: "POST", body: JSON.stringify({ version: VERSION }) }); } catch {}
  await new Promise(r => setTimeout(r, 400));
  if (process.platform === "win32" && answered && !theirs) {
    // a village server from before /api/version: stop the process holding the port, if it is one
    const ps = `$c = Get-NetTCPConnection -LocalPort ${PORT} -State Listen -ErrorAction SilentlyContinue; if ($c) { $p = Get-CimInstance Win32_Process -Filter "ProcessId=$($c.OwningProcess)"; if ($p.CommandLine -like '*app*server.js*') { Stop-Process -Id $p.ProcessId -Force } }`;
    await run("powershell", ["-NoProfile", "-Command", ps], __dirname, 10000);
  }
  await new Promise(r => setTimeout(r, 600));
  server.listen(PORT, host());
}
server.on("error", e => { if (e.code === "EADDRINUSE") return void takeOver(); throw e; });
server.on("listening", () => console.log(`Agent Quest 3D ${VERSION} at http://127.0.0.1:${PORT}`));
server.listen(PORT, host());
