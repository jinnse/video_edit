"use client"

import { useState, useEffect } from "react"
import { SettingsPanel } from "@/components/settings-panel"
import VideoPlayer from "@/components/video-player"
import { ChatBot } from "@/components/chat-bot"

import type { Video, ChatMessage } from "@/types/video-finder"
import { Button } from "@/components/ui/button"
import Link from "next/link"

const INITIAL_CHAT_MESSAGES: ChatMessage[] = [
  { id: 1, text: "안녕하세요! 오늘 어떤 비디오를 찾아드릴까요?", isBot: true },
]

export default function VideoResultPage() {
  const [selectedVideo, setSelectedVideo] = useState<string | null>(null)
  const [selectedCount, setSelectedCount] = useState<string | null>(null)
  const [selectedType, setSelectedType] = useState<string>("highlights")
  const [currentVideoIndex, setCurrentVideoIndex] = useState(-1) // 초기값을 -1로 설정 (선택되지 않음)
  const [isPlaying, setIsPlaying] = useState(false) // 재생 상태 관리
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(INITIAL_CHAT_MESSAGES)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [username, setUsername] = useState("")
  const [showUserMenu, setShowUserMenu] = useState(false)

  // 로그인 상태 확인
  useEffect(() => {
    // 클라이언트 사이드에서만 실행
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('token')
      const user = localStorage.getItem('user')
      
      if (token && user) {
        try {
          const userData = JSON.parse(user)
          setIsLoggedIn(true)
          setUsername(userData.username || 'User')
        } catch (error) {
          console.error('사용자 데이터 파싱 오류:', error)
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          setIsLoggedIn(false)
          window.location.href = '/login'
        }
      } else {
        // 로그인되지 않은 경우 로그인 페이지로 리다이렉트
        setIsLoggedIn(false)
        window.location.href = '/login'
      }
    }
  }, [])

  // 로그아웃 함수
  const handleLogout = () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      setIsLoggedIn(false)
      setUsername("")
      setShowUserMenu(false)
      window.location.href = '/'
    }
  }

  // isPlaying 상태 변화 추적
  useEffect(() => {
    console.log("isPlaying 상태 변화:", isPlaying)
  }, [isPlaying])
  const [prompt, setPrompt] = useState("")
  const [editedVideos, setEditedVideos] = useState<Video[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [videoOptions, setVideoOptions] = useState<string[]>([])

  // AI 에이전트가 편집한 결과를 표시할 샘플 데이터
  const SAMPLE_EDITED_VIDEOS: Video[] = [
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

  // 영상 길이를 가져오는 함수 (개선된 버전)
  const getVideoDuration = (url: string): Promise<string> => {
    return new Promise((resolve) => {
      const video = document.createElement('video')
      video.preload = 'metadata'
      
      let timeoutId: NodeJS.Timeout
      
      const cleanup = () => {
        if (timeoutId) clearTimeout(timeoutId)
        video.remove()
      }
      
      video.onloadedmetadata = () => {
        cleanup()
        const duration = video.duration
        if (duration && isFinite(duration)) {
          const minutes = Math.floor(duration / 60)
          const seconds = Math.floor(duration % 60)
          const formattedDuration = `${minutes}:${seconds.toString().padStart(2, '0')}`
          resolve(formattedDuration)
        } else {
          resolve("0:01")
        }
      }
      
      video.onerror = () => {
        cleanup()
        resolve("0:01") // 에러 시 기본값
      }
      
      // 10초 타임아웃 설정
      timeoutId = setTimeout(() => {
        cleanup()
        resolve("0:01")
      }, 10000)
      
      video.src = url
    })
  }

  // 비디오 옵션을 가져오는 함수
  const fetchVideoOptions = async () => {
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "https://www.videofinding.com:5000"}/api/v1/bucketdata`,
      )
      if (response.ok) {
        const data = await response.json()
        const videoExtensions = [".mp4", ".avi", ".mov", ".webm", ".mkv", ".flv", ".wmv"]

        // original/ 폴더에 있는 비디오 파일만 필터링
        const originalVideoFiles = data.filter(
          (item: string) =>
            item.startsWith("original/") && videoExtensions.some((ext) => item.toLowerCase().endsWith(ext)),
        )

        console.log("Original 폴더 비디오 파일들:", originalVideoFiles)
        setVideoOptions(originalVideoFiles.length > 0 ? originalVideoFiles : [])
      }
    } catch (error) {
      console.log("비디오 옵션 로딩 오류")
    }
  }

  useEffect(() => {
    fetchVideoOptions()
  }, [])

  const handlePromptSubmit = async (incomingPrompt?: string) => {
    const effectivePrompt = (incomingPrompt ?? prompt).trim()
    console.log("handlePromptSubmit 호출됨!")
    console.log("현재 prompt:", effectivePrompt)
    console.log("현재 selectedVideo:", selectedVideo)

    if (!effectivePrompt) {
      console.log("프롬프트가 비어있음")
      return
    }
    if (!selectedVideo) {
      console.log("비디오가 선택되지 않음")
      return
    }

    console.log("처리 시작 - isProcessing을 true로 설정")
    setIsProcessing(true)

    try {
      console.log("백엔드로 전송하는 데이터:", {
        selectedVideo,
        prompt: effectivePrompt,
      })

      // original/ 접두사 제거
      const cleanSelectedVideo = selectedVideo.replace('original/', '')
      
      const params = new URLSearchParams({
        selectedVideo: cleanSelectedVideo,
        prompt: effectivePrompt,
      })

      const response = await fetch(`https://www.videofinding.com:5002/api/v1/video_ai?${params}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      })

      if (response.ok) {
        const data = await response.json()
        console.log("🎬 백엔드 응답 전체:", data)
        console.log("🎬 응답 데이터 타입:", typeof data)
        console.log("🎬 allOutputs:", data.allOutputs)
        console.log("🎬 videoUrl:", data.videoUrl)
        console.log("🎬 cloudfrontUrl:", data.cloudfrontUrl)
        console.log("🎬 editedVideos:", data.editedVideos)

        // 백엔드에서 반환하는 데이터 처리
        if (data.ok) {
          let processedVideos: Video[] = []
          
          // allOutputs 배열이 있는 경우 처리
          if (data.allOutputs && Array.isArray(data.allOutputs)) {
            console.log("allOutputs 배열 처리:", data.allOutputs)
            
            // 백엔드에서 제공하는 여러 CloudFront URL 사용
            const videoUrls: string[] = []
            
            // 1. cloudfrontUrls 배열이 있으면 사용 (새로운 방식)
            if (data.cloudfrontUrls && Array.isArray(data.cloudfrontUrls)) {
              videoUrls.push(...data.cloudfrontUrls)
              console.log("🎬 cloudfrontUrls 배열 사용:", data.cloudfrontUrls)
            }
            // 2. cloudfrontUrl이 있으면 추가 (하위 호환성)
            else if (data.cloudfrontUrl) {
              videoUrls.push(data.cloudfrontUrl)
              console.log("🎬 cloudfrontUrl 사용:", data.cloudfrontUrl)
            }
            
            // 3. videoUrls 배열이 있으면 CloudFront URL로 변환
            if (data.videoUrls && Array.isArray(data.videoUrls)) {
              console.log("🎬 videoUrls 배열 발견:", data.videoUrls)
              data.videoUrls.forEach((url: string) => {
                // S3 URL에서 파일명 추출하여 CloudFront URL 생성
                const filenameMatch = url.match(/\/([^\/\?]+\.mp4)/)
                if (filenameMatch) {
                  const filename = filenameMatch[1]
                  const cloudfrontUrl = `https://d1nmrhn4eusal2.cloudfront.net/${filename}`
                  videoUrls.push(cloudfrontUrl)
                  console.log("🎬 S3 URL을 CloudFront URL로 변환:", cloudfrontUrl)
                }
              })
            }
            
            // 4. allOutputs에서 URL 패턴 찾기 (기존 방식)
            if (videoUrls.length === 0 && data.allOutputs) {
              data.allOutputs.forEach((output: any, index: number) => {
                console.log(`🎬 allOutputs[${index}] 처리:`, output)
                if (typeof output === 'string') {
                  // S3 프리사인 URL 패턴 찾기
                  const s3UrlMatches = output.match(/https:\/\/[^\s\)]+\.s3\.amazonaws\.com\/[^\s\)]+\.mp4\?[^\)\s]+/g)
                  if (s3UrlMatches) {
                    s3UrlMatches.forEach((s3Url: string) => {
                      const filenameMatch = s3Url.match(/\/([^\/\?]+\.mp4)/)
                      if (filenameMatch) {
                        const filename = filenameMatch[1]
                        const cloudfrontUrl = `https://d1nmrhn4eusal2.cloudfront.net/${filename}`
                        videoUrls.push(cloudfrontUrl)
                        console.log("🎬 S3 URL을 CloudFront URL로 변환:", cloudfrontUrl)
                      }
                    })
                  }
                  
                  // CloudFront URL 패턴 찾기
                  const cloudfrontMatches = output.match(/https:\/\/[^\s\)]+\.cloudfront\.net\/[^\s\)]+\.mp4/g)
                  if (cloudfrontMatches) {
                    videoUrls.push(...cloudfrontMatches)
                    console.log("🎬 CloudFront URL들 추가:", cloudfrontMatches)
                  }
                }
              })
            }
            
            console.log("🎬 추출된 모든 URL들:", videoUrls)
            
            // 중복 제거
            const uniqueVideoUrls = [...new Set(videoUrls)]
            console.log("🎬 중복 제거 후 URL들:", uniqueVideoUrls)
            
            if (uniqueVideoUrls.length > 0) {
              // 실제 영상 길이를 가져와서 비디오 객체 생성 (순차적으로 처리)
              processedVideos = []
              for (let index = 0; index < uniqueVideoUrls.length; index++) {
                const url = uniqueVideoUrls[index]
                console.log(`🎬 비디오 ${index + 1} 길이 가져오는 중:`, url)
                const duration = await getVideoDuration(url)
                console.log(`🎬 비디오 ${index + 1} 길이:`, duration)
                
                processedVideos.push({
                  id: Date.now() + index,
                  title: `편집된 비디오 ${index + 1} - ${selectedVideo}`,
                  url: url,
                  duration: duration,
                  thumbnailUrl: data.thumbnailUrls?.[index] || data.thumbnailUrl || undefined,
                })
              }
            } else {
              // 기존 allOutputs 처리 로직 (순차적으로 처리)
              processedVideos = []
              for (let index = 0; index < data.allOutputs.length; index++) {
                const output = data.allOutputs[index]
                console.log(`🎬 allOutputs[${index}] 처리:`, output)
                
                // output이 문자열인 경우 (URL 또는 메시지)
                if (typeof output === 'string') {
                  // URL인지 확인 (http로 시작하는지)
                  if (output.startsWith('http')) {
                    console.log(`🎬 비디오 ${index + 1} 길이 가져오는 중:`, output)
                    const duration = await getVideoDuration(output)
                    console.log(`🎬 비디오 ${index + 1} 길이:`, duration)
                    
                    processedVideos.push({
                      id: Date.now() + index,
                      title: `편집된 비디오 ${index + 1} - ${selectedVideo}`,
                      url: output,
                      duration: duration,
                      thumbnailUrl: data.thumbnailUrl || undefined,
                    })
                  }
                  // 메시지인 경우 무시
                }
                // output이 객체인 경우
                else if (typeof output === 'object' && output !== null) {
                  const videoUrl = output.url || output.videoUrl || output.cloudfrontUrl
                  if (videoUrl) {
                    console.log(`🎬 비디오 ${index + 1} 길이 가져오는 중:`, videoUrl)
                    const duration = await getVideoDuration(videoUrl)
                    console.log(`🎬 비디오 ${index + 1} 길이:`, duration)
                    
                    processedVideos.push({
                      id: Date.now() + index,
                      title: output.title || `편집된 비디오 ${index + 1} - ${selectedVideo}`,
                      url: videoUrl,
                      duration: duration,
                      thumbnailUrl: output.thumbnailUrl || data.thumbnailUrl || undefined,
                    })
                  }
                }
              }
            }
          }
          
          // 기존 videoUrl, cloudfrontUrl 처리 (하위 호환성)
          if (processedVideos.length === 0 && (data.videoUrl || data.cloudfrontUrl)) {
            const videoUrl = data.videoUrl || data.cloudfrontUrl
            const duration = await getVideoDuration(videoUrl)
            processedVideos = [{
              id: Date.now(),
              title: data.videoFilename || `편집된 비디오 - ${selectedVideo}`,
              url: videoUrl,
              duration: duration,
              thumbnailUrl: data.thumbnailUrl || undefined,
            }]
          }
          
          // 기존 editedVideos 형식 처리
          if (processedVideos.length === 0 && data.editedVideos) {
            processedVideos = data.editedVideos
          }
          
          if (processedVideos.length > 0) {
            console.log("🎬 처리된 비디오들:", processedVideos)
            console.log("🎬 첫 번째 비디오 URL:", processedVideos[0]?.url)
            console.log("🎬 첫 번째 비디오 제목:", processedVideos[0]?.title)
            setEditedVideos(processedVideos)
            setCurrentVideoIndex(-1)
            setIsPlaying(false)
            
            // 채팅에 성공 메시지 추가
            const videoCount = processedVideos.length
            const successMessage: ChatMessage = {
              id: chatMessages.length + 1,
              text: `✅ "${effectivePrompt}" 요청이 성공적으로 처리되었습니다!\n📁 생성된 비디오: ${videoCount}개`,
              isBot: true,
            }
            setChatMessages((prev) => [...prev, successMessage])
          } else {
            // 비디오가 생성되지 않은 경우 (메시지만 있는 경우)
            console.log("비디오 URL이 없음, 메시지만 표시")
            
            // allOutputs에서 메시지 추출
            let messageText = "❌ 비디오를 생성할 수 없습니다."
            if (data.allOutputs && Array.isArray(data.allOutputs)) {
              const messages = data.allOutputs.filter((output: any) => 
                typeof output === 'string' && !output.startsWith('http')
              )
              if (messages.length > 0) {
                messageText = messages.join('\n')
              }
            }
            
            const errorMessage: ChatMessage = {
              id: chatMessages.length + 1,
              text: messageText,
              isBot: true,
            }
            setChatMessages((prev) => [...prev, errorMessage])
          }
        } else if (data.editedVideos) {
          // 기존 editedVideos 형식 지원
          setEditedVideos(data.editedVideos)
        } else {
          // 응답에 videoUrl이 없으면 샘플 데이터 사용
          setEditedVideos(SAMPLE_EDITED_VIDEOS)

          // 채팅에 오류 메시지 추가
          const errorMessage: ChatMessage = {
            id: chatMessages.length + 1,
            text: "❌ 비디오 URL을 찾을 수 없습니다. 다시 시도해주세요.",
            isBot: true,
          }
          setChatMessages((prev) => [...prev, errorMessage])
        }

        setPrompt("")
      } else {
        const errorData = await response.json()
        console.error("백엔드 오류:", errorData)

        // 채팅에 오류 메시지 추가
        const errorMessage: ChatMessage = {
          id: chatMessages.length + 1,
          text: `❌ 오류가 발생했습니다: ${errorData.error || "알 수 없는 오류"}`,
          isBot: true,
        }
        setChatMessages((prev) => [...prev, errorMessage])
      }
    } catch (error) {
      console.error("전송 오류:", error)
      console.error("오류 타입:", typeof error)
      if (error instanceof Error) {
        console.error("오류 메시지:", error.message)
        console.error("오류 스택:", error.stack)
      }

      // CORS 오류인 경우 사용자에게 알림
      if (error instanceof TypeError && error.message.includes("Failed to fetch")) {
        alert("서버 연결에 실패했습니다. CORS 설정을 확인해주세요.")
      } else {
        alert("요청 처리 중 오류가 발생했습니다.")
      }
    } finally {
      console.log("처리 완료 - isProcessing을 false로 설정")
      setIsProcessing(false)
    }
  }

  const handleChatSubmit = async (message: string) => {
    // 사용자 메시지 추가
    const newMessage: ChatMessage = {
      id: chatMessages.length + 1,
      text: message,
      isBot: false,
    }
    setChatMessages((prev) => [...prev, newMessage])

    // 비디오 미선택 안내
    if (!selectedVideo) {
      const botResponse: ChatMessage = {
        id: chatMessages.length + 2,
        text: "먼저 왼쪽에서 비디오를 선택해주세요.",
        isBot: true,
      }
      setChatMessages((prev) => [...prev, botResponse])
      return
    }

    // 챗봇 입력을 프롬프트로 사용해서 동일 플로우 실행
    await handlePromptSubmit(message)
  }

  const handleVideoNavigate = (direction: "prev" | "next") => {
    if (direction === "prev") {
      setCurrentVideoIndex((prev) => (prev > 0 ? prev - 1 : editedVideos.length - 1))
    } else {
      setCurrentVideoIndex((prev) => (prev < editedVideos.length - 1 ? prev + 1 : 0))
    }
  }

  const handleVideoSelect = (index: number) => {
    setCurrentVideoIndex(index)
  }

  return (
    <div className="min-h-screen bg-gray-950 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Window Header */}
        <div className="sticky top-0 z-50 bg-gray-900/80 backdrop-blur-sm rounded-t-lg px-6 py-3 flex items-center justify-between border border-gray-800/50">
          {/* Left - Logo */}
          <Link href="/" className="text-xl font-bold text-white tracking-tight hover:text-gray-300 transition-colors">
            Clip Haus
          </Link>

          {/* Center - Navigation Menu */}
          <div className="flex items-center space-x-12 text-sm text-gray-300">
            <Link href="/storage" className="hover:text-white transition-colors">
              Storage
            </Link>
            <Link href="/video-result" className="hover:text-white transition-colors">
              Analyze
            </Link>
          </div>

          {/* Right - Login Button or User Menu */}
          {isLoggedIn ? (
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center space-x-2 text-white hover:text-gray-300 transition-colors"
              >
                <div className="w-8 h-8 bg-gradient-to-r from-purple-600 to-pink-500 rounded-full flex items-center justify-center text-white font-semibold text-sm">
                  {username.charAt(0).toUpperCase()}
                </div>
              </button>
              
              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-48 bg-gray-800 rounded-lg shadow-lg border border-gray-700 py-2">
                  <div className="px-4 py-2 text-sm text-gray-300 border-b border-gray-700">
                    {username}
                  </div>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 transition-colors"
                  >
                    로그아웃
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Link href="/login">
              <Button
                variant="outline"
                className="bg-transparent text-white border border-gray-600 hover:bg-gray-700/50 hover:border-gray-500 transition-colors duration-200 px-6 py-2 rounded-lg"
              >
                Login
              </Button>
            </Link>
          )}
        </div>

        {/* Main Content */}
        <div className="bg-gray-900/60 backdrop-blur-sm rounded-b-lg p-6 flex gap-6 border-x border-b border-gray-800/50 min-h-[600px]">
          {/* Left Panel */}
          <div className="flex-1 space-y-6">
            <SettingsPanel
              selectedCount={selectedCount}
              selectedType={selectedType}
              onCountSelect={setSelectedCount}
              onTypeSelect={setSelectedType}
            />

            <VideoPlayer
              videos={editedVideos}
              currentVideoIndex={currentVideoIndex}
              selectedType={selectedType}
              isPlaying={isPlaying}
              onNavigate={handleVideoNavigate}
              onVideoSelect={handleVideoSelect}
              onPlayStateChange={setIsPlaying}
            />
          </div>

          {/* Right Panel - Chat Bot */}
          <div className="w-80 flex flex-col">
            <div className="flex-1">
              <ChatBot
                messages={chatMessages}
                onMessageSubmit={handleChatSubmit}
                selectedVideo={selectedVideo}
                onVideoSelect={setSelectedVideo}
                videos={videoOptions} // SettingsPanel에서 가져온 비디오 목록을 여기에 전달해야 함
              />
            </div>
          </div>
        </div>
      </div>

      {/* Processing Modal */}
      {isProcessing && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-lg p-8 max-w-md w-full mx-4">
            <div className="flex justify-center mb-6">
              <div className="relative w-32 h-20 bg-black rounded-lg overflow-hidden border-2 border-gray-600">
                <div className="absolute top-0 left-0 w-full h-full flex transition-transform duration-200">
                  {Array.from({ length: 8 }, (_, i) => (
                    <div key={i} className="w-1/8 h-full flex-shrink-0 border-r border-gray-600">
                      <div className="w-full h-full bg-gradient-to-br from-blue-400 to-purple-600 opacity-80"></div>
                    </div>
                  ))}
                </div>
                <div className="absolute top-1 left-1 right-1 flex justify-between">
                  {Array.from({ length: 6 }, (_, i) => (
                    <div key={i} className="w-1 h-1 bg-gray-400 rounded-full"></div>
                  ))}
                </div>
                <div className="absolute bottom-1 left-1 right-1 flex justify-between">
                  {Array.from({ length: 6 }, (_, i) => (
                    <div key={i} className="w-1 h-1 bg-gray-400 rounded-full"></div>
                  ))}
                </div>
              </div>
            </div>
            <div className="text-center">
              <h3 className="text-lg font-semibold text-white mb-2">영상을 편집 중입니다...</h3>
              <div className="flex justify-center space-x-1 mb-4">
                {Array.from({ length: 3 }, (_, i) => (
                  <div
                    key={i}
                    className={`w-2 h-2 rounded-full ${i === 0 ? "bg-blue-400" : "bg-gray-400"} animate-pulse`}
                  ></div>
                ))}
              </div>
              <p className="text-sm text-gray-400">잠시만 기다려주세요...</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
