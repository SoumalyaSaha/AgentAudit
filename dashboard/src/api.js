// Single place that decides where the Python runner lives.
//
//   dev   -> relative '/api', proxied by Vite to 127.0.0.1:8765 (loopback only)
//   build -> absolute VITE_API_URL if provided at build time (the Render URL),
//            otherwise falls back to relative '/api'
//
// VITE_API_URL is read at build time, so the deployed bundle points at whatever
// backend was configured when it was built -- it never discovers or contacts a
// remote host on its own, and the dev server still only ever reaches loopback.
//
// `import.meta.env` exists in every Vite bundle, but NOT in the Node render
// smoke test (esbuild --format=cjs), where import.meta is a bare object. Read
// it defensively so a config lookup can never crash a page render.
function readApiBase() {
  try {
    return (import.meta.env && import.meta.env.VITE_API_URL) || '/api'
  } catch {
    return '/api'
  }
}

// The runner exposes everything under /api (/api/runs, /api/run) and callers
// append /runs or /run to this base. Accept BOTH the service root
// (https://x.onrender.com, the documented DASHBOARD_API_URL value) and a base
// that already ends in /api, so a mis-suffixed variable can never turn live
// mode into a silent 404 -> snapshot fallback.
function normalizeApiBase(raw) {
  const trimmed = String(raw || '').replace(/\/+$/, '')
  return /\/api$/i.test(trimmed) ? trimmed : `${trimmed}/api`
}

export const API_BASE = normalizeApiBase(readApiBase())

/**
 * Fetch the run list from the backend.
 * Returns a plain array; throws on any network/HTTP/shape failure so callers
 * can decide whether to fall back to the bundled snapshot.
 */
export async function getRuns({ signal } = {}) {
  const res = await fetch(`${API_BASE}/runs`, { signal })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  const runs = Array.isArray(data?.runs) ? data.runs : null
  if (!runs) throw new Error('unexpected /api/runs payload')
  return runs
}

/**
 * Turn a failed API call into a sentence a judge can act on.
 * Network failures (server asleep, offline, wrong URL) surface as TypeError.
 */
export function describeApiError(err) {
  const msg = String(err?.message || err)
  if (err instanceof TypeError || /failed to fetch|networkerror|load failed/i.test(msg)) {
    return `Cannot reach the audit runner at ${API_BASE}.`
  }
  return `Audit runner error: ${msg}`
}
