import React, { useState, useEffect, useRef } from 'react'
import {
  MessageSquare,
  Send,
  Plus,
  BookOpen,
  Clock,
  Sparkles,
  Bot,
  User,
  Loader2,
  RefreshCw,
} from 'lucide-react'
import { citizenService } from '../../services/citizenService'
import { Button } from '../../components/Button'
import { Alert } from '../../components/Alert'
import type {
  ChatConversationSummary,
  ChatMessage,
} from '../../types/citizen'

const QUICK_PROMPTS = [
  'Are there any active road closures or detours in the city?',
  'What happens after I report a road pothole or crack?',
  'How does RoadX calculate road defect severity and risk levels?',
  'How do I track the repair progress of my submitted grievance?',
]

export const CitizenChatbotTab: React.FC = () => {
  const [conversations, setConversations] = useState<ChatConversationSummary[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')

  const [isLoadingConversations, setIsLoadingConversations] = useState(true)
  const [isLoadingMessages, setIsLoadingMessages] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadConversations()
  }, [])

  useEffect(() => {
    if (activeConversationId) {
      loadConversationMessages(activeConversationId)
    } else {
      setMessages([])
    }
  }, [activeConversationId])

  useEffect(() => {
    scrollToBottom()
  }, [messages, isSending])

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }

  const loadConversations = async () => {
    setIsLoadingConversations(true)
    setError(null)
    try {
      const data = await citizenService.listChatConversations()
      setConversations(data)
      if (data.length > 0 && !activeConversationId) {
        setActiveConversationId(data[0].id)
      } else if (data.length === 0) {
        // Automatically initialize the first conversation session
        await handleNewConversation('Citizen Inquiries & Road Advisories')
      }
    } catch {
      setError('Unable to load conversational sessions. You can start a new session below.')
    } finally {
      setIsLoadingConversations(false)
    }
  }

  const loadConversationMessages = async (conversationId: string) => {
    setIsLoadingMessages(true)
    setError(null)
    try {
      const data = await citizenService.getChatConversation(conversationId)
      setMessages(data.messages || [])
    } catch (err: unknown) {
      setError('Could not retrieve conversation history. The session might be archived.')
    } finally {
      setIsLoadingMessages(false)
    }
  }

  const handleNewConversation = async (customTitle?: string) => {
    setError(null)
    try {
      const title = customTitle || `Inquiry ${new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`
      const newSession = await citizenService.createChatConversation(title)
      setConversations((prev) => [
        {
          id: newSession.id,
          citizen_id: newSession.citizen_id,
          title: newSession.title,
          created_at: newSession.created_at,
          updated_at: newSession.updated_at,
          message_count: 0,
        },
        ...prev,
      ])
      setActiveConversationId(newSession.id)
      setMessages([])
    } catch (err: unknown) {
      setError('Unable to create a new chat session. The AI assistant service may be offline.')
    }
  }

  const handleSendMessage = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim()
    if (!text || isSending) return

    let convId = activeConversationId
    if (!convId) {
      try {
        const newSession = await citizenService.createChatConversation()
        convId = newSession.id
        setActiveConversationId(newSession.id)
        setConversations((prev) => [
          {
            id: newSession.id,
            citizen_id: newSession.citizen_id,
            title: newSession.title,
            created_at: newSession.created_at,
            updated_at: newSession.updated_at,
            message_count: 0,
          },
          ...prev,
        ])
      } catch {
        setError('Failed to initialize chat session. Please verify backend connectivity.')
        return
      }
    }

    // Optimistically add user message to UI
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: convId,
      role: 'USER',
      content: text,
      created_at: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, tempUserMsg])
    setInputText('')
    setIsSending(true)
    setError(null)

    try {
      const response = await citizenService.sendChatMessage(convId, text)
      // Replace or append with official saved messages
      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== tempUserMsg.id)
        return [...filtered, response.user_message, response.assistant_message]
      })
    } catch (err: unknown) {
      // Friendly fallback error as required by prompt
      setError(
        'The RoadX AI Assistant is currently experiencing high demand or the RAG service is temporarily unavailable. Please try again shortly or inspect Road Operations directly.'
      )
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold text-slate-900">RoadX Citizen AI Assistant</h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
              Grounded RAG
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Ask questions regarding road closures, municipal maintenance bylaws, and defect lifecycle resolution.
          </p>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => handleNewConversation()}
          className="flex items-center gap-1.5 self-start sm:self-auto text-indigo-600 hover:text-indigo-900 border-indigo-200"
        >
          <Plus className="w-4 h-4" />
          <span>New Session</span>
        </Button>
      </div>

      {error && (
        <Alert variant="warning" title="Assistant Notice" onDismiss={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Main Chat Interface */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-6 min-h-[580px]">
        {/* Session History Sidebar */}
        <div className="md:col-span-4 bg-white rounded-xl border border-slate-200 overflow-hidden flex flex-col h-[600px]">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-slate-500" />
              <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Chat Sessions</h2>
            </div>
            <button
              type="button"
              onClick={loadConversations}
              className="text-slate-400 hover:text-slate-600 p-1 rounded"
              title="Refresh sessions"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {isLoadingConversations ? (
              <div className="py-12 text-center text-xs text-slate-400">Loading sessions...</div>
            ) : conversations.length === 0 ? (
              <div className="py-12 text-center text-xs text-slate-400">No previous sessions.</div>
            ) : (
              conversations.map((c) => (
                <button
                  type="button"
                  key={c.id}
                  onClick={() => setActiveConversationId(c.id)}
                  className={`w-full text-left p-3 rounded-lg text-xs transition-colors flex items-center justify-between ${
                    activeConversationId === c.id
                      ? 'bg-blue-50 text-blue-900 font-semibold border border-blue-200 shadow-2xs'
                      : 'text-slate-600 hover:bg-slate-50 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <MessageSquare className={`w-4 h-4 shrink-0 ${activeConversationId === c.id ? 'text-blue-600' : 'text-slate-400'}`} />
                    <span className="truncate">{c.title}</span>
                  </div>
                  {c.message_count > 0 && (
                    <span className="text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-500 font-mono">
                      {c.message_count}
                    </span>
                  )}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Active Conversation Pane */}
        <div className="md:col-span-8 bg-white rounded-xl border border-slate-200 flex flex-col h-[600px] overflow-hidden">
          {/* Messages Stream */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-slate-50/30">
            {isLoadingMessages ? (
              <div className="py-24 text-center">
                <Loader2 className="w-7 h-7 animate-spin text-blue-600 mx-auto mb-2" />
                <p className="text-xs text-slate-500">Loading conversation history...</p>
              </div>
            ) : messages.length === 0 ? (
              <div className="py-12 text-center space-y-4 max-w-md mx-auto">
                <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-800">How can RoadX assist you today?</h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Ask questions grounded in municipal datasets, detour routes, and road failure repair standards.
                  </p>
                </div>

                <div className="space-y-2 pt-2 text-left">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Suggested Questions</p>
                  {QUICK_PROMPTS.map((prompt, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleSendMessage(prompt)}
                      className="w-full p-2.5 rounded-lg border border-slate-200 hover:border-blue-300 hover:bg-blue-50/50 text-left text-xs text-slate-700 transition-colors"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div
                  key={msg.id || idx}
                  className={`flex gap-3 ${msg.role === 'USER' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role !== 'USER' && (
                    <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-1">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl p-4 text-sm leading-relaxed ${
                      msg.role === 'USER'
                        ? 'bg-blue-600 text-white rounded-tr-xs'
                        : 'bg-white border border-slate-200 text-slate-800 shadow-2xs rounded-tl-xs'
                    }`}
                  >
                    {/* Safe text rendering avoiding any HTML execution */}
                    <p className="whitespace-pre-wrap">{msg.content}</p>

                    {/* Grounded RAG Source Citations */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-slate-100 space-y-2 text-xs">
                        <div className="flex items-center gap-1.5 text-slate-400 font-semibold text-[11px]">
                          <BookOpen className="w-3.5 h-3.5 text-indigo-500" />
                          <span>Grounded Municipal Knowledge Sources:</span>
                        </div>
                        <div className="space-y-1.5">
                          {msg.sources.map((src, sIdx) => (
                            <div
                              key={sIdx}
                              className="bg-slate-50 p-2 rounded-md border border-slate-200/80 text-[11px]"
                            >
                              <div className="flex items-center justify-between font-medium text-slate-800">
                                <span className="truncate">{src.title}</span>
                                {src.relevance_score !== null && src.relevance_score !== undefined && (
                                  <span className="text-[10px] font-mono text-emerald-600">
                                    {(src.relevance_score * 100).toFixed(0)}% Match
                                  </span>
                                )}
                              </div>
                              <p className="text-[10px] text-slate-500">
                                {src.source} • Category: {src.category}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {msg.role === 'USER' && (
                    <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center shrink-0 mt-1">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))
            )}

            {isSending && (
              <div className="flex gap-3 justify-start">
                <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs p-4 shadow-2xs text-xs text-slate-500 flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                  <span>Synthesizing answer from municipal road records & RAG knowledge...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Box */}
          <div className="p-4 bg-white border-t border-slate-200">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSendMessage()
              }}
              className="flex items-end gap-2"
            >
              <div className="flex-1 relative">
                <textarea
                  id="chat-input-textarea"
                  rows={2}
                  maxLength={1000}
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a question about road advisories, potholes, or repair timelines (Press Enter to send)..."
                  disabled={isSending}
                  className="w-full resize-none px-3.5 py-2.5 text-sm rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder:text-slate-400"
                />
                <span className="absolute bottom-1 right-2 text-[10px] text-slate-400 pointer-events-none">
                  {inputText.length}/1000
                </span>
              </div>

              <Button
                type="submit"
                variant="primary"
                disabled={!inputText.trim() || isSending}
                className="h-10 px-4 flex items-center justify-center"
                aria-label="Send Message"
              >
                {isSending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              </Button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}
