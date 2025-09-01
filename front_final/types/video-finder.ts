export interface Video {
  id: number
  title: string
  url: string
  duration?: string
  thumbnailUrl?: string
}

export interface ChatMessage {
  id: number
  text: string
  isBot: boolean
}

export interface VideoType {
  name: string
  icon: string
} 