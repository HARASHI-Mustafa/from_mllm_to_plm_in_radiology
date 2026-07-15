import { useEffect, useState } from 'react'
import Header from './components/Header'
import UploadPanel from './components/UploadPanel'
import AnalysisControl from './components/AnalysisControl'
import CaseSummary from './components/CaseSummary'
import GeneratedReport from './components/GeneratedReport'
import StructuredFindingsTable from './components/StructuredFindingsTable'
import DecisionSupport from './components/DecisionSupport'
import ExportButtons from './components/ExportButtons'
import Icon from './components/Icon'
import { analyzeImage } from './api/radiologyApi'

const workflows = [
  ['upload', 'Image intake', 'JPG or PNG chest X-ray'],
  ['brain', 'Report generation', 'CheXagent Findings and Impression'],
  ['database', 'Structured extraction', '14 PLM finding labels'],
  ['shield', 'Review support', 'Priority, reasons, and exports'],
]

const seconds = (value) => typeof value === 'number' ? `${value.toFixed(1)}s` : 'Not reported'

function RuntimeMetadata({ metadata }) {
  if (!metadata) return null
  const runtime = metadata.mllm_runtime || {}
  return (
    <section className="card runtime-card">
      <div className="card-kicker">
        <Icon name="clock" size={18} />
        <span>Run metadata</span>
      </div>
      <h2>{metadata.mode === 'real' ? 'Real pipeline run' : `${metadata.mode || 'Pipeline'} run`}</h2>
      <div className="runtime-grid">
        <div><span>MLLM runtime</span><strong>{seconds(runtime.total_seconds)}</strong></div>
        <div><span>PLM runtime</span><strong>{seconds(metadata.plm_runtime_seconds)}</strong></div>
      </div>
    </section>
  )
}

export default function App() {
  const [image, setImage] = useState(null)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const resultReady = Boolean(
    result?.case_summary &&
    result?.generated_report &&
    result?.structured_findings &&
    result?.decision_support,
  )

  useEffect(() => () => image?.objectUrl && URL.revokeObjectURL(image.objectUrl), [image])

  const selectImage = (file) => {
    if (!file) return
    if (image?.objectUrl) URL.revokeObjectURL(image.objectUrl)
    const objectUrl = URL.createObjectURL(file)
    setImage({ file, name: file.name, size: `${(file.size / 1024).toFixed(1)} KB`, url: objectUrl, objectUrl })
    setResult(null)
    setError('')
  }

  const reset = () => {
    if (image?.objectUrl) URL.revokeObjectURL(image.objectUrl)
    setImage(null)
    setResult(null)
    setLoading(false)
    setError('')
  }

  const analyze = async () => {
    if (!image?.file) return
    setLoading(true)
    setError('')
    try {
      const [analysisResult] = await Promise.all([
        analyzeImage(image.file),
        new Promise((resolve) => setTimeout(resolve, 1000)),
      ])
      setResult(analysisResult)
    } catch (err) {
      setError('Analysis API is not available. Please start the FastAPI backend and check the selected pipeline mode.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Header />
      <main className="page-shell">
        {!image && (
          <>
            <div className="empty-upload-wrap"><UploadPanel image={image} onSelect={selectImage} /></div>
            <section className="workflow-section">
              <div className="workflow-grid">
                {workflows.map(([icon, title, detail], index) => (
                  <article className="workflow-card" key={title}>
                    <span className="workflow-number">{String(index + 1).padStart(2, '0')}</span>
                    <div className="workflow-icon"><Icon name={icon} size={22} /></div>
                    <h3>{title}</h3>
                    <p>{detail}</p>
                  </article>
                ))}
              </div>
              <AnalysisControl hasImage={false} loading={false} complete={false} onAnalyze={analyze} onReset={reset} />
            </section>
          </>
        )}

        {image && (
          <section className="workspace-grid">
            <UploadPanel image={image} onSelect={selectImage} />
            <AnalysisControl hasImage loading={loading} complete={resultReady} onAnalyze={analyze} onReset={reset} />
          </section>
        )}

        {error && <div className="error-banner"><Icon name="alert" size={18} /> {error}</div>}

        {resultReady && (
          <div className="results-stack">
            <section className="results-overview-grid">
              <CaseSummary caseSummary={result.case_summary} decisionSupport={result.decision_support} />
              <DecisionSupport data={result.decision_support} />
              <RuntimeMetadata metadata={result.api_metadata} />
            </section>
            <GeneratedReport report={result.generated_report} />
            <StructuredFindingsTable findings={result.structured_findings} />
            <ExportButtons result={result} />
          </div>
        )}
      </main>
    </>
  )
}
