import React from 'react'
import { ENGINE_INFO, RUNS, engineLabel, modeLabel } from '../data'

const NAV = [
  { key: 'history', label: 'Run History', icon: 'history' },
  { key: 'detail', label: 'Run Detail', icon: 'fact_check' },
  { key: 'health', label: 'Agent Health', icon: 'monitoring' },
  { key: 'new', label: 'New Audit', icon: 'add_circle' },
]

function Glyph({ name }) {
  // Material-style glyphs, drawn as inline SVG so there is no icon
  // dependency (and nothing to fetch at runtime).
  const paths = {
    history: 'M12 8v4l3 2M3.05 11a9 9 0 1 0 .5-4M3 4v5h5',
    fact_check: 'M9 11l2 2 4-4M20 12v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h9M9 2h6l4 4',
    monitoring: 'M3 12h4l2 5 4-10 2 5h6',
    add_circle: 'M12 8v8M8 12h8M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
    download: 'M12 3v12m0 0 4-4m-4 4-4-4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2',
    search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
    arrow_back: 'M19 12H5m0 0 7 7m-7-7 7-7',
    arrow_forward: 'M5 12h14m0 0-7-7m7 7-7 7',
    memory: 'M6 8h12v8H6zM9 4v4m6-4v4M9 16v4m6-4v4M3 11h3m12 0h3M3 14h3m12 0h3',
    notifications: 'M18 9a6 6 0 1 0-12 0c0 6-2 7-2 7h16s-2-1-2-7M13.7 20a2 2 0 0 1-3.4 0',
    person: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
    security: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
    terminal: 'M4 17l6-5-6-5M12 19h8',
    help: 'M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
    sync: 'M4 4v6h6M20 20v-6h-6M4 14a8 8 0 0 1 13.7-5.7L20 11M20 10a8 8 0 0 1-13.7 5.7L4 13',
    bolt: 'M13 2 4 14h7l-1 8 9-12h-7l1-8z',
    dataset: 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
    verified: 'M12 2l2.9 2.1 3.6-.4 1 3.5 3.3 1.6-1.3 3.4 1.3 3.4-3.3 1.6-1 3.5-3.6-.4L12 22l-2.9-2.1-3.6.4-1-3.5L1.2 15 2.5 11.6 1.2 8.2l3.3-1.6 1-3.5 3.6.4L12 2zM9 12l2 2 4-4',
    rule: 'M12 3v18M5 8h14M7 8l-3 6a3 3 0 0 0 6 0L7 8M17 8l-3 6a3 3 0 0 0 6 0l-3-6',
    warning: 'M12 3 2 20h20L12 3zM12 9v5m0 3h.01',
    grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
    troubleshoot: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01',
    developer: 'M16 18l6-6-6-6M8 6l-6 6 6 6',
    policy: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z',
    check_circle: 'M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM8 12l3 3 5-6',
    bug: 'M8 2l1.9 1.9M16 2l-1.9 1.9M9 7h6v4a6 6 0 0 1-12 0V7zM3 13h4M17 13h4M4 8l3 2M20 8l-3 2',
    gavel: 'M14 3 21 10M17.5 6.5 12 12M10 5 5 10l3 3 5-5M4 21h9',
    task: 'M9 6h11M9 12h11M9 18h11M4 6l1 1 2-2M4 12l1 1 2-2M4 18l1 1 2-2',
    psychology: 'M9 3h6v5H9zM8 8h8v6a4 4 0 0 1-4 4v3M12 18v3M8 21h8',
    science: 'M9 3v6L4 19a1 1 0 0 0 .9 1.5h14.2A1 1 0 0 0 20 19l-5-10V3M8 3h8',
    expand: 'M7 10l5 5 5-5M7 4l5 5 5-5',
    collapse: 'M7 14l5-5 5 5M7 20l5-5 5 5',
    code: 'M9 18l-6-6 6-6M15 6l6 6-6 6',
    difference: 'M12 3v18M5 8h14M5 16h14',
    refresh: 'M4 4v6h6M20 20v-6h-6M4 14a8 8 0 0 1 13.7-5.7L20 11M20 10a8 8 0 0 1-13.7 5.7L4 13',
    timer: 'M12 22a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 10v4l2 2M9 2h6',
    play: 'M6 3l14 9-14 9V3z',
    stop: 'M6 6h12v12H6z',
  }
  return (
    <svg
      width="18"
      height="18"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="shrink-0"
    >
      {paths[name] ? <path d={paths[name]} /> : null}
    </svg>
  )
}

export function Icon({ name, className = '' }) {
  return (
    <span className={className}>
      <Glyph name={name} />
    </span>
  )
}

export default function Layout({ page, setPage, children }) {
  // Header chips reflect the runs that actually exist in the history.
  const backends = [...new Set(RUNS.map((r) => r.backend))]
  const modes = [...new Set(RUNS.map((r) => r.nemotron_mode))]
  const hasSandbox = backends.includes('sandbox')
  const hasLive = modes.includes('live')

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-edge bg-panel/80 backdrop-blur sticky top-0 z-20">
        <div className="px-6 h-14 flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <span className="w-6 h-6 rounded border border-verified/40 bg-verified/10 grid place-items-center">
              <Icon name="verified" className="text-verified-soft" />
            </span>
            <span className="font-semibold tracking-tight">AgentAudit</span>
          </div>

          <div className="h-5 w-px bg-edge" />

          <div className="flex items-center gap-2 micro-label text-ink-dim">
            <Icon name="memory" className="text-ink-faint" />
            <span>Backend:</span>
            <span className="text-ink">
              {hasSandbox ? 'Local + Sandbox' : 'Local'}
            </span>
          </div>

          <div className="flex items-center gap-2 micro-label text-ink-dim">
            <Icon name="sync" className="text-ink-faint" />
            <span>Nemotron:</span>
            <span className="text-ink">
              {hasLive ? 'live + recorded replay' : 'recorded replay'}
            </span>
          </div>

          <div className="ml-auto flex items-center gap-4 text-ink-faint">
            <Icon name="notifications" />
            <Icon name="person" />
            <Icon name="security" />
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        <aside className="w-[240px] shrink-0 border-r border-edge bg-panel/40 hidden md:block">
          <div className="px-5 py-5">
            <div className="micro-label text-ink-faint mb-1">Auditor Gateway</div>
            <div className="text-sm text-ink-dim">Audit Operations</div>
          </div>
          <nav className="px-3">
            {NAV.map((item) => (
              <button
                key={item.key}
                onClick={() => setPage(item.key)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded mb-1 text-sm transition-colors ${
                  page === item.key
                    ? 'bg-surface-2 text-ink border border-edge-strong'
                    : 'text-ink-dim hover:text-ink hover:bg-surface'
                }`}
              >
                <Icon name={item.icon} className={page === item.key ? 'text-verified-soft' : ''} />
                {item.label}
              </button>
            ))}
          </nav>
          <div className="px-5 py-6 mt-4 border-t border-edge">
            <div className="flex items-center gap-2 micro-label text-ink-faint">
              <Icon name="terminal" />
              <span>agent-cli v1.4</span>
            </div>
            <div className="mt-3 flex items-center gap-2 micro-label text-ink-faint">
              <Icon name="help" />
              <span>help</span>
            </div>
          </div>
        </aside>

        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  )
}
