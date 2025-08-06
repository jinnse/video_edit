"use client"

import { useState } from "react"
import { SettingsPanel } from "@/components/settings-panel"
import { VideoPlayer } from "@/components/video-player"
import { PromptSection } from "@/components/prompt-section"
import { ChatBot } from "@/components/chat-bot"
import type { Video, ChatMessage } from "@/types/video-finder"
import { Button } from "@/components/ui/button"
import Link from "next/link"

const SAMPLE_VIDEOS: Video[] = [
  {
    id: 1,
    title: "Business Meeting",
    url: "/placeholder.svg?height=120&width=200&text=Business+Meeting",
    duration: "5:32",
  },
  {
    id: 2,
    title: "Design Workshop",
    url: "/placeholder.svg?height=120&width=200&text=Design+Workshop",
    duration: "8:15",
  },
  {
    id: 3,
    title: "Marketing Presentation",
    url: "/placeholder.svg?height=120&width=200&text=Marketing+Presentation",
    duration: "12:45",
  },
]

const INITIAL_CHAT_MESSAGES: ChatMessage[] = [
  { id: 1, text: "안녕하세요! 오늘 어떤 비디오를 찾아드릴까요?", isBot: true },
  { id: 2, text: "샘플 비디오를 찾고 있어요", isBot: false },
  { id: 3, text: "네, 도와드릴게요! 어떤 종류의 비디오를 원하시나요?", isBot: true },
]

export default function VideoResultPage() {
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null)
  const [selectedCount, setSelectedCount] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<string>("highlights")
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0)
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES)
  const [prompt, setPrompt] = useState("")

  const handlePromptSubmit = async () => {
    if (!prompt.trim()) return
    console.log("Sending prompt to backend:", prompt)
    alert(`Prompt sent: ${prompt}`)
    setPrompt("")
  }

  const handleChatSubmit = (message: string) => {
    const newMessage: ChatMessage = {
      id: chatMessages.length + 1,
      text: message,
      isBot: false,
    }
    setChatMessages((prev) => [...prev, newMessage])

    // Simulate bot response
    setTimeout(() => {
      const botResponse: ChatMessage = {
        id: chatMessages.length + 2,
        text: "요청사항을 이해했습니다. 적합한 비디오를 찾아드리겠습니다.",
        isBot: true,
      }
      setChatMessages((prev) => [...prev, botResponse])
    }, 1000)
  }

  const navigateVideo = (direction: "prev" | "next") => {
    if (direction === "prev") {
      setCurrentVideoIndex((prev) => (prev > 0 ? prev - 1 : SAMPLE_VIDEOS.length - 1))
    } else {
      setCurrentVideoIndex((prev) => (prev < SAMPLE_VIDEOS.length - 1 ? prev + 1 : 0))
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Window Header */}
        <div className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-sm rounded-t-lg px-6 py-3 flex items-center justify-between border border-gray-800/50">
          {/* Left - Logo */}
          <Link href="/" className="text-xl font-bold text-white tracking-tight hover:text-gray-300 transition-colors">
            Video Finder
          </Link>
          
          {/* Center - Navigation Menu */}
          <nav className="flex items-center space-x-8 text-gray-300 text-sm font-medium">
            <Link href="#" className="hover:text-white transition-colors duration-200">
              Storage
            </Link>
            <Link href="/video-result" className="hover:text-white transition-colors duration-200">
              Video Result
            </Link>
            <Link href="#" className="hover:text-white transition-colors duration-200">
              Text
            </Link>
            <Link href="#" className="hover:text-white transition-colors duration-200">
              Video
            </Link>
          </nav>
          
          {/* Right - Login Button */}
          <Button
            variant="outline"
            className="bg-transparent text-white border border-gray-600 hover:bg-gray-700/50 hover:border-gray-500 transition-colors duration-200 px-6 py-2 rounded-lg"
          >
            Login
          </Button>
        </div>

        {/* Main Content */}
        <div className="bg-gray-900/60 backdrop-blur-sm rounded-b-lg p-6 flex gap-6 border-x border-b border-gray-800/50">
          {/* Left Panel */}
          <div className="flex-1 space-y-6">
            <SettingsPanel
              selectedVideo={selectedVideo}
              selectedCount={selectedCount}
              selectedType={selectedType}
              onVideoSelect={setSelectedVideo}
              onCountSelect={setSelectedCount}
              onTypeSelect={setSelectedType}
            />

            <VideoPlayer
              videos={SAMPLE_VIDEOS}
              currentVideoIndex={currentVideoIndex}
              selectedType={selectedType}
              onNavigate={navigateVideo}
              onVideoSelect={setCurrentVideoIndex}
            />

            <PromptSection prompt={prompt} onPromptChange={setPrompt} onSubmit={handlePromptSubmit} />
          </div>

          {/* Right Panel - Chat Bot */}
          <div className="w-80">
            <ChatBot messages={chatMessages} onMessageSubmit={handleChatSubmit} />
          </div>
        </div>
      </div>
    </div>
  )
} 