"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { ChevronRight, ChevronDown } from "lucide-react"

interface SettingsPanelProps {
  selectedCount: string | null
  selectedType: string
  onCountSelect: (count: string) => void
  onTypeSelect: (type: string) => void
}

export function SettingsPanel({
  selectedCount,
  selectedType,
  onCountSelect,
  onTypeSelect,
}: SettingsPanelProps) {
  // Video Input 관련 상태 제거
} 
