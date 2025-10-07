# ClipHaus
AI 기반 영상 분석 및 자동 쇼츠 제작 플랫폼

---

## 프로젝트 개요
최근 쇼츠(Shorts)나 릴스(Reels) 등 짧은 영상 콘텐츠가 폭발적으로 인기를 얻고 있습니다.
하지만 하나의 영상을 제작하기 위해서는 긴 원본 영상을 여러 명의 담당자가 시청하고,
적절한 장면을 선택해 편집하는 과정이 필요합니다.

이 과정은 시간과 인력, 비용이 많이 소모되는 문제가 있습니다.
이에 따라 본 프로젝트는 AI 기술을 활용하여 영상 분석 및 자동 쇼츠 제작을 수행하는 서비스를 개발하는 것을 목표로 합니다.

---

## 프로젝트 목적
 - 시간과 인력, 비용 절감
 - 긴 영상을 AI가 자동으로 분석하여 핵심 장면과 대사를 인식하고, 필요한 구간만 추출해 자동으로 쇼츠를 제작
 - 영상의 요약 텍스트를 자동 생성하여 빠르게 내용을 파악할 수 있도록 지원
 - 사용자가 특정 장면이나 대사를 자연어로 검색하면 해당 장면을 자동으로 찾아 소스 영상으로 사용

---

## 아키텍처
<img width="744" height="496" alt="cliphaus_architect" src="https://github.com/user-attachments/assets/84e105aa-3aa5-4bff-8145-00aa46af7ff7" />

---

## 주요 기능 요약
- 🎬 AI 장면 탐지	Twelvelabs Pegasus 모델을 활용해 영상 내 장면을 인식 및 분류
- 🗣️ 대사 인식	Amazon Transcribe로 음성을 텍스트로 변환하고, 해당 대사 구간을 매핑
- 🧠 요약 생성	변환된 자막(JSON)을 기반으로 영상의 핵심 내용을 요약
- ✂️ 쇼츠 제작	장면 및 대사 정보를 바탕으로 자동 편집된 쇼츠 영상 생성

---

## 서비스 처리 흐름 (Processing Flow)
1️⃣ 사용자가 영상을 업로드하면 → S3 버킷에 저장됩니다.  
2️⃣ 업로드 이벤트를 감지한 Stepfunction이 실행 -> s3 에 저장  
   - MediaConvert로 영상 변환 및 저장  
   - Transcribe가 음성을 텍스트로 변환해 json 파일로 저장 (timestamp, 요약 내용)

3️⃣ 프론트엔드에서 사용자가 영상을 선택 후 자연어로 입력   
4️⃣ 각 기능에 맞게 Bedrock Flow에서 분배
  - 장면 탐지 : Twelvelabs Pegasus를 이용하여 해당 장면 탐지
  - 대사 탐지 : Transcribe로 변환된 json을 이용하여 해당 대사 탐지
  - 요약 : Transcribe로 변환된 json을 이용하여 영상 요약
  - 쇼츠 생성 : Pegasus와 Transcribe를 이용하여 쇼츠 제작

5️⃣ 각 기능의 결과 값을 json으로 받아 영상 편집 에이전트를 통해 영상 추출
  - 텍스트 or 영상 장면을 확인하여 timestamp 시간대와 일치하는 영상을 편집하여 영상으로 추출

6️⃣ 최종 결과가 프론트엔드에서 표시됩니다.

---

##  기대 효과
- 영상 제작에 필요한 시간, 인력, 비용 절감
- 최소 인원으로 빠른 쇼츠 제작 및 업로드 가능
- 스포츠, 방송사, 기업 등에서 빠른 콘텐츠 제작

---

##  기술스택
- Bedrock Agent
- Bedrock Flow
- Lambda
- Stepfucnction
- Twelvelabs Pegasus
- Transcribe
- MediaConvert
- S3
- EventBridge
- Python
