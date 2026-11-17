import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Decision, Scan, View } from '../types'

// Ratusz: Agent Quest (by christian-24) extended with a hall of petitions, estate charters and a
// port for agents on other machines. Same village, same pane, plus the petitions you answer here.
const PANE = 'ratusz'
const TITLE = 'Ratusz'
const VERSION = '0.1.0'
const POLL_MS = 3000
const PORT = 4791 // the original Agent Quest keeps 4790, so both can run side by side
const VILLAGE_URL = `http://127.0.0.1:${PORT}`
const RESPAWN_MS = 30000

const view = atom({ plugin: 'ratusz', key: 'view' } as const, null)

// Module memory, rebuilt on a reload.
let lastDigest = ''
let isScanning = false
let isRunning = false
let serverUp = false
let lastSpawnAt = 0

const ago = (iso: string, now: number) => {
  const s = Math.max(0, (now - Date.parse(iso)) / 1000)
  return s < 60 ? 'teraz' : s < 3600 ? `${Math.floor(s / 60)} min` : `${Math.floor(s / 3600)} h`
}

// The village is a small local web server (app/server.js) shown in Claude's browser pane. Every
// session keeps one alive: if another session's server already holds the port this child exits at
// once, and it is tried again later in case that session has ended.
function keepServer($: EngineInterface) {
  if (serverUp || Date.now() - lastSpawnAt < RESPAWN_MS) return
  serverUp = true
  lastSpawnAt = Date.now()
  void (async () => {
    try {
      for await (const _ of $.process.spawn({ argv: ['node', `${$.plugin.root}/app/server.js`] })) { /* the server says little */ }
    } catch { /* node missing or refused: the pane still shows the party */ }
    serverUp = false
  })()
}

// petitions come from the server, which holds them for the village, the phone and the push buttons
async function petitions($: EngineInterface): Promise<Decision[]> {
  try {
    const r = await $.http.fetch(`${VILLAGE_URL}/api/decisions`)
    if (!r.ok) return []
    return (JSON.parse(r.text) as { pending: Decision[] }).pending
  } catch { return [] }
}
async function decide($: EngineInterface, id: string, status: 'approved' | 'rejected') {
  try {
    await $.http.fetch(`${VILLAGE_URL}/api/decisions/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) })
  } catch { /* the server is down; the pane says so */ }
  lastDigest = '' // redraw on the next scan
}

// The scan loop belongs to the module, not to one event: a /reload-plugins brings a new module
// without a new session.start, so whichever hook comes first (start, command, a draw) starts it.
function ensureRunning($: EngineInterface) {
  if (isRunning) return
  isRunning = true
  const scanOnce = async () => {
    keepServer($)
    if (isScanning) return
    isScanning = true
    try {
      const ran = await $.process.run(['node', `${$.plugin.root}/scanner/scan.js`], { timeoutMs: 20000 })
      if (ran.exitCode !== 0) throw new Error(ran.stderr.slice(0, 300) || `scanner exited ${ran.exitCode}`)
      const scan = JSON.parse(ran.stdout) as Scan
      const pending = await petitions($)
      const digest = JSON.stringify([scan.agents.map(a => [a.id, a.state, a.verb, a.name, a.feed[a.feed.length - 1]?.at]), pending.map(p => p.id)])
      if (digest === lastDigest) return
      lastDigest = digest
      const feed = scan.agents
        .flatMap(a => a.feed.map(f => ({ ...f, who: a.name })))
        .sort((x, y) => y.at.localeCompare(x.at))
        .slice(0, 6)
      const fresh: View = { svg: '', agents: scan.agents, feed, tools: scan.tools, petitions: pending, updatedAt: scan.now, error: null }
      await update($, view, () => fresh)
    } catch (err) {
      const raw = err instanceof Error ? err.message : String(err)
      const message = /ENOENT|not found|spawn node/i.test(raw) ? 'Brak Node.js na tej maszynie. Zainstaluj Node 20+ (nodejs.org), a wioska i skaner ruszą same.' : raw
      await update($, view, v => (v ? { ...v, error: message } : { svg: '', agents: [], feed: [], tools: [], petitions: [], updatedAt: Date.now(), error: message }))
    } finally {
      isScanning = false
    }
  }

  void scanOnce()
  $.clock.every(POLL_MS, () => { void scanOnce() })
}

async function openVillage($: EngineInterface) {
  keepServer($)
  try {
    const r = await $.mcp.call('Claude_Browser', 'preview_start', { url: VILLAGE_URL })
    if (r.isError) throw new Error('refused')
  } catch {
    $.ui.toast(`Otwórz ${VILLAGE_URL} w przeglądarce Claude`)
  }
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    const started = await next(e)
    await $.command.register({ name: 'ratusz', description: 'Otwórz panel Ratusza (petycje, drużyna)' })
    await $.command.register({ name: 'ratusz-3d', description: 'Otwórz wioskę 3D z Ratuszem w przeglądarce Claude' })

    void $.ui.open({ id: PANE, title: TITLE })
    ensureRunning($)

    return started
  })

  on('command.run', { command: 'ratusz' }, async $ => {
    ensureRunning($)
    await $.ui.open({ id: PANE, title: TITLE })

    return { text: 'Ratusz jest otwarty obok czatu.' }
  })

  on('command.run', { command: 'ratusz-3d' }, async $ => {
    ensureRunning($)
    await openVillage($)

    return { text: `Wioska 3D z Ratuszem: ${VILLAGE_URL}` }
  })

  on('ui.render', { component: 'Pane', requestId: PANE }, async ($, e) => {
    ensureRunning($)
    const { Box, Text, Button, Link } = $.ui.resolve(e)
    const v = await read($, view)
    if (!v) return <Text dimColor>Budzenie wioski…</Text>

    const now = v.updatedAt
    const working = v.agents.filter(a => a.state === 'working').length
    const waiting = v.agents.filter(a => a.state === 'waiting').length
    const subs = v.agents.filter(a => a.kind === 'subagent' && a.state === 'working').length
    const party = v.agents.slice(0, 10).map(a => (
      <Text dimColor={a.state === 'resting' || a.state === 'done'} wrap="truncate-end">
        {a.kind === 'subagent' ? '  ↳ ' : '• '}{a.name} — {a.verb} · {a.project}{a.machine ? ` · ${a.machine}` : ''} · {ago(a.lastAt, now)}
      </Text>
    ))
    const petitionRows = v.petitions.slice(0, 5).map(d => (
      <Box flexDirection="column">
        <Text wrap="truncate-end"><Text color="#f2c45a">◆ </Text>{d.project || d.machine} · {d.agent || d.source} ({d.machine}) · {ago(d.at, now)}</Text>
        <Text wrap="truncate-end">  {d.title}{d.command ? ` — ${d.command}` : ''}</Text>
        <Box flexDirection="row" gap={1}>
          <Button label="Zatwierdź" variant="primary" onPress={() => { void decide($, d.id, 'approved') }} />
          <Button label="Odrzuć" onPress={() => { void decide($, d.id, 'rejected') }} />
        </Box>
      </Box>
    ))
    const feed = v.feed.map(f => (
      <Text dimColor wrap="truncate-end">{ago(f.at, now)}  {f.who.slice(0, 18)}  {f.tool}  {f.detail}</Text>
    ))

    return (
      <Box flexDirection="column" gap={1}>
        <Box flexDirection="row" gap={2} flexWrap="wrap">
          <Text bold color={v.petitions.length ? '#f2c45a' : undefined}>{v.petitions.length} petycji</Text>
          <Text bold color="#6ee08a">{working} pracuje</Text>
          <Text color="#ffd36b">{waiting} czeka na Ciebie</Text>
          <Text dimColor>{subs} subagentów · v{VERSION}</Text>
        </Box>
        <Box flexDirection="row" gap={2} flexWrap="wrap">
          <Button label="Otwórz wioskę 3D" variant="primary" onPress={() => { void openVillage($) }} />
          <Link href={VILLAGE_URL} label={VILLAGE_URL} />
        </Box>
        {v.error ? <Text color="#ff6a5a">Skaner: {v.error}</Text> : null}
        {v.petitions.length ? <Text bold>Petycje</Text> : null}
        {petitionRows}
        <Text bold>Drużyna</Text>
        {party}
        <Text bold>Aktywność</Text>
        {feed}
      </Box>
    )
  })
}
