import { useRef, useState } from 'react'
import Icon from './Icon'

const pipelineSteps = ['CheXagent report', 'PLM extraction', 'Clinical review queue']

export default function UploadPanel({ image, onSelect }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const acceptFile = (file) => {
    if (file && ['image/jpeg', 'image/png'].includes(file.type)) onSelect(file)
  }

  const fileInput = (
    <input
      ref={inputRef}
      type="file"
      accept=".jpg,.jpeg,.png,image/jpeg,image/png"
      onChange={(event) => acceptFile(event.target.files[0])}
      hidden
    />
  )

  if (image) {
    return (
      <section className="card image-card">
        <div className="section-heading compact">
          <div>
            <span className="eyebrow">Clinical input</span>
            <div className="panel-title"><Icon name="image" size={20} /><h2>Chest X-ray preview</h2></div>
          </div>
          <span className="ready-chip"><span /> Ready</span>
        </div>
        <div className="image-review-grid">
          <div className="xray-frame">
            <img src={image.url} alt="Uploaded chest X-ray preview" />
            <div className="image-overlay">CXR input</div>
          </div>
          <aside className="file-sidecar">
            <div className="file-meta-card">
              <div className="file-icon"><Icon name="file" size={18} /></div>
              <div>
                <span>Selected image</span>
                <strong>{image.name}</strong>
                <small>{image.size}</small>
              </div>
            </div>
            <div className="pipeline-mini">
              {pipelineSteps.map((step, index) => (
                <div className="pipeline-mini-step" key={step}>
                  <span>{index + 1}</span>
                  <p>{step}</p>
                </div>
              ))}
            </div>
            <button type="button" className="button secondary change-button" onClick={() => inputRef.current?.click()}>
              <Icon name="image" size={16} /> Change image
            </button>
          </aside>
        </div>
        {fileInput}
      </section>
    )
  }

  return (
    <section className="card upload-card">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Clinical input</span>
          <div className="panel-title"><Icon name="upload" size={22} /><h2>Chest X-ray analysis</h2></div>
        </div>
      </div>
      <div className="upload-workspace">
        <div
          className={`drop-zone ${dragging ? 'dragging' : ''}`}
          onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => { event.preventDefault(); setDragging(false); acceptFile(event.dataTransfer.files[0]) }}
          onClick={() => inputRef.current?.click()}
          role="button"
          tabIndex={0}
          onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') inputRef.current?.click() }}
        >
          {fileInput}
          <div className="upload-illustration">
            <Icon name="image" size={44} />
          </div>
          <p><strong>Drop a frontal chest X-ray</strong> or browse from your device.</p>
          <small>Accepted formats: JPG, JPEG, PNG</small>
          <button type="button" className="button primary" onClick={(event) => { event.stopPropagation(); inputRef.current?.click() }}>
            <Icon name="upload" size={17} /> Select image
          </button>
        </div>
      </div>
    </section>
  )
}
