import Icon from './Icon'

export default function DecisionSupport({ data }) {
  if (!data) {
    return <section className="card data-fallback">Decision-support details are unavailable.</section>
  }

  const priority = data.review_priority || 'unknown'
  const reasons = (data.reasons ?? []).filter(
    (reason) => reason !== 'One or more active findings belong to high-risk or low-support labels from the 200-case safety analysis.',
  )

  return (
    <section className={`card decision-card priority-${priority}`}>
      <div className="decision-header">
        <div className="decision-icon"><Icon name="shield" size={22} /></div>
        <div>
          <span className="eyebrow">Decision-support summary</span>
          <h2>Clinical review required</h2>
        </div>
      </div>
      <div className="decision-pills">
        <span>Review <strong>{data.review_recommended ? 'recommended' : 'not required'}</strong></span>
        <span>Priority <strong>{priority}</strong></span>
      </div>
      <div className="reason-box">
        <h3>Review rationale</h3>
        <ul>{reasons.map((reason) => <li key={reason}><Icon name="check" size={15} /> <span>{reason}</span></li>)}</ul>
      </div>
      <div className="final-note">
        <Icon name="alert" size={19} />
        <p><strong>Decision-support output only.</strong> Final interpretation requires clinical review.</p>
      </div>
    </section>
  )
}
