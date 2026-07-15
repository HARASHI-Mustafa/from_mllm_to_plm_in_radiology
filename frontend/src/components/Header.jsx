import Icon from './Icon'

export default function Header() {
  return (
    <header className="site-header">
      <div className="header-inner">
        <div className="brand-mark"><Icon name="activity" size={24} /></div>
        <div className="header-copy">
          <h1>MLLM - PLM Workflow</h1>
          <p>Chest X-ray report generation, structured finding extraction, and decision-support visualization.</p>
        </div>
        <div className="header-badges">
          <div className="badge safety-badge">
            <Icon name="alert" size={15} /> Decision-support only
          </div>
        </div>
      </div>
    </header>
  )
}
