import React, { useEffect, useState } from 'react'
import { Chart } from '../components/Chart'
import { fetchSpec } from '../lib/api'

export function Session({ id }: { id: string }) {
  const [overview, setOverview] = useState<any>(null)
  const [zoneMix, setZoneMix] = useState<any>(null)
  const [depth, setDepth] = useState<any>(null)
  const [transitions, setTransitions] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetchSpec(id, 'overview').then(setOverview),
      fetchSpec(id, 'zone_mix').then(setZoneMix),
      fetchSpec(id, 'depth_dist').then(setDepth),
      fetchSpec(id, 'transitions').then(setTransitions),
    ]).catch((e) => setError(String(e)))
  }, [id])

  return (
    <div style={{ padding: 16 }}>
      <h2>Session {id}</h2>
      {error && <div style={{ color: 'red' }}>{error}</div>}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <div>{overview && <Chart spec={overview} />}</div>
        <div>{zoneMix && <Chart spec={zoneMix} />}</div>
        <div>{depth && <Chart spec={depth} />}</div>
        <div>{transitions && <Chart spec={transitions} />}</div>
      </div>
    </div>
  )
}


