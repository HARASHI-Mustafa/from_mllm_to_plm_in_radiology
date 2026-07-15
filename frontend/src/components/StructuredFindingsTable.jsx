const probabilityKeys = [
  ['present', 'Present'],
  ['uncertain', 'Uncertain'],
  ['absent', 'Absent'],
  ['not_mentioned', 'Not mentioned'],
]

const percent = (value = 0) => `${(value * 100).toFixed(1)}%`
const pretty = (value = '') => value.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
const stateOrder = {
  present: 0,
  uncertain: 1,
  absent: 2,
  not_mentioned: 3,
}

function Probability({ type, value }) {
  return (
    <div className="probability-cell">
      <span>{percent(value)}</span>
      <div className="probability-track"><i className={type} style={{ width: `${Math.max(value * 100, value ? 1 : 0)}%` }} /></div>
    </div>
  )
}

export default function StructuredFindingsTable({ findings }) {
  if (!findings || typeof findings !== 'object') {
    return <section className="data-fallback">Structured findings are unavailable.</section>
  }

  const sortedFindings = Object.entries(findings).sort(([, a], [, b]) => {
    const stateA = stateOrder[a.state] ?? Number.MAX_SAFE_INTEGER
    const stateB = stateOrder[b.state] ?? Number.MAX_SAFE_INTEGER
    if (stateA !== stateB) return stateA - stateB
    return (b.confidence ?? 0) - (a.confidence ?? 0)
  })

  return (
    <section>
      <div className="section-title">
        <div className="inline-section-title"><span className="heading-dot" /><div><span className="eyebrow">PLM extraction</span><h2>Structured finding extraction</h2></div></div>
      </div>
      <div className="card table-card">
        <div className="table-scroll">
          <table>
            <thead><tr><th>Label</th><th>Final state</th><th>Confidence</th>{probabilityKeys.map(([, label]) => <th key={label}>{label} %</th>)}<th>Source</th></tr></thead>
            <tbody>
              {sortedFindings.map(([label, item]) => (
                <tr className={`finding-row state-${item.state}`} key={label}>
                  <td className="label-cell">{label}</td>
                  <td><span className={`state-badge ${item.state}`}>{pretty(item.state)}</span></td>
                  <td><strong className="confidence">{percent(item.confidence)}</strong><small className="confidence-level">{pretty(item.confidence_level)}</small></td>
                  {probabilityKeys.map(([key]) => <td key={key}><Probability type={key} value={item.probabilities?.[key] ?? 0} /></td>)}
                  <td><span className="source-chip">{pretty(item.source)}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-legend">
          {probabilityKeys.map(([key, label]) => <span key={key}><i className={key} /> {label}</span>)}
        </div>
      </div>
    </section>
  )
}
