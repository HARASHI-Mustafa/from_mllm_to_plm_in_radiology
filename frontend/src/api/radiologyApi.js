import { API_BASE_URL } from './config'

export const exportUrls = {
  json: `${API_BASE_URL}/api/exports/json`,
  csv: `${API_BASE_URL}/api/exports/csv`,
  markdown: `${API_BASE_URL}/api/exports/markdown`,
  generatedReport: `${API_BASE_URL}/api/exports/generated-report`,
}

export async function analyzeImage(file) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error('Analysis API is not available. Please start the FastAPI backend.')
  }

  return response.json()
}
