"use client"

import { useState, useEffect } from "react"
import { ChatBot } from "@/components/chat-bot"
import { SettingsPanel } from "@/components/settings-panel"
import VideoPlayer from "@/components/video-player"
import type { Video, ChatMessage } from "@/types/video-finder"
import { Button } from "@/components/ui/button"
import Link from "next/link"

const INITIAL_CHAT_MESSAGES: ChatMessage[] = [
  { id: 1, text: "안녕하세요! 오늘 어떤 비디오를 찾아드릴까요?", isBot: true },
]

export default function HomePage() {
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null)
  const [selectedCount, setSelectedCount] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<string>("highlights")
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES)
  const [videos, setVideos] = useState<Video[]>([])
  const [currentVideoIndex, setCurrentVideoIndex] = useState(0)
  const [prompt, setPrompt] = useState("")

  useEffect(() => {
    const initializeVideos = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://13.125.181.147:5001"}/api/v1/bucketdata`,
        )
        if (response.ok) {
          const data = await response.json()
          const videoExtensions = [".mp4", ".avi", ".mov", ".webm", ".mkv", ".flv", ".wmv"]
          const videoFiles = data.filter((item: string) =>
            videoExtensions.some((ext) => item.toLowerCase().endsWith(ext)),
          )

          const videoData: Video[] = videoFiles.map((file: string, index: number) => ({
            id: index + 1,
            title: file.replace(/\.[^/.]+$/, "").replace(/-/g, " "),
            url: `https://d1nmrhn4eusal2.cloudfront.net/${file}`,
            duration: "2:30",
            thumbnailUrl: `https://d3il8axvt9p9ix.cloudfront.net/${file.replace(/\.[^/.]+$/, ".jpg")}`,
          }))

          setVideos(videoData.length > 0 ? videoData : getDefaultVideos())
        } else {
          setVideos(getDefaultVideos())
        }
      } catch (error) {
        console.log("Failed to fetch videos, using defaults")
        setVideos(getDefaultVideos())
      }
    }

    const getDefaultVideos = (): Video[] => [
      {
        id: 1,
        title: "Business Meeting",
        url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        duration: "2:30",
        thumbnailUrl: "/images/video-title1.png",
      },
      {
        id: 2,
        title: "Design Workshop",
        url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        duration: "3:15",
        thumbnailUrl: "/images/video-title2.png",
      },
      {
        id: 3,
        title: "Marketing Presentation",
        url: "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        duration: "4:20",
        thumbnailUrl: "/images/video-title3.png",
      },
    ]

    initializeVideos()
  }, [])

  const handleChatSubmit = async (message: string) => {
    const newMessage: ChatMessage = {
      id: chatMessages.length + 1,
      text: message,
      isBot: false,
    }
    setChatMessages((prev) => [...prev, newMessage])

    // AI API 호출
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://13.125.181.147:5001"}/api/v1/video_ai`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            prompt: message,
            selectedVideo: selectedVideo,
            selectedCount: selectedCount,
            selectedType: selectedType,
          }),
        }
      )

      if (response.ok) {
        const data = await response.json()
        const botResponse: ChatMessage = {
          id: chatMessages.length + 2,
          text: data.output || "요청사항을 처리했습니다.",
          isBot: true,
        }
        setChatMessages((prev) => [...prev, botResponse])
      } else {
        throw new Error("API 호출 실패")
      }
    } catch (error) {
      console.error("AI API 호출 오류:", error)
      const botResponse: ChatMessage = {
        id: chatMessages.length + 2,
        text: "죄송합니다. 요청을 처리하는 중 오류가 발생했습니다.",
        isBot: true,
      }
      setChatMessages((prev) => [...prev, botResponse])
    }
  }

  const handleVideoNavigate = (direction: "prev" | "next") => {
    if (direction === "prev") {
      setCurrentVideoIndex((prev) => (prev > 0 ? prev - 1 : videos.length - 1))
    } else {
      setCurrentVideoIndex((prev) => (prev < videos.length - 1 ? prev + 1 : 0))
    }
  }

  const handleVideoSelect = (index: number) => {
    setCurrentVideoIndex(index)
  }

  const handleVideoSelectFromDropdown = (videoFileName: string) => {
    setSelectedVideo(videoFileName)

    // Find the corresponding video in the videos array
    const videoIndex = videos.findIndex(
      (video) =>
        video.url.includes(videoFileName) ||
        video.title.toLowerCase().includes(videoFileName.replace(".mp4", "").toLowerCase()),
    )

    if (videoIndex !== -1) {
      setCurrentVideoIndex(videoIndex)
    }
  }

  const handlePromptSubmit = () => {
    if (prompt.trim()) {
      handleChatSubmit(prompt)
      setPrompt("")
    }
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-sm px-6 py-3 flex items-center justify-between border-b border-gray-800/50">
        <Link href="/" className="text-xl font-bold text-white tracking-tight hover:text-gray-300 transition-colors">
          Video Finder
        </Link>

        <nav className="flex items-center space-x-8 text-gray-300 text-sm font-medium">
          <Link href="#" className="hover:text-white transition-colors duration-200">
            Storage
          </Link>
          <Link href="/video-result" className="hover:text-white transition-colors duration-200">
            Analyze
          </Link>
        </nav>

        <Button
          variant="outline"
          className="bg-transparent text-white border border-gray-600 hover:bg-gray-700/50 hover:border-gray-500 transition-colors duration-200 px-6 py-2 rounded-lg"
        >
          Login
        </Button>
      </div>

      <div className="flex h-[calc(100vh-73px)]">
        <div className="flex-1 max-w-4xl bg-gray-900/60 border-r border-gray-800/50 flex flex-col">
          <div className="p-4">
            <h2 className="text-xl font-bold text-white mb-4 tracking-tight">Settings</h2>
            <SettingsPanel
              selectedVideo={selectedVideo}
              selectedCount={selectedCount}
              selectedType={selectedType}
              onVideoSelect={handleVideoSelectFromDropdown}
              onCountSelect={setSelectedCount}
              onTypeSelect={setSelectedType}
            />
          </div>

          {/* Main content area for video player */}
          <div className="flex-1 flex items-center justify-center p-4">
            {selectedVideo ? (
              <div className="w-full">
                <VideoPlayer
                  videos={videos}
                  currentVideoIndex={currentVideoIndex}
                  selectedType={selectedType}
                  onNavigate={handleVideoNavigate}
                  onVideoSelect={handleVideoSelect}
                />
              </div>
            ) : (
              <div className="text-center">
                <p className="text-gray-400 text-lg">비디오를 선택해주세요</p>
              </div>
            )}
          </div>
        </div>

        <div className="w-96 bg-gray-900/60 border-l border-gray-800/50">
          <ChatBot messages={chatMessages} onMessageSubmit={handleChatSubmit} />
        </div>
      </div>
    </div>
  )
}
