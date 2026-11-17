// Agent Quest scanner: reads Claude Code transcripts under ~/.claude/projects and prints one JSON
// object describing every recent agent (sessions and their subagents) and which building of the
// village its current work belongs to. Run by the mod every few seconds: node scanner/scan.js

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execFileSync } = require("child_process");

const ROOT = path.join(os.homedir(), ".claude", "projects");
const SHOW_HOURS = 12;            // sessions quiet for longer are left out
const SUB_DONE_MINUTES = 10;      // finished subagents stay this long
const ACTIVE_MS = 90_000;         // a transcript written this recently is active
const THINKING_MS = 20_000;       // no tool call for this long while active: thinking
const TAIL_BYTES = 1024 * 1024; // big enough to see past screenshots in a transcript
const HEAD_BYTES = 48 * 1024;

// a command that runs a test suite (the runner itself, not just the word "test" in a path)
const TEST_CMD = /\b(pytest|jest|vitest|mocha|phpunit|unittest|playwright test)\b|\b(flutter|dotnet|go|cargo|mvn|gradlew?|deno|bun) test\b|\b(npm|yarn|pnpm)( run)? test\b|python -m pytest/i;
const POST_FILE = /post|marketing|social|newsletter|kampani|reklam|campaign|linkedin|instagram|facebook|tiktok/i;

function readSlice(file, start, len) {
  const fd = fs.openSync(file, "r");
  try { const buf = Buffer.alloc(len); const n = fs.readSync(fd, buf, 0, len, start); return buf.subarray(0, n).toString("utf8"); }
  finally { fs.closeSync(fd); }
}
function parseLines(text, dropFirst) {
  const lines = text.split("\n"); if (dropFirst) lines.shift();
  const out = []; for (const l of lines) { if (!l.trim()) continue; try { out.push(JSON.parse(l)); } catch {} } return out;
}
const readTail = (file, size) => { const start = Math.max(0, size - TAIL_BYTES); return parseLines(readSlice(file, start, size - start), start > 0); };
const readHead = (file, size) => parseLines(readSlice(file, 0, Math.min(size, HEAD_BYTES)), false).slice(0, -1);
const readJson = file => { try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return null; } };
const clip = (s, n) => { s = String(s ?? "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1) + "…" : s; };

// Which building a tool call belongs to, and the verb shown over the agent's head.
function placeOf(name, input, role) {
  const i = input || {};
  if (/^(Edit|Write|MultiEdit|NotebookEdit)$/.test(name)) {
    if (role === "marketing" || POST_FILE.test(i.file_path || "")) return ["herald", "writing a post"];
    return ["forge", "editing"];
  }
  if (/^(Read|Grep|Glob|LS|NotebookRead)$/.test(name) || /list_events|get_page_text|read_page/.test(name)) return ["library", "reading"];
  if (/^(Bash|PowerShell)$/.test(name)) return TEST_CMD.test(i.command || "") ? ["alchemist", "testing"] : ["arena", "running commands"];
  if (/^(WebSearch|WebFetch)$/.test(name) || /Browser|chrome|computer-use|navigate/.test(name)) return ["watchtower", "scouting the web"];
  if (/^(Agent|Task|SendMessage|Workflow|TaskStop)$/.test(name) || /start_session/.test(name)) return ["castle", "commanding"];
  return ["chapel", "planning"];
}

const textOf = content => typeof content === "string" ? content : Array.isArray(content) ? content.filter(c => c.type === "text").map(c => c.text).join(" ") : "";

function summarise(entries, role) {
  let cwd = null, title = null, lastPrompt = null, turnEnded = false, last = null, lastTextAt = null, lastText = null;
  const feed = [];
  // test runs: a Bash/PowerShell test command and whether its result reported failures
  const testCalls = new Map(), tests = [];
  // plans an agent wrote in plan mode (the ExitPlanMode call carries the whole plan)
  const plans = [];
  for (const e of entries) {
    if (e.type === "user" && Array.isArray(e.message?.content)) for (const c of e.message.content) {
      const call = c.type === "tool_result" && testCalls.get(c.tool_use_id);
      if (!call) continue;
      const out = textOf(c.content);
      const failed = Boolean(c.is_error) || /\b[1-9]\d* (failed|failing|errors?)\b|FAILED|Tests? failed/i.test(out);
      tests.push({ at: call.at, command: call.command, failed });
    }
    if (e.type === "assistant") for (const c of e.message?.content || []) {
      if (c.type === "tool_use" && c.name === "ExitPlanMode" && typeof c.input?.plan === "string")
        plans.push({ at: e.timestamp, text: c.input.plan.slice(0, 12000) });
      const cmd = c.input?.command || "";
      if (c.type === "tool_use" && /^(Bash|PowerShell)$/.test(c.name) && TEST_CMD.test(cmd) && !/^\s*(git|gh|cd [^&]*&&\s*git)\b/.test(cmd))
        testCalls.set(c.id, { at: e.timestamp, command: clip(c.input.description || c.input.command, 120) });
    }
  }
  for (const e of entries) {
    if (e.cwd) cwd = e.cwd;
    if (e.type === "custom-title" && e.customTitle) title = e.customTitle;
    if (e.type === "user" && !e.isMeta && typeof e.message?.content === "string" && !e.message.content.startsWith("<")) { lastPrompt = e.message.content; turnEnded = false; }
    if (e.type === "assistant" && e.message) {
      for (const c of e.message.content || []) {
        if (c.type === "tool_use" && !/^mcp__ccd_|^(ToolSearch|TodoWrite)$/.test(c.name)) {
          const i = c.input || {};
          const short = c.name.replace(/^mcp__.*?__/, "");
          last = { tool: short, raw: c.name, input: i, at: e.timestamp };
          feed.push({ at: e.timestamp, tool: short, detail: clip(i.description || i.command || i.file_path || i.pattern || i.url || i.query || i.prompt || "", 120) });
        }
        if (c.type === "text" && c.text.trim()) { lastTextAt = e.timestamp; lastText = c.text; }
      }
      turnEnded = e.message.stop_reason === "end_turn";
    }
    if (e.type === "system" && e.subtype === "stop_hook_summary") turnEnded = true;
  }
  return { cwd, title, lastPrompt, turnEnded, last, lastTextAt, lastText, feed: feed.slice(-6), tests: tests.slice(-10), plans: plans.slice(-3) };
}

function guessRole(text) {
  if (/finans|faktur|przych[oó]d|koszt|bud[zż]et|ksi[eę]gow|invoice|revenue|billing|stripe|p[lł]atno[sś]|cennik|pricing/i.test(text)) return "finance";
  if (/marketing|social|post(y|s)?\b|kampani|campaign|newsletter|seo|reklam|content|instagram|facebook|linkedin|tiktok|media/i.test(text)) return "marketing";
  if (/test|review|qa\b|scenariusz|bug|audyt|audit|accessib|verify|sprawdz/i.test(text)) return "testers";
  return "backend";
}

function decide(s, mtimeMs, now, role) {
  const active = now - mtimeMs < ACTIVE_MS && !s.turnEnded;
  if (active) {
    const lastAt = s.last ? Date.parse(s.last.at) : 0;
    if (s.last && now - lastAt < THINKING_MS) { const [b, verb] = placeOf(s.last.raw, s.last.input, role); return { state: "working", building: b, verb }; }
    return { state: "working", building: "chapel", verb: "thinking" };
  }
  if (now - mtimeMs < 3600_000) return { state: "waiting", building: "tavern", verb: "waiting for you" };
  return { state: "resting", building: "tavern", verb: "resting" };
}

// The folder a session works in, lifted to its project: out of a Claude worktree, up to the git root.
function projectRoot(cwd) {
  if (!cwd) return null;
  const dir = cwd.replace(/[\\/]\.claude[\\/]worktrees[\\/].*$/, "");
  const home = os.homedir().toLowerCase();
  for (let up = dir, i = 0; i < 6; i++) {
    if (up.toLowerCase() === home) break; // a home folder that is itself a repo is no project
    if (fs.existsSync(path.join(up, ".git"))) return up;
    const parent = path.dirname(up);
    if (parent === up) break;
    up = parent;
  }
  return dir.replace(/[\\/](backend|frontend|src|app)$/i, "");
}

function scan(hours = SHOW_HOURS) {
  const now = Date.now();
  // where you assign agents to a village role; kept outside the plugin so updates never lose it
  const roles = readJson(path.join(os.homedir(), ".claude", "agent-quest", "roles.json")) || {};
  const agents = [];
  if (!fs.existsSync(ROOT)) return { now, agents, tools: [] };
  for (const projDir of fs.readdirSync(ROOT)) {
    const pdir = path.join(ROOT, projDir);
    let files; try { files = fs.readdirSync(pdir); } catch { continue; }
    for (const f of files) {
      if (!f.endsWith(".jsonl")) continue;
      const file = path.join(pdir, f), st = fs.statSync(file);
      const id = f.slice(0, -6), sdir = path.join(pdir, id);
      const subDir = path.join(sdir, "subagents");
      const subFiles = fs.existsSync(subDir) ? fs.readdirSync(subDir).filter(x => x.endsWith(".jsonl")) : [];
      const subStats = subFiles.map(x => ({ x, st: fs.statSync(path.join(subDir, x)) }));
      const lastMs = Math.max(st.mtimeMs, ...subStats.map(x => x.st.mtimeMs));
      if (now - lastMs > hours * 3600_000) continue;

      let s = summarise(readTail(file, st.size));
      let title = (readJson(path.join(sdir, "custom-title.json")) || {}).customTitle || s.title;
      let cwd = s.cwd;
      if (!title || !cwd) { const h = summarise(readHead(file, st.size)); title = title || clip(h.lastPrompt || "Untitled", 50); cwd = cwd || h.cwd; }
      const role = roles[id] || guessRole(`${title} ${s.lastPrompt || ""} ${cwd || ""}`);
      if (role === "marketing") s = summarise(readTail(file, st.size), role);
      const place = decide(s, st.mtimeMs, now, role);
      const root = projectRoot(cwd);
      const project = root ? path.basename(root) : projDir;
      agents.push({ id, kind: "session", name: clip(title, 40), project, root, role, ...place, lastAt: new Date(lastMs).toISOString(), feed: s.feed, tests: s.tests, plans: s.plans, parent: null,
        lastPrompt: s.lastPrompt ? clip(s.lastPrompt, 300) : null, lastText: s.lastText ? clip(s.lastText, 500) : null });

      for (const { x, st: sst } of subStats) {
        const ageMin = (now - sst.mtimeMs) / 60000;
        const sub = summarise(readTail(path.join(subDir, x), sst.size));
        const working = now - sst.mtimeMs < ACTIVE_MS && !sub.turnEnded;
        if (!working && ageMin > SUB_DONE_MINUTES) continue;
        const meta = readJson(path.join(subDir, x.replace(/\.jsonl$/, ".meta.json"))) || {};
        let p;
        if (working && sub.last) { const [b, verb] = placeOf(sub.last.raw, sub.last.input, role); p = { state: "working", building: b, verb }; }
        else if (working) p = { state: "working", building: "chapel", verb: "thinking" };
        else p = { state: "done", building: "castle", verb: "reporting back" };
        agents.push({ id: x.replace(/^agent-|\.jsonl$/g, ""), kind: "subagent", name: clip(meta.description || "Subagent", 40), project, root, role, ...p,
          lastAt: sst.mtime.toISOString(), feed: sub.feed.slice(-3), tests: sub.tests, parent: id });
      }
    }
  }
  // agents of other machines, as the Port heard of them (app/ratusz.js); their project is matched by name
  try {
    const roots = new Map(agents.filter(a => a.root).map(a => [path.basename(a.root), a.root]));
    for (const r of require("../app/ratusz").remoteAgents()) agents.push({ ...r, root: roots.get(r.project) ?? r.root });
  } catch {}
  agents.sort((a, b) => b.lastAt.localeCompare(a.lastAt));
  return { now, agents, tools: scanTools() };
}

const OTHER_TOOLS = [["Codex", /^codex/i], ["Copilot", /copilot/i], ["Ollama", /^ollama/i], ["LM Studio", /lm ?studio|^lms\.exe/i]];
function scanTools() {
  try {
    const out = process.platform === "win32" ? execFileSync("tasklist", ["/fo", "csv", "/nh"], { windowsHide: true, encoding: "utf8", maxBuffer: 8 << 20 })
      : execFileSync("ps", ["-A", "-o", "comm="], { encoding: "utf8" });
    const names = out.split(/\r?\n/).map(l => path.basename(l.split('","')[0].replace(/^"/, "")));
    return OTHER_TOOLS.filter(([, re]) => names.some(n => re.test(n))).map(([n]) => n);
  } catch { return []; }
}

module.exports = { scan, projectRoot };
if (require.main === module) {
  let atlas = 0;
  try { atlas = require("./atlas").ensureAtlas(); } catch {}
  process.stdout.write(JSON.stringify({ ...scan(), atlas }));
}
