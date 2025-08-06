"use client"

import { useState, useEffect } from "react" // useEffect 임포트 추가
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, Play } from "lucide-react"
import type { Video } from "@/types/video-finder"

interface VideoPlayerProps {
  videos: Video[]
  currentVideoIndex: number
  selectedType: string
  onNavigate: (direction: "prev" | "next") => void
  onVideoSelect: (index: number) => void
}

export function VideoPlayer({ videos, currentVideoIndex, selectedType, onNavigate, onVideoSelect }: VideoPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(true) // 초기값을 true로 변경
  const [showControls, setShowControls] = useState(false)

  // 컴포넌트가 마운트될 때 (초기 로드 시) 비디오가 재생 중이면 컨트롤을 숨김
  useEffect(() => {
    if (isPlaying) {
      const timer = setTimeout(() => setShowControls(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [isPlaying]) // isPlaying 상태가 변경될 때마다 실행

  const getVideoLayoutClass = () => {
    return "aspect-video"
  }

  const handlePlayToggle = () => {
    setIsPlaying(!isPlaying)
    if (!isPlaying) {
      setShowControls(false)
      setTimeout(() => setShowControls(false), 3000)
    } else {
      setTimeout(() => setShowControls(false), 1500)
    }
  }

  return (
    <div
      className={`bg-black rounded-xl relative flex items-center justify-center shadow-2xl cursor-pointer border border-gray-800/50 overflow-hidden ${getVideoLayoutClass()}`}
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
      onClick={handlePlayToggle}
    >
      {/* Gradient overlay for better contrast */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30 pointer-events-none z-10"></div>

      {/* Navigation Arrows */}
      {showControls && (
        <>
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-4 text-white hover:bg-white/20 z-20 transition-all duration-300 backdrop-blur-sm bg-black/30 border border-white/20"
            onClick={(e) => {
              e.stopPropagation()
              onNavigate("prev")
            }}
          >
            <ChevronLeft className="h-8 w-8" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="absolute right-4 text-white hover:bg-white/20 z-20 transition-all duration-300 backdrop-blur-sm bg-black/30 border border-white/20"
            onClick={(e) => {
              e.stopPropagation()
              onNavigate("next")
            }}
          >
            <ChevronRight className="h-8 w-8" />
          </Button>
        </>
      )}

      {/* Play/Pause Button */}
      {(showControls || !isPlaying) && (
        <Button
          variant="ghost"
          size="icon"
          className="text-white hover:bg-white/20 z-20 w-20 h-20 rounded-full bg-black/50 hover:bg-black/70 transition-all duration-300 backdrop-blur-sm border border-white/20"
          onClick={handlePlayToggle}
        >
          {isPlaying ? (
            <div className="w-8 h-8 flex items-center justify-center">
              <div className="flex gap-1.5">
                <div className="w-2 h-8 bg-white rounded-sm"></div>
                <div className="w-2 h-8 bg-white rounded-sm"></div>
              </div>
            </div>
          ) : (
            <div className="w-12 h-12 flex items-center justify-center">
              <div className="w-0 h-0 border-l-[16px] border-l-white border-t-[12px] border-t-transparent border-b-[12px] border-b-transparent ml-1"></div>
            </div>
          )}
        </Button>
      )}

      {/* Video Thumbnails Grid (shown when paused) */}
      {!isPlaying && (
        <div className="absolute bottom-6 left-6 right-6 flex gap-4 z-20">
          {videos.slice(0, 3).map((video, index) => (
            <div
              key={video.id}
              className={`flex-1 rounded-lg cursor-pointer hover:scale-105 transition-all duration-300 border-2 shadow-xl ${
                index === currentVideoIndex
                  ? "border-cyan-400 shadow-cyan-400/25"
                  : "border-gray-700/50 hover:border-gray-600/70"
              }`}
              onClick={() => {
                onVideoSelect(index)
                setIsPlaying(true)
              }}
            >
              <div className="relative rounded-lg overflow-hidden bg-gray-800 aspect-video">
                <img src={video.url || "/placeholder.svg"} alt={video.title} className="w-full h-full object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30"></div>
                <div className="absolute inset-0 bg-black/30 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity duration-200">
                  <Play className="h-10 w-10 text-white drop-shadow-lg" />
                </div>
                <div className="absolute bottom-2 left-2 bg-black/80 backdrop-blur-sm text-white text-xs px-2 py-1 rounded border border-white/20">
                  {video.duration}
                </div>
                <div className="absolute bottom-2 right-2 bg-cyan-500/80 backdrop-blur-sm text-white text-xs px-2 py-1 rounded border border-cyan-400/30 font-medium">
                  {index + 1}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Video Info */}
      <div className="absolute bottom-4 left-4 text-white text-sm z-20 bg-black/80 backdrop-blur-sm px-4 py-2 rounded-lg border border-white/20">
        <span className="font-medium">{videos[currentVideoIndex]?.title}</span>
        <span className="text-gray-300 ml-2">
          ({currentVideoIndex + 1}/{videos.length})
        </span>
      </div>
    </div>
  )
} 