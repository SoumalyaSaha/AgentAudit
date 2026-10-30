// Single shared fetch of the runner's run list — one source of truth for the
// whole app.
//
// WHY THIS EXISTS (not per-page fetches):
// RunHistory used to fetch /api/runs itself, while App's default Run Detail
// target (mostRecentRun) and openScenario (latestRunFor) read the BUNDLED
// run_history.json snapshot. On a live deployment that split is a golden-rule
// violation: the sidebar's Run Detail would show the newest build-time run
// while the runner already held newer ones. Fetching once here means every
// selection path — history rows, Run Detail default, scenario jumps — reads
// the same list: live when reachable, bundled snapshot when not.
//
// The bundle fallback is the same honest behavior as before: if the runner is
// unreachable (Render asleep, snapshot-only build), `runs` is the recorded
// run_history.json and `source` is 'bundled', which the badge renders as
// "Snapshot".
//
// renderToString never runs effects, so the Node render smoke test sees only
// the bundled initial state and makes no network call.

import React from 'react'
import { RUNS } from './data'
import { getRuns } from './api'

export default function useRuns() {
  // null until the first fetch settles — `runs` below never exposes that.
  const [liveRuns, setLiveRuns] = React.useState(null)
  const [source, setSource] = React.useState('bundled') // 'live' | 'bundled'
  const [loading, setLoading] = React.useState(true)
  const [refreshKey, setRefreshKey] = React.useState(0)

  React.useEffect(() => {
    const ac = new AbortController()
    let cancelled = false
    setLoading(true)
    getRuns({ signal: ac.signal })
      .then((list) => {
        if (cancelled) return
        setLiveRuns(list)
        setSource('live')
      })
      .catch((err) => {
        if (cancelled || err?.name === 'AbortError') return
        // Keep whatever list we already had; only the badge flips to Snapshot.
        setSource('bundled')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
      ac.abort()
    }
  }, [refreshKey])

  const refresh = React.useCallback(() => setRefreshKey((k) => k + 1), [])

  return {
    /** Live list when reachable, bundled run_history.json otherwise. */
    runs: liveRuns || RUNS,
    source,
    loading,
    refresh,
  }
}
