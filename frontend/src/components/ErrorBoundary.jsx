import { Component } from 'react'

export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('The application could not render:', error, errorInfo)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="render-error" role="alert">
          <h1>The interface could not be displayed</h1>
          <p>Please refresh the page. If the issue continues, check the browser console for details.</p>
          <button type="button" onClick={() => window.location.reload()}>Reload page</button>
        </main>
      )
    }

    return this.props.children
  }
}
