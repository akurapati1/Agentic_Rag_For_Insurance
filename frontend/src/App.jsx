import React, { useEffect, useState, useCallback } from 'react'
import { ShieldCheck, RefreshCw } from 'lucide-react'
import DocumentPanel from './components/DocumentPanel.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import { fetchDocuments } from './api.js'

export default function App() {
  const [documents, setDocuments] = useState([])
  const [docsLoading, setDocsLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const loadDocuments = useCallback(async () => {
    setDocsLoading(true)
    try {
      const data = await fetchDocuments()
      setDocuments(data.documents)
    } catch (e) {
      console.error('Failed to load documents:', e)
    } finally {
      setDocsLoading(false)
    }
  }, [])

  useEffect(() => { loadDocuments() }, [loadDocuments])

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50">
      {/* Navbar */}
      <header className="flex items-center gap-3 px-5 py-3 bg-brand-900 text-white shadow-md z-10 shrink-0">
        <ShieldCheck className="w-6 h-6 text-blue-300" />
        <span className="font-bold text-lg tracking-tight">Insurance RAG Assistant</span>
        <span className="ml-2 text-xs bg-blue-700 text-blue-200 px-2 py-0.5 rounded-full">
          Powered by OpenRouter
        </span>
        <div className="ml-auto flex items-center gap-2">
          <button
            onClick={loadDocuments}
            className="p-1.5 rounded hover:bg-blue-800 text-blue-300 hover:text-white transition"
            title="Refresh documents"
          >
            <RefreshCw className={`w-4 h-4 ${docsLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="text-xs px-3 py-1.5 rounded bg-blue-800 hover:bg-blue-700 transition"
          >
            {sidebarOpen ? 'Hide Docs' : 'Show Docs'}
          </button>
        </div>
      </header>

      {/* Main layout */}
      <main className="flex flex-1 overflow-hidden">
        {/* Sidebar — document panel */}
        {sidebarOpen && (
          <aside className="w-80 shrink-0 border-r bg-white overflow-y-auto">
            <DocumentPanel
              documents={documents}
              onRefresh={loadDocuments}
              loading={docsLoading}
            />
          </aside>
        )}

        {/* Chat area */}
        <section className="flex-1 overflow-hidden">
          <ChatPanel documentCount={documents.length} />
        </section>
      </main>
    </div>
  )
}
