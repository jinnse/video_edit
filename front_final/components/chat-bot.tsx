"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Send, ChevronRight, ChevronDown } from "lucide-react"
import type { ChatMessage } from "@/types/video-finder"

interface ChatBotProps {
  messages: ChatMessage[]
  onMessageSubmit: (message: string) => void
  selectedVideo?: string | null
  onVideoSelect?: (video: string) => void
  videos?: any[]
}

export function ChatBot({ messages, onMessageSubmit, selectedVideo, onVideoSelect, videos }: ChatBotProps) {
  const [chatInput, setChatInput] = useState("")
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return

    onMessageSubmit(chatInput)
    setChatInput("")
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (!chatInput.trim()) return

      onMessageSubmit(chatInput)
      setChatInput("")
    }
  }

  const getVideoDisplayName = (videoPath: string) => {
    const fileName = videoPath.split("/").pop() || videoPath
    return fileName.replace(/\.[^/.]+$/, "")
  }

  return (
    <Card className="h-full flex flex-col shadow-2xl bg-gray-800/60 backdrop-blur-sm border-gray-700/50">
      <style jsx>{`
        textarea::-webkit-scrollbar {
          display: none;
        }
        .chat-messages::-webkit-scrollbar {
          display: none;
        }
      `}</style>
      <div className="p-4 border-b border-gray-700/50 bg-gray-800/40 flex items-center justify-between">
        <h2 className="text-lg font-bold text-white tracking-tight">Chat Bot</h2>
        {videos && videos.length > 0 && (
          <div className="relative">
            <Button
              variant="secondary"
              className="w-48 justify-between bg-gray-800/80 hover:bg-gray-700/80 text-white shadow-lg border border-gray-700/50 backdrop-blur-sm transition-all duration-200 text-sm py-2"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            >
              <span className="flex items-center gap-2 truncate">
                {selectedVideo ? getVideoDisplayName(selectedVideo) : "Video Input"}
              </span>
              {isDropdownOpen ? (
                <ChevronDown className="h-4 w-4 text-gray-400" />
              ) : (
                <ChevronRight className="h-4 w-4 text-gray-400" />
              )}
            </Button>

            {isDropdownOpen && (
              <div className="absolute top-full right-0 z-50 w-48 mt-1 bg-gray-800/90 border border-gray-700/50 rounded-lg shadow-lg backdrop-blur-sm">
                <div className="py-2 max-h-48 overflow-y-auto">
                  {videos.map((video, index) => (
                    <button
                      key={index}
                      className="w-full px-3 py-2 text-left text-white hover:bg-gray-700/50 transition-colors duration-150 flex items-center gap-2"
                      onClick={() => {
                        onVideoSelect?.(video)
                        setIsDropdownOpen(false)
                      }}
                    >
                      <span className="text-sm truncate">{getVideoDisplayName(video)}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4 bg-gray-800/20 chat-messages" style={{ minHeight: '200px', maxHeight: '400px' }}>
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.isBot ? "justify-start" : "justify-end"}`}>
            <div
              className={`max-w-xs px-4 py-3 rounded-xl text-sm shadow-lg backdrop-blur-sm border transition-all duration-200 break-words whitespace-pre-wrap ${
                message.isBot
                  ? "bg-gray-700/60 text-gray-100 border-gray-600/50"
                  : "bg-gradient-to-r from-purple-600/80 to-pink-500/80 text-white border-purple-500/30 shadow-purple-500/20"
              }`}
            >
              {message.isBot ? (
                <div dangerouslySetInnerHTML={{
                  __html: message.text
                    .replace(/\n/g, '<br>')
                    .replace(/📥 다운로드: (https?:\/\/[^\s]+)/g, '📥 <a href="$1" target="_blank" class="text-blue-400 hover:text-blue-300 underline" download>다운로드 링크</a>')
                }} />
              ) : (
                message.text
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Chat Input */}
      <div className="p-4 border-t border-gray-700/50 bg-gray-800/40">
        <form onSubmit={handleSubmit}>
          <div className="flex gap-2">
            <textarea
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="메시지를 입력하세요..."
              className="flex-1 bg-gray-700/60 border border-gray-600/50 text-white placeholder:text-gray-400 shadow-md focus:border-purple-500/50 focus:ring-purple-500/20 rounded-md px-3 py-2 resize-none overflow-y-auto"
              style={{ 
                height: '40px',
                scrollbarWidth: 'none',
                msOverflowStyle: 'none'
              }}
              rows={1}
            />
            <Button
              type="submit"
              size="icon"
              className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 shadow-lg transition-all duration-200 shadow-purple-500/25 flex-shrink-0"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </Card>
  )
} 