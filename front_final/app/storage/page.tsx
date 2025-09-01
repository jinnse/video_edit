"use client"
import { Button } from "@/components/ui/button"
import type React from "react"

import { Input } from "@/components/ui/input"
import Image from "next/image"
import Link from "next/link"
import { Search, Upload, X, Play, Trash2 } from "lucide-react"
import { useState, useCallback, useRef, useEffect } from "react"

interface VideoFile {
  id: string
  filename: string
  path: string
  thumbnail: string
  type: "original" | "cut" | "all"
  size?: string
  uploadDate?: string
}

export default function StoragePage() {
  const [isDragOver, setIsDragOver] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [activeTab, setActiveTab] = useState<"original" | "cut" | "all">("all")
  const [videos, setVideos] = useState<VideoFile[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState("")
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [username, setUsername] = useState("")
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [videoToDelete, setVideoToDelete] = useState<VideoFile | null>(null)
  const [showSuccessModal, setShowSuccessModal] = useState(false)
  const [successMessage, setSuccessMessage] = useState("")
  const [showVideoModal, setShowVideoModal] = useState(false)
  const [currentVideoUrl, setCurrentVideoUrl] = useState("")
  const [showUploadSuccessModal, setShowUploadSuccessModal] = useState(false)
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState("")

  // 로그인 상태 확인
  useEffect(() => {
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
  }, [])

  // 로그아웃 함수
  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setIsLoggedIn(false)
    setUsername("")
    setShowUserMenu(false)
    window.location.href = '/'
  }

  // 삭제 확인 모달 열기
  const openDeleteModal = (video: VideoFile) => {
    setVideoToDelete(video)
    setShowDeleteModal(true)
  }

  // 삭제 확인 모달 닫기
  const closeDeleteModal = () => {
    setShowDeleteModal(false)
    setVideoToDelete(null)
  }

  // 성공 모달 닫기
  const closeSuccessModal = () => {
    setShowSuccessModal(false)
    setSuccessMessage("")
  }

  // 업로드 성공 모달 닫기
  const closeUploadSuccessModal = () => {
    setShowUploadSuccessModal(false)
    setUploadSuccessMessage("")
  }

  // S3에 비디오 업로드 함수
  const uploadVideoToS3 = async (file: File) => {
    try {
      console.log("📤 S3 업로드 시작:", file.name)

      // 1. Presigned URL 요청
      const presignedResponse = await fetch("/api/storage/s3_input", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename: `original/${file.name}`,
          contentType: file.type,
        }),
      })

      if (!presignedResponse.ok) {
        throw new Error(`Presigned URL 요청 실패: ${presignedResponse.status}`)
      }

      const { uploadUrl } = await presignedResponse.json()
      console.log("✅ Presigned URL 생성됨:", uploadUrl)

      // 2. 파일을 S3에 직접 업로드
      const uploadResponse = await fetch(uploadUrl, {
        method: "PUT",
        headers: {
          "Content-Type": file.type,
        },
        body: file,
      })

      if (!uploadResponse.ok) {
        throw new Error(`S3 업로드 실패: ${uploadResponse.status}`)
      }

      console.log("✅ S3 업로드 완료:", file.name)
      setUploadSuccessMessage(`${file.name} 업로드가 완료되었습니다!`)
      setShowUploadSuccessModal(true)
    } catch (error) {
      console.error("❌ S3 업로드 오류:", error)
      alert(`${file.name} 업로드에 실패했습니다: ${error}`)
      throw error
    }
  }

  // S3 버킷에서 비디오 파일 목록 조회
  const fetchVideosFromS3 = async () => {
    setIsLoading(true)
    try {
      console.log("Fetching videos from S3 bucket: video-input-pipeline-20250724")

      // S3 버킷에서 모든 파일 조회
      const response = await fetch("/api/bucket/bucketdata")
      console.log("API Response status:", response.status)

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`)
      }

      const allFiles = await response.json()
      console.log("All files from S3:", allFiles)

      // 디버깅: 폴더별 파일 분류
      const originalFiles = allFiles.filter((file: string) => file.startsWith("original/"))
      const outputFiles = allFiles.filter((file: string) => file.startsWith("output/"))
      const thumbnailFiles = allFiles.filter((file: string) => file.startsWith("thumbnails/"))

      console.log("📂 original/ files:", originalFiles)
      console.log("📂 output/ files:", outputFiles)
      console.log("📂 thumbnails/ files:", thumbnailFiles)

      const videoExtensions = [".mp4", ".avi", ".mov", ".webm", ".mkv", ".flv", ".wmv"]

      // Original Videos 처리 (original/ 폴더)
      const originalVideos: VideoFile[] = allFiles
        .filter(
          (file: string) =>
            file.startsWith("original/") && videoExtensions.some((ext) => file.toLowerCase().endsWith(ext)),
        )
        .map((file: string) => {
          const filename = file.replace("original/", "")
          const baseName = filename.replace(/\.[^/.]+$/, "") // 확장자 제거
          return {
            id: `original-${file}`,
            filename: filename,
            path: file,
            thumbnail: `https://d3il8axvt9p9ix.cloudfront.net/${baseName}.jpg`,
            type: "original" as const,
          }
        })

      // Cut Videos 처리 (output/ 폴더)
      const cutVideos: VideoFile[] = allFiles
        .filter(
          (file: string) =>
            file.startsWith("output/") && videoExtensions.some((ext) => file.toLowerCase().endsWith(ext)),
        )
        .map((file: string) => {
          const filename = file.replace("output/", "")
          const baseName = filename.replace(/\.[^/.]+$/, "") // 확장자 제거
          return {
            id: `cut-${file}`,
            filename: filename,
            path: file,
            thumbnail: `https://d3il8axvt9p9ix.cloudfront.net/${baseName}.jpg`,
            type: "cut" as const,
          }
        })

      // All Videos (모든 비디오 합치기)
      const allVideos: VideoFile[] = [...originalVideos, ...cutVideos]

      // 중복 제거하여 설정
      const uniqueVideos = [...originalVideos, ...cutVideos]
      setVideos(uniqueVideos)

      console.log("Processed videos:", {
        originalVideos: originalVideos.length,
        cutVideos: cutVideos.length,
        total: uniqueVideos.length,
      })
      console.log("Original videos:", originalVideos)
      console.log("Cut videos:", cutVideos)

      // 썸네일 URL 디버깅
      originalVideos.forEach((video) => {
        console.log(`🖼️ ${video.filename} 썸네일: ${video.thumbnail}`)
      })
      cutVideos.forEach((video) => {
        console.log(`🖼️ ${video.filename} 썸네일: ${video.thumbnail}`)
      })
    } catch (error) {
      console.error("Error fetching videos:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // 컴포넌트 마운트 시 비디오 목록 조회
  useEffect(() => {
    fetchVideosFromS3()
  }, [])

  // 현재 탭에 따른 필터링된 비디오 목록
  const filteredVideos = videos.filter((video) => {
    const matchesTab = activeTab === "all" ? true : video.type === activeTab
    const matchesSearch = searchTerm === "" || video.filename.toLowerCase().includes(searchTerm.toLowerCase())
    return matchesTab && matchesSearch
  })

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (e.currentTarget === e.target) {
      setIsDragOver(false)
    }
  }, [])

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragOver(false)

      const files = Array.from(e.dataTransfer.files)
      const videoFiles = files.filter((file) => file.type.startsWith("video/"))

      if (videoFiles.length === 0) return

      setIsUploading(true)
      setUploadProgress(videoFiles.map((file) => file.name))

      // 실제 S3 업로드 처리
      for (const file of videoFiles) {
        try {
          await uploadVideoToS3(file)
          setUploadProgress((prev) => prev.filter((name) => name !== file.name))
        } catch (error) {
          console.error("업로드 실패:", file.name, error)
          setUploadProgress((prev) => prev.filter((name) => name !== file.name))
        }
      }

      setIsUploading(false)
      // 업로드 완료 후 비디오 목록 새로고침
      fetchVideosFromS3()
    },
    [videos.length],
  )

  const handleFileUpload = useCallback(
    async (files: FileList | null) => {
      if (!files) return

      const videoFiles = Array.from(files).filter((file) => file.type.startsWith("video/"))
      if (videoFiles.length === 0) return

      setIsUploading(true)
      setUploadProgress(videoFiles.map((file) => file.name))

      // 실제 S3 업로드 처리
      for (const file of videoFiles) {
        try {
          await uploadVideoToS3(file)
          setUploadProgress((prev) => prev.filter((name) => name !== file.name))
        } catch (error) {
          console.error("업로드 실패:", file.name, error)
          setUploadProgress((prev) => prev.filter((name) => name !== file.name))
        }
      }

      setIsUploading(false)
      // 업로드 완료 후 비디오 목록 새로고침
      fetchVideosFromS3()
    },
    [videos.length],
  )

  const handleInputVideoClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleFileInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      handleFileUpload(e.target.files)
      // Reset the input value so the same file can be selected again
      e.target.value = ""
    },
    [handleFileUpload],
  )

  // 비디오 재생 함수
  const handlePlayVideo = useCallback((video: VideoFile) => {
    // CloudFront URL 생성
    let videoUrl = ""
    if (video.type === "original") {
      videoUrl = `https://d1o2nq4o6c2uay.cloudfront.net/${video.filename}`
    } else if (video.type === "cut") {
      videoUrl = `https://d1nmrhn4eusal2.cloudfront.net/${video.filename}`
    }

    console.log("🎬 비디오 재생:", video.filename, "URL:", videoUrl)

    // 모달에서 비디오 재생
    setSelectedVideo(video)
    setCurrentVideoUrl(videoUrl)
    setShowVideoModal(true)
    setIsPlaying(true)
  }, [])

  // 비디오 모달 닫기
  const closeVideoModal = () => {
    setShowVideoModal(false)
    setSelectedVideo(null)
    setCurrentVideoUrl("")
    setIsPlaying(false)
  }

  // S3에서 파일 삭제
  const handleDeleteVideo = useCallback(async (video: VideoFile) => {
    try {
      console.log(`🗑️ 파일 삭제 시작: ${video.path}`)

      const response = await fetch("/api/bucket/deletefile", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          file_key: video.path,
        }),
      })

      if (response.ok) {
        const result = await response.json()
        console.log("✅ 파일 삭제 성공:", result)

        // 비디오 목록에서 제거
        setVideos((prev) => prev.filter((v) => v.id !== video.id))

        // 성공 메시지 표시
        setSuccessMessage(`비디오 파일이 성공적으로 삭제되었습니다!`)
        setShowSuccessModal(true)
      } else {
        const error = await response.json()
        console.error("❌ 파일 삭제 실패:", error)

        // 실패한 경우에도 삭제된 파일이 있다면 표시
        if (error.deleted_files && error.deleted_files.length > 0) {
          // 비디오 파일이 삭제되었으므로 목록에서 제거
          setVideos((prev) => prev.filter((v) => v.id !== video.id))

          // 비디오가 삭제되었으므로 목록에서 제거
          setVideos((prev) => prev.filter((v) => v.id !== video.id))
        } else {
          alert(`파일 삭제에 실패했습니다: ${error.error}`)
        }
      }
    } catch (error) {
      console.error("❌ 삭제 요청 오류:", error)
      alert("파일 삭제 중 오류가 발생했습니다.")
    }
  }, [])

  const users = ["All Video", "Cut Video", "Original Video", "Input Video"]

  return (
    <div
      className="min-h-screen bg-gray-950 flex flex-col relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept="video/*"
        multiple
        className="hidden"
        onChange={handleFileInputChange}
      />

      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900/80 backdrop-blur-md">
        {/* Left - Logo */}
        <div className="flex flex-col items-start">
          <Link href="/" className="text-white font-semibold text-lg hover:text-gray-300 transition-colors">
            Clip Haus
          </Link>
        </div>

        {/* Center - Navigation Menu */}
        <div className="flex items-center space-x-12 text-sm text-gray-300">
          <Link href="/storage" className="text-white transition-colors">
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
            <Button variant="outline" className="border-gray-600 text-white hover:bg-gray-700 bg-transparent">
              Login
            </Button>
          </Link>
        )}
      </nav>

      <div className="flex flex-1">
        {/* Left Sidebar */}
        <div className="w-80 bg-gray-900 border-r border-gray-700 flex flex-col">
          {/* Search Bar */}
          <div className="p-6 border-b border-gray-700">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <Input
                placeholder="Search videos..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10 bg-gray-800 border-gray-600 text-white placeholder-gray-400 focus:border-gray-500"
              />
            </div>
          </div>

          {/* Video Categories */}
          <div className="flex-1 p-6">
            <h2 className="text-white font-semibold text-lg mb-6">Video Categories</h2>
            <div className="space-y-2">
              <button
                onClick={() => setActiveTab("all")}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                  activeTab === "all"
                    ? "bg-purple-600/20 text-purple-300 border border-purple-500/30"
                    : "text-gray-300 hover:text-white hover:bg-gray-800"
                }`}
              >
                All Videos
              </button>
              <button
                onClick={() => setActiveTab("original")}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                  activeTab === "original"
                    ? "bg-purple-600/20 text-purple-300 border border-purple-500/30"
                    : "text-gray-300 hover:text-white hover:bg-gray-800"
                }`}
              >
                Original Videos
              </button>
              <button
                onClick={() => setActiveTab("cut")}
                className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                  activeTab === "cut"
                    ? "bg-purple-600/20 text-purple-300 border border-purple-500/30"
                    : "text-gray-300 hover:text-white hover:bg-gray-800"
                }`}
              >
                Cut Videos
              </button>
            </div>

            <div className="mt-8">
              <button
                onClick={handleInputVideoClick}
                className="w-full bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 text-white px-4 py-2 rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Upload Video
              </button>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-gray-700">
            <h1 className="text-2xl font-bold text-white">
              {activeTab === "original" ? "Original Videos" : activeTab === "cut" ? "Cut Videos" : "All Videos"}
            </h1>
            <p className="text-gray-400 mt-1">{filteredVideos.length} videos found</p>
          </div>

          {/* Video Grid */}
          <div className="flex-1 p-6">
            {isLoading ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-gray-400">Loading videos...</div>
              </div>
            ) : filteredVideos.length === 0 ? (
              <div className="flex items-center justify-center h-64">
                <div className="text-center">
                  <div className="text-gray-400 text-lg mb-2">No videos found</div>
                  <div className="text-gray-500 text-sm">
                    {searchTerm ? "Try adjusting your search terms" : "Upload your first video to get started"}
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
                {filteredVideos.map((video) => (
                  <div key={video.id} className="group cursor-pointer">
                    <div className="relative bg-gray-800 rounded-lg overflow-hidden mb-3 aspect-video">
                      <Image
                        src={video.thumbnail || "/placeholder.svg"}
                        alt={video.filename}
                        fill
                        className="object-cover group-hover:scale-105 transition-transform duration-200"
                      />
                      {/* Overlay with actions */}
                      <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-2">
                        <button
                          className="p-2 bg-white/20 rounded-full hover:bg-white/30 transition-colors"
                          onClick={(e) => {
                            e.stopPropagation()
                            handlePlayVideo(video)
                          }}
                        >
                          <Play className="w-4 h-4 text-white" />
                        </button>
                        <button
                          className="p-2 bg-white/20 rounded-full hover:bg-white/30 transition-colors"
                          onClick={(e) => {
                            e.stopPropagation()
                            openDeleteModal(video)
                          }}
                        >
                          <Trash2 className="w-4 h-4 text-white" />
                        </button>
                      </div>
                      {/* Type badge */}
                      <div className="absolute top-2 left-2">
                        <span
                          className={`px-2 py-1 text-xs rounded-full ${
                            video.type === "original"
                              ? "bg-blue-500/80 text-white"
                              : video.type === "cut"
                                ? "bg-green-500/80 text-white"
                                : "bg-gray-500/80 text-white"
                          }`}
                        >
                          {video.type}
                        </span>
                      </div>
                    </div>
                    <p className="text-gray-300 text-sm truncate group-hover:text-white transition-colors">
                      {video.filename}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {isDragOver && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg p-12 border-4 border-dashed border-blue-500 text-center">
            <Upload className="w-16 h-16 text-blue-500 mx-auto mb-4" />
            <p className="text-xl font-semibold text-gray-800 mb-2">파일을 여기에 놓으세요</p>
            <p className="text-gray-600">비디오 파일을 업로드할 수 있습니다</p>
          </div>
        </div>
      )}

      {(isUploading || uploadProgress.length > 0) && (
        <div className="fixed top-4 right-4 z-40 bg-blue-500 text-white p-4 rounded-lg shadow-lg max-w-sm">
          <div className="flex items-center justify-between mb-2">
            <p className="font-semibold">업로드 중...</p>
            <button
              onClick={() => {
                setIsUploading(false)
                setUploadProgress([])
              }}
              className="text-white hover:text-gray-200"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-sm">잠시 사용하는 동안을 설정해 보세요.</p>
          {uploadProgress.length > 0 && (
            <div className="mt-2 space-y-1">
              {uploadProgress.map((filename, index) => (
                <div key={index} className="text-xs bg-blue-600 rounded px-2 py-1">
                  {filename}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 삭제 확인 모달 */}
      {showDeleteModal && videoToDelete && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-gray-900/95 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-gray-700/50 max-w-md w-full mx-4">
            <div className="text-center">
              {/* 아이콘 */}
              <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Trash2 className="w-8 h-8 text-red-400" />
              </div>
              
              {/* 제목 */}
              <h3 className="text-xl font-bold text-white mb-4">파일 삭제</h3>
              
              {/* 메시지 */}
              <p className="text-gray-300 mb-6">
                <span className="font-semibold text-white">{videoToDelete.filename}</span>을(를) 정말로 삭제하시겠습니까?
              </p>
              <p className="text-sm text-gray-400 mb-8">
                이 작업은 되돌릴 수 없습니다.
              </p>
              
              {/* 버튼들 */}
              <div className="flex gap-3">
                <Button
                  onClick={closeDeleteModal}
                  variant="outline"
                  className="flex-1 bg-transparent border-gray-600 text-gray-300 hover:bg-gray-700 hover:text-white"
                >
                  취소
                </Button>
                <Button
                  onClick={() => {
                    handleDeleteVideo(videoToDelete)
                    closeDeleteModal()
                  }}
                  className="flex-1 bg-red-600 hover:bg-red-700 text-white"
                >
                  삭제
                </Button>
              </div>
            </div>
          </div>
                 </div>
       )}

               {/* 성공 모달 */}
        {showSuccessModal && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
            <div className="bg-gray-900/95 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-gray-700/50 max-w-md w-full mx-4">
              <div className="text-center">
                {/* 아이콘 */}
                <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                  <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                
                {/* 제목 */}
                <h3 className="text-xl font-bold text-white mb-4">삭제 완료</h3>
                
                {/* 메시지 */}
                <p className="text-gray-300 mb-8 whitespace-pre-line">
                  {successMessage}
                </p>
                
                {/* 버튼 */}
                <Button
                  onClick={closeSuccessModal}
                  className="w-full bg-green-600 hover:bg-green-700 text-white"
                >
                  확인
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* 업로드 성공 모달 */}
        {showUploadSuccessModal && (
          <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
            <div className="bg-gray-900/95 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-gray-700/50 max-w-md w-full mx-4">
              <div className="text-center">
                {/* 아이콘 */}
                <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                  <Upload className="w-8 h-8 text-blue-400" />
                </div>
                
                {/* 제목 */}
                <h3 className="text-xl font-bold text-white mb-4">업로드 완료</h3>
                
                {/* 메시지 */}
                <p className="text-gray-300 mb-8">
                  {uploadSuccessMessage}
                </p>
                
                {/* 버튼 */}
                <Button
                  onClick={closeUploadSuccessModal}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                >
                  확인
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* 비디오 플레이어 모달 */}
        {showVideoModal && selectedVideo && (
          <div className="fixed inset-0 bg-black/90 z-50 flex items-center justify-center">
            <div className="relative w-full h-full max-w-6xl max-h-[90vh] bg-black rounded-lg overflow-hidden">
              {/* 닫기 버튼 */}
              <button
                onClick={closeVideoModal}
                className="absolute top-4 right-4 z-10 w-8 h-8 bg-black/50 hover:bg-black/70 text-white rounded-full flex items-center justify-center transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
              
              {/* 비디오 플레이어 */}
              <video
                src={currentVideoUrl}
                controls
                autoPlay
                className="w-full h-full object-contain"
                onEnded={closeVideoModal}
              >
                Your browser does not support the video tag.
              </video>
              
              {/* 비디오 제목 */}
              <div className="absolute bottom-4 left-4 right-4 bg-black/50 text-white p-3 rounded-lg">
                <h3 className="text-lg font-semibold">{selectedVideo.filename}</h3>
                <p className="text-sm text-gray-300">{selectedVideo.type} video</p>
              </div>
            </div>
          </div>
        )}
     </div>
   )
 }
