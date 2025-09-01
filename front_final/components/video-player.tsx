"use client"

import type React from "react"

import { useState, useEffect, useRef } from "react"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight, Play } from "lucide-react"
import type { Video } from "@/types/video-finder"

interface VideoPlayerProps {
  videos: Video[]
  currentVideoIndex: number
  selectedType: string
  isPlaying: boolean
  onNavigate: (direction: "prev" | "next") => void
  onVideoSelect: (index: number) => void
  onPlayStateChange: (isPlaying: boolean) => void
}

function VideoPlayer({ videos, currentVideoIndex, selectedType, isPlaying, onNavigate, onVideoSelect, onPlayStateChange }: VideoPlayerProps) {
  const [showControls, setShowControls] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    if (isPlaying && showControls) {
      const timer = setTimeout(() => setShowControls(false), 3000)
      return () => clearTimeout(timer)
    }
  }, [isPlaying, showControls])

  // 비디오가 변경될 때만 재생 상태 초기화
  useEffect(() => {
    if (currentVideoIndex >= 0) {
      onPlayStateChange(false)
    }
  }, [currentVideoIndex, onPlayStateChange])

  const handlePlayToggle = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
        onPlayStateChange(false)
      } else {
        videoRef.current.play().catch((error) => {
          if (typeof window !== 'undefined') {
            console.error("비디오 재생 실패:", error)
          }
          onPlayStateChange(false)
        })
        onPlayStateChange(true)
      }
    }
  }

  const handleVideoClick = (e: React.MouseEvent) => {
    // Only handle click if it's not a drag operation
    if (e.detail === 1) {
      // Single click only
      handlePlayToggle()
    }
  }

  const currentVideo = currentVideoIndex >= 0 ? videos[currentVideoIndex] : null
  const hasPlayableVideo =
    currentVideo?.url &&
    typeof currentVideo.url === "string" &&
    (currentVideo.url.includes("cloudfront.net") ||
      currentVideo.url.includes("googleapis.com") ||
      currentVideo.url.includes("s3.amazonaws.com") ||
      currentVideo.url.startsWith("http")) &&
    currentVideo.url.endsWith(".mp4")  // 실제 비디오 파일인지 확인
  
  // 디버깅을 위한 로그 (클라이언트 사이드에서만)
  if (typeof window !== 'undefined') {
    console.log("현재 비디오:", currentVideo)
    console.log("재생 가능한 비디오:", hasPlayableVideo)
    console.log("현재 비디오 URL:", currentVideo?.url)
  }

  return (
    <div
      className="relative bg-black rounded-xl shadow-2xl border border-gray-800/50 overflow-hidden w-full h-full"
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      {/* Main Video Content - 비디오가 선택되었을 때만 표시 */}
      {currentVideoIndex >= 0 && hasPlayableVideo ? (
        <video
          ref={videoRef}
          src={currentVideo.url}
          className="w-full h-full object-contain cursor-pointer bg-black"
          onClick={handleVideoClick}
          onError={(e) => {
            if (typeof window !== 'undefined') {
              console.error("❌ 비디오 로딩 오류:", e)
              console.error("❌ 비디오 URL:", currentVideo.url)
            }
          }}
        />
      ) : (
        <div className="w-full h-full bg-gray-800 flex items-center justify-center">
          <span className="text-gray-400">
            {currentVideoIndex >= 0 ? "비디오를 선택해주세요" : "썸네일을 클릭하여 비디오를 선택하세요"}
          </span>
        </div>
      )}

      {/* Gradient Overlay */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-black/30 pointer-events-none z-20"></div>

      {/* Navigation Controls */}
      {showControls && (
        <>
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-4 top-1/2 -translate-y-1/2 text-white hover:bg-white/20 z-40 transition-colors duration-200 backdrop-blur-sm bg-black/30 border border-white/20"
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
            className="absolute right-4 top-1/2 -translate-y-1/2 text-white hover:bg-white/20 z-40 transition-colors duration-200 backdrop-blur-sm bg-black/30 border border-white/20"
            onClick={(e) => {
              e.stopPropagation()
              onNavigate("next")
            }}
          >
            <ChevronRight className="h-8 w-8" />
          </Button>
        </>
      )}

      {hasPlayableVideo && (showControls || !isPlaying) && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white hover:bg-white/20 z-40 w-20 h-20 rounded-full bg-black/50 hover:bg-black/70 transition-colors duration-200 backdrop-blur-sm border border-white/20"
          onClick={(e) => {
            e.stopPropagation()
            handlePlayToggle()
          }}
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

      {/* Video Thumbnails Grid - 재생 중이 아니거나 비디오가 선택되지 않았을 때 */}
      {(() => {
        const shouldShowThumbnails = (!isPlaying || currentVideoIndex === -1) && videos.length > 0
        if (typeof window !== 'undefined') {
          console.log("썸네일 그리드 표시 조건:", {
            isPlaying,
            currentVideoIndex,
            videosLength: videos.length,
            shouldShowThumbnails
          })
        }
        return shouldShowThumbnails
      })() && (
        <div className="absolute inset-0 z-30 bg-black/90">
          <div className="absolute bottom-6 left-6 right-6">
            <div className="grid grid-cols-3 gap-4 h-32">
              {videos.slice(0, 3).map((video, index) => (
                <div
                  key={video.id}
                  className={`relative rounded-lg cursor-pointer hover:scale-102 transition-transform duration-200 border-2 shadow-xl overflow-hidden ${
                    index === currentVideoIndex
                      ? "border-cyan-400 shadow-cyan-400/25"
                      : "border-gray-700/50 hover:border-gray-600/70"
                  }`}
                  onClick={() => {
                    if (typeof window !== 'undefined') {
                      console.log("썸네일 클릭됨:", index)
                      console.log("선택된 비디오:", videos[index])
                      console.log("현재 currentVideoIndex:", currentVideoIndex)
                    }
                    
                    // 이미 같은 비디오가 선택되어 있으면 재생만 토글
                    if (currentVideoIndex === index) {
                      onPlayStateChange(!isPlaying)
                    } else {
                      // 다른 비디오 선택
                      onVideoSelect(index)
                      onPlayStateChange(true)
                    }
                  }}
                >
                  <img
                    src={video.thumbnailUrl || video.url || "/placeholder.svg"}
                    alt={video.title}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      if (typeof window !== 'undefined') {
                        console.error("썸네일 로딩 실패:", video.thumbnailUrl || video.url)
                        console.error("비디오 객체:", video)
                      }
                    }}
                    onLoad={() => {
                      if (typeof window !== 'undefined') {
                        console.log("썸네일 로딩 성공:", video.thumbnailUrl || video.url)
                      }
                    }}
                  />
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
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Video Info */}
      <div className="absolute bottom-4 left-4 text-white text-sm z-30 bg-black/80 backdrop-blur-sm px-4 py-2 rounded-lg border border-white/20">
        <span className="font-medium">{currentVideo?.title || "비디오 제목"}</span>
        <span className="text-gray-300 ml-2">
          ({currentVideoIndex + 1}/{videos.length})
        </span>
      </div>
    </div>
  )
}

export default VideoPlayer 