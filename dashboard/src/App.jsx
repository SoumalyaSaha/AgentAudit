import React from 'react'
import Layout from './components/Layout'
import RunHistory from './pages/RunHistory'
import RunDetail from './pages/RunDetail'
import AgentHealth from './pages/AgentHealth'
import NewAudit from './pages/NewAudit'
import { RUNS, latestRunFor } from './data'

export default function App() {
  const [page, setPage] = React.useState('history')
  const [run, setRun] = React.useState(null)

  const openRun = React.useCallback((r) => {
    setRun(r)
    setPage('detail')
  }, [])

  const openScenario = React.useCallback((scenario) => {
    setRun(latestRunFor(scenario))
    setPage('detail')
  }, [])

  let content
  if (page === 'history') content = <RunHistory setPage={setPage} openRun={openRun} />
  else if (page === 'detail')
    content = <RunDetail run={run} setPage={setPage} openScenario={openScenario} />
  else if (page === 'health') content = <AgentHealth />
  else content = <NewAudit setPage={setPage} openRun={openRun} />

  return (
    <Layout page={page} setPage={setPage}>
      {content}
    </Layout>
  )
}
