import React, { useEffect, useState } from 'react'

async function fetchJSON(url: string) {
  const r = await fetch(url)
  if (!r.ok) throw new Error(`${r.status}`)
  return r.json()
}

export function Report() {
  const [report, setReport] = useState<any>(null)
  const [zoneTotals, setZoneTotals] = useState<any[]>([])
  const [lengthBuckets, setLengthBuckets] = useState<any[]>([])
  const [coverage, setCoverage] = useState<any[]>([])
  const [roles, setRoles] = useState<any[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const base = '/report'
    Promise.all([
      fetchJSON(`${base}/run`).then(setReport),
      fetchJSON(`${base}/charts/zone_totals.json`).then(setZoneTotals).catch(() => setZoneTotals([])),
      fetchJSON(`${base}/charts/length_buckets.json`).then(setLengthBuckets).catch(() => setLengthBuckets([])),
      fetchJSON(`${base}/charts/coverage_over_time.json`).then(setCoverage).catch(() => setCoverage([])),
      fetchJSON(`${base}/charts/roles_over_time.json`).then(setRoles).catch(() => setRoles([])),
    ]).catch((e) => setError(String(e)))
  }, [])

  return (
    <div style={{ padding: 16 }}>
      <h2>Run Report</h2>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {report && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
          <div><b>Conversations</b><div>{report.scale?.sessions_total ?? '-'}</div></div>
          <div><b>Messages</b><div>{report.scale?.messages_total ?? '-'}</div></div>
          <div><b>Agentic share</b><div>{(report.quality?.agentic_share ?? 0).toFixed(2)}</div></div>
          <div><b>Coverage mean</b><div>{(report.zones?.coverage?.assistant_non_unknown_share_mean ?? 0).toFixed(2)}</div></div>
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>
          <h4>Zone totals</h4>
          <pre style={{ maxHeight: 280, overflow: 'auto' }}>{JSON.stringify(zoneTotals, null, 2)}</pre>
        </div>
        <div>
          <h4>Length buckets</h4>
          <pre style={{ maxHeight: 280, overflow: 'auto' }}>{JSON.stringify(lengthBuckets, null, 2)}</pre>
        </div>
        <div>
          <h4>Coverage over time</h4>
          <pre style={{ maxHeight: 280, overflow: 'auto' }}>{JSON.stringify(coverage, null, 2)}</pre>
        </div>
        <div>
          <h4>Roles over time</h4>
          <pre style={{ maxHeight: 280, overflow: 'auto' }}>{JSON.stringify(roles, null, 2)}</pre>
        </div>
      </div>
    </div>
  )
}
