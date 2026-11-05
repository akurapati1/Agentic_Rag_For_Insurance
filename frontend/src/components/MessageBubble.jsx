import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Bot, User, FileText } from 'lucide-react'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
        ${isUser ? 'bg-brand-600 text-white' : 'bg-white border border-gray-200 text-brand-600'}`}>
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      <div className={`flex flex-col gap-1 max-w-[78%] ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble */}
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed
          ${isUser
            ? 'bg-brand-600 text-white rounded-tr-sm'
            : 'bg-white border border-gray-100 text-gray-800 rounded-tl-sm shadow-sm'
          }`}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-li:my-0">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-0.5">
            {message.sources.map((src) => (
              <span
                key={src}
                className="inline-flex items-center gap-1 text-xs bg-brand-50 text-brand-700 px-2 py-0.5 rounded-full border border-brand-100"
              >
                <FileText className="w-3 h-3" />
                {src}
              </span>
            ))}
          </div>
        )}

        {/* Agent trace: what the agent searched for */}
        {!isUser && message.trace?.queries?.length > 0 && (
          <details className="text-[11px] text-gray-500 px-1">
            <summary className="cursor-pointer select-none">
              Agent searched {message.trace.queries.length} quer{message.trace.queries.length === 1 ? 'y' : 'ies'} ·
              {' '}{message.trace.kept_after_grading}/{message.trace.retrieved} passages kept
            </summary>
            <ul className="list-disc ml-4 mt-1">
              {message.trace.queries.map((q) => <li key={q}>{q}</li>)}
            </ul>
          </details>
        )}

        {/* Model tag */}
        {!isUser && message.model && message.model !== 'none' && (
          <span className="text-[10px] text-gray-400 px-1">via {message.model}</span>
        )}
      </div>
    </div>
  )
}
