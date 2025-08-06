"use client"

import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send } from "lucide-react"

interface PromptSectionProps {
  prompt: string
  onPromptChange: (prompt: string) => void
  onSubmit: () => void
}

export function PromptSection({ prompt, onPromptChange, onSubmit }: PromptSectionProps) {
  return (
    <div>
      <h3 className="text-lg font-semibold text-white mb-4 tracking-tight">Prompt</h3>
      <div className="flex gap-3">
        <Textarea
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder="Enter your prompt here..."
          className="flex-1 bg-gray-800/60 border-gray-700/50 text-white placeholder:text-gray-400 shadow-lg focus:border-purple-500/50 focus:ring-purple-500/20 backdrop-blur-sm resize-none"
          rows={3}
        />
        <Button
          className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 text-white self-end shadow-lg transition-all duration-200 px-6 shadow-purple-500/25"
          onClick={onSubmit}
        >
          <Send className="h-4 w-4 mr-2" />
          Send
        </Button>
      </div>
    </div>
  )
} 