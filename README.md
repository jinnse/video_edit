# ClipHaus
영상을 sd 화질로 추출하여 챗봇을 이용한 영상 클립 추출

## 프로젝트 개요
이 서비스는 업로드된 영상을 분석하여 쇼츠 제작, 영상 요약, 객체 탐지, 대사 탐지 기능을 제공하는 서비스입니다.
## 프로젝트 목적
- 쇼츠가 점점 늘어나는 상황에 제작시 많은 시간과 인력이 소모된다 
- 영상을 다 보지 않고도 빠르게 영상에 대한 요약
- 영상을 ai로 분석하고 빠르게 쇼츠 제작
- 필요한 장면, 대사 부분만 추출해 소스로 사용 가능
## 아키텍처
video_edit/cliphaus_architect.png
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

##  디렉토리 구조

##  기대 효과

##  기술스택

### 커밋컨벤션

| 태그이름                       | 내용                                          |
|----------------------------|---------------------------------------------|
| :sparkles: `feature`          | 새로운 기능을 추가할 경우                              |
| :bug:`fix `                | 버그를 고친 경우                                   |
| :bug:`!hotfix`             | 급하게 치명적인 버그를 고쳐야하는 경우                       |
| `style`                    | 코드 포맷 변경, 세미 콜론 누락, 코드 수정이 없는 경우            |
| :recycle:`refactor`        | 코드 리팩토링                                     |
| :memo:`comment`            | 필요한 주석 추가 및 변경                              |
| :memo:`docs`	              | 문서, Swagger 를 수정한 경우                        |
| :hammer:`test`             | 테스트 추가, 테스트 리팩토링(프로덕션 코드 변경 X)              |
| `chore`	                   | 빌드 태스트 업데이트, 패키지 매니저를 설정하는 경우(프로덕션 코드 변경 X) |
| `rename`                   | 파일 혹은 폴더명을 수정하거나 옮기는 작업만인 경우                |
| `remove`                   | 파일을 삭제하는 작업만 수행한 경우                         |
| :construction_worker: `ci` | 배포 방식 수정 및 새로 추가                            |
| :green_heart: `ci`         | 기존 배포 스크립트 수정                               |


# LetsGit
Git 초보를 위한 연습장

### 𝟭. 'LetsGit' Clone
```
git clone <깃허브 주소>
```
- 미션을 하기 위해서 제가 올려놓은 프로젝트를 clone 해주세요 !!

### 𝟮. ISSUE 생성
- LetsGit의 Issues를 들어가주세요.

- New issue > ✨ [FEATURE] Get Started 에 들어가서 이슈 생성을 해보세요. 미리 템플릿을 만들어두었으니 작성해보세요.

### 𝟯. branch 만들기
```
1. git pull origin main -> 다른 사람이 업데이트해놨다면 먼저 pull 해주세요!
2. git branch -> 브랜치 확인
3. git branch feature/#1 -> 브랜치 이름은 자신이 생성한 이슈 번호로 // 꼭 main 에서 브랜치 생성하기기
4. git branch -> 잘 생성됐는지 확인
5. git checkout feature/#1 -> 자신의 브랜치로 이동하기
6. git branch -> 내가 어디에 있는지 확인 또 확인... 
```

### 5. 깃허브에 업로드 해보기
```
1. git add .
2. git commit -m "커밋메시지" 
3. git push origin "자신의 branch 이름"
```

### 6. PR 생성
- push를 하면 위에 pr 생성을 하도록 문구가 뜹니다.

- 미리 만들어둔 PR 템플릿에 작성해주세요. (resolve 옆에는 자신의 이슈 번호)

### 7. Merge 하기
- PR까지 완료했다면 합쳐봅시다 !!! 
- 'Squash and merge' 이용용
