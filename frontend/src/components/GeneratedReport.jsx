import Icon from './Icon'

function ReportCard({ title, text, type }) {
  return (
    <article className={`report-card ${type}`}>
      <div className="report-title">
        <span className={`report-icon ${type}`}><Icon name={type === 'findings' ? 'list' : 'file'} size={18} /></span>
        <div>
          <h3>{title}</h3>
        </div>
      </div>
      <div className="report-text">
        {text.split('\n').map((line, index) => line ? <p className={line.endsWith(':') ? 'report-subhead' : ''} key={index}>{line}</p> : <br key={index} />)}
      </div>
    </article>
  )
}

export default function GeneratedReport({ report }) {
  if (!report?.findings || !report?.impression) {
    return <section className="data-fallback">Generated report is unavailable.</section>
  }

  return (
    <section className="card generated-report-card">
      <div className="section-title">
        <div className="inline-section-title">
          <span className="heading-dot" />
          <div><span className="eyebrow">MLLM output</span><h2>Generated radiology report</h2></div>
        </div>
      </div>
      <div className="report-grid">
        <ReportCard title="Findings" text={report.findings} type="findings" />
        <ReportCard title="Impression" text={report.impression} type="impression" />
      </div>
    </section>
  )
}
