# FilmCraft 스킬 구현 계획

> 계획 모드가 지정한 경로라서, 승인 직후 첫 동작으로 이 파일을 `.claude/plans/filmcraft-skill.md`로 옮긴다(구현 단계 0).

## Context

- 이 맥에는 FilmCraft(어도비 프리미어 프로 클론, Rust, 0.7.2)가 설치돼 있고 700개 명령을 CLI·MCP·제어 채널로 노출한다. Claude는 FilmCraft를 모른다.
- 목표: 프로젝트 스킬 `.claude/skills/filmcraft`. 성진님이 "이 영상으로 ○○ 만들어줘"라고 하면, Claude가 FilmCraft CLI/MCP로 숙련 편집자 수준의 결과(다시 열리는 `.fcproj` + 검수를 통과한 결과물)를 내게 한다. 페르소나 없이 활용 역량 전반을 다루고, skill-maker 프레임을 철저히 따른다.

**대조 실험이 바꾼 전제.** 스킬 없는 Opus 5.5를 6과제(합성 4, 실촬영본 2)로 시험했다.

- 할 줄 아는 것: `--help`·`describe`·`commands | grep`만으로 CLI를 꽤 잘 다룬다(`--save`, `run` 스크립트, 사후 측정 포함).
- 부족한 것:
  1. 이 빌드에 없는 기능을 쫓는 헛걸음(바이너리 `strings`로 970MB 모델을 받았다 삭제)
  2. 매번 손으로 다시 짠 전사·자막 레이아웃·타임라인 요약·프레임 시트·검수
  3. FilmCraft 고유 함정을 시행착오로 발견(`keepSeconds` 양쪽 적용, `createCaptions`가 문장 중간에서 끊음, 세로 화면의 캡션 크기 배율, 저장 대화상자의 브리지 차단)
  4. 편집 표준 공백(세로 세이프존, 라우드니스 미정규화, 컷어웨이에 디졸브)
  5. 작업 폴더 밖 쓰기

그래서 스킬은 명령을 가르치지 않는다. 담는 것은 위의 차이와 그 이유, 그리고 FilmCraft에 없는 다섯 가지 도구다. 명령 사양은 `describe`가 소유한다(skill-maker "Interface over document").

## 결정 요약 (사용자 결정, 이번 세션)

| 항목 | 결정 |
|---|---|
| 범위 | 토킹헤드·롱폼, 세로 숏폼, 하이라이트·몽타주, 마감·납품 전부. 기능은 최대한 다룬다 |
| 파일 분할 | 로드 시점 기준이되 크지 않으면 최대한 합침 → **SKILL.md 하나**(references 없음). 분기 지식은 절 첫 줄의 "언제 쓰나"로 구분 |
| 편집 판단의 근거 | 공개 표준·플랫폼 사양·FilmCraft 코드는 스킬에, 취향은 각 사용자와의 대화에 (아래 '스킬의 성격'으로 갱신) |
| 작업 방식 | 헤드리스(CLI) 기본, 요청 시 브리지(실행 중인 앱) |
| 음성인식 | 외부 mlx-whisper(`mlx-community/whisper-large-v3-turbo`) → `transcript.set` |
| ffmpeg | 분석·검수만. 예외는 최종 MP4의 무손실 `-c copy -movflags +faststart` 하나. Edit List 제거·챕터 리먹스는 하지 않음 |
| 번들 코드 | `transcribe`, `captions`, `qc`, `timeline`, `frames`. 박자 감지는 보류 |
| MCP | 브리지 MCP만 레포 `.mcp.json`에 등록. 헤드리스는 CLI |
| 사실 회귀 테스트 | 둔다. 스킬이 기대는 FilmCraft 동작을 설치된 CLI로 확인 |
| 스킬 언어 | 영어. 승인 받을 때 한국어 요약을 동봉 |
| 개발 기록 | 커밋·PR 본문에만. 대조 실험 수치, 버린 대안, 기준 모델(Opus 5.5 / FilmCraft 0.7.2 / 2026-10-14) |
| codex | 검증은 `gpt-6.1-sol`, effort `high`. Agent로 대체할 때는 `sonnet` |
| 추가 실촬영본 | 구현 세션에서 Claude가 유튜브(`uvx yt-dlp`)와 공개 출처(Pexels·Internet Archive 등)에서 유형별 1~3개 수집. 개인 테스트 전용, 배포·커밋하지 않음(사용자 판단: 사적이용 복제). 아이폰 돌비비전 원본은 사용자가 찍어 주면 추가(선택) |
| 새 유형의 쓰임 | SKILL.md를 쓰기 전에 유형별 스킬 없는 기준선 대조 실험 → 차이를 스킬에 반영 → 같은 파일로 스킬 포함 재실험 |
| `.gitignore` | `.tmp/etc/` 추가(main 직접 chore 커밋) |
| 스킬의 성격 (2026-10-14 성진님 지적) | 혼자 끝까지 만드는 편집자가 아니라 여러 사용자와 의논하며 만드는 동료. 취향 규칙(전환·필러·자막 위치·리듬·룩)은 레일이라 빼고 사용자의 몫으로 둔다. 남기는 것은 사람마다 갈리지 않는 것(FilmCraft 함정, 플랫폼 사양·qc, 화면 글자 정확성, 발언 왜곡 금지, 플랫폼 UI 영역). 사용자를 비전문가로 가정하지 않는다. 단계 14a(취향 원칙 경계 확인)는 폐기 |
| 협업 리듬 (같은 날) | 바꾸기 쉬운 것은 Claude가 자기 감각으로 먼저 해 보이고 이유를 말한다. 되돌리기 비싸거나 결과의 성격을 정하는 것(구간 선택, 전체 룩, 긴 내보내기, 모델 다운로드)은 후보와 근거를 보여 주고 먼저 묻는다 |
| 번역 자막 (1c 이후) | `captions`에 `--cues X.srt` 입력 모드 추가: 모델이 쓴 번역 큐를 같은 규칙으로 줄바꿈·분할·줄 끝 문장부호 제거 (2026-10-14 성진님 결정) |

## 대조 실험의 차이 → 스킬 안의 자리

skill-maker 완료 조건 "모든 차이는 자리가 있거나 뺀 이유가 기록된다"를 이 표로 지킨다.

| 관찰된 차이 (과제) | 자리 |
|---|---|
| 릴리스 빌드에 STT 없음 → 모델 다운로드 헛걸음 (T1) | SKILL.md §8 첫 줄 + `cli.py transcribe` |
| Whisper 단어 시간이 0.3~0.4초 어긋남 → 음량으로 보정 (T1) | `transcribe`가 발화 구간에 스냅(결정적 로직) |
| `keepSeconds`가 양쪽에 적용, 필러 먼저 제거하면 공백이 겹침 (T1) | SKILL.md §8 |
| `createCaptions`가 문장 중간에서 끊고 `add`/`setTimes`는 겹침 거부 (T1·R2). 코드: 기본 maxChars 42(영어 기준), 글자를 탐욕적으로 채움, 문장 끝은 블록이 절반 이상 찼을 때만 끊음, CPS·한글/라틴 폭·줄 끝 문장부호 규칙 없음(`crates/edit/src/transcript.rs:321`) | `cli.py captions` → SRT → `captions.import`(관대). 단계 8에서 값을 맞춘 `createCaptions`와 규칙 충족도를 비교해 이기지 못하면 명령을 뺀다 |
| 캡션 `size`는 1080라인 기준이라 세로에선 1.78배 → 줄넘침 (R1) | SKILL.md §9 + `captions`가 번인과 같은 기준으로 줄 폭 계산 |
| 기본 폰트 Inter에 한글 없음 (실측; T1·T2·R1은 스스로 알았음) | SKILL.md §9 한 줄(필수 확인) + 사실 테스트 |
| 미리보기엔 자막, 내보내기 기본은 미번인 (실측) | SKILL.md §6·§13 |
| 내보내기 기본 range가 In/Out (코드) | SKILL.md §13 |
| 세로 세이프존 침범 (T2·R1) | `frames --overlay`(수치 소유, `--help`에 표) + SKILL.md §10 원칙 |
| 라우드니스 미정규화·"근접" 판정 (T2·T1) | `qc` 대상 기준(`qc --help`) + SKILL.md §13 |
| 컷어웨이에 디졸브 (T3) | SKILL.md 편집 원칙 |
| 소스 무관 기계적 순환 배치 (T2) | SKILL.md §11 |
| 테스트 패턴으로 LUT 역산 (T4) | SKILL.md §12 |
| ffmpeg 리먹스(faststart·챕터) (T4·R2) | SKILL.md §13: faststart만 허용, 챕터는 설명란 |
| ASR 고유명사 오인식 교정 (R1·R2 잘함) | SKILL.md 원칙 한 줄(넣는 이유: 실패 비용이 큼, 공개 자막 오류) |
| inspect 요약 파이썬 반복·대형 출력 527KB (4/6, 실측) | `cli.py timeline` |
| 프레임 추출·이어붙이기 반복 (6/6) | `cli.py frames` |
| ffprobe+ebur128 반복 (6/6) | `cli.py qc` |
| 작업 폴더 밖 쓰기, venv·모델 방치 (T1·R1·R2) | SKILL.md "Working files" |
| zsh에서 `$VAR` 옵션 미분리 (T1·실측) + CLI가 모르는 옵션 무시 | SKILL.md CLI 절 |
| 브리지: 경로 없는 프로젝트에 `--save` → 저장 대화상자로 채널 차단 (실측) | SKILL.md §15 |
| 분할화면에서 말하는 쪽 크롭 (R1 잘함) | SKILL.md §7·§10 |
| `--save` 사용, describe 활용, 사후 프레임 확인 (전원 잘함) | **넣지 않음**: 기본값으로 이미 함. CLI 의미론 절에는 실패 형태만 남김 |
| 명령 문법·파라미터 목록(700개) | **넣지 않음**: `describe` 소유, 1~2일마다 바뀜 |
| (1c M1 음악 몽타주, $0.73·32턴) numpy로 박자 감지를 직접 짜서 4턴에 성공(122BPM) | **넣지 않음(보류 유지)**: 스스로 해냄. SKILL.md §11에 "박자는 측정" 한 줄만 |
| (1c 전원) 작업 폴더 밖 `/tmp` 쓰기 5/5, restricted에서 Read 실패로 턴 낭비 | SKILL.md §14 |
| (1c M1·V1·C1) 라우드니스 미정규화, 트루피크 +0.1~+1.0 dBTP(클리핑) 3/5 | `qc`(fail) + SKILL.md §13 `loudnessLufs` |
| (1c 전원) moov 끝 5/5 | `qc` warn + §13 faststart |
| (1c V1·L1) `transcript.downloadModel` 헛걸음 재현 2/2 | SKILL.md §8 첫 줄 |
| (1c V1) BGM 구간 Whisper 환각("시리야"·"네" 반복), BGM 아래 silencedetect 무력 → faster-whisper VAD 설치 | `transcribe` review에 반복·no_speech 표시, 발화 구간 못 찾으면 원래 시간 유지(스냅 안전 조건) + SKILL.md §8 한 줄 |
| (1c V1) 한국어 자막 줄 길이 위반 8/35, (L1) 번역 자막 위반 39/47(줄 26자, 7초 초과, 줄 끝 마침표) | `captions`(전사 입력) + `captions --cues`(번역 입력, 성진님 결정) |
| (1c V1) 번인 자막이 이미 있는 영상에 사이드카만 냄 | **넣지 않음**: 잘함 |
| (1c H1) 60fps HLG 소스를 30fps 시퀀스로 | SKILL.md §10 "시퀀스는 소스 fps" |
| (1c H1) ffmpeg에 zscale 없어 HDR 썸네일 톤매핑 실패 | `frames --media` HDR 노트 |
| (1c H1) AV1 HDR 렌더가 1/4 크기에도 프레임당 8~27초 | SKILL.md §6 한 줄(렌더 비용) |
| (1c H1) 세로 제목이 Shorts·Reels 세이프 박스 상단에 걸침 | `frames --overlay` + §10 |
| (1c C1) 내장 S-Log3 입력 LUT, 로그 아닌 클립을 측정으로 구별 | **넣지 않음**: 잘함 |
| (1c C1·L1) `out/`에 `FilmCraft Previews/` 남김 | SKILL.md §14 |
| (1c L1) 40분 요약 자체는 잘함(-14 LUFS, burn, entire, 59.94 유지) | **넣지 않음** |

## 구현 후 디렉토리 구조

```
/Users/seongjin/Coding/video/
├── .mcp.json                         # 브리지 MCP: filmcraft-cli mcp --bridge 127.0.0.1:9876
├── pytest.ini                        # testpaths=tests, pythonpath=.claude/skills/filmcraft/scripts
├── tests/
│   ├── filmcraft_skill/              # 번들 코드 테스트 (CLI 프로토콜·유닛 인터페이스·구조)
│   │   ├── conftest.py               # ffmpeg로 픽스처 생성(target 없이 tmp_path), filmcraft-cli 탐지·skip
│   │   ├── fixtures/                 # 녹화된 외부 출력: whisper JSON, sequence.inspect JSON (소형)
│   │   ├── test_structure.py
│   │   ├── test_transcribe.py
│   │   ├── test_captions.py
│   │   ├── test_timeline.py
│   │   ├── test_frames.py
│   │   └── test_qc.py
│   └── filmcraft_facts/              # 사실 회귀 테스트: 설치된 filmcraft-cli 동작 = 스킬 문장
│       └── test_facts.py
└── .claude/skills/filmcraft/
    ├── SKILL.md
    └── scripts/
        ├── cli.py                    # 유일한 진입점 (PEP 723)
        └── filmcraft/                # 유일한 패키지 (stdlib 이름과 충돌 없음)
            ├── __init__.py
            ├── timecode.py           # 공용: ticks↔초↔프레임↔TC (유리수 fps)
            ├── filmcraft_cli/        # 시스템: filmcraft-cli 호출과 그 출력(inspect의 "Float(…)" 디버그 문자열 등)
            ├── whisper/              # 시스템: mlx-whisper 실행(uvx)과 JSON
            ├── ffmpeg/               # 시스템: ffprobe 스트림, ebur128, silencedetect, 프레임 추출
            ├── mp4/                  # 시스템: MP4 상위 atom 순서(moov 위치)·elst 존재
            ├── transcribe/           # 기능
            ├── captions/             # 기능 (레이아웃 규칙 = 순수 코어 + SRT 쓰기)
            ├── timeline/             # 기능
            ├── frames/               # 기능 (Pillow 타일·라벨·세이프존 오버레이)
            └── qc/                   # 기능 (대상별 기준 = 코드 상수, --help로 노출)
```

- `data/`는 만들지 않는다(스킬이 유지하는 상태 없음).
- `.claude/plans/`, `.tmp/`는 건드리지 않는다. **`.tmp/etc/국회 회의 영상.mp4`(636MB, 미추적)는 절대 스테이징하지 않는다.** 경로를 지정해서만 `git add`한다.
- 레포 밖: `~/.local/bin/filmcraft-cli`(앱 버전과 같은 0.7.2). mlx-whisper 모델(약 1.6GB)은 계획 세션에서 이미 `~/.cache/huggingface`에 받아 둠.

## SKILL.md 섹션 구조 (영어로 작성, 한 덩어리 = 한 줄)

**쓰기 규칙** (skill-maker 대조에서 보강)
- **출처 표시 금지**: SKILL.md에는 어느 실험·모델·날짜에서 나온 줄인지 쓰지 않는다. 그런 개발 기록은 PR 본문에 둔다. 측정값은 다음 결정을 바꾸는 이유일 때만 남긴다(예: "필터 없는 `commands`는 약 16만 자").
- **권위의 종류 표시**: 수치와 원칙마다 어떤 종류인지 드러낸다. 같은 무게로 쓰면 모델이 관행을 규정처럼, 또는 규정을 취향처럼 다룬다.
  - 규정(한국 방송 -24 LKFS)
  - 측정된 플랫폼 동작(YouTube -14 LUFS)
  - 업계 관행(넷플릭스 자막 규칙, 릴스·틱톡 -14)
  - 공식 광고 기준(세이프존)
  - 성진님 결정(ffmpeg 경계, faststart 예외)
  - FilmCraft 사실(사실 테스트가 지킴)
- **클라이언트가 소유한 값**: 플랫폼·FilmCraft가 바꿀 수 있는 수치는 번들 코드의 `--help`(qc 기준표, 자막 규칙, 세이프존)나 사실 테스트가 갖는다. 본문에는 그 값이 틀렸을 때 생기는 실패를 쓴다.

**분할 원칙 (사용자 지적 반영).** 파일은 로드 시점으로 나누고, 크지 않으면 최대한 합친다.
- 편집 지식(말·자막·타이틀·세로·몽타주·오디오·색·납품)과 설치 절차는 전부 SKILL.md에 둔다.
  - 크기가 작다: 숫자 규칙은 `captions --help`·`qc --help`, 명령 사양은 `describe`가 소유해서 분기마다 10~15줄 남짓이다.
  - 실제 작업은 분기가 섞인다(토킹헤드로 쇼츠 = 말+세로).
- 실행 중인 앱(브리지) 절차도 10~12줄이라 합친다(사용자 결정). 헤드리스 작업이 매번 읽는 비용은 약 700토큰이고, 마지막 절에 두어 분기임이 읽히게 한다.
- 그래서 `references/` 폴더는 만들지 않는다(skill-maker 트리에서 references는 "한 분기에서만 읽는 것"이 있을 때만 둔다).
- 예산: SKILL.md는 약 200줄 이내. 구현 중 어떤 분기 절이 커져서 다른 경로가 매번 내는 비용이 눈에 띄면, 그 절만 그 분기의 로드 시점으로 떼어 낸다(분량이 아니라 로드 시점 기준).

**Frontmatter**
- `name: filmcraft`
- `description`:
  - FilmCraft = 이 맥에 설치된 프리미어식 오픈소스 편집기, `filmcraft-cli`(헤드리스) 또는 실행 중인 앱(브리지)으로 조작
  - 할 수 있는 일: 컷편집, 전사 기반 편집, 세로 쇼츠·릴스, 하이라이트·음악 몽타주, 오디오 믹스·라우드니스, 색보정, 한국어 자막·타이틀, 검수된 내보내기, Premiere/Resolve 인계
  - 트리거 어휘: 영상 편집, 컷편집, 자막, 쇼츠, 릴스, 하이라이트, 색보정, .fcproj
  - 경계: "Not for developing FilmCraft's own source code"
  - 이웃 스킬과 트리거가 겹치지 않음(skill-doctor 확인)
- `allowed-tools`: `Bash(filmcraft-cli *)`, `Bash(uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" *)`, `Bash(ffprobe *)`. 형식은 `claude plugin validate --strict`로 확인한다.

**본문 섹션** (모든 경로 → 분기 순서. 분기 절은 첫 줄이 "언제 쓰나")

1. **What finished means** — 완료는 아래가 모두 갖춰진 상태다.
   - **프로젝트 보존**: 저장한 `.fcproj`를 새 프로세스로 열어 편집이 그대로인지 확인한다.
   - **기술 QC**: 결과물이 있으면 대상 기준 `cli.py qc`를 통과한다. 다시 내보내기는 최대 2회까지 하고, 넘으면 측정값과 함께 보고하고 멈춘다.
   - **편집 검수**: 컷 지점과 글자가 있는 프레임을 `frames`로 보고, 최종 컷 전사로 끊긴 문장·뜻이 바뀐 이어붙이기를 확인한다.
   - **보고서**: 바꾼 것, 내린 편집 판단(지운 필러, 추정한 고유명사), 검증 못 한 것(직접 듣지 못한 컷의 자연스러움).
   - 편집은 FilmCraft에서만 한다(사용자가 열어 고칠 수 있어야 하므로). ffmpeg/ffprobe는 측정용이고, 예외는 최종 MP4 faststart 리먹스 하나다.
   - **지킬 것과 자유로운 것**(완료 기준이 특정 결과물 하나를 요구하지 않도록):
     - 지킬 것: 발언의 뜻, 사용자가 명시한 길이·비율·대상, 다시 열리는 프로젝트, 대상 기준
     - 자유로운 것: 샷 선택, 컷 리듬, 자막·타이틀 디자인, 전환 스타일. 이것들은 판단으로 고르고 보고서에 이유를 쓴다
2. **Before the first command** — setup.md를 흡수한다.
   - `filmcraft-cli --version`과 앱 버전(`defaults read /Applications/FilmCraft.app/Contents/Info CFBundleShortVersionString`)을 비교한다.
   - 없거나 다르면 앱 버전과 같은 CLI를 설치한다:
     1. `gh release download v<ver> -R storytold/filmcraft -p 'filmcraft-cli-<ver>-macos-universal.zip' -p SHA256SUMS.txt`
     2. SHA256 검증
     3. `~/.local/bin/filmcraft-cli`에 설치
     - 이유: 앱보다 새 CLI가 쓴 프로젝트는 앱이 못 열 수 있다.
   - FilmCraft는 1~2일마다 릴리스된다. 이 스킬과 `describe`·실제 결과가 다르면 결과를 믿고 보고한다. 업데이트 뒤에는 `uv run --with pytest --with pillow pytest tests/filmcraft_facts`로 낡은 문장을 찾는다.
3. **Headless or the running app**
   - 기본은 `filmcraft-cli --project P --save …`. 창이 없고 자동저장도 없으니 저장은 내 책임이다.
   - 사용자가 앱에서 보거나 같이 작업하길 원하거나 그 프로젝트가 앱에 열려 있으면 → §15.
   - 앱에 열린 `.fcproj`를 디스크에서 동시에 편집하지 않는다.
4. **How the CLI fails quietly** — 실패 형태와 이유만 쓴다. 기본값 모델이 이미 하는 describe 사용법·params 표기는 넣지 않는다.
   - **찾기**: 필터 없는 `commands`는 약 16만 자다.
   - **세션**:
     - 호출마다 새 세션이다. `--save` 없이 하면 편집이 사라진다.
     - 의존 단계는 `run file.jsonl --save` 하나로 묶는다. 실패한 줄이 있으면 저장 전에 끝난다(`--keep-going`이면 부분 저장).
     - 선택·타깃·Source 모니터는 호출 사이에 사라진다.
   - **무시되는 값**: `time`의 실수, 오타 키, `mcp` 외의 모르는 CLI 옵션은 오류 없이 무시된다. 결과를 반드시 읽는다: `cuts:0`, `null`, 변하지 않은 `durationFrames`, `path:null`.
   - **zsh**: 따옴표 없는 `$OPTS`는 단어로 쪼개지지 않는다.
   - **시간·ID**:
     - timecode는 시퀀스 시작 TC를 무시하고, Mark Out은 그 프레임을 포함한다.
     - 대상 없는 `razor`는 모든 트랙을 자르고, 오른쪽 조각은 새 ID를 받는다.
     - `graphics.*`의 `track`은 0부터 세는 인덱스다.
     - `newSequenceFromClip`은 필요한 트랙만 만든다.
   - **describe에 기본값이 안 나오는 함정**: `clip.audioGain` 기본 mode는 adjust다. `clip.speedDuration`은 `reverse`를 빼면 역재생을 해제한다. `sequence.linkedSelection`은 `on`을 빼면 토글한다.
5. **Command families by job** — 일→명령군 지도, 접두사와 "언제"만 쓴다.
   - 조립·트림: `timeline.*`, `sequence.*`(헤드리스에선 `trim.*` 대신 `timeline.trim/roll/slip/slide`)
   - 전사: `transcript.*`
   - 자막: `captions.*`
   - 그래픽·템플릿: `graphics.*`
   - 효과·키프레임: `effects.*`
   - 영역 가리기·추적: `masks.*` + 블러
   - 색: `lumetri.*`, `lut.*`, `scopes.read`
   - 오디오: `essentialSound.*`, `clip.audioGain`, `mixer.*`
   - 멀티캠: `clip.synchronize {method:"audio"}` → `clip.createMulticam` → `multicam.*`
   - 속도·정지: `clip.speedDuration`, `clip.frameHold*`(시간 리맵 키프레임은 렌더되지 않음)
   - 미디어 관리: `media.*`
   - 마커: `markers.*`
   - 내보내기: `file.exportMedia`
   - 인계: Premiere/Resolve는 FCP7 XML, Resolve는 OTIO도, Avid는 AAF/OMF, 단순한 목록은 EDL. Lumetri 등 넘어가지 않는 것은 보고한다.
   - 받아오기: `.prproj`는 열 수 없다 → Premiere에서 FCP7 XML/AAF/OTIO로 내보내 달라고 한다. 가져오면 현재 프로젝트에 합쳐진다.
6. **Seeing and hearing the edit**
   - 재생할 수 없으니 재료는 `frames --media`·`transcribe`, 타임라인은 `timeline`(raw `inspect`는 클립당 약 2KB), 결과는 `frames`(세로면 `--overlay`)와 `qc`로 본다.
   - 미리보기 `render`는 자막을 그리지만, 내보내기는 `burnCaptions:true`일 때만 박는다.
7. **Editorial judgment** — 모든 경로에 쓰이는 원칙. 각 원칙에 이유와 뒤집히는 조건을 붙인다. 예시는 비슷한 두 경우가 왜 다르게 결정되는지 보여 줄 때만 쓴다(정답 템플릿 금지). 기본값 모델을 고치는 줄은 피할 행동을 구체적으로 이름 붙인다. 예: "컷어웨이 진입·이탈마다 디졸브를 거는 것", "소스를 내용과 무관하게 순서대로 돌리는 것".
   - **자르고 남길 것**: 의미 없는 것은 자르고, 숨(양쪽 0.15~0.3초)은 남긴다. 필러가 의미를 가지면 남기고 보고한다.
   - **컷 지점**: 단어 경계의 무음에서 자른다.
   - **전환**: 직컷이 기본이다. 디졸브는 시간·장면 전환을 뜻한다. 뒤집히는 조건: 실제 장면 전환, 의도된 몽타주 스타일, 요청.
   - **프레이밍**: 말하는 사람을 화면에 둔다.
   - **글자 정확성**: 화면의 글자는 정확해야 한다(ASR 교정, 추정은 보고). 뜻을 바꾸는 이어붙이기를 하지 않는다.
   - **화면 겹침**: 박힌 그래픽 위에 또 얹지 않고, 플랫폼 UI 영역을 피한다.
   - **오디오 우선순위**: 대사 명료도가 먼저다.
8. **Speech as material** — 언제: 토킹헤드·인터뷰·강의·회의·요약본·자막 작업.
   - 릴리스 빌드는 전사가 안 되니 모델 다운로드를 쫓지 않는다. `transcribe` → `review` 확인 → JSONL 단어 텍스트 교정(시간 유지) → `run --save`.
   - 고르기: `transcript.inspect`·`search` → `select` + `extract`/`lift`. 요약은 문장 경계에서 자르고 질문과 답을 짝으로 남긴다.
   - **필러**: 기본값이 영어다. 한국어 후보는 음·어·아·그·저·뭐(단독 토큰)이고, 담화표지(그러니까 등)는 판단할 몫이다. 필러를 먼저 지우고 공백을 지운다.
   - **공백**: `removePauses`는 keep을 양쪽에 남긴다(최소 2×keep, 프레임 정렬로 더 남을 수 있고, 1프레임 이하는 그대로).
   - **크로스페이드**: 대사 컷에 2~4프레임 오디오 크로스페이드를 넣는다.
   - **자막**:
     - `captions` → `captions.import`(관대; 개별 `add`/`setTimes`는 겹침을 거부) → import가 돌려준 트랙에 같은 스타일로 `setStyle`. `transcript.createCaptions`는 영어 기준이라 쓰지 않는다. 숫자 규칙은 `captions --help`.
     - 위치는 하단 중앙이고, 박힌 글자를 가리면 위로 올린다.
     - 번인과 사이드카를 둘 다 쓰면 유튜브에서 두 번 보인다.
9. **On-screen text** — 언제: 자막·타이틀·로워서드 등 화면에 글자가 들어갈 때.
   - **한글 폰트**: 기본 폰트 Inter에 한글이 없다. 모든 캡션 트랙·텍스트 레이어에 설치된 한국어 패밀리(`fonts.list`)를 지정하고 렌더로 확인한다.
   - **캡션 크기**: `size`는 1080라인 기준이라 1080×1920에선 1.78배 커진다.
   - **템플릿**: 이름에 en dash가 들어간다.
   - **방송 슈퍼**: 중복하지 않고, 가리는 건 의도가 있을 때만 한다.
10. **Changing the frame shape** — 언제: 출력 비율이 소스와 다를 때(쇼츠·릴스·정사각).
    - **시퀀스**: 결과물 크기와 소스 fps를 따른다.
    - **크기가 다른 클립**: 원본 크기로 놓이므로 `fillFrame`/`fitToFrame`을 쓴다.
    - **피사체 맞춤**: Motion position/scale로 세이프 박스 중심에 맞춘다. 분할화면은 구간마다 말하는 쪽. `auto_reframe`은 추정치라 프레임으로 검증한다.
    - **업스케일**: 화질 손실은 보고한다.
    - **세이프존**: 수치는 플랫폼이 바꾸는 값이라 `frames --help`·`--overlay`가 소유한다(기본 표: Meta 14%/35%/6%, TikTok 240/660/120+버튼열, Shorts 288/672/48/192, 공통 박스 x 120~780·y 290~1150). 본문에는 "글자와 얼굴은 오버레이 박스 안, 수치는 광고 기준이라 일반 게시물 UI와 다를 수 있음"만 쓴다.
    - **폰 미디어**: 회전은 반영된다. HEIC·EXIF 회전은 지원하지 않는다. HDR은 SDR 시퀀스에서 자동 톤매핑된다.
11. **Many clips and music** — 언제: 여러 클립·B-roll·음악 중심 편집.
    - **훑기**: `frames --media --every`, `clip.sceneEditDetection {wait:true, applyCuts:false, generateMarkers:true}`.
    - **고르기**: 다양성·훅·반복 금지·액션 컷. 순서를 기계적으로 돌리지 않는다.
    - **음악**: 박자는 측정한다(ffmpeg 에너지 onset). 박이 정수 프레임이 되는 fps를 고르고 프레이즈 끝에서 끝낸다.
    - **B-roll**: 직컷으로 말의 공백을 덮거나 말을 예시하고, 대사는 J/L로 이어 간다.
    - **조립**: `timeline.place {items}`(sourceIn·duration은 ticks 정수). 헤드리스에선 `source.insert/overwrite` 대신 이것을 쓴다.
    - **더킹**: `essentialSound.setType` → 음악 클립에 `ducking.*` + `generateDucking`(대사 클립은 거부). 바깥 페이드는 `applyAudioTransition`.
12. **Color** — 언제: 색보정이 요청됐거나 화면이 명백히 틀어졌을 때.
    - **순서**: Basic → 매칭 → 룩 → 비네트.
    - **스코프**: `scopes.read`(중립 RGB, 파형 0~100%, 피부톤)로 판단한다.
    - **Lumetri**: 파라미터 id는 `effects.list detail=true`로 찾는다. `applyMatch`의 `distanceBefore/After`로 효과를 확인한다.
    - **하지 말 것**: 차트·테스트 패턴으로 보정을 역산하지 않는다.
    - **LUT**: 로그는 `setInputLut`, 크리에이티브는 `setLook`.
13. **Delivery** — 모든 내보내기에 쓴다.
    - **내보내기 기본값**: `range:"entire"`를 명시한다(기본은 In/Out). `burnCaptions`/`captionSidecar`는 의도대로 정한다. `loudnessLufs`는 `qc` 대상값에 맞춘다(BS.1770 측정 + 트루피크 리미터).
    - **YouTube 권장**: H.264 High, `keyframeDistance`=fps/2, 48kHz AAC.
    - **세로**: 프리셋 "Social Vertical 1080×1920".
    - **속도**: `hardwareEncoding/gpuRendering:"auto"`(CRF·2-pass와 함께 못 씀). H.265는 하드웨어 전용이고 AV1은 없다.
    - **오프라인 미디어**: `media.findMissing`, `--allow-offline` 금지.
    - **검수**: `qc`(재내보내기 최대 2회).
    - **faststart**: `-c copy -movflags +faststart`만 한다(Edit List는 유지).
    - **유튜브 챕터**: 설명란 타임스탬프로 한다(규칙은 구현 때 출처로 확인).
14. **Working files**
    - 중간 파일은 프로젝트 옆 `<name>.work/`에 두고, 끝나면 필요 없는 것은 지운다. 작업 폴더 밖에는 쓰지 않는다.
    - 전역 설치는 하지 않는다. Whisper 모델(약 1.6GB)을 처음 받기 전에는 알린다.

15. **Working in the running app** — 언제: 사용자가 앱에서 보거나 같이 작업할 때, 프로젝트가 앱에 열려 있을 때. 마지막 절에 두어 헤드리스 경로와 섞이지 않게 한다.
- **연결**: `nc -z 127.0.0.1 9876`으로 확인한다.
  - 앱이 꺼져 있으면 `open -a FilmCraft --args --control 9876`(인자는 새로 띄울 때만 전달된다).
  - 포트 없이 실행 중이면 사용자에게 저장 후 종료를 부탁한다(직접 종료 금지).
  - 프로젝트 MCP `filmcraft`는 세션 시작 때 승인해야 보인다.
- **명령**: `filmcraft-cli --bridge 127.0.0.1:9876 exec|run|import|inspect|export`. `render`는 헤드리스 전용이다.
- **저장 함정**: 경로 없는 앱 프로젝트에 `--save`/`file.save`를 보내면 macOS 저장 대화상자가 떠서 모든 요청이 60초 timeout으로 막힌다. 먼저 `file.saveAs {path}`를 보낸다. 이미 막혔다면 `osascript … key code 53`(손쉬운 사용 권한 필요)이나 사용자에게 Cancel을 부탁한다.
- **보기**: MCP `ui_screenshot {panel, max_side}`, `render_frame {seconds}`. UI 전용 동작만 `ui_elements`/`ui_click`으로 한다.
- **스킬 도구와 함께 쓰기**: `timeline`·`captions`는 `--bridge`로 쓴다. `frames`·`qc`는 `file.saveCopy {path}` 사본으로 돌린다. 디스크 원본은 앱의 미저장 편집과 다를 수 있다.
- **예의**: 사용자가 입력 중이면 UI를 조작하지 않는다. 끝나도 앱은 둔다. `app.quit`은 저장 프롬프트 없이 종료한다(저널 보존).

## 번들 코드 계약 (`scripts/cli.py`)

**공통 규칙**
- 실행: `uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" <command> …`
- PEP 723 헤더: `requires-python >=3.12`, 의존성은 `pillow`(frames 전용). mlx-whisper는 `uvx --from mlx-whisper mlx_whisper` 서브프로세스로 돌려서 cli.py 환경을 가볍게 유지한다.
- `cli.py`는 파서·도움말·디스패치·종료 코드만 갖는다. 도메인 결정은 각 유닛에 있다.
- stdout은 JSON 한 문서이고, 앞에 싼 신호(요약·다음 행동)와 큰 산출물 경로가 온다. 진행 상황은 stderr로 낸다.
- 종료 코드: 0 성공, 2 인자 오류, 1 외부 도구 실패(메시지와 stderr 꼬리 포함). `qc` 불통과는 3이다(`--help`에 명시).
- 각 `<command> --help`가 자기 인자·출력·실패를 혼자서 설명한다. argparse 출력은 실행해서 줄바꿈이 깨지지 않는지 확인한다.

**프로젝트 원천 규칙** (codex 리뷰 반영)
- 프로젝트를 읽는 명령(`timeline`, `captions`)은 `--project P`와 `--bridge ADDR` 중 정확히 하나를 받는다. FilmCraft CLI 자신도 이 조합을 거부한다(`apps/filmcraft-cli/src/main.rs:151-154`).
- 렌더가 필요한 `frames`는 헤드리스에서만 돈다(브리지 `render`는 거부됨, `main.rs:464`). 앱 상태를 검수하려면 먼저 브리지로 `file.saveCopy {path}`(앱의 경로·dirty를 바꾸지 않음, `commands.rs:1500`)를 하고, 그 사본에 `frames`를 돌린다. 단일 프레임은 MCP `render_frame`으로 본다.
- 수용 테스트: 앱에 미저장 편집이 있어 디스크 파일과 다를 때, `timeline --bridge`는 앱 상태를 보여 주고 사본의 `frames`는 그 상태를 그린다.

**`transcribe MEDIA --item ID --out X.jsonl [--language ko] [--model …] [--max-shift 0.5]`**
- 하는 일:
  1. mlx-whisper(uvx)로 단어 시간이 있는 전사를 만든다.
  2. ffmpeg로 발화 구간을 구한다.
  3. 단어 시간을 스냅한다(아래 안전 조건).
  4. ticks로 바꿔 `transcript.set` JSONL 한 줄을 쓴다.
- 스냅 안전 조건:
  - 경계 이동은 `--max-shift`초 이내다.
  - 단어 구간 전체로 판단한다(양 끝을 따로 옮기지 않음).
  - `start < end`(최소 1프레임)를 지킨다.
  - 단어 순서와 비겹침을 보존한다.
  - 대응하는 발화 구간이 없으면 원래 시간을 유지하고 `review`에 남긴다.
- stdout: `{item, language, words, seconds, speech_seconds, snapped, unmatched, review:[{i,text,start_s,reason:"low_prob"|"unmatched"}], out, next:"filmcraft-cli --project P --save run X.jsonl"}`

**`captions (--project P | --bridge ADDR | --cues IN.srt) --out X.srt [--font F] [--size N] [--margin M] [--anchor bottom|top] [--lines 2] [--cps 12] [--min 0.833] [--max 7]`**
- 스타일 계약: 계산에 쓰는 font·size·margin·anchor를 인자로 받고 결과 JSON에 그대로 돌려준다. 프로젝트에 이미 캡션 트랙이 있어도 그 스타일을 추정하지 않는다. `captions.import`는 기본 스타일(Inter/54/0.08)의 새 트랙을 만들기 때문이다(`crates/engine/src/captions.rs:135-141`, `crates/project/src/caption.rs:101-109`).
- 기본값:
  - 가로: font "Apple SD Gothic Neo", size 54
  - 세로(높이 > 너비): size 40
  - 최종값은 단계 8의 렌더 실측으로 정한다.
- 줄 폭 계산: 번인과 같은 기준을 쓴다. px = size × 높이/1080, 최대 폭 = 프레임 너비의 0.9이고, 실제 폰트 폭으로 줄을 바꾼다(`crates/captions/src/burn.rs:112-119`). 그래서 Pillow로 같은 폰트 파일의 글자 폭을 재고, 폰트 파일을 못 찾으면 보수적 em 추정(한글 1.0em, 라틴·숫자 0.6em)과 안전 계수를 쓴다.
- 입력과 처리:
  - `transcript.inspect`의 **시퀀스 시간** 단어를 쓴다(편집·배속 반영; 실측 확인: 원본 6.98초 → 시퀀스 4.644초).
  - 문장·절 경계에서 나눈다.
  - 넷플릭스 한국어 규칙을 적용한다(줄당 16자 기본, 라틴·공백·문장부호 0.5, 2줄, 12cps, 5/6~7초, 줄 끝 마침표·쉼표 제거, 아래가 넓은 피라미드). 숫자 규칙은 `captions --help`가 소유한다.
  - 시작 시각을 **엄격히 증가**시키고 프레임에 정렬한다. 같은 시작의 큐는 import가 버리기 때문이다(`crates/captions/src/lib.rs:155-162`).
- stdout: `{cues, style:{font,size,margin,anchor}, max_line_units, cps_violations:[…], out, next:["… exec captions.import path=OUT", "… exec captions.setStyle track=<import가 돌려준 track> font=… size=… margin=… anchor=…"]}`
- 사용 절차: 모델은 import 결과의 `warnings`가 비어 있는지 확인한다.

**`timeline (--project P | --bridge ADDR) [--sequence ID] --out DETAIL.json`**
- stdout은 싼 신호만: `{summary:{name,fps,size,duration_tc,tracks:[{name,clips,locked,muted}],clips,captions,markers,transitions}, detail:"DETAIL.json"}`, 300클립이어도 2KB 이내.
- 상세 파일: 클립별 `{clip,item,name,track,start_tc,end_tc,src_in_tc,src_out_tc,speed,reverse,gain_db,effects:[names],enabled}`, 전환, 마커, 캡션 트랙 요약. 크기 제한은 두지 않는다(리뷰 실측: 표의 필드는 compact로 클립당 약 197바이트).
- 숨기는 일: inspect의 디버그 문자열(`Float(…)`, `Vec2(…)`) 파싱, 유리수 fps TC 계산.

**`frames (--project P | --media FILE) (--at T… | --cuts | --every SEC) [--overlay shorts|reels|tiktok|all] [--cols N] [--width PX] --out SHEET.png`**
- `--project`는 헤드리스 `render`를 쓴다(자막·그래픽 포함). `--media`는 ffmpeg 추출이다.
- 그리는 것: TC 라벨, 타일, 세로일 때 세이프존 박스. 세이프존 수치는 코드 상수이고, `frames --help`가 플랫폼별 표와 권위 종류(공식 광고 기준/권고)를 함께 보여 준다.
- stdout: `{sheet, frames:[{t,tc}], size}`

**`qc FILE --target youtube|shorts|reels|tiktok|broadcast-kr [--expect-duration S] [--expect-fps F] [--expect-size WxH]`**
- 판정 계약: 각 체크는 `fail`(필수) 또는 `warn`(권고)이고, 허용 오차가 있다. 측정이 안 되는 경우 값은 `null`이고 `reason`을 붙인다(오디오 스트림 없음, 무음이라 게이트 통과 못 함 → `-∞` 대신 null, `crates/audio-dsp/src/loudness.rs:332-337`).
- 오디오 필수 여부는 대상이 정한다.
- 종료 코드: 0(경고만 있음), 3(fail 있음)
- stdout: `{target, pass, failed:[…], warnings:[…], checks:[{name,value,expected,tolerance,level,pass,reason}]}`
- 대상별 기준표(초안). 구현 때 출처로 확정하고 `qc --help`에 표로 노출한다. 각 기준에 권위 종류(규정/측정된 플랫폼 동작/관행/성진님 결정)를 함께 표시한다:

  | 체크 | youtube | shorts / reels / tiktok | broadcast-kr |
  |---|---|---|---|
  | 컨테이너 | MP4 (fail) | MP4 (fail) | 기록만 |
  | 영상 | H.264 (warn), High (warn) | H.264 (warn) | 기록만 |
  | 해상도 | `--expect-size` 일치 (fail) | 1080×1920 (fail) | 기록만 |
  | fps | `--expect-fps` 일치 (fail) | ≤60 (fail) | 기록만 |
  | 길이 | `--expect-duration` ±1프레임 (fail) | 플랫폼 상한 (fail, 수치는 구현 때 출처 확인) | 기록만 |
  | 오디오 | 있음 (fail), AAC-LC·48k·스테레오 (warn) | 있음 (fail) | 있음 (fail) |
  | 통합 라우드니스 | -14 LUFS: ±1 pass / ±2 warn / 밖은 fail | -14 LUFS: ±1 pass / ±2 warn / 밖은 fail | -24 LKFS ±2 (fail) |
  | 트루피크 | ≤ -1 dBTP (fail) | ≤ -1 dBTP (fail) | ≤ -1 dBTP (warn, 미확인) |
  | moov 위치 | 끝이면 warn → faststart 리먹스 | 끝이면 warn → faststart 리먹스 | 기록만 |
  | elst | 기록만 | 기록만 | 기록만 |

- 반복 종료: 다시 내보내기는 최대 2회다. `loudnessLufs` 목표가 트루피크 리미터 때문에 달성되지 않으면(엔진이 피크 제한을 우선, `crates/export/src/audio_out.rs:120-126`) 그 사실과 측정값을 보고하고 멈춘다.
- 범위: 기술 QC다. 편집 품질(컷의 자연스러움, 의미 보존)은 판정하지 않는다. 그쪽은 SKILL.md "What finished means"의 편집 검수가 맡는다.

**유닛과 의존 방향**
- 기능(`transcribe`, `captions`, `timeline`, `frames`, `qc`) → 시스템(`filmcraft_cli`, `whisper`, `ffmpeg`, `mp4`) → 공용 `timecode`. 역방향은 없다.
- 기능끼리는 import하지 않는다.
- 각 유닛의 인터페이스는 `__init__.py`다. 밖에서 `filmcraft.<unit>.<module>`을 직접 import하지 않는다(테스트 포함).
- 외부 형식(whisper JSON 필드, inspect 디버그 문자열, ffprobe 키)은 해당 시스템 유닛 밖으로 새지 않는다. 기능은 스킬 자체의 타입만 본다.

## 테스트 설계 (`coding` 스킬 기준으로 이음매를 합의)

**이음매**
- `cli.py` 하위 명령 프로토콜(서브프로세스, 실제 진입점)
- 순수 코어의 안정 계약
  - `captions`의 레이아웃 함수: 단어 → 큐
  - `transcribe`의 스냅 함수: 단어·발화구간 → 단어
  - `qc`의 판정 함수: 측정값·대상 → 결과
- 구조 규칙

**기대값의 독립성**
- 자막 레이아웃: 넷플릭스 규칙의 손으로 푼 예제로 기대값을 만든다(16자 넘는 문장 분할, 초당 12자 초과 처리, 줄 끝 마침표 제거). 줄 폭 계산은 같은 계산을 테스트에서 반복하지 않고, FilmCraft 번인 렌더를 오라클로 삼는다(배경 박스 높이로 줄 수 측정).
- 스냅 (두 층):
  - (a) 순수 코어: 무음·발화 구간을 아는 합성 버스트에 어긋난 단어 시간을 넣고 경계가 무음 쪽으로 가는지 본다. 경계 사례도 넣는다: 발화 밖 단어(→ 원래 시간 유지 + review), 최대 이동 초과, 0길이가 될 상황, 순서 역전 위험.
  - (b) 실제 말: `say`로 구절을 **따로** 합성한 뒤 ffmpeg로 알려진 무음을 끼워 이어 붙여, 독립적인 기준 구간을 만든다. 녹화 Whisper JSON(또는 실제 경로)의 스냅 결과가 그 구간과 더 가까워지는지 본다.
- 시간 좌표 (전사 → 자막 경로):
  - 미디어 시간 단어를 넣은 클립에 트림·이동·배속(예: 200%)·리플 삭제·재사용을 한 프로젝트를 만든다.
  - 예상 시퀀스 시간은 손으로 계산한다(시퀀스 = 시작 + (미디어 − sourceIn)/speed).
  - `captions` → SRT → `captions.import`까지 비교한다.
  - import 전후 텍스트·큐 수·시간이 보존되는지, `warnings`가 비었는지 확인한다.
- 영속성: 저장한 프로젝트를 새 프로세스로 열어 `timeline` 요약과 대표 프레임 렌더가 저장 전과 같은지 본다.
- `removePauses`(사실 테스트): 프레임에 맞지 않는 단어 경계와 keep 값, 지워지지 않을 1프레임 이하 구간을 넣고, 독립적으로 계산한 프레임 결과(시작은 올림·끝은 내림)와 비교한다.
- qc:
  - 알려진 사양으로 만든 파일(ffmpeg 생성: 해상도·코덱·moov 끝/앞·오디오 없음·무음)을 쓴다.
  - 라우드니스는 `loudnorm`으로 맞춘 파일을 다른 방식으로 측정한 값으로 확인한다.
  - 측정 불가(무음·오디오 없음)는 `null`+`reason`이 나오는지 본다.
- timeline: 실제 CLI로 만든 프로젝트를 쓴다. 기대값은 프로젝트를 만든 명령의 입력(시작·끝 프레임)에서 온다. 300클립에서 stdout ≤ 2KB이고 상세 파일이 모든 클립을 담는지 확인한다.

**대역(double)과 미검증 경계**
- whisper만 녹화 JSON으로 대신한다. 모델이 1.6GB에 느리기 때문이다.
- 실제 mlx-whisper 경로는 환경변수 `FILMCRAFT_TEST_WHISPER=1`일 때만 `say`로 만든 한국어 음성으로 돈다.
- 그 외 ffmpeg와 filmcraft-cli는 실물로 돌린다. CLI가 없으면 해당 테스트를 skip하고 이유를 출력한다.

**구조 테스트** (`test_structure.py`)
- `scripts/` 최상위 이름이 정확히 `cli.py`와 `filmcraft/` 둘이다.
- `sys.path`를 편집하지 않는다.
- import 방향을 지킨다(기능 → 시스템 → 공용).
- 유닛 내부를 직접 import하지 않는다(테스트 파일 포함).

**사실 회귀 테스트** (`tests/filmcraft_facts/test_facts.py`) — 각 테스트의 docstring에 지키는 스킬 문장의 파일과 섹션을 쓴다.
1. `--save` 없이 하면 편집이 소실된다.
2. 실패한 `run`(`--keep-going` 없음)은 저장하지 않는다.
3. `--brige=…` 같은 모르는 옵션은 무시되고 빈 세션으로 돈다.
4. `timeline.razor {"time":3.5}`는 `cuts:0`이다.
5. 기본 캡션 폰트가 Inter이고, 한글 렌더가 명시 한국어 폰트와 다르다.
6. 내보내기 기본값은 자막을 번인하지 않는다.
7. 기본 range는 In/Out이다.
8. `removePauses`는 keep을 양쪽에 남긴다(남는 공백 ≥ 2×keep, 프레임 정렬 결과와 정확히 일치, 1프레임 이하 구간은 그대로).
9. `createCaptions`가 문장 중간에서 끊는다.
10. `captions.import`는 관대하고 `captions.add`는 겹침을 거부한다.
11. `transcript.generate`가 이 빌드에서 비활성이다.
12. 캡션 크기가 프레임 높이에 비례한다.
13. MP4는 moov가 끝에 있고 elst가 있다.
14. `newSequenceFromClip`은 V1/A1만 만든다.
15. `loudnessLufs` 결과가 ±0.5 LU 안에 든다.
16. `clip.audioGain`의 기본 mode는 adjust다.
17. 한국어 `tts.create`는 거의 무음이다.

**실행**: 레포 루트에서 `uv run --with pytest --with pillow pytest`. `pytest.ini`의 `pythonpath`로 패키지를 찾는다(스킬 코드는 `sys.path`를 건드리지 않는다).

## 구현 단계 (TaskCreate 트래커. description에 아래 완료 판정을 그대로 쓴다)

| # | 단계 | 완료 판정 |
|---|---|---|
| 0 | 계획 파일 이름 변경 | `.claude/plans/filmcraft-skill.md`가 있고 원본 경로에는 없음 |
| 1 | CLI 설치 | `~/.local/bin/filmcraft-cli --version`이 `filmcraft-cli 0.7.2`이고, SHA256이 SHA256SUMS.txt와 일치 |
| 1a | `.gitignore` | main에서 `.tmp/etc/` 한 줄 추가 → `chore: .tmp/etc 테스트 영상 폴더 무시` 커밋·푸시. `git status`에 `.tmp/etc/`가 더는 안 보임 |
| 1b | 실촬영본 수집 | `.tmp/etc/`에 유형별 1개 이상(①음악 1곡+여러 클립 ②한국어 자연 발화 혼잣말 토킹헤드 ③HDR 영상(유튜브 VP9.2/AV1 HDR) ④노출·색이 틀어진 영상 ⑤30분 이상 긴 영상, 아이폰 원본은 있으면). `.tmp/etc/SOURCES.txt`에 파일명·URL·라이선스/출처·받은 날짜·ffprobe 요약을 기록. 각 파일이 `filmcraft-cli probe`로 열림(열리지 않으면 그 자체를 사실로 기록) |
| 1c | 새 유형 기준선 대조 실험 | 계획 세션과 같은 격리 방식(`--safe-mode --restricted`, Bash·파일 도구, `FILMCRAFT_DATA_DIR` 격리)으로 유형별 1건씩: 음악 몽타주, 자연 발화 토킹헤드 컷·자막, HDR 소스의 세로 쇼츠, 실제 화면 색보정, 긴 영상 요약. 각 건의 비용·턴·헛걸음·결과물 결함을 "대조 실험의 차이" 표에 행으로 추가하고 자리(SKILL.md 절·번들 코드·뺀 이유)를 정함. 박자 감지 보류를 근거로 다시 판단하고, 번들 코드 목록이 바뀌면 성진님께 확인받은 뒤 계획을 갱신 |
| 2 | 브랜치 | `feat/filmcraft-skill`이 `main`에서 갈라져 나옴 |
| 3 | 테스트 골격·구조 테스트 | `pytest.ini`, `tests/filmcraft_skill/test_structure.py`가 있고, 빈 `scripts/cli.py`·`filmcraft/` 스텁 상태에서 구조 테스트 통과, 규칙 위반을 일부러 넣으면 실패(뮤테이션 확인) |
| 4 | `timeline` (TDD) | 실제 CLI로 만든 3트랙·클립 6개 프로젝트에서 상세 파일의 시작·끝 TC가 만든 입력과 일치. 300클립에서 stdout ≤ 2KB, 상세 파일은 300클립 전부. `--project`·`--bridge`를 함께 주면 exit 2. `--help`가 인자·출력·실패를 설명 |
| 5 | `qc` (TDD) | 대상별 기준표를 출처로 확정(플랫폼 길이 상한 포함). ffmpeg로 만든 통과·불통과·측정불가 파일에서 각 체크가 fail/warn/null을 기대대로 판정. fail이면 exit 3, 경고만이면 0. `--help`에 기준표 |
| 6 | `frames` (TDD) | `--at` 3개 → 3칸 시트, TC 라벨. `--overlay shorts`가 288/672/48/192 박스를 그림(픽셀 확인). `--media` 모드 동작. 브리지 사본 절차(`file.saveCopy` → frames)를 1회 실행 |
| 7 | `transcribe` (TDD) | 순수 코어 경계 사례 전부 통과(이동 상한, 0길이 금지, 순서 보존, 미대응 유지). 독립 기준 음성에서 스냅 후 오차가 줄어듦. JSONL을 `filmcraft-cli run`으로 적용한 뒤 `transcript.inspect`의 **모든 단어 텍스트·시간**이 JSONL과 일치(편집 안 한 시퀀스). `FILMCRAFT_TEST_WHISPER=1`로 실제 경로 1회 통과 |
| 8 | `captions` (TDD) | 손으로 푼 예제 전부 통과. 시간 좌표 테스트(트림·이동·배속·리플·재사용) 통과. import `warnings` 비어 있음. 기존 캡션 트랙이 없는 프로젝트와 다른 스타일 트랙이 있는 프로젝트 모두에서 생성 → import → `setStyle`(같은 스타일) → 렌더했을 때, 가장 긴 큐의 배경 박스 높이가 2줄 이하(픽셀 측정). 같은 전사(국회 영상 사본)에서 `transcript.createCaptions {maxChars:16, lines:2}`와 규칙 위반 수를 비교해, 이 명령이 확실히 적지 않으면 명령을 빼고 SKILL.md §8에 맞춘 `createCaptions` 값을 쓴다 |
| 9 | 사실 회귀 테스트 | 17개 통과(0.7.2). 각 docstring이 스킬 문장을 가리킴 |
| 10 | SKILL.md 작성 | 위 섹션 구조(§1~§15)를 충족하고, 한 덩어리가 한 줄. 약 200줄 이내(넘으면 커진 분기 절만 로드 시점 기준으로 reference 분리를 검토하고 성진님께 알림). 대조 표의 모든 행에 자리가 있음. 버전에 묶인 주장은 사실 테스트가 지키거나 "확인 방법"으로 쓰임. 분기 절(§8~§12, §15)의 첫 줄이 "언제 쓰나" |
| 11 | `.mcp.json` | 새 세션에서 `filmcraft` MCP가 승인 후 연결되고, 앱이 꺼져 있을 때 도구 호출만 실패하고 세션은 정상 |
| 12 | 검증 실행 | `claude plugin validate --strict .claude/skills` exit 0. 전체 pytest green(runner exit code). 각 `--help` 실행 확인 |
| 13 | 스킬 포함 재실험 | T1·T2·R1·R2와 단계 1c의 새 유형 과제를 스킬을 켠 격리 실행으로 다시 돌림. 비교 항목: 비용·턴, 헛걸음 소멸, `qc` 통과, 세이프존 준수, 자막 레이아웃 반복 없음. 개선이 없거나 나빠진 항목은 원인을 추적해 수정 |
| 14 | 독립 리뷰 | codex(`gpt-6.1-sol`, `high`)에게 스킬 전문 + 코드 + 테스트를 보내 네 속성(Principle over rail, Interface over document, For the model, Dense)과 계약을 리뷰받음. 지적은 재현해서 채택하거나 이유와 함께 기각 |
| 14a | 원칙 경계 확인 | 결정을 가르는 편집 원칙(필러 남기기, 직컷 vs 디졸브, 박힌 슈퍼 가리기 vs 피하기, 자막 위치 이동, 업스케일 허용 범위)마다 대조 실험에 쓰지 않은 사례나 조건 하나를 바꾼 사례를 만들어, 원칙이 내릴 결정을 성진님께 보여 주고 같은 판단인지 AskUserQuestion으로 확인. 갈리는 지점은 원칙의 경계 조건으로 반영 |
| 15 | 사용자 승인 | 전문(영어) + 한국어 요약을 제시하고, 전체 텍스트 승인을 받음. 승인은 텍스트에 대한 것이고, 여러 실제 세션에서의 성능 증거가 아님을 함께 밝힘 |
| 16 | 커밋·PR·머지 | 논리 단위 커밋(코드 유닛별, 문서, `.mcp.json`) → 푸시 → PR(한국어, 무엇을 바꿨나/왜/영향/검증, 개발 기록은 본문에) → `gh pr merge --squash`. 스테이징은 경로 지정만 |

## 검증 (end-to-end)

- **번들 코드**: `uv run --with pytest --with pillow pytest` exit 0. 실패를 먼저 본 기록과 뮤테이션 확인을 보고서에 남긴다.
- **스킬 형식**: `claude plugin validate --strict /Users/seongjin/Coding/video/.claude/skills` exit 0.
- **실제 진입점**: 다섯 명령 모두 `uv run "…/cli.py" <cmd> --help`와 실제 실행을 1회씩 한다(국회 영상 사본으로 transcribe→captions→frames→qc 연쇄).
- **스킬 효과**:
  - 스킬을 켠 격리 `claude -p`로 T1·T2·R1·R2를 다시 돌린다.
  - 결과물을 `qc`로 검수하고 프레임 시트로 확인한다.
  - 스킬 없는 기준선과 비용·턴·실패를 비교한다(수치는 PR 본문에).
- **영속성**: 각 재실험 결과물의 `.fcproj`를 새 프로세스로 열어 `timeline` 요약이 보고서와 일치하는지 확인한다.
- **브리지**:
  - 사용자 동의를 받고 앱을 `--control`로 띄운다(`--data-dir`는 임시 폴더).
  - `filmcraft-cli --bridge`, `timeline --bridge`, `captions --bridge`, MCP `ui_screenshot`·`render_frame`을 1회씩 확인한다.
  - 앱에 미저장 편집을 만든 상태에서 `file.saveCopy` → `frames`가 앱 상태를 그리는지 확인한다.
  - 끝나면 앱을 원래 상태로 되돌린다.
- **스킬 포함 재실험 방법**: 스킬은 프로젝트 `.claude/skills`에서 로드되므로, 각 실험 폴더에 `.claude/skills/filmcraft` 심볼릭 링크를 두고(`.mcp.json`은 두지 않음) 돌린다. `--safe-mode`는 스킬을 끄므로 쓰지 않고, `--restricted`와 `--tools`로 격리한다. 전사에서 `Skill` 도구 호출로 스킬이 실제로 쓰였는지 확인한다.
- **독립 리뷰**: 단계 14의 리뷰 결과와 처리 내역을 보고한다.

## Git

- **브랜치**: `feat/filmcraft-skill`
- **커밋 예**:
  - `feat: filmcraft 스킬 번들 코드 골격과 구조 테스트`
  - `feat: timeline 요약 명령`
  - …
  - `docs: filmcraft SKILL.md`
  - `feat: 브리지 MCP 등록`
- **PR 제목**: `feat: FilmCraft 편집 스킬 추가`. 본문 섹션은 무엇을 바꿨나 / 왜 / 영향 / 검증이고, 검증에는 실행한 명령과 수치를 쓴다.
- **개발 기록(PR 본문)**: 대조 실험 표, 버린 대안(명령 래퍼, 헤드리스 MCP, 박자 감지 보류 이유), 기준 모델·버전·날짜.
- **스테이징**: `git add .claude/skills/filmcraft tests pytest.ini .mcp.json`처럼 경로를 지정한다. `-A`, `.`는 금지(`.tmp/etc` 영상, `.claude/plans`). `.gitignore`의 `.tmp/etc/`는 단계 1a에서 main에 따로 커밋한다.

## skill-maker 준수 대조표

skill-maker 원문의 요구를 하나씩 이 계획의 위치에 맞췄다. 구현이 끝나면 단계 14의 리뷰어에게도 이 표를 함께 보낸다.

| skill-maker 요구 | 이 계획에서 |
|---|---|
| 모델이 이미 하는 것은 빼고, 기본값과의 차이만 이유와 함께 담는다 | 대조 실험 6건과 단계 1c의 새 유형 실험, "차이 → 자리" 표, '넣지 않음' 행 |
| Principle over rail: 이유·조건·뒤집히는 조건, 금지는 이유보다 강하지 않게 | §7 원칙마다 이유와 뒤집히는 조건(직컷 예외 등), 쓰기 규칙 |
| Interface over document: 도구가 소유한 것은 도구에 | 명령 사양은 `describe`, 숫자 규칙은 `captions`·`qc`·`frames --help`, prose엔 언제·경계·실패만 |
| For the model, not the maintainer | 쓰기 규칙: 출처 표시 금지, 개발 기록은 PR 본문 |
| Dense / 클라이언트 소유 값은 실패로 쓴다 | 쓰기 규칙, 약 200줄 예산, 사실 테스트가 버전 묶인 문장을 지킴 |
| 기본값을 고치는 줄은 피할 행동을 구체적으로 | §7 규칙: "컷어웨이마다 디졸브", "기계적 순환" 같은 행동명 |
| 새 스킬이 이웃 스킬에 주는 비용, 경계 | skill-doctor 실행(겹침 없음), description에 "Not for developing FilmCraft" |
| 사용자가 아는 것 끌어내기(대조·구체 사례·권위 구분) | 비전문가 → 공개 표준·플랫폼 사양·코드를 근거로, 권위 종류 표시, 취향은 결과물로 확인 |
| 다듬은 원칙은 새 사례로 경계 확인 | 단계 14a 원칙 경계 확인 |
| 못 정하는 것은 AskUserQuestion으로 합의, 원장 유지 | 이번 세션 질문 묶음 다수, "결정 요약"·"부록: 근거 원장" |
| 위치·언어 결정 | 프로젝트 스킬 `.claude/skills/filmcraft`, 영어 |
| 원칙은 이유·조건·뒤집힘·가르는 사례, 예시는 차이를 보일 때만 | §7 규칙 |
| 완료를 확인 가능한 말로, 지킬 것과 자유로운 것을 구분 | §1 |
| 지식은 작동할 곳에(계산·검증 계약은 인터페이스로), 모델이 직접 하는 일을 감싸지 않음 | 번들 5개는 FilmCraft에 없는 일만, 명령 래퍼 없음, `createCaptions`와 비교해 못 이기면 `captions`를 뺌 |
| 파일은 필요해지는 시점으로 나눈다 | 분할 원칙: 분기 지식이 작아 SKILL.md 하나로 합침(사용자 결정), 커지면 그 절만 로드 시점으로 분리 |
| 코드 트리: `cli.py` 하나, 스킬 이름 패키지 하나, 기능·시스템·저장소 유닛, `data/`, 레포의 `tests/` | 디렉토리 구조(`data/` 없음 = 상태 없음), 유닛과 의존 방향 |
| `uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py"` + allowed-tools 같은 표기, PEP 723 | 공통 규칙, frontmatter |
| `cli.py`는 표면만, 결정은 유닛에; `--help` 두 단계가 각각 자족적 | 공통 규칙 |
| stdout은 JSON 한 문서, 싼 신호 먼저, 큰 상세는 고유 핸들; stderr는 진행; 0/2, 그 외는 `--help`가 정의 | 공통 규칙, `timeline` 상세 파일 핸들, `qc` exit 3 |
| 외부 시스템 형식은 그 이름의 유닛 하나에, import는 한 방향 | 시스템 유닛 `filmcraft_cli`·`whisper`·`ffmpeg`·`mp4`, 구조 테스트 |
| 테스트·유지보수 코드는 스킬 밖 레포에, 구조 테스트가 트리를 지킨다 | `tests/filmcraft_skill`(구조 테스트 포함), `tests/filmcraft_facts` |
| 완료: 전체 텍스트 승인, 성능 증거로 내세우지 않음 | 단계 15 |
| 완료: `claude plugin validate --strict` (스킬 폴더의 부모) | 단계 12: `.claude/skills` |
| 완료: 코드가 자기 계약대로 검증되고 `--help`가 일치 | 단계 4~8 완료 판정, 단계 12 |
| 완료: 다른 계열 리뷰어가 네 속성으로 초안 검토, 무조건 수용하지 않음 | 단계 14(codex `gpt-6.1-sol` high), 계획 리뷰 반영 내역의 채택·부분 채택 기록 |
| 완료: 개발 기록은 스킬 밖 | PR 본문(사용자 결정) |

## 수용한 가정 (구현 때 확인)

- 넷플릭스 규칙을 한국어 유튜브 자막의 기본값으로 쓴다. 공식 한국 방송 기준에는 글자 수 수치가 없다.
- 세로 공통 안전 박스(x 120~780, y 290~1150)는 조사 에이전트의 권고다. 공식 수치는 광고 기준뿐이다.
- 한국 방송 트루피크 상한은 미확인이다. `qc broadcast-kr`는 I만 강제하고 TP는 -1 dBTP를 경고로만 둔다.

## codex 계획 리뷰 반영 내역 (gpt-6.1-sol, high, 2026-10-14 09:10)

리뷰어는 FilmCraft 소스로 사실 다섯 가지를 확인했다. 캡션 크기 배율, 전사의 미디어→시퀀스 시간 변환, 기본 In/Out 내보내기 범위, `burnCaptions` 기본값 false, 새 스키마 거부. 지적 8건은 모두 소스로 재확인해 채택했다.

| # | 등급 | 지적 | 처리 |
|---|---|---|---|
| 1 | major | `captions`의 스타일 계약 부재. import는 기본 스타일 새 트랙을 만들고, 번인은 실제 폰트 폭으로 다시 줄을 바꾼다 | 채택: font·size·margin·anchor를 인자로 받아 결과에 반환하고 `next`에 `setStyle` 포함. 폭은 같은 폰트로 측정. 렌더 실측을 완료 판정에 추가 |
| 2 | major | 스냅 안전 조건 부재(0길이·이동 상한) | 채택: 상한·구간 단위·`start<end`·순서·미대응 유지를 계약에 넣음. 독립 기준 음성 테스트 추가 |
| 3 | major | `timeline` 40KB 기준이 필드 계약과 모순(클립당 197B) | 채택: stdout은 요약, 상세는 파일 핸들 |
| 4 | major | `--project`/`--bridge` 우선순위 없음, 라이브 상태 경로 없음 | 채택: 둘 중 하나만 받음. `frames`·`qc`는 `file.saveCopy` 사본으로. 불일치 수용 테스트 추가 |
| 5 | major | QC 판정·허용오차·측정불가·반복 종료 계약 부재 | 채택: fail/warn/null 체계, 기준표 초안, 재내보내기 최대 2회, 기술 QC와 편집 검수를 분리 |
| 6 | major | 시간 좌표·큐 유실·영속성 검증 부재 | 채택: 트림·이동·배속·리플·재사용 시간 테스트, import 전후 보존·warnings, 새 프로세스 재개방 |
| 7 | minor | prose가 인터페이스를 복제(describe 사용법, 숫자 규칙)하고 금지에 예외 없음 | 부분 채택: describe 사용법·params 표기와 자막 숫자 규칙 삭제(`captions --help` 소유), 직컷 원칙에 뒤집히는 조건 추가. **유지**: `clip.audioGain` 기본 adjust처럼 `describe`에 기본값이 안 나오는 함정, 조용한 실패 형태 |
| 8 | minor | `removePauses` 공백 = 2×keep은 부정확(프레임 정렬) | 채택: "최소 2×keep, 정렬로 더 남을 수 있음, 1프레임 이하는 그대로"로 고치고 사실 테스트를 독립 계산과 비교 |

구현 단계 14에서 같은 리뷰어(스레드 이어가기)로 스킬 전문·코드를 다시 리뷰받는다.

---

## 부록: 근거 원장

### 사실 (실측·코드 근거)
- 설치: `/Applications/FilmCraft.app` 0.7.2 (build 71438c6). `filmcraft-cli` 미설치, Rust 툴체인 없음. 릴리스 v0.7.2에 `filmcraft-cli-0.7.2-macos-universal.zip` 존재.
- 소스 `.tmp/filmcraft` = 0.7.2. 받은 CLI의 `help` 출력이 소스 `HELP` 상수와 글자 단위로 동일.
- 릴리스 주기 1~2일 (v0.2.1 10/06 → v0.4.0 10/08 → v0.5.0 10/10 → v0.6.0 10/11 → v0.7.2 10/12).
- 명령 700개. `commands --json` 159k자, MCP `command_list` 무필터 223KB. 항목 필드: id, label, menu, params(자유 텍스트 의사 스키마), shortcut(s), defaultShortcut, enabled(선택 상태 기준, 사유 없음).
- `--save` 없이 `exec file.newSequenceFromClip` → exit 0과 새 ID를 반환하지만, 다음 호출에서 시퀀스가 없다.
- 헤드리스는 자동저장·복구 저널이 없고 사용자 환경설정도 읽지 않는다(`apps/filmcraft/src/main.rs:207`만 `start_autosave`). MCP 헤드리스도 종료 시 저장하지 않는다. 앱 세션은 `<data-dir>/Auto-Save`, `Recovery`를 쓴다.
- 한글: 기본 폰트로 쓰면 `graphics.newText`·캡션 모두 "NO GLYPH" 상자다(한자는 craft-fonts로 정상). `font:"Noto Sans KR"`/`"Apple SD Gothic Neo"`를 지정하면 정상이다. 폴백은 bundled → craft-fonts → 이미 로드된 face 순서다(`crates/text/src/fonts.rs:464`). `captions.setStyle`에 `font`가 있다(`crates/engine/src/captions.rs:299`, captions.md 문서에는 누락).
- `render`/MCP `render_frame`은 캡션을 그리지만 `file.exportMedia` 기본값은 `burnCaptions:false`다.
- 내보내기:
  - 1080p29.97 25초에 12~17초 걸린다(CPU 렌더, 소프트웨어 H.264).
  - `loudnessLufs:-14`를 주면 결과가 -14.0 LUFS다.
  - MP4는 moov가 끝에 있고 `edts/elst`가 있다.
  - 브리지(앱) 3초 내보내기는 0.8초다.
- 세로 시퀀스에 16:9 클립은 원본 크기로 놓인다. `clip.fillFrame`을 쓰면 scale 177.8%가 된다. 회전 메타데이터가 있는 HEVC 10bit 폰 영상은 정상이다.
- CLI 호출 오버헤드는 300클립에서도 0.2초 미만이다. 그러나 `inspect sequence`는 527KB(compact), MCP `sequence_inspect`는 1.35MB다.
- 조용한 실패: `timeline.razor {"time":3.5}` → `cuts:0`. 없는 클립에 `effects.apply` → `null`(isError false). 모르는 CLI 옵션은 무시된다(`mcp`만 검사).
- 코드 조사(Explore 3건):
  - **시간**: `time`(정수) > `frame` > `seconds` > `timecode` 순서이고, 타입이 틀리면 '없음'으로 처리된다. timecode는 시작 TC를 무시한다. markOut은 그 프레임을 포함한다.
  - **대상**: params 문서에 `clips`/`items`가 있을 때만 선택 대신 ID를 받는다.
  - **razor**: 대상이 없으면 전 트랙을 자르고, 오른쪽 조각은 새 ID다. undo는 ID까지 복원한다.
  - **그래픽**: `graphics.*` track은 인덱스다.
  - **내보내기**: 기본 range는 In/Out이고, 기본 스케일링은 ScaleToFit이다.
  - **오디오**: `audioGain` 기본은 adjust다. 라우드니스 조회·무음 감지 명령은 없다.
  - **기타**: `speedDuration`은 reverse를 빼면 역재생이 해제된다. 시간 리맵은 렌더되지 않는다.
  - **TTS**: 영어 로봇 음성뿐이고, 한국어는 거의 무음이다.
  - **미지원**: HEIC, EXIF 회전, Dolby Vision 메타데이터.
- mlx-whisper(large-v3-turbo, 한국어):
  - 합성 25초 음성: 정확하고 필러도 잡지만, 단어 시간이 최대 0.3~0.4초 어긋난다.
  - 실촬영 8:43: 약 2분, 197구간·995단어. 고유명사 오인식이 있다(김앤장→김현장, 사전 통지→사전 통제).
- 전사 파이프라인 실측: `transcript.set` → `removeFillers {"fillers":["음","어"]}` → `removePauses {0.5, 0.15}` → `createCaptions` → `setStyle font` 동작. 24.9초가 18.5초로 줄었다.
- `captions.import`: 붙은 자막을 허용하고, 겹침은 잘라 맞추고, 20ms 자막은 1프레임으로 늘린다.
- 브리지:
  - 일반 실행된 앱에는 포트가 없다.
  - `open -a FilmCraft --args --control 9876 …` → 4초 뒤 포트가 열린다.
  - `--bridge` exec/import/inspect/export는 정상이다. 명시 `items`도 브리지에서 동작한다.
  - **경로 없는 프로젝트에 `--save` → 저장 대화상자 → 모든 요청 timeout.** Esc(System Events key code 53)로 풀었다.
  - `render`는 브리지를 거부한다. 창 스크린샷은 3200×1960, 25MB다.
- 새 스키마 거부: 앱보다 새 CLI가 쓴 프로젝트(schema_version 상승)는 구버전이 열지 못한다(codex 리뷰가 소스로 확인) → SKILL.md §2에서 버전을 맞추는 근거.
- 이웃 스킬(skill-doctor): interview, codex, coding, skill-maker, ultra-search. 겹침 없음.
- 레포: origin `github.com/tjdwls101010/Claude-Video`, main, PR 템플릿 없음.

### 대조 실험 요약 (스킬 없는 Opus 5.5, 격리 `claude -p`)

| 과제 | 비용·턴 | 잘한 것 | 부족·헛걸음 |
|---|---|---|---|
| T1 토킹헤드(합성) | $1.13·40 | mlx-whisper 자력 설치, 타이밍 보정, 폰트 지정 | STT 모델 970MB 헛다운로드, keepSeconds 시행착오, 자막 재배치·겹침 오류, 폴더 밖 쓰기 |
| T2 세로 릴스(합성) | $0.57·31 | 30fps 박 정렬, fillFrame, 컷 위치 측정 | 라우드니스 없음, 상단 UI 영역 타이틀, 기계적 순환 |
| T3 B-roll·더킹(합성) | $0.45·18 | Essential Sound 더킹, 라우드니스 측정 | 컷어웨이 디졸브 |
| T4 색·납품(합성) | $1.18·33 | scopes.read, FCP7 XML 인계 | 테스트 패턴 LUT 역산, ffmpeg faststart 리먹스 |
| R1 세로 쇼츠(국회) | $1.36·42 | 말하는 쪽 크롭, ASR 교정, 로고 가림 | 캡션 크기 배율 몰라 렌더 3회, 쇼츠 하단 UI 침범 |
| R2 3분 요약(국회) | $1.33·42 | 14컷 선별, 크로스페이드, 교정 46자막 | `captions.add` 겹침, MP4 챕터 리먹스 |

### 공개 표준 (ultra-search, 원문 인용 확인)
- **YouTube 권장 업로드**(support.google.com/youtube/answer/1722171):
  - 컨테이너: MP4, Edit List 없음, Fast Start
  - 영상: H.264 High·B 2·closed GOP=fps/2, VBR, 원 fps, BT.709
  - 오디오: AAC-LC 48kHz, 128/384/512 kbps
  - 비트레이트: 1080p 8/12 Mbps, 4K 35~45/53~68
- **YouTube 라우드니스**: 공식 수치 없음. 측정상 약 -14 LUFS로 큰 소리만 낮춘다. 릴스·틱톡도 공식 수치 없음.
- **한국 방송**: -24 LKFS ±2dB(방송미디어통신위원회고시 제2026-17호 제3조).
- **세로 세이프존**:
  - Meta: 14%/35%/6%
  - TikTok: 240/660/120px + 버튼열
  - Shorts 광고: 288/672/48/192px
- **넷플릭스 한국어 자막**: 16자(라틴 등 0.5), 2줄, 12cps, 5/6~7초, 줄 끝 마침표·쉼표 금지, U+2026. 방통위 가이드는 최대 2줄, 오탈자 2% 이내.

### 대조 실험 재현 방법 (단계 1c·13용, 이번 세션의 scratchpad는 다음 세션에서 사라짐)
- 과제 폴더 하나 = `task.md`, `media/`(입력은 `cp -c`로 APFS 복제), `out/`, `.fcdata/`. `--restricted`는 파일 도구를 작업 폴더로 가두므로 입력은 반드시 폴더 안에 둔다.
- 과제 문장 끝에 붙인 공통 문단: "도구: 이 맥에는 FilmCraft(어도비 프리미어 프로를 클론한 오픈소스 영상 편집기)가 설치되어 있고, 그 CLI `filmcraft-cli`가 PATH에 있어. ffmpeg/ffprobe도 있어. FilmCraft GUI 앱은 띄우지 말고 CLI로 작업해. 끝나면 무엇을 했고 결과물이 어디 있는지 짧게 보고해."
- 기준선(스킬 없음):
  `cd <과제 폴더> && FILMCRAFT_DATA_DIR="$PWD/.fcdata" claude -p --safe-mode --restricted --strict-mcp-config --tools Bash Read Write Edit Glob Grep --allowedTools Bash Read Write Edit Glob Grep --permission-mode acceptEdits --model opus --max-budget-usd 30 --output-format json "$(cat task.md)" > result.json 2> stderr.log`
- 스킬 포함(단계 13): 같은 명령에서 `--safe-mode`를 빼고, 과제 폴더에 `.claude/skills/filmcraft` → 레포 스킬 심볼릭 링크를 둔다. 전사에서 `Skill` 호출을 확인한다.
- 분석: `result.json`의 `total_cost_usd`·`num_turns`·`permission_denials`·`session_id`. 과정은 `~/.claude/projects/*/<session_id>.jsonl`의 `tool_use`/`tool_result`를 순서대로 뽑아 헛걸음·반복 손작업·오류를 본다. 결과물은 `qc`·`frames`(구현 후) 또는 ffprobe·ebur128·프레임 추출로 검수한다.
- 이번 세션 과제 문장 원문 (공통 문단 앞에 둔다. 합성 미디어는 ffmpeg/`say`로 다시 만든다: `talk_ko.mp4` = smptehdbars 1080p29.97 + `say -v Yuna`로 만든 한국어 음성(무음 `[[slnc ms]]`·"음/어" 포함), `broll_a/b/c` = testsrc2·mandelbrot·life 8초, `music_120bpm.wav` = aevalsrc 120bpm 60초, `edit.fcproj` = 채도·대비를 낮춘 talk+broll):
  - T1: "`media/talk_ko.mp4`는 내가 한국어로 혼자 말하는 영상이야. 말 사이에 늘어지는 공백이랑 "음", "어" 같은 군더더기를 잘라서 템포를 살리고, 한국어 자막을 달아서 유튜브에 올릴 수 있게 `out/`에 내보내 줘. 나중에 내가 FilmCraft에서 열어 손볼 수 있게 프로젝트 파일도 `out/`에 남겨 줘."
  - T2: "`media/`에 있는 B-roll 세 개(`broll_a.mp4`, `broll_b.mp4`, `broll_c_noaudio.mp4`)와 음악 `music_120bpm.wav`로 인스타 릴스용 15초짜리 세로 영상을 만들어 줘. 음악 박자에 맞춰 컷이 넘어가게 하고, 화면 위쪽에 "오늘의 하이라이트"라는 타이틀을 넣어 줘. 결과 영상과 FilmCraft 프로젝트 파일을 `out/`에 남겨 줘."
  - T3: "`media/talk_ko.mp4`(내 한국어 내레이션)를 중심으로, 말하는 중간중간 `broll_a.mp4`, `broll_b.mp4`를 컷어웨이로 덮고, `music_120bpm.wav`를 배경음악으로 깔되 내가 말할 때는 음악이 작아지게 해 줘. 화면 전환은 자연스럽게. 유튜브용으로 `out/`에 내보내고 FilmCraft 프로젝트 파일도 남겨 줘."
  - T4: "`proj/edit.fcproj`는 거의 완성된 FilmCraft 편집본이야. 화면 색이 좀 칙칙하니 보정해 주고, 유튜브 업로드 사양에 맞춘 마스터 파일을 뽑아 줘. 그리고 프리미어 프로에서 이어서 작업할 수 있게 넘겨줄 파일도 만들어 줘. 결과물은 전부 `out/`에."
  - R1: "`media/국회 회의 영상.mp4`는 국회 국정감사 질의 영상이야. 여기서 가장 임팩트 있는 질의 장면 하나를 골라 50초 안팎의 유튜브 쇼츠(세로 영상)로 만들어 줘. 말하는 사람이 잘 보이게 화면을 잡고, 자막은 크게, 화면 위쪽에 내용을 요약하는 제목 한 줄을 넣어 줘. 결과 영상과 FilmCraft 프로젝트 파일을 `out/`에 남겨 줘."
  - R2: "`media/국회 회의 영상.mp4`(국회 국정감사 질의 영상)를 유튜브에 올릴 3분 이내 요약본으로 만들어 줘. 핵심 질의응답만 남기고, 한국어 자막을 넣고, 주제가 바뀌는 곳에 챕터 마커를 달아 줘. 결과 영상, 자막 파일, FilmCraft 프로젝트 파일을 `out/`에 남겨 줘."
