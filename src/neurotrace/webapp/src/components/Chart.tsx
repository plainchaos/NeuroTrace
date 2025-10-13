import React, { useEffect, useRef } from 'react'
import embed, { VisualizationSpec } from 'vega-embed'

type Props = { spec: VisualizationSpec; width?: number; height?: number }

export function Chart({ spec }: Props) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const view = embed(ref.current, spec, { actions: false })
    return () => {
      view.then((v) => v.finalize()).catch(() => void 0)
    }
  }, [spec])
  return <div ref={ref} />
}


