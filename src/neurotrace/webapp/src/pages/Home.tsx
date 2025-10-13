import React, { useEffect, useState } from 'react'
import { fetchSessions, SessionItem } from '../lib/api'

export function Home() {
  const [items, setItems] = useState<SessionItem[]>([])
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    fetchSessions().then(setItems).catch((e) => setError(String(e)))
  }, [])
  return (
    <div style={{ padding: 16 }}>
      <h1>Neurotrace Sessions</h1>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <ul>
        {items.map((s) => (
          <li key={s.id}>
            <a href={`#/sessions/${encodeURIComponent(s.id)}`}>{s.id}</a> — {s.message_count} messages
          </li>
        ))}
      </ul>
    </div>
  )
}


