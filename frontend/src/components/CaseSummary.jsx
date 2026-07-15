import Icon from './Icon'

const prettify = (value = '') => value.replaceAll('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())

export default function CaseSummary({ caseSummary, decisionSupport }) {
  if (!caseSummary || !decisionSupport) {
    return <section className="data-fallback">Case summary is unavailable.</section>
  }

  const activeCount = caseSummary.active_abnormal_findings?.length ?? 0

  return (
    <section className="card clinical-summary-card">
      <div className="card-kicker">
        <Icon name="activity" size={18} />
        <span>Case summary</span>
      </div>
      <h2>{prettify(caseSummary.case_status)}</h2>
      <p>Structured extraction identified {activeCount} active abnormal finding{activeCount === 1 ? '' : 's'} for clinical review.</p>
      <div className="summary-stat-grid">
        <div><span>Present</span><strong>{caseSummary.present_abnormal_findings?.length ?? 0}</strong></div>
        <div><span>Uncertain</span><strong>{caseSummary.uncertain_abnormal_findings?.length ?? 0}</strong></div>
        <div><span>No finding</span><strong>{prettify(caseSummary.no_finding_state)}</strong></div>
      </div>
      <div className="finding-chip-list">
        {(caseSummary.active_abnormal_findings ?? []).slice(0, 5).map((label) => <span key={label}>{label}</span>)}
        {activeCount === 0 && <span>No active abnormal findings</span>}
      </div>
    </section>
  )
}
