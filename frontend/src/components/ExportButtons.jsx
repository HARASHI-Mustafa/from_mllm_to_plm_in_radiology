import { useState } from 'react'
import Icon from './Icon'
import { exportUrls } from '../api/radiologyApi'

const downloads = [
  ['JSON', exportUrls.json, '/mock/mock_result.json', 'decision_support_output.json'],
  ['CSV', exportUrls.csv, '/mock/structured_findings.csv', 'structured_findings.csv'],
  ['Markdown', exportUrls.markdown, '/mock/decision_support_report.md', 'decision_support_report.md'],
  ['Report TXT', exportUrls.generatedReport, '/mock/generated_report.txt', 'generated_report.txt'],
]

export default function ExportButtons({ result }) {
  const [copied, setCopied] = useState(false)

  const copySummary = async () => {
    if (!result?.case_summary || !result?.decision_support) return
    const findings = result.case_summary.active_abnormal_findings.join(', ') || 'None'
    const summary = `CXR decision-support summary\nCase status: ${result.case_summary.case_status.replaceAll('_', ' ')}\nActive findings: ${findings}\nReview priority: ${result.decision_support.review_priority}\nDecision-support output only. Final interpretation requires clinical review.`
    await navigator.clipboard.writeText(summary)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  const downloadFile = async (url, fallbackUrl, filename) => {
    try {
      const response = await fetch(url)
      if (!response.ok) throw new Error('Backend export unavailable.')
      const blob = await response.blob()
      const objectUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = objectUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(objectUrl)
    } catch (err) {
      const link = document.createElement('a')
      link.href = fallbackUrl
      link.download = filename
      document.body.appendChild(link)
      link.click()
      link.remove()
    }
  }

  if (!result?.case_summary || !result?.decision_support) {
    return <section className="card data-fallback">Export data is unavailable.</section>
  }

  return (
    <section className="card export-card">
      <div className="export-heading">
        <div className="export-icon"><Icon name="download" size={21} /></div>
        <div><span className="eyebrow">Artifacts</span><h2>Export outputs</h2></div>
      </div>
      <div className="export-actions">
        {downloads.map(([label, href, fallbackHref, filename]) => (
          <button className="button secondary" type="button" onClick={() => downloadFile(href, fallbackHref, filename)} key={label}>
            <Icon name={label === 'JSON' ? 'file' : 'download'} size={17} /> {label}
          </button>
        ))}
        <button className="button primary" onClick={copySummary}><Icon name={copied ? 'check' : 'copy'} size={17} /> {copied ? 'Copied' : 'Copy summary'}</button>
      </div>
    </section>
  )
}
