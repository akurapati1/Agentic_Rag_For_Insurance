import React, { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, Trash2, Loader2, CheckCircle, AlertCircle } from 'lucide-react'
import { uploadDocuments, deleteDocument } from '../api.js'

export default function DocumentPanel({ documents, onRefresh, loading }) {
  const [uploading, setUploading] = useState(false)
  const [uploadResults, setUploadResults] = useState([])
  const [deletingFile, setDeletingFile] = useState(null)

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!acceptedFiles.length) return
    setUploading(true)
    setUploadResults([])
    try {
      const data = await uploadDocuments(acceptedFiles)
      setUploadResults(data.results)
      await onRefresh()
    } catch (e) {
      setUploadResults([{ status: 'error', detail: e.message }])
    } finally {
      setUploading(false)
    }
  }, [onRefresh])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    multiple: true,
  })

  const handleDelete = async (filename) => {
    setDeletingFile(filename)
    try {
      await deleteDocument(filename)
      await onRefresh()
    } catch (e) {
      console.error(e)
    } finally {
      setDeletingFile(null)
    }
  }

  return (
    <div className="flex flex-col h-full gap-4 p-4">
      {/* Header */}
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Documents</h2>
        <p className="text-xs text-gray-500 mt-0.5">Upload PDFs to build your knowledge base</p>
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all
          ${isDragActive
            ? 'border-brand-500 bg-brand-50 scale-[1.02]'
            : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50'
          }`}
      >
        <input {...getInputProps()} />
        {uploading ? (
          <div className="flex flex-col items-center gap-2 text-brand-600">
            <Loader2 className="w-8 h-8 animate-spin" />
            <p className="text-sm font-medium">Processing PDFs…</p>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-500">
            <Upload className="w-8 h-8" />
            <p className="text-sm font-medium">
              {isDragActive ? 'Drop PDFs here' : 'Drag & drop PDFs'}
            </p>
            <p className="text-xs">or click to browse</p>
          </div>
        )}
      </div>

      {/* Upload results */}
      {uploadResults.length > 0 && (
        <div className="flex flex-col gap-1">
          {uploadResults.map((r, i) => (
            <div
              key={i}
              className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg
                ${r.status === 'indexed' ? 'bg-green-50 text-green-700'
                  : r.status === 'error' ? 'bg-red-50 text-red-700'
                  : 'bg-yellow-50 text-yellow-700'}`}
            >
              {r.status === 'indexed'
                ? <CheckCircle className="w-3.5 h-3.5 shrink-0" />
                : <AlertCircle className="w-3.5 h-3.5 shrink-0" />}
              <span className="truncate font-medium">{r.filename || 'File'}</span>
              {r.status === 'indexed' && <span className="ml-auto shrink-0">{r.chunks} chunks</span>}
              {r.status === 'error' && <span className="ml-auto shrink-0">{r.detail}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Document list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin flex flex-col gap-1">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
          </div>
        ) : documents.length === 0 ? (
          <div className="flex flex-col items-center py-10 text-gray-400 gap-2">
            <FileText className="w-8 h-8" />
            <p className="text-sm">No documents indexed yet</p>
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.filename}
              className="flex items-center gap-2 px-3 py-2.5 bg-white rounded-lg border border-gray-100 hover:border-gray-200 group"
            >
              <FileText className="w-4 h-4 shrink-0 text-brand-500" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate" title={doc.filename}>
                  {doc.filename}
                </p>
                <p className="text-xs text-gray-400">{doc.chunks} chunks</p>
              </div>
              <button
                onClick={() => handleDelete(doc.filename)}
                disabled={deletingFile === doc.filename}
                className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-50 hover:text-red-500 text-gray-400 transition-all"
                title="Remove document"
              >
                {deletingFile === doc.filename
                  ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  : <Trash2 className="w-3.5 h-3.5" />}
              </button>
            </div>
          ))
        )}
      </div>

      {/* Stats footer */}
      {documents.length > 0 && (
        <div className="text-xs text-gray-400 text-center border-t pt-2">
          {documents.length} document{documents.length !== 1 ? 's' : ''} ·{' '}
          {documents.reduce((s, d) => s + d.chunks, 0)} total chunks
        </div>
      )}
    </div>
  )
}
