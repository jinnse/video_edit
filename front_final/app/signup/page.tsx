"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import Link from "next/link"
import { useState } from "react"

export default function SignUpPage() {
  const [username, setUsername] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [verificationCode, setVerificationCode] = useState("")
  const [isEmailVerified, setIsEmailVerified] = useState(false)
  const [showVerificationField, setShowVerificationField] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [passwordError, setPasswordError] = useState("")
  const [showTooltip, setShowTooltip] = useState("")

  // 비밀번호 유효성 검사
  const validatePassword = (password: string) => {
    if (password.length < 8) {
      return "비밀번호는 최소 8자 이상이어야 합니다"
    }
    if (!/[A-Z]/.test(password)) {
      return "비밀번호는 대문자를 포함해야 합니다"
    }
    if (!/[a-z]/.test(password)) {
      return "비밀번호는 소문자를 포함해야 합니다"
    }
    if (!/\d/.test(password)) {
      return "비밀번호는 숫자를 포함해야 합니다"
    }
    if (!/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) {
      return "비밀번호는 특수문자를 포함해야 합니다"
    }
    return ""
  }

  // 비밀번호 변경 시 유효성 검사
  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPassword = e.target.value
    setPassword(newPassword)
    setPasswordError(validatePassword(newPassword))
  }

  // Check 버튼 활성화 조건
  const canCheck = username.trim() && email.trim() && password.trim() && !passwordError && !isLoading

  // Signup 버튼 활성화 조건 (항상 클릭 가능하지만 이메일 인증 완료 시에만 작동)
  const canSignup = isEmailVerified && !isLoading

  // 필드 비활성화 조건
  const fieldsDisabled = isLoading || showVerificationField || isEmailVerified

  // Verify 버튼 비활성화 조건
  const verifyDisabled = isLoading || !verificationCode || isEmailVerified || !showVerificationField

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!isEmailVerified) {
      setError('이메일 인증이 필요합니다')
      return
    }

    setIsLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await fetch('https://www.videofinding.com:5005/api/v1/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          email: email,
          password: password
        })
      })

      const data = await response.json()

      if (response.ok && data.success) {
        setSuccess('회원가입이 완료되었습니다! 로그인 페이지로 이동합니다.')
        setTimeout(() => {
          window.location.href = '/login'
        }, 2000)
      } else {
        setError(data.error || '회원가입에 실패했습니다.')
      }
    } catch (error) {
      console.error('회원가입 오류:', error)
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSendVerification = async () => {
    if (!canCheck) {
      return
    }

    setIsLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await fetch('https://www.videofinding.com:5005/api/v1/send-verification', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          email: email,
          password: password
        })
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess('회원가입 요청이 완료되었습니다. 이메일을 확인하여 인증을 완료해주세요.')
        setShowVerificationField(true)
      } else {
        setError(data.error || '회원가입 요청에 실패했습니다.')
      }
    } catch (error) {
      console.error('회원가입 요청 오류:', error)
      setError('서버 연결에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleVerifyEmail = async () => {
    if (!username || !verificationCode) {
      setError('사용자명과 인증 코드를 입력해주세요.')
      return
    }

    setIsLoading(true)
    setError("")
    setSuccess("")

    try {
      const response = await fetch('https://www.videofinding.com:5005/api/v1/verify-email', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username: username,
          code: verificationCode
        })
      })

      const data = await response.json()

      if (response.ok) {
        setSuccess('이메일 인증이 완료되었습니다! 이제 회원가입을 완료할 수 있습니다.')
        setIsEmailVerified(true)
        setShowVerificationField(false)
        setVerificationCode("") // 인증 코드 필드 초기화
      } else {
        setError(data.error || '인증 코드 확인에 실패했습니다.')
      }
    } catch (error) {
      console.error('인증 코드 확인 오류:', error)
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
              <h1 className="text-3xl font-bold text-white mb-2">SIGN UP</h1>
            </div>

            <form onSubmit={handleSignUp} className="space-y-6">
              {error && (
                <div className="bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              )}
              
              {success && (
                <div className="bg-green-500/20 border border-green-500/50 text-green-300 px-4 py-3 rounded-lg text-sm">
                  {success}
                </div>
              )}

              <div className="relative">
                <Input
                  type="text"
                  placeholder="USER NAME"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="bg-gray-800/50 border-gray-600 text-white placeholder:text-gray-400 focus:border-orange-500 focus:ring-orange-500/20 h-12 rounded-lg"
                  required
                  disabled={fieldsDisabled}
                  onFocus={() => setShowTooltip("username")}
                  onBlur={() => setShowTooltip("")}
                />
                {showTooltip === "username" && !username && (
                  <div className="absolute -top-2 left-0 transform -translate-y-full bg-gray-800 text-white text-xs px-2 py-1 rounded shadow-lg z-10">
                    사용자명을 입력해주세요
                  </div>
                )}
              </div>

              <div className="relative">
                <Input
                  type="email"
                  placeholder="EMAIL"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-gray-800/50 border-gray-600 text-white placeholder:text-gray-400 focus:border-orange-500 focus:ring-orange-500/20 h-12 rounded-lg pr-20"
                  required
                  disabled={fieldsDisabled}
                  onFocus={() => setShowTooltip("email")}
                  onBlur={() => setShowTooltip("")}
                />
                                 <Button
                   type="button"
                   onClick={handleSendVerification}
                   variant="outline"
                   className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-transparent border-gray-600 text-gray-300 hover:bg-gray-700/50 hover:text-white text-sm px-3 py-1 h-8 rounded disabled:opacity-50"
                   disabled={!canCheck || isEmailVerified}
                 >
                   {isLoading ? 'Sending...' : isEmailVerified ? 'Verified' : 'Check'}
                 </Button>
                {showTooltip === "email" && !email && (
                  <div className="absolute -top-2 left-0 transform -translate-y-full bg-gray-800 text-white text-xs px-2 py-1 rounded shadow-lg z-10">
                    이메일을 입력해주세요
                  </div>
                )}
              </div>

                             {/* 이메일 인증 코드 입력 - 조건부 렌더링 */}
               {showVerificationField && !isEmailVerified && (
                 <div className="relative">
                   <Input
                     type="text"
                     placeholder="Verification Code (6 digits)"
                     value={verificationCode}
                     onChange={(e) => setVerificationCode(e.target.value)}
                     className="bg-gray-800/50 border-gray-600 text-white placeholder:text-gray-400 focus:border-orange-500 focus:ring-orange-500/20 h-12 rounded-lg pr-20"
                     maxLength={6}
                     disabled={isLoading}
                   />
                   <Button
                     type="button"
                     onClick={handleVerifyEmail}
                     variant="outline"
                     className="absolute right-2 top-1/2 transform -translate-y-1/2 bg-transparent border-gray-600 text-gray-300 hover:bg-gray-700/50 hover:text-white text-sm px-3 py-1 h-8 rounded disabled:opacity-50"
                     disabled={isLoading || !verificationCode}
                   >
                     {isLoading ? 'Verifying...' : 'Verify'}
                   </Button>
                 </div>
               )}

              <div className="relative">
                <Input
                  type="password"
                  placeholder="PASSWORD"
                  value={password}
                  onChange={handlePasswordChange}
                  className={`bg-gray-800/50 border-gray-600 text-white placeholder:text-gray-400 focus:border-orange-500 focus:ring-orange-500/20 h-12 rounded-lg ${
                    passwordError ? 'border-red-500' : ''
                  }`}
                  required
                  disabled={fieldsDisabled}
                  onFocus={() => setShowTooltip("password")}
                  onBlur={() => setShowTooltip("")}
                />
                {passwordError && (
                  <div className="text-red-400 text-xs mt-1">
                    {passwordError}
                  </div>
                )}
                {showTooltip === "password" && !password && (
                  <div className="absolute -top-2 left-0 transform -translate-y-full bg-gray-800 text-white text-xs px-2 py-1 rounded shadow-lg z-10">
                    비밀번호를 입력해주세요 (대문자, 소문자, 숫자, 특수문자 포함)
                  </div>
                )}
              </div>

              <div className="relative">
                <Button
                  type="submit"
                  className="w-full bg-white hover:bg-gray-100 text-gray-900 font-semibold h-12 rounded-lg transition-colors"
                  onMouseEnter={() => !canSignup && setShowTooltip("signup")}
                  onMouseLeave={() => setShowTooltip("")}
                >
                  sign up
                </Button>
                {showTooltip === "signup" && !canSignup && (
                  <div className="absolute -top-2 left-1/2 transform -translate-x-1/2 -translate-y-full bg-gray-800 text-white text-xs px-2 py-1 rounded shadow-lg z-10">
                    이메일 인증이 필요합니다
                  </div>
                )}
              </div>
            </form>

            <div className="text-center mt-6">
              <Link href="/login" className="text-gray-400 hover:text-white text-sm transition-colors">
                Go back login page
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
