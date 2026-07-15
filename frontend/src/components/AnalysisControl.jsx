import Icon from './Icon'

const steps = [
  ['upload', 'Uploading image', 'Input stored for analysis'],
  ['brain', 'Generating report', 'Findings and Impression'],
  ['database', 'Extracting findings', '14 structured labels'],
  ['shield', 'Preparing support', 'Review priority and safety checks'],
]

export default function AnalysisControl({ hasImage, loading, complete, onAnalyze, onReset }) {
  if (!hasImage) {
    return (
      <section className="empty-analysis">
        <button className="button primary analyze-button" disabled><Icon name="activity" size={18} /> Analyze image</button>
        <p className="helper-text">Upload a chest X-ray image to start the workflow.</p>
      </section>
    )
  }

  return (
    <section className="card analysis-card">
      <div className="section-heading compact">
        <div>
          <span className="eyebrow">Workflow control</span>
          <div className="panel-title"><Icon name="activity" size={20} /><h2>Analysis run</h2></div>
        </div>
        {complete && <span className="complete-label"><Icon name="check" size={15} /> Completed</span>}
      </div>

      <div className="step-list" aria-label="Analysis progress">
        {steps.map(([icon, label, detail], index) => {
          const done = complete || (!loading && index === 0)
          const active = loading || complete || index === 0
          return (
            <div className={`analysis-step ${active ? 'active' : ''} ${loading ? 'running' : ''}`} key={label}>
              <div className="step-symbol">{done ? <Icon name="check" size={16} /> : <Icon name={icon} size={17} />}</div>
              <div><strong>{label}</strong><span>{loading && index > 0 ? 'Processing...' : detail}</span></div>
              <span className={`step-status ${done ? 'done' : ''}`}>{done ? 'Done' : loading ? 'Running' : 'Pending'}</span>
            </div>
          )
        })}
      </div>

      <button className="button primary analyze-button" disabled={!hasImage || loading || complete} onClick={onAnalyze}>
        {loading ? <><span className="spinner" /> Running analysis...</> : <><Icon name="activity" size={18} /> {complete ? 'Analysis complete' : 'Run full analysis'}</>}
      </button>
      {complete && <p className="helper-text">Results are ready for review and export.</p>}
      <button className="button secondary reset-button" onClick={onReset}><Icon name="reset" size={16} /> Reset workspace</button>
    </section>
  )
}
