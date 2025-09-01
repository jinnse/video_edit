"use client"

import type React from "react"
import { Button } from "@/components/ui/button"
import Image from "next/image"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { useRef, useState, useEffect } from "react"

export default function MainPage() {
  const router = useRouter()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [username, setUsername] = useState("")
  const [showUserMenu, setShowUserMenu] = useState(false)

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
      }
    }
  }, [])

  // 로그아웃 함수
  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setIsLoggedIn(false)
    setUsername("")
    setShowUserMenu(false)
    router.push('/')
  }

  const handleButtonClick = () => {
    if (isLoggedIn) {
      router.push("/storage")
    } else {
      router.push("/login")
    }
  }

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    try {
      console.log("파일 선택 이벤트 시작")

      const files = event.target.files
      if (!files || files.length === 0) {
        console.log("파일이 선택되지 않음")
        return
      }

      const selectedFile = files[0]
      console.log("선택된 비디오 파일:", selectedFile.name)
      console.log("파일 타입:", selectedFile.type)
      console.log("파일 크기:", selectedFile.size)

      // 백엔드에서 S3 presigned URL 요청
      console.log("Presigned URL 요청 시작")
      const res = await fetch("https://www.videofinding.com:5001/api/v1/s3_input", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          filename: selectedFile.name,
          contentType: "video/mp4",
        }),
      })

      console.log("Presigned URL 응답:", res.status)

      if (!res.ok) {
        const errorText = await res.text()
        console.error("Presigned URL 요청 실패:", errorText)
        alert("Presigned URL 요청 실패!")
        return
      }

      const responseData = await res.json()
      console.log("Presigned URL 응답 데이터:", responseData)

      const { uploadUrl } = responseData
      console.log("Presigned URL:", uploadUrl)

      // presigned URL로 S3 업로드
      console.log("S3 업로드 시작")
      const uploadRes = await fetch(uploadUrl, {
        method: "PUT",
        body: selectedFile,
        headers: {
          "Content-Type": selectedFile.type || "video/mp4",
        },
      })

      console.log("S3 업로드 응답:", uploadRes.status)

      if (uploadRes.ok) {
        console.log("비디오 업로드 성공!")
        alert("비디오 업로드 완료!")
      } else {
        const errorText = await uploadRes.text()
        console.error("S3 업로드 실패:", errorText)
        alert("업로드 실패!")
      }
    } catch (error) {
      console.error("파일 업로드 중 오류 발생:", error)
      if (error instanceof Error) {
        console.error("오류 스택:", error.stack)
        console.error("오류 메시지:", error.message)
      }
      console.error("오류 타입:", typeof error)
      console.error("오류 객체:", JSON.stringify(error, null, 2))
      alert("파일 업로드 중 오류가 발생했습니다!")
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 relative">
      {/* 상단 왼쪽 모서리 주황색 그라데이션 오버레이 */}
      <div className="absolute inset-0 bg-gradient-to-br from-customOrangeBrown/15 to-transparent pointer-events-none z-0"></div>
      {/* 기존 보라색/파란색 그라데이션 오버레이 */}
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-blue-900/20 pointer-events-none z-0"></div>

      {/* Navigation */}
      <nav className="sticky top-0 z-50 flex items-center justify-between px-6 py-4 border-b border-gray-700 bg-gray-900/80 backdrop-blur-md">
        {/* Left - Logo */}
        <div className="flex flex-col items-start">
          <Link href="/" className="text-white font-semibold text-lg hover:text-gray-300 transition-colors">
            Clip Haus
          </Link>
        </div>

        {/* Center - Navigation Menu */}
        <div className="flex items-center space-x-12 text-sm text-gray-300">
          <button
            onClick={() => isLoggedIn ? router.push("/storage") : router.push("/login")}
            className="hover:text-white transition-colors cursor-pointer"
          >
            Storage
          </button>
          <button
            onClick={() => isLoggedIn ? router.push("/video-result") : router.push("/login")}
            className="hover:text-white transition-colors cursor-pointer"
          >
            Analyze
          </button>
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

      {/* Hero Section */}
      <section className="relative px-6 py-16 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="mb-16 relative">
            <Image
              src="/images/hero-sunset.png"
              alt="Dramatic sunset over city skyline"
              width={700}
              height={400}
              className="rounded-2xl mx-auto object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-gray-900/30 to-transparent rounded-2xl"></div>
          </div>

          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Clip Haus
            <br />
            Search Quickly
          </h1>

          <p className="text-gray-300 text-lg mb-12 max-w-md mx-auto leading-relaxed">
            You can insert a video,
            <br />
            analyze it,
            <br />
            and then search it quickly.
          </p>

          {/* 숨겨진 파일 입력 요소 */}
          <input type="file" ref={fileInputRef} onChange={handleFileChange} accept="video/*" className="hidden" />

          <Button
            onClick={handleButtonClick}
            className="bg-gradient-to-r from-purple-600 to-pink-500 hover:from-purple-700 hover:to-pink-600 text-white px-8 py-3 rounded-full text-lg"
          >
            Input Video
          </Button>
        </div>
      </section>

      {/* Features Section */}
      <section className="relative px-6 py-16">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold text-white mb-12">
            It is possible to provide
            <br />
            like this
          </h2>

          <div className="flex justify-center items-center space-x-24 mb-16">
            <Image
              src="/images/icon-document-pencil.png"
              alt="Document and pencil icon"
              width={80}
              height={80}
              className="rounded-full object-cover"
            />
            <Image
              src="/images/icon-youtube-shorts.png"
              alt="YouTube Shorts icon"
              width={80}
              height={80}
              className="object-contain"
            />
            <Image
              src="/images/icon-video-scissors.png"
              alt="Video and scissors icon"
              width={80}
              height={80}
              className="rounded-full object-cover"
            />
          </div>
        </div>
      </section>

      {/* Content Sections */}
      <section className="relative px-6 py-8">
        <div className="max-w-6xl mx-auto space-y-16">
          {/* First Content Block */}
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <h3 className="text-2xl font-bold mb-4 text-white">
                Create highlights
                <br />
                quickly
              </h3>
              <p className="text-gray-400">Easily create highlights in your videos</p>
            </div>
            <div>
              <Image
                src="/images/traffic-light-sunset.png"
                alt="Traffic light and buildings at sunset"
                width={400}
                height={250}
                className="rounded-2xl object-cover w-full"
              />
            </div>
          </div>

          {/* Second Content Block */}
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div className="order-2 md:order-2">
              <h3 className="text-2xl font-bold mb-4 text-white">
                Create the perfect
                <br />
                shorts
              </h3>
              <p className="text-gray-400">You can make shorts at a fast pace</p>
            </div>
            <div className="order-1 md:order-1">
              <Image
                src="/images/blue-sky.png"
                alt="Beautiful blue sky with wispy clouds"
                width={400}
                height={250}
                className="rounded-2xl object-cover w-full"
              />
            </div>
          </div>

          {/* Third Content Block */}
          <div className="grid md:grid-cols-2 gap-8 items-center">
            <div>
              <h3 className="text-2xl font-bold mb-4 text-white">
                Summary of the
                <br />
                video
              </h3>
              <p className="text-gray-400">You can check the video content by summarizing it in text.</p>
            </div>
            <div>
              <Image
                src="/images/video-title4.png"
                alt="Skyscrapers and clouds"
                width={400}
                height={250}
                className="rounded-2xl object-cover w-full"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Footer Spacing */}
      <div className="h-16"></div>
    </div>
  )
}
