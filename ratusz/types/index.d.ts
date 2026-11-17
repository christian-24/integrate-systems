/** One sprite of pixels/atlas.json: rows of palette keys per frame, '.' transparent. */
export type Pixel = {
  w: number
  h: number
  anchor: [number, number]
  palette: Record<string, string>
  frames: string[][]
}

export type Pos = { x: number; y: number }

export type FeedRow = { at: string; tool: string; detail: string }

/** One agent as scanner/scan.js reports it; `machine` is set for agents heard of through the Port. */
export type Agent = {
  id: string
  kind: 'session' | 'subagent'
  name: string
  project: string
  role: 'backend' | 'testers' | 'marketing' | 'finance'
  state: 'working' | 'waiting' | 'resting' | 'done'
  building: string
  verb: string
  lastAt: string
  feed: FeedRow[]
  parent: string | null
  machine?: string
}

/** A petition: something an agent asks you for, held by app/ratusz.js until you answer. */
export type Decision = {
  id: string
  at: string
  status: 'pending' | 'approved' | 'rejected' | 'expired'
  kind: 'approval' | 'review' | 'question'
  machine: string
  source: string
  project: string
  session: string
  agent: string
  title: string
  command: string
  rule: string
  url: string
  note: string
  answeredAt: string | null
}

export type Scan = { now: number; agents: Agent[]; tools: string[]; atlas?: number }

/** What the pane draws: the rows beside the chat, rebuilt when the village or the petitions change. */
export type View = {
  svg: string
  agents: Agent[]
  feed: (FeedRow & { who: string })[]
  tools: string[]
  petitions: Decision[]
  updatedAt: number
  error: string | null
}

declare module 'claude-code' {
  interface PluginState {
    ratusz: { view: View | null }
  }
}
