import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import axios from 'axios'
import toast from 'react-hot-toast'
import { Upload, Github, Play } from 'lucide-react'

const Review = () => {
  const [code, setCode] = useState('')
  const [language, setLanguage] = useState('javascript')
  const [loading, setLoading] = useState(false)
  const [mode, setMode] = useState('paste')
  const navigate = useNavigate()

  const languages = [
    'javascript', 'typescript', 'python', 'java', 'csharp', 'cpp', 'go',
    'rust', 'ruby', 'php', 'swift', 'kotlin', 'scala', 'html', 'css'
  ]

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!code.trim()) {
      toast.error('Please enter some code to review')
      return
    }

    setLoading(true)

    try {
      const response = await axios.post('/api/review/analyze', {
        code,
        language,
        fileName: `code.${language}`
      })

      toast.success('Review started! Processing...')
      navigate(`/history/${response.data.reviewId}`)
    } catch (error) {
      toast.error(error.response?.data?.error || 'Failed to start review')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      setCode(event.target.result)
      const ext = file.name.split('.').pop()
      const langMap = {
        js: 'javascript',
        ts: 'typescript',
        py: 'python',
        java: 'java',
        cs: 'csharp',
        cpp: 'cpp',
        go: 'go',
        rs: 'rust',
        rb: 'ruby',
        php: 'php',
        swift: 'swift',
        kt: 'kotlin'
      }
      setLanguage(langMap[ext] || 'javascript')
      toast.success(`File "${file.name}" loaded`)
    }
    reader.readAsText(file)
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">New Code Review</h1>
        <p className="mt-2 text-gray-600">
          Submit your code for AI-powered analysis
        </p>
      </div>

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="border-b border-gray-200 px-6 py-3">
          <div className="flex space-x-4">
            <button
              onClick={() => setMode('paste')}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                mode === 'paste'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              Paste Code
            </button>
            <button
              onClick={() => setMode('upload')}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                mode === 'upload'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Upload className="w-4 h-4 inline mr-2" />
              Upload File
            </button>
            <button
              onClick={() => setMode('github')}
              className={`px-4 py-2 rounded-lg font-medium transition ${
                mode === 'github'
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Github className="w-4 h-4 inline mr-2" />
              GitHub
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="p-6">
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Programming Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="block w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              >
                {languages.map((lang) => (
                  <option key={lang} value={lang}>
                    {lang.charAt(0).toUpperCase() + lang.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            {mode === 'upload' && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Upload Code File
                </label>
                <input
                  type="file"
                  accept=".js,.ts,.jsx,.tsx,.py,.java,.cs,.cpp,.go,.rs,.rb,.php,.swift,.kt"
                  onChange={handleFileUpload}
                  className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>
            )}

            {mode === 'github' && (
              <div className="mb-4 p-4 bg-gray-50 rounded-lg">
                <p className="text-gray-600 text-sm mb-3">
                  Connect your GitHub account to import code from repositories
                </p>
                <button
                  type="button"
                  onClick={() => toast.info('GitHub integration coming soon')}
                  className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition"
                >
                  <Github className="w-5 h-5" />
                  Connect GitHub
                </button>
              </div>
            )}

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Code
              </label>
              <div className="border border-gray-300 rounded-lg overflow-hidden">
                <Editor
                  height="400px"
                  language={language}
                  value={code}
                  onChange={(value) => setCode(value || '')}
                  theme="vs"
                  options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false
                  }}
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || !code.trim()}
                className="flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play className="w-5 h-5" />
                {loading ? 'Starting Review...' : 'Start Review'}
              </button>
            </div>
          </div>
        </form>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-blue-900 mb-2">
          What will be analyzed?
        </h3>
        <ul className="space-y-2 text-blue-800">
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Security vulnerabilities and potential attacks</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Performance bottlenecks and optimization opportunities</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Code quality and best practices</span>
          </li>
          <li className="flex items-start">
            <span className="mr-2">•</span>
            <span>Potential bugs and edge cases</span>
          </li>
        </ul>
      </div>
    </div>
  )
}

export default Review
