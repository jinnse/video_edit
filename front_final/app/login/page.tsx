"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"

export default function LoginPage() {
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError("")

    try {
      const response = await fetch('/api/auth/signin', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          password: password
        })
      })

      const data = await response.json()

      if (response.ok) {
        // 로그인 성공
        localStorage.setItem('token', data.token)
        localStorage.setItem('user', JSON.stringify(data.user))
        console.log('로그인 성공:', data)
        
        // 메인 페이지로 리다이렉트
        router.push('/')
      } else {
        // 로그인 실패
        setError(data.error || '로그인에 실패했습니다.')
        console.error('로그인 실패:', data)
      }
    } catch (error) {
      console.error('로그인 오류:', error)
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0 bg-gray-950"></div>
      <div className="absolute inset-0 bg-gradient-to-br from-customOrangeBrown/15 to-transparent pointer-events-none z-0"></div>
      <div className="absolute inset-0 bg-gradient-to-br from-purple-900/20 via-transparent to-blue-900/20 pointer-events-none z-0"></div>

      <div className="relative z-10 flex items-center justify-center min-h-screen px-4">
        <div className="absolute top-8 left-8">
          <Link href="/" className="text-white text-xl font-bold hover:text-gray-300 transition-colors">
            Clip Haus
          </Link>
        </div>

        <div className="w-full max-w-md">
          <div className="bg-gray-900/80 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-gray-700/50">
            <div className="text-center mb-8">
              <h1 className="text-3xl font-bold text-white mb-2">SIGN IN</h1>
            </div>

            <form onSubmit={handleLogin} className="space-y-6">
              {error && (
                <div className="bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}
              
              <div>
                <Input
                  type="text"
                  placeholder="ID"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="bg-gray-800/50 border-gray-600 text-white placeholder:text-gray-400 focus:border-orange-500 focus:ring-orange-500/20 h-12 rounded-lg"
                  required
                  disabled={isLoading}
                />
              </div>

              <div>
                <Input
                  type="password"
                  placeholder="PASSWORD"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-gray-800/50 border-gray-600 text-white placeholder:text-gray-400 focus:border-orange-500 focus:ring-orange-500/20 h-12 rounded-lg"
                  required
                  disabled={isLoading}
                />
              </div>

              <Button
                type="submit"
                className="w-full bg-white hover:bg-gray-100 text-gray-900 font-semibold h-12 rounded-lg transition-colors disabled:opacity-50"
                disabled={isLoading}
              >
                {isLoading ? '로그인 중...' : 'LOG IN'}
              </Button>
            </form>

            <div className="text-center mt-6">
              <Link href="/signup" className="text-gray-400 hover:text-white text-sm transition-colors">
                sign up
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
