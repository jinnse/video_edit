"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Send } from "lucide-react"
import type { ChatMessage } from "@/types/video-finder"

interface ChatBotProps {
  messages: ChatMessage[]
  onMessageSubmit: (message: string) => void
}

export function ChatBot({ messages, onMessageSubmit }: ChatBotProps) {
  const [chatInput, setChatInput] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!chatInput.trim()) return

    onMessageSubmit(chatInput)
    setChatInput("")
  }

  return (
    <Card className="h-full flex flex-col shadow-2xl bg-gray-800/60 backdrop-blur-sm border-gray-700/50">
      <div className="p-4 border-b border-gray-700/50 bg-gray-800/40">
        <h2 className="text-lg font-bold text-white tracking-tight">Chat Bot</h2>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-800/20">
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.isBot ? "justify-start" : "justify-end"}`}>
            <div
              className={`max-w-xs px-4 py-3 rounded-xl text-sm shadow-lg backdrop-blur-sm border transition-all duration-200 ${
                message.isBot
                  ? "bg-gray-700/60 text-gray-100 border-gray-600/50"
                  : "bg-gradient-to-r from-purple-600/80 to-pink-500/80 text-white border-purple-500/30 shadow-purple-500/20"
              }`}
            >
              {message.text}
            </div>
          </div>
        ))}
      </div>

      {/* Chat Input */}
      <div className="p-4 border-t border-gray-700/50 bg-gray-800/40">
        <form onSubmit={handleSubmit}>
          <div className="flex gap-2">
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="메시지를 입력하세요..."
              className="flex-1 bg-gray-700/60 border-gray-600/50 text-white placeholder:text-gray-400 shadow-md focus:border-purple-500/50 focus:ring-purple-500/20"
            />
            <Button
              type="submit"
              size="icon"
              className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 shadow-lg transition-all duration-200 shadow-purple-500/25"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </Card>
  )
} 