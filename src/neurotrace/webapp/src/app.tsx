import React, { useEffect, useState } from 'react'
import { Home } from './pages/Home'
import { Session } from './pages/Session'
import { Report } from './pages/Report'

type Route = { path: string; params?: Record<string, string> }

function parseRoute(): Route {
  const hash = window.location.hash.replace(/^#/, '') || '/'
  const parts = hash.split('/').filter(Boolean)
  if (parts[0] === 'sessions' && parts[1]) {
    return { path: '/sessions/:id', params: { id: parts[1] } }
  }
  if (parts[0] === 'report') {
    return { path: '/report' }
  }
  return { path: '/' }
}

export function App() {
  const [route, setRoute] = useState<Route>(parseRoute())
  useEffect(() => {
    const onHash = () => setRoute(parseRoute())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  return (
    <div>
      <nav style={{ padding: 8, borderBottom: '1px solid #ddd' }}>
        <a href="#/" style={{ marginRight: 12 }}>Home</a>
        <a href="#/report">Report</a>
      </nav>
      {route.path === '/' && <Home />}
      {route.path === '/report' && <Report />}
      {route.path === '/sessions/:id' && route.params?.id && <Session id={route.params.id} />}
    </div>
  )
}


