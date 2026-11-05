# `video` 스킬: FilmCraft 편집 + 코드로 만드는 그래픽·모션 그래픽 — 구현 계획

> 계획 모드가 지정한 경로라서, 승인 직후 첫 동작으로 이 파일을 `.claude/plans/video-graphics.md`로 옮긴다(구현 단계 0). 계획 모드에서는 지정 경로 밖에 쓸 수 없다.

## Context

- `.claude/skills/filmcraft`는 FilmCraft(프리미어식 오픈소스 편집기, 0.7.2)를 CLI로 다루는 프로젝트 스킬이다(PR #1, skill-maker 프레임). 실제 4일차 숏츠 작업(10/14)에서 사용자와 의논하며 편집하는 리듬은 잘 작동했다.
- 성진님 목표: 편집 중 "여기에 이런 그래픽·효과"가 필요할 때, Claude가 그 그래픽을 **코드로 창작**해 렌더하고 FilmCraft 타임라인에 얹는 역량을 더한다. FilmCraft 네이티브 그래픽도 가능하지만 Claude의 코드 창작 능력을 최대한 쓰고 싶다. 영상 소스 없는 단독 모션 그래픽 영상도 같은 길로 만든다. 효과음도 코드로 만든다.
- 스킬은 여러 사용자가 쓴다. 각자의 방법·취향은 스킬 본문이 아니라 각 사용자의 `data/`에 쌓인 과거 결과물에서 읽고, Claude는 자기 미적 판단을 살려 제안하되 결정은 사용자를 따르는 동료로 남는다. Claude가 이미 잘하는 것(디자인, 말에 맞춘 타이밍, 문구 충실성)은 쓰지 않는다.
- 범위가 FilmCraft 조작에서 영상 제작 전반으로 넓어져 스킬 이름을 `video`로 바꾼다.
- 성공 기준은 품질 하나. 기존 스킬은 유지하고(전면 재작성 불필요: 실제 세션에서 잘 작동), 기준선 대조에서 드러난 차이만 더한다.

## 결정 요약 (이번 세션, 성진님 결정)

| 항목 | 결정 |
|---|---|
| 코드/네이티브 경계 | 디자인되는 그래픽(타이틀·로워서드·콜아웃·숫자·데이터 그래픽·자료 화면 연출·인트로·그래픽 전환 요소·그라디언트 바 같은 레이아웃 요소)은 코드. 움직이지 않는 것은 정지 PNG. FilmCraft는 컷·타이밍·배치·트랙 순서, 영상 픽셀을 다루는 것(뒤 화면 블러·크롭·리프레이밍·색), 소리, 샷 사이 전환, 자막. 사용자가 FilmCraft에서 직접 고치고 싶어 하는 그래픽은 네이티브 |
| 렌더러 | 번들 렌더 명령 `graphic`(Playwright + 설치된 Chrome + ffmpeg). HyperFrames 의존 없음 |
| `data/` | 사용자별 작업 기록. 사용자마다 자기 `data/`(git 제외). 별도 선호 메모 없이 과거 결과물(프로젝트·그래픽 HTML·최종 영상)이 취향의 기록 |
| 작품 폴더 구조 | 4일차 폴더(`원본/소스/레퍼런스/vrew`)는 그 작품에 맞춘 분류라 관례로 삼지 않는다. `data/<작품>/` 루트에 FilmCraft 프로젝트와 결과물(최종 영상, 딸린 자막·인계 파일), 그리고 `assets/`(가져온 재료), `graphics/`(코드 그래픽의 페이지와 렌더, 지우지 않음), `etc/`(그 밖: 다른 도구 파일, 다시 쓸 작업 파일; 일회용 파일은 끝날 때 지움). `results/`는 두지 않는다("결과물은 1개"). `data/assets/`의 공용 재료는 작품의 `assets/`로 복사(APFS 복제)해 작품 폴더만으로 프로젝트가 열리게. `FilmCraft Previews/`는 FilmCraft가 프로젝트 옆에 자동으로 만든다 |
| 장르 | 장르별 만드는 법은 레일이라 쓰지 않는다. 영상마다의 결정은 사용자와 Claude가 대화로 한다. 원칙이 갈리는 경계 사례(단어 단위 자막 애니메이션, 영상 속 물체를 따라가는 강조 등)도 규칙을 쓰지 않고 그 자리에서 이유와 함께 고르거나 묻는다(기존 "Working with the user") |
| 기준선 검토 | 스킬 없는 결과 3건(g1–g3)에 "어떤 영상이든 틀렸다"고 볼 문제는 없고 취향 차이뿐(성진 판정). 그래서 스킬에는 렌더 도구, 실측 사실, 경계 원칙만 들어간다 |
| 스킬 위치 | 프로젝트 스킬 유지(`.claude/skills/video`, 다른 프로젝트엔 심볼릭 링크, 다른 사용자는 레포 클론). `data/`는 스킬 폴더 안(git 제외). 플러그인 배포는 실제로 나눌 때 따로 |
| 이웃 경계 | `🐝Work`의 k-politics와 트리거가 겹칠 수 있으나 그대로 둔다(성진님은 보통 `/video`로 직접 부름). video 자신의 description 경계 문장은 유지 |
| 기술 조건의 범위 | 스킬 내용이 숏츠의 조건(세로·30fps·SDR)을 전제하지 않는지는 Claude 실험을 늘리지 않고 `graphic` 테스트로 확인한다: 23.976·25·29.97·59.94 fps, 1920×1080·1080×1920·1080×1080·3840×2160, HDR(HLG) 시퀀스 |
| 일반 그래픽 원칙 | 넣지 않는다("이미 클로드가 충분히 이해하는 규칙"). 기준선에서 드러난 차이만 |
| 범위 추가 | 효과음을 그래픽과 같은 페이지에서 Web Audio로 합성. 단독 모션 그래픽 영상 포함. 디자인 자막 경로·쇼츠 썸네일 잘림 영역은 이번 범위 밖 |
| ffmpeg 예외 규칙 | 새 예외 조항을 쓰지 않는다("대화하며 Claude가 충분히 대처"). 기존 "편집은 FilmCraft에서만, ffmpeg는 측정만" 문장은 `graphic` 렌더를 금지하는 것으로 읽히지 않도록 범위만 "영상·소리의 편집"으로 좁힌다 |
| 스킬 이름 | `filmcraft` → `video`. 이름 변경만 담은 refactor 커밋을 먼저. Obsidian/Work의 링크도 새 경로로 |
| 그대로 이어받는 이전 결정 | 프로젝트 스킬, SKILL.md는 영어(승인 때 한국어 요약 동봉), 파일 분할은 로드 시점 기준이되 작으면 합침, 개발 기록은 커밋·PR 본문, 헤드리스 기본·브리지 선택, 사실 회귀 테스트 유지 |
| codex | 검증·리뷰는 `gpt-6.1-sol`, effort `medium`. Agent로 대체할 때는 `sonnet` |
| 시스템 유닛 이름 (구현 중 결정, 10/15) | `filmcraft_cli/` → `filmcraft/`. 패키지가 `video`라 `filmcraft.filmcraft` 충돌 이유가 사라짐. 별도 refactor 커밋 |

## skill-maker 원문 대비 감사 (성진님 지적 후, 2026-10-14)

첫 계획 제출 때 빠졌던 skill-maker 요구와 그 처리:

| skill-maker 요구 (원문) | 빠졌던 것 | 처리 |
|---|---|---|
| "have a Claude with no skills … attempt them, **show the user the result, and follow each objection down to its reason**" | 기준선 g1–g3를 혼자 분석만 하고 성진님께 보이지 않음 | 결과 영상을 보여 드림 → "어떤 영상이든 틀린 문제는 없고 취향 차이뿐"(성진). 차이는 렌더 인프라·사실뿐임이 확정 |
| "Before adding one, run `claude -p "/skill-doctor"`" | 구현 뒤(단계 11)로 미룸 | 계획 세션에서 실행: 레포는 겹침 없음, `🐝Work`는 k-politics와 겹칠 수 있음 → 성진 결정으로 그대로 둠. 단계 11에서 새 description으로 한 번 더 |
| "**Your phrasing is not their knowledge** … apply it to a case the extraction did not use … ask whether the user would decide the same" | 코드/FilmCraft 경계 원칙을 새 사례로 시험하지 않음 | 새 사례(펀치인 vs 이미지 안 확대, 단어 단위 자막 애니메이션, 영상 속 물체 위 강조, 자주 고치는 타이틀)로 판정을 보임 → 성진: 장르·사례별 규칙은 레일, 애매한 경우는 대화로. 원칙은 그대로 두고 애매한 경우는 규칙 없이 그 자리에서 이유와 함께 고른다 |
| "A principle carries … **a case where it decides between two similar-looking options**" | 경계 원칙에 판정 사례 없음 | 장르와 무관한 한 쌍(말하는 사람에게 다가가는 확대 = FilmCraft, 띄운 이미지 안의 확대 = 페이지)을 본문 경계 문장에 넣음 |
| "Where the skill will live (project, user or plugin) …" + "a skill shipped in a plugin keeps state … in the plugin's data directory" | 여러 사용자라는 새 전제에서 위치를 다시 묻지 않음 | 물음 → 프로젝트 스킬 유지(성진). `data/`는 스킬 폴더 안 |
| "Keep kinds of authority apart" | 새 문장마다 권위 종류를 표시하지 않음 | "권위 표시" 단락 추가 |
| "Starting from an existing skill … **Know which behaviors must survive before changing anything** … count deletion and consolidation as improvements" | 지켜야 할 기존 동작 목록과 삭제 검토가 없음 | "지켜야 할 기존 동작" 단락 추가(삭제 검토 결과 포함) |
| "Say how the model will know the work is done, in terms it can check. Separate what must be preserved from what the model is free to vary" | 그래픽의 완료 판정이 "프레임을 본다"뿐 | "Before you hand something over"에 확인 가능한 판정(FilmCraft 렌더에서 들어올 때·정점·나갈 때, `fallback`·`blocked` 없음, 페이지 보존)과 자유로운 것(디자인·움직임)을 넣음 |

## 기준선 대조의 차이 → 스킬 안의 자리

skill-maker 완료 조건("모든 차이는 자리가 있거나 뺀 이유가 기록된다")을 이 표로 지킨다. 근거는 부록 원장.

| 관찰 (출처) | 자리 |
|---|---|
| 같은 종류 요청에 네이티브 2건·HTML 1건으로 갈림, 네이티브 키프레임 경로가 시행착오(t1–t10·easetest)로 약 2배 비쌈 (g1·g2 vs g3) | SKILL.md Graphics 첫 줄: 경계와 그 이유(성진 결정). 실험 경위는 PR 본문 |
| 네이티브 그래픽은 FCP7 XML 인계로 넘어가지 않고, 렌더한 오버레이는 넘어감 (소스) | SKILL.md Graphics 경계의 이유 한 구절(선택을 바꾸는 인계 호환성 사실) |
| (사용자 결정) 취향은 각자의 `data/`에 쌓인 과거 결과물에서 읽는다 | SKILL.md Working with the user 한 줄 + 기본 저장 위치 |
| 렌더러를 처음부터 작성(`npm i puppeteer-core`) (g3) | `graphic` 명령 |
| 태그 없는 BT.601 인코딩 → FilmCraft가 BT.709로 읽어 빨강이 밝아짐, 재인코딩 (g3, 실측) | `graphic`이 BT.709 행렬로 변환하고 `setparams`로 primaries·transfer·matrix·range를 모두 기록(`-color_primaries` 출력 옵션만으로는 `unknown`으로 남음, 실측). 테스트가 지킴 |
| 없는 폰트·한글 없는 폰트가 조용히 대체됨(Chrome 실측: 없는 family의 한글 → AppleMyungjo, Inter의 한글 → Apple SD Gothic Neo) | `graphic`의 `fonts` 보고(실제로 그린 폰트) |
| 미리보기를 ffmpeg(sRGB) 합성으로 판단 (g3). 4일차 실제 세션이 그라디언트를 "60%에서 100%로 튀는 결함"으로 오진 | SKILL.md Graphics: FilmCraft 렌더로 판단(선형 광) + 사실 테스트 20 |
| 소리 있는 클립을 `timeline.place {"track":"new"}`로 얹으면 소리가 A1에 덮어쓰기로 들어가 대사가 잘림, exit 0 (실측) | SKILL.md "How the CLI fails quietly" 한 줄 + `graphic`의 `next`에 `"audioTrack":"new"` + 사실 테스트 21 |
| 같은 경로로 다시 렌더하면 헤드리스 render·export가 새 내용을 읽음 (실측) | SKILL.md Graphics: 원본 유지·제자리 재렌더 + 사실 테스트 22 |
| 효과음 없음(요청 없음) (g1–g3) | `graphic`의 소리(`window.renderAudio`) + SKILL.md Graphics 한 줄(성진 결정: 범위 포함) |
| 세 건 모두 단어 타이밍용 Whisper를 따로 설치 | **넣지 않음(새 내용)**: 기존 `transcribe`·`transcript.inspect`가 이미 해결 |
| `/tmp`·작업 폴더 밖 쓰기, Read 거부 (g1·g2·g3) | **넣지 않음(새 내용)**: 기존 "Working files" |
| 저해상도 캡처를 크게 확대해 흐림 (g1) | **넣지 않음**: 판단의 문제이고 프레임 확인으로 드러남. 기존 "Upscaling loses detail; say by how much" |
| 디자인·말에 맞춘 박자·얼굴 회피·문구 충실성·방송 자막 덮기 (g1–g3 잘함) | **넣지 않음**(성진 결정) |
| HEVC 알파는 불투명 렌더, QuickTime Animation·PNG-in-MOV는 못 읽음 (실측) | **넣지 않음**(성진: 대화 중 Claude가 대처). `graphic`은 늘 ProRes 4444를 낸다 |
| 이미지 시퀀스 기본 29.97df, 무태그 SD는 BT.601 (실측·소스) | **넣지 않음**: `graphic`이 시퀀스 fps의 MOV와 태그를 내므로 모델이 마주치지 않는다 |

## 구현 후 디렉토리 구조

```
/Users/seongjin/Coding/video/
├── .gitignore                         # + .claude/skills/video/data (사용자별, 미디어 포함)
├── .mcp.json                          # 그대로 (FilmCraft 브리지 MCP, 서버 이름 filmcraft)
├── pytest.ini                         # pythonpath = .claude/skills/video/scripts tests
├── README.md                          # 그래픽·효과음·단독 모션, graphic 명령, data/, 새 경로
├── tests/
│   ├── video_skill/                   # 이전 filmcraft_skill
│   │   ├── fixtures/
│   │   ├── test_structure.py          # PKG="video", KINDS에 graphic(feature)·chrome(system)
│   │   ├── test_transcribe.py  test_captions.py  test_timeline.py  test_frames.py  test_qc.py
│   │   └── test_graphic.py            # 신규
│   ├── filmcraft_facts/test_facts.py  # 이름 유지(FilmCraft 사실), 사실 20–24 추가
│   └── support/__init__.py            # SKILL_DIR → .claude/skills/video
└── .claude/skills/video/
    ├── SKILL.md
    ├── data -> (사용자 자신의 작업 폴더; git 제외. 성진: ~/💎Obsidian/.tmp/유튜브)
    └── scripts/
        ├── cli.py                     # 유일한 진입점. + graphic 하위 명령, PEP 723에 playwright 추가
        └── video/                     # 유일한 패키지 (stdlib에 video 없음)
            ├── __init__.py  timecode.py  errors.py          # 공용
            ├── filmcraft/  whisper/  mp4/                    # 시스템 (filmcraft_cli에서 개명)
            ├── ffmpeg/                                      # 시스템: + 알파 ProRes 인코딩·오디오 mux
            ├── chrome/                                      # 시스템(신규): Playwright로 설치된 Chrome 구동
            ├── transcribe/  captions/  timeline/  frames/  qc/   # 기능 (그대로)
            └── graphic/                                     # 기능(신규): 페이지 → MOV/PNG
```

- 레포 밖: `~/💎Obsidian/🐝Work/.claude/skills/video` → `/Users/seongjin/Coding/video/.claude/skills/video` (기존 `filmcraft` 링크 제거).
- `references/`는 만들지 않는다: 새 Graphics 절은 거의 모든 숏츠 작업(타이틀·그라디언트·자료 화면)이 지나는 경로라 로드 시점이 SKILL.md와 같고, 페이지 작성 계약은 `graphic --help`가 소유해 본문은 약 10줄이다.
- 사용자별 `data/`의 모양(성진 결정, SKILL.md "Working files"에 적는 관례):
```
data/
├── assets/                  여러 작품이 같이 쓰는 재료(로고·BGM·아웃트로 모음)
└── <작품>/                  예: 261013_국정감사 4일차
    ├── <이름>.fcproj         FilmCraft 프로젝트
    ├── <결과물>.mp4          내보낸 결과물(딸린 자막 파일·인계 파일도 여기)
    ├── assets/              가져온 재료: 원본·컷편집 영상, 음악, 로고, 레퍼런스(공용 재료는 복사해 옴)
    ├── graphics/            코드로 만든 그래픽: 페이지(HTML)와 그 렌더. 프로젝트가 재생하므로 지우지 않음
    ├── etc/                 그 밖: 다른 도구 파일(Vrew 등), 전사·자막 원고처럼 다시 쓸 작업 파일. 일회용(프레임 시트 등)은 끝날 때 지움
    └── FilmCraft Previews/  FilmCraft가 자동으로 만드는 렌더 캐시(결과물 아님)
```
- 이 관례는 기존 `<project>.work/` 규칙을 대신한다. 4일차 폴더를 새 구조로 옮기는 일은 이번 범위 밖이다(성진님이 원하면 프로젝트 미디어 경로 재연결과 함께 따로).

## SKILL.md 섹션 구조 (영어, 한 덩어리 = 한 줄, 약 170줄 예산)

표시: (유지) 그대로 / (수정) 문장 수정 / (신규) 새 내용. 새 문장은 기준선 차이 표의 행에 대응하는 것만.

**Frontmatter (수정)**
- `name: video`
- `description` (1024자 이내, `claude plugin validate --strict`로 확인):
  - 할 수 있는 일: FilmCraft(이 맥의 프리미어식 편집기, `filmcraft-cli` 헤드리스 또는 실행 중인 앱)로 영상을 만들고 편집하며, 그래픽·모션 그래픽을 코드(HTML/CSS/SVG/Canvas)로 만들어 편집에 얹는다: 컷·전사 기반 편집, 세로 숏폼, 몽타주, 타이틀·로워서드·콜아웃·데이터 그래픽·자료 화면·인트로와 효과음, 단독 모션 그래픽 영상, 오디오·라우드니스, 색, 한국어 자막, 검수된 내보내기, Premiere/Resolve 인계
  - 트리거: 영상 편집, 컷편집, 자막, 쇼츠, 릴스, 하이라이트, 몽타주, 모션 그래픽, 그래픽, 타이틀, 로워서드, 인트로, 효과음, 색보정, 내보내기, 유튜브 업로드용, .fcproj, FilmCraft
  - 경계: "Not for downloading, summarizing or transcribing a video without editing it, still images such as thumbnails or posters, slide decks, or developing FilmCraft's own source code."
- `allowed-tools` (유지): `Bash(filmcraft-cli *)`, `Bash(uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" *)`, `Bash(ffprobe *)`

**본문**

0. 제목·도입 (수정): "Making video with FilmCraft". 도구가 여섯(`transcribe|captions|timeline|frames|qc|graphic`)이고 각 `--help`가 수치·출력·종료 코드를 소유한다는 문장.
1. **Working with the user** (유지 + 수정 2)
   - 취향 목록에 "graphics: how many, how they look and how much they move"를 더한다(밀도는 사람마다 갈린다: 반례 근거).
   - (신규, 권위: 성진 결정) `data/`: 사용자의 이전 작품(프로젝트, `graphics/`의 페이지, 내보낸 영상)이 그가 고른 것의 기록이다. 모양·구성처럼 취향이 갈리는 것을 제안할 때 비슷한 이전 작품이 있으면 거기서 그의 취향을 읽는다. 따를 의무는 없다. 사용자가 다른 폴더를 말하지 않으면 새 작품은 `data/<piece>/`에 만든다(그래야 다음 작업의 기록이 된다).
2. **Before you hand something over** (수정 2)
   - 마지막 줄(권위: 성진 결정)을 "Edit picture and sound only in FilmCraft, so the user can open the project and change it; graphics are pages rendered with `graphic` and placed there. ffmpeg and ffprobe otherwise only measure; the one exception … faststart"로.
   - "You looked at the result" 줄에 그래픽의 확인 가능한 완료 판정을 더한다: 각 그래픽을 FilmCraft 렌더(`frames --project`)에서 들어올 때·가장 많이 보일 때·나갈 때 보았고, `graphic`이 보고한 폰트 대체(`fallback`)와 차단된 로드(`blocked`)가 없거나 사용자가 받아들였으며, 페이지가 `graphics/`에 있다. 디자인과 움직임은 자유롭게 고른다(완료 판정이 특정 모양을 요구하지 않는다).
3. **Before the first command** (유지)
4. **Headless or the running app** (유지)
5. **How the CLI fails quietly** (유지 + 신규 1): "Placing media with sound: `timeline.place` puts the sound on the targeted audio track (A1 unless targeting changed), overwriting what is there, unless `audioTrack` names another track, so music or a graphic's sound effects placed this way silently cut the speech under them; `graphics.newFromFile` leaves the sound out. Pass `"audioTrack": "new"` or a free track." (기본값은 `targeting().audio_dest`, `.tmp/filmcraft/crates/engine/src/commands.rs:857,875`)
6. **Command families by job** (유지)
7. **Seeing and hearing the edit** (유지)
8. **What does not depend on taste** (유지)
9. **Speech as material** (유지)
10. **On-screen text** (유지)
11. **Graphics and motion graphics** (신규, "When:" 첫 줄)
    - When: a title, lower third, callout, number or chart, how an inserted image is shown, a layout element (bar, gradient, frame), an intro or sting, or a motion graphic video on its own.
    - 경계와 이유: 디자인은 HTML 페이지로 쓰고 `graphic`으로 렌더한다. FilmCraft는 컷·타이밍·배치·트랙 순서, 영상 자체의 픽셀을 다루는 일(그래픽 뒤 화면 블러·리프레이밍·색), 소리, 샷 사이 전환, 자막을 맡는다. 이유: 코드에서 디자인의 폭이 가장 넓고, FilmCraft 그래픽은 텍스트·도형을 키프레임으로 움직이는 방식이라 시간 기준·이징을 맞추느라 시험 렌더를 거듭하게 되며, 렌더한 그래픽은 FCP7 XML 인계로 넘어가지만 네이티브 그래픽은 넘어가지 않는다. 뒤집히는 조건: 사용자가 그 그래픽을 FilmCraft에서 직접 고치고 싶어 하면 네이티브로. 판정 사례 한 쌍(비슷해 보이지만 갈리는 것, 장르와 무관): 말하는 사람에게 다가가는 확대는 영상 자체의 픽셀이라 FilmCraft의 Motion, 화면에 띄운 이미지 안에서 한 곳으로 다가가는 확대는 그래픽 안의 움직임이라 페이지. 경계가 애매한 경우(단어 단위 자막 애니메이션, 영상 속 물체를 따라가는 강조 등)는 규칙을 두지 않고 그 자리에서 고른 쪽과 이유를 말한다(기존 "Working with the user", 성진 결정). (권위: 성진 결정 + FilmCraft 사실 — FCP7 인계는 소스 근거)
    - 페이지는 `graphic`으로 렌더한다. 페이지 계약·출력·불러올 수 있는 것은 `graphic --help`가 소유한다(본문에 형식·fps·알파를 다시 쓰지 않는다).
    - 그래픽이 화면 위에 어떻게 앉는지는 FilmCraft 렌더(`frames --project`)로 판단한다(페이지 자체를 고칠 때 브라우저로 보는 것은 무방): FilmCraft는 선형 광으로 합성해서, 부분적으로 투명한 것(어두운 그라디언트, 그림자, 90% 상자)이 브라우저나 ffmpeg 합성에서보다 눈에 띄게 옅게 나온다. 그런 층은 페이지에서 맞아 보이는 것보다 불투명도를 높인다.
    - 페이지와 렌더는 작품의 `graphics/`에 두고 남긴다: 프로젝트가 렌더를 재생하고, 수정 요청이 오면 바꾸는 것은 페이지다. 같은 경로로 다시 렌더하면 프로젝트가 새 렌더를 읽는다(권위: FilmCraft 사실, 사실 테스트 22). 길이나 소리 유무가 바뀌면 `graphic`의 출력이 다시 놓을지를 알려 준다.
    - 효과음은 같은 페이지에서 만들 수 있다. 그러면 소리가 그 프레임에 붙어 다닌다(청취 불가 보고는 기존 "Before you hand something over"가 이미 다룸).
12. **Changing the frame shape** (유지)
13. **Many clips and music** (유지)
14. **Color** (유지)
15. **Delivery** (유지)
16. **Working files** (수정, 권위: 성진 결정): 첫 줄 "Intermediates go in `<project>.work/` …"을 작품 폴더 관례로 바꾼다: 작품 루트에 프로젝트와 결과물(딸린 자막·인계 파일 포함), `assets/`(가져온 재료; `data/assets/`의 공용 재료는 복사해 와서 작품 폴더만으로 프로젝트가 열리게), `graphics/`(프로젝트가 재생하므로 지우지 않음), `etc/`(그 밖, 일회용 파일은 끝날 때 지움). 이유 한 구절: 모든 작품이 같은 모양이어야 다음 작업에서 찾아 읽을 수 있다. 기존 "Write nothing outside the user's folders", "No global installs", "`FilmCraft Previews/` … not an output" 줄은 유지.
17. **Working in the running app** (유지 + 조건부): 구현 단계 13의 실측에서 앱이 같은 경로 재렌더를 반영하지 않으면 그 사실과 대처(새 이름으로 렌더 후 `media.replace` 등, 실측으로 정함) 한 줄. 반영하면 아무것도 더하지 않는다.

**권위 표시 (새·수정 문장)**: Graphics 경계 = 성진 결정(+인계는 FilmCraft 사실), 선형 광 = FilmCraft 사실(사실 테스트 20), 제자리 재렌더 = FilmCraft 사실(22), 소리 배치 = FilmCraft 사실(21), `data/`·작품 폴더 관례·저장 위치 = 성진 결정, "Edit picture and sound only in FilmCraft" = 성진 결정. 본문에는 권위를 꼬리표로 쓰지 않고 문장의 이유로 드러낸다(사실은 "FilmCraft …한다", 결정은 이유와 함께). 개발 기록은 PR 본문.

**지켜야 할 기존 동작** (회귀 기준, skill-maker "know which behaviors must survive")
- 협업 리듬: 바꾸기 쉬운 것은 해 보이고 보여 줌, 비싸거나 성격을 정하는 것은 먼저 물음, 내린 결정·확인 못 한 것 보고.
- 넘기기 전 확인: 새 프로세스로 다시 열리는 `.fcproj`, 대상 `qc` 통과(재내보내기 최대 2회), 컷과 글자 프레임 확인, 최종 컷 전사 확인.
- 헤드리스 기본, 브리지의 저장 함정·예의, 조용한 실패 목록, 명령군 지도.
- 다섯 명령(`transcribe·captions·timeline·frames·qc`)의 `--help`와 출력 계약(이름 변경 단계에서 대조), 사실 테스트 1–19.
- 삭제 검토 결과: 기존 문장 중 새 경계와 부딪히는 것은 "Edit only in FilmCraft…"(범위 좁힘)와 "Working files" 첫 줄(작품 폴더 관례로 대체) 둘뿐. "Text and shapes: `graphics.*`"와 Inter 한글 문장은 네이티브 자막·사용자가 직접 고칠 그래픽에 여전히 필요해 남긴다. 더 지울 문장은 찾지 못했다.

## 번들 코드: `graphic` 명령

**명령 표면 (`cli.py graphic --help`가 소유, 초안)**
```
graphic PAGE.html --out X.mov|X.png (--project P.fcproj | --bridge 127.0.0.1:PORT | --size WxH --fps F)
        [--sequence ID] [--duration S] [--frame-at T]
```
- 크기·fps: `--project`/`--bridge`면 시퀀스에서(`filmcraft_cli.read_sequence`의 `width`·`height`·`rate`, 유리수 그대로). 시퀀스가 없을 때(단독 모션 시작)만 `--size`·`--fps`(`30000/1001` 같은 분수 허용, `29.97` 같은 소수는 거부: 정확한 NTSC가 아니므로).
- 출력 종류는 확장자: `.mov` = ProRes 4444(인코더 입력 `yuva444p10le`), straight 알파, 시퀀스 fps. 페이지가 소리를 내면 48 kHz PCM 트랙. `.png` = `--frame-at T`(기본 0, 캡처할 페이지 시각; 타임라인 위치가 아님) 한 프레임, 알파 유지.
- 길이·프레임(worked example로 테스트에 고정): 길이는 양의 유한수(`--duration` 또는 `window.duration`). 프레임 수 = 길이×fps를 반올림(0.5는 올림), 최소 1. 프레임 i는 페이지 시각 i/fps에서 캡처, 마지막은 (N−1)/fps. 보고하는 실제 길이 = N/fps. 예: 3 s @ 30000/1001 → 90프레임, 3.003 s / 0.01 s @ 30 → 1프레임 / 1/60 s @ 30 → 0.5 → 1프레임.
- 시간 계약(순서): 페이지 로드 → `document.fonts.ready`와 모든 `<img>`의 decode 대기(`blocked`에 기록된 네트워크 이미지는 제외) → 첫 프레임 전에 그때 존재하는 애니메이션 집합을 기록하고 멈춤. 매 프레임: ① `window.seek(t)`가 있으면 호출하고 Promise면 기다림 ② **기록해 둔(페이지가 처음부터 가진) 애니메이션만** `currentTime = t×1000`으로 맞춤(CSS 애니메이션은 페이지 시작을 0으로 세며 delay 포함). `seek` 안에서 새로 만든 애니메이션은 렌더러가 건드리지 않는다(`seek`가 소유) ③ 두 번의 `requestAnimationFrame`으로 반영을 기다림 ④ 캡처. CSS 트랜지션은 벽시계로 돌아 결정적이지 않으므로 지원하지 않는다: 하나라도 보이면 오류(exit 1)로 알리고 `@keyframes`나 `seek`를 쓰라고 안내. 벽시계·시드 없는 난수·그리는 순서에 기대면 안 된다(`--help`에 명시).
- 제한 시간과 실패 분류(모두 exit 1, `error`에 단계 이름, 기존 `--out` 보존): 로드 30 s, 폰트·이미지 15 s, 프레임당 `seek` 10 s, `renderAudio` 60 s(값은 `chrome` 유닛 인자로 받아 테스트에서 줄일 수 있게). 로드하지 못한 **로컬** 파일(`file:` 없음·디코드 실패), 잡히지 않은 예외, `unhandledrejection`도 실패. 네트워크 요청은 실패가 아니라 `blocked` 보고이고, 차단된 네트워크 이미지는 decode 실패 판정에서 제외한다(페이지가 그 때문에 던지면 위 규칙으로 실패).
- 소리: `window.renderAudio(sampleRate, seconds)`가 `AudioBuffer`(OfflineAudioContext로 생성)를 돌려주면 그래픽 첫 프레임부터 MOV에 넣는다. 프레임 캡처보다 먼저 부르고(WAV를 인코더에 처음부터 넘겨 한 번에 mux하기 위해), 결과는 페이지 상태에 영향을 주지 않아야 한다(`--help`에 명시). 샘플 수 = round(N/fps × 48000)(0.5 올림)로 맞춰 남으면 자르고 모자라면 무음으로 채운다(영상 길이가 기준). 예: 90프레임 @ 30000/1001 → 144144 샘플. 무음이면 레벨은 `null`.
- 색: Chrome 캡처는 sRGB. `scale=out_color_matrix=bt709:out_range=tv`로 변환하고 `setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv`로 네 태그를 모두 기록(출력 옵션 `-color_primaries`만으로는 primaries·transfer가 `unknown`, 실측). FilmCraft는 BT.709 전달 함수를 sRGB 곡선으로 처리하므로(`crates/color/src/lib.rs:189–203`) 왕복이 맞는다. 다른 플레이어에서의 색은 미검증으로 남긴다.
- 불러오기: `file:`과 `data:`만. 네트워크 요청은 막고 `blocked`에 나열(재렌더가 몇 달 뒤에도 같은 프레임을 내야 하므로). 폰트: 글자가 있는 요소마다 요청한 family와 **실제로 글자를 그린 폰트**(CDP `CSS.getPlatformFontsForNode`, 글리프 수 포함)를 보고하고, 요청한 family가 아닌 폰트가 글리프를 그렸으면 `fallback`으로 표시한다. `document.fonts.check`는 없는 폰트에도 true라 쓰지 않는다(실측: 없는 family의 한글은 AppleMyungjo, Inter의 한글은 Apple SD Gothic Neo로 조용히 대체). 글자가 나중에 나타날 수 있으므로 표본 시각(처음, 매 정수 초, 끝)마다 보이는 요소를 확인한다. CSS 애니메이션의 시간은 페이지가 열린 순간을 0으로 센다(나중에 만든 애니메이션은 `window.seek`에서 직접 다룬다)고 `--help`에 적는다.
- stdout(JSON 한 문서, 싼 신호 먼저): `{out, kind: video|still, size, fps, frames, seconds, coverage: [{t, painted, opaque}](처음·중간·끝; painted = 알파>0인 화면 비율, opaque = 알파≥250인 비율. 화면을 가리는지는 opaque로 판단), audio: {peak_dbfs, lufs}|null, fonts: [{family, drawn_by: [{face, glyphs}], fallback}], blocked: [...], replaced: {length_changed, audio_changed, size_changed, fps_changed}|null, took_s, next}`.
- `next` (늘 가져오기 + `timeline.place`; 자리표시자 `<item>`·`<start s>`·정지 PNG면 `<hold ticks>`): `--project`면 `filmcraft-cli --project P --save import OUT` → `filmcraft-cli --project P --save exec timeline.place '{"item":<item>,"track":"new","audioTrack":"new","seconds":<start s>[,"duration":<hold ticks>]}'`(`--sequence`가 있으면 그 시퀀스를 먼저 여는 명령 포함), `--bridge`면 같은 명령을 `--bridge`로, `--save` 없이(저장은 사용자 몫). `--size/--fps`(시퀀스 없음)면 이 렌더로 시퀀스를 만드는 `file.newSequenceFromClip` 안내. `graphics.newFromFile`은 소리를 버리므로 쓰지 않는다(실측). `replaced`가 있으면 배치 명령에 앞서 조건문을 붙인다(명령은 프로젝트의 배치 여부를 조회하지 않으므로): 길이·소리·크기·fps가 그대로면 "이미 놓았다면 놓인 클립이 새 렌더를 재생하므로 할 일 없음, 아직이면 아래 명령", 바뀌었으면 "이미 놓았다면 그 클립(소리 클립 포함)을 지우고 다시 놓기"(사실 테스트 23의 실측으로 문구 확정).
- 종료 코드: 0 기록함, 1 Chrome·ffmpeg 실패, 페이지 실패(위 분류), 출력 검증 실패(`error`, `stderr_tail`), 2 명령줄을 바꿔야 함(MOV인데 길이 없음, 길이가 양의 유한수가 아님, `.mov`/`.png` 아닌 확장자, 출처가 둘 또는 없음, 페이지 파일 없음, `--out`이 페이지 자신, `--fps`가 소수 표기).
- 출력 검증: 쓴 MOV를 ffprobe로 다시 재서 codec `prores`·profile `4444`·디코드 형식에 알파가 있음(`yuva444p12le`로 디코드됨, 실측)·네 색 태그 `bt709`/`tv`·프레임 수 = N, 소리가 있으면 48 kHz PCM·샘플 수. 어긋나면 실패(조용한 오류 방지). ffprobe 해석은 `ffmpeg/` 안에 둔다.
- 원자적 교체: `--out` 옆 임시 파일에 쓰고, 검증을 통과한 뒤에만 `os.replace`로 바꾼다. 실패하면 기존 렌더의 바이트가 그대로 남는다(프로젝트가 재생 중인 파일을 깨뜨리지 않게).
- Playwright는 `chrome/`을 실제로 쓸 때 import한다(다른 명령과 그 테스트가 Playwright 없이 돈다).

**유닛과 의존 방향** (구조 테스트가 지킴. 각 `__init__.py`에 literal `__all__`)
- `graphic/` (기능): `__all__ = ["render", "HELP"]`. `render(page, out, *, source=None, size=None, rate=None, sequence=None, duration=None, frame_at=0) -> dict`(stdout 문서). 입력 확인, 프레임 시각 계산(`timecode.Rate` 유리수), Chrome 캡처를 인코더로 파이프, coverage(Pillow), 소리 WAV(stdlib `wave`), 임시 파일·검증·원자적 교체, `replaced`·`next` 조립. 의존: `chrome`, `ffmpeg`, `filmcraft_cli`, 공용.
- `chrome/` (시스템, 신규): `__all__ = ["open_page", "Page", "FontUse", "Pcm", "Timeouts"]`. `open_page(path, width, height, timeouts=Timeouts()) -> Page`(컨텍스트 관리자: 로드·폰트·이미지 대기, 애니메이션 집합 기록). `Page.audio(sample_rate, seconds) -> Pcm | None`, `Page.frames(times, on_frame: Callable[[float, bytes], None])`(시간 계약대로 seek·캡처, `times`는 임의 순서 허용), `Page.fonts(at_times) -> list[FontUse]`, `Page.blocked -> list[str]`. 실패는 `ToolError`(단계 이름 포함). Playwright로 설치된 Google Chrome(`channel="chrome"`, 다운로드 없음) 실행, `file:`/`data:` 외 요청 차단, 로드·폰트·이미지 대기, 시간 계약대로 seek·캡처(PNG 바이트를 `on_frame`으로), CDP `CSS.getPlatformFontsForNode`로 폰트 사용, 페이지 오류 수집, `renderAudio` 결과를 채널별 float 샘플로. Chrome 없으면 설치 방법(사용자에게 먼저 묻기)을 담은 ToolError. Playwright·CDP 세부는 이 유닛 밖으로 새지 않는다(사용자의 `design` 스킬 `chrome/`과 같은 방식).
- `ffmpeg/` (시스템, 확장): docstring을 "측정, 그리고 렌더한 그래픽을 알파 중간 파일로 인코딩"으로 고치고 `__all__`에 `AlphaWriter`를 더한다: `AlphaWriter(out, rate, size, audio_wav: Path | None = None)`(컨텍스트 관리자, `write(png_bytes)`로 프레임을 파이프, 닫을 때 같은 ffmpeg 호출에서 WAV를 PCM으로 mux). `probe` 결과는 이미 있는 `VideoStream.profile`·`pix_fmt`·`transfer`·`primaries`(`ffmpeg/probe.py:21–30`)에 `color_space`·`color_range`·`frames`(nb_frames)·`has_alpha`를 더하고, `AudioStream`에 `samples`(검증용 샘플 수)를 더한다. 인자·필터 문자열·ffprobe 키 해석은 이 유닛 안에만.
- `cli.py`: 파서·도움말·디스패치·종료 코드만.
- PEP 723: `dependencies = ["pillow>=10", "playwright>=1.50"]`. Playwright는 uv 캐시에 있음(1.63), Chrome은 설치된 앱을 쓴다.

**경로 규칙**: `--out`이 페이지 자신이면 exit 2. 그 밖의 겹침(페이지가 `--out`을 불러오는 경우)은 원자적 교체 덕에 기존 파일을 깨뜨리지 않으므로 따로 막지 않는다.

## 테스트 설계 (`coding` 스킬 기준으로 이음매 합의)

**이음매**
- `cli.py graphic`의 프로토콜: 진짜 진입점을 `uv run`으로(테스트 헬퍼 `skill(..., via_uv=True)`, PEP 723의 Playwright가 해석되는 경로). Chrome·ffmpeg·filmcraft-cli 모두 실물. 없으면 이유를 출력하고 skip하되, 완료 판정은 "graphic·사실 테스트가 skip 없이 실제로 돌았다"를 요구한다(`-ra` 요약의 skip은 기존 Whisper 1건만).
- 사실 회귀 테스트: SKILL.md의 새 문장이 기대는 FilmCraft 동작.
- `chrome` 유닛 인터페이스(`open_page`·`Page`): 한 페이지 세션 안에서만 보이는 계약(임의 순서 캡처의 결정성, 짧은 제한 시간의 실패)을 여기서 본다. CLI는 호출마다 새 브라우저라 이것을 관찰할 수 없다.
- 구조 규칙: 새 유닛의 종류와 import 방향.
- 대역(double) 없음. 미검증으로 남는 것: 실행 중인 앱(브리지)의 같은 경로 재렌더 반영(단계 13에서 1회 실측), Chrome이 없는 머신의 실제 안내 문구(Chrome 경로 재정의 환경 변수로 없는 경로를 가리켜 오류 형태만 확인), FilmCraft 밖 플레이어(Premiere 등)에서의 색.

**기대값의 독립성**
- 프레임 수·길이: worked example(위 계약의 예: 3 s @ 30000/1001 → 90프레임·3.003 s·144144 샘플, 0.01 s @ 30 → 1프레임, 1/60 s @ 30 → 1프레임). 픽스처 시퀀스는 `30000/1001`(정수 fps에서만 맞는 구현을 잡기 위해).
- 기술 조건의 범위(숏츠 조건을 전제하지 않는지): `24000/1001`·`25`·`30000/1001`·`60000/1001` fps 시퀀스에서 프레임 수·`r_frame_rate`가 시퀀스와 같고, 1920×1080·1080×1920·1080×1080·3840×2160에서 크기가 같으며 FilmCraft 왕복 색이 맞는다(4K는 1초로 짧게). HLG 시퀀스(`sequence.settings workingSpace "rec2100-hlg"`): BT.709 태그 오버레이를 FilmCraft가 작업 공간으로 변환해 SDR 흰색·회색이 의도한 밝기로 오는지 실측해 사실 테스트 24로 고정하고, 변환하지 않으면 `graphic`이 시퀀스 작업 공간에 맞게 변환·태그하고 그 테스트를 둔다.
- 색·알파: 페이지가 칠한 값이 기대값. 불투명 빨강, 50% 빨강, 50% 회색(#808080), 중간톤 살색(예 #C8A08C), 반투명 가장자리(1px 안티앨리어싱 원), 투명. MOV를 ffmpeg로 RGBA 디코드해 straight 알파(50% 빨강에서 RGB 255,0,0 유지, 알파 128±1)와 네 색 태그를 본다. 같은 값을 PNG 출력으로도 본다.
- FilmCraft 왕복: 파랑·회색 배경 시퀀스에 MOV와 PNG를 각각 얹어 `render` → 기대값은 sRGB 표준(IEC 61966-2-1) 전달 함수로 손계산한 선형 합성값(50% 빨강 over 파랑 ≈ (188,0,187)), 불투명 회색·살색은 페이지 값 ±2. 구현은 합성을 계산하지 않으므로 독립.
- 시간: CSS `@keyframes`(delay 0.5 s 포함)로 상자가 0→1000px 선형 이동, `window.seek`로 같은 움직임을 그리는 페이지, 둘을 한 페이지에 섞은 페이지 → 프레임 n의 상자 왼쪽 가장자리가 손계산 값 ±1px. `seek` 안에서 만든 애니메이션은 `seek`가 정한 시각대로 그려짐(렌더러가 덮어쓰지 않음). 결정성(`chrome` 이음매): `Page.frames([1.0, 0.5, 1.0])`의 첫째와 셋째 바이트가 같다. CSS 트랜지션이 있는 페이지는 exit 1.
- 실패: CLI로 — `seek`가 끝나지 않는 Promise → 제한 시간 뒤 exit 1·단계 이름, 없는 로컬 이미지 → exit 1, 잡히지 않은 예외·`unhandledrejection` → exit 1, 셋 모두 기존 `--out`의 바이트가 그대로. `chrome` 이음매에서 제한 시간을 줄여 — `renderAudio`가 끝나지 않음 → 단계 이름 `audio`, 폰트 대기가 끝나지 않음(`@font-face`가 FIFO 파일을 가리켜 읽기가 멈추게 함) → 단계 이름 `fonts`. FIFO로 멈춤을 만들 수 없으면 그 실패는 미검증으로 적는다.
- 소리: 페이지가 0.5초부터 1 kHz 사인(진폭 0.1 = −20 dBFS)을 합성 → ffmpeg로 첫 비무음 샘플 0.5 s ±1 ms, 피크 −20 ±0.2 dBFS, 샘플 수 = worked example. `renderAudio`가 더 긴 버퍼를 주면 잘리고 짧으면 채워진다.
- 폰트: `"Apple SD Gothic Neo"`로 쓴 한글은 그 폰트가 그림(fallback 없음), 없는 family로 쓴 한글과 `"Inter"`로 쓴 한글은 `fallback`으로 표시되고 실제로 그린 폰트 이름이 나옴(macOS 기본 폰트만 써서 머신 차이를 줄임).
- 네트워크: `<img src="https://example.com/a.png">`(던지지 않는 요청) → `blocked`에 그 URL, 렌더는 성공.
- 배치: `next`의 자리표시자를 채워 실행한 뒤 `inspect sequence`로 확인 — 그래픽 클립이 새 비디오 트랙의 지정 시작 프레임에 렌더 길이(정지 PNG는 지정 길이)로 있고, 소리 있는 렌더면 소리가 새 오디오 트랙에 같은 위치·길이로 있으며, A1 대사 클립은 그대로, `--sequence`로 지정한 시퀀스에 놓였는지.
- 재렌더: 같은 `--out`에 같은 길이로 다시 렌더 → `replaced`의 변화 없음·`next`의 조건문이 "이미 놓았다면 할 일 없음", 길이·fps·소리 유무를 각각 바꿔 다시 렌더 → 해당 `*_changed: true`와 "이미 놓았다면 다시 놓기". 처음 렌더(`--out` 없음)는 `replaced: null`과 배치 명령만.
- coverage: 화면 전체를 1% 알파로 칠한 페이지 → painted 1.0·opaque 0.0, 절반을 불투명하게 칠한 페이지 → painted·opaque 0.5 ±0.01.
- 종료 코드: 각 사용 오류 → 2(소수 `--fps`, 0·음수·무한 길이, `--out` = 페이지 포함), 위 실패 → 1.

**사실 회귀 테스트 추가** (`tests/filmcraft_facts/test_facts.py`, docstring에 지키는 SKILL.md 문장)
- 20. 합성은 선형 광: 50% 빨강 PNG over 파랑 → (188,0,187) ±2 (SKILL.md › Graphics, 판단은 FilmCraft 렌더로).
- 21. 소리 있는 클립을 `audioTrack` 없이 `timeline.place`하면 A1이 잘리고, `"audioTrack":"new"`면 A1이 그대로이며, `graphics.newFromFile`은 소리 클립을 만들지 않는다 (SKILL.md › How the CLI fails quietly).
- 22. 같은 경로로 바꾼 렌더를 다음 헤드리스 `render`가 읽는다 (SKILL.md › Graphics, 제자리 재렌더).
- 23. 놓인 클립의 파일이 같은 경로에서 길어지거나 짧아질 때, 무음이던 파일에 소리가 생기거나 소리가 사라질 때 비디오 클립과 소리 클립이 어떻게 되는지(실측 후 고정) (`graphic --help`·`next`의 재배치 문구).
- 24. HLG 시퀀스에서 BT.709 태그 오버레이가 어떤 밝기로 합성되는지(실측 후 고정) (`graphic --help`의 HDR 시퀀스 문구, 또는 `graphic`의 변환이 기대는 동작).

**구조 테스트**: `PKG="video"`, `SCRIPTS`를 새 경로로, `KINDS`에 `"graphic": "feature"`, `"chrome": "system"`. 기존 깨뜨리기 표본들은 그대로 통과해야 한다.

**실행**: 레포 루트에서 `uv run --with pytest --with pillow pytest -ra`(graphic 테스트는 진입점을 `uv run`으로 부르므로 pytest 환경에 Playwright가 없어도 된다). 변경 전 기준선: 146 passed, 1 skipped, exit 0 (74초, 2026-10-14 이 세션에서 실행). 렌더 속도는 테스트의 시간 제한이 아니라 조건(1080×1920, 3초, Chrome 기동 포함, 3회 중앙값)을 고정한 별도 측정으로 PR에 기록한다.

## 구현 단계 (TaskCreate 트래커. description에 완료 판정을 그대로 쓴다)

| # | 단계 | 완료 판정 |
|---|---|---|
| 0 | 계획 파일 이름 변경 | `.claude/plans/video-graphics.md`가 있고 원본 경로에는 없음 |
| 1 | `.gitignore`의 기존 미커밋 변경 정리 | 작업 트리의 `.tmp/etc/` → `.tmp/` 변경(성진 수정)을 main에 `chore: .tmp 전체 무시`로 커밋·푸시. `git status`에 `.gitignore` 없음 |
| 2 | 브랜치 | `feat/video-graphics`가 `main`에서 갈라짐 |
| 3 | 이름 변경 refactor (동작 불변) | 바꾸기 전에 `pytest --collect-only -q` 노드 목록과 `cli.py --help`·각 `<명령> --help` 출력을 저장. `git mv .claude/skills/filmcraft .claude/skills/video`, `scripts/filmcraft` → `scripts/video`, import·`pytest.ini`·`tests/support`·`tests/filmcraft_skill`→`tests/video_skill`·구조 테스트 PKG·깨뜨리기 픽스처의 문자열 import·docstring·SKILL.md `name`·README 경로. 미추적 `data` 링크를 새 폴더로 옮기고(`readlink`가 같은 대상) `.gitignore`에 `.claude/skills/video/data`. 판정: ① 전체 pytest 146 passed/1 skipped, exit 0 ② 수집 노드 목록이 경로 접두사만 다르고 같음 ③ `--help` 출력이 패키지 이름 외에 같음 ④ `grep -rnE "skills/filmcraft|scripts/filmcraft|from filmcraft[ .]|import filmcraft\b|filmcraft_skill|PKG = \"filmcraft\"" .claude/skills/video tests README.md pytest.ini .gitignore`가 빈 결과(검색 범위는 이 경로들로 한정: `.claude/plans`·`.tmp`·`data`·개발 기록 제외. 제품명 FilmCraft·`filmcraft-cli`·`filmcraft_cli`·`filmcraft_facts`·MCP 서버 `filmcraft`는 패턴에 걸리지 않고 남음) ⑤ 구조 테스트 뮤테이션(일부러 방향 위반을 넣으면 실패) ⑥ `claude plugin validate --strict .claude/skills` exit 0 ⑦ Obsidian/Work 링크 교체 후 `~/💎Obsidian/🐝Work/.claude/skills/video/SKILL.md`를 실제로 읽을 수 있음. 커밋 `refactor: 스킬 이름을 video로 변경` |
| 4 | 사실 테스트 20–24 | 20–22(위), 23(놓인 클립의 파일을 같은 경로에서 길이·소리 유무를 바꾸면 클립이 어떻게 되는지, 단계 7의 `next` 문구가 기대는 동작), 24(HLG 시퀀스의 BT.709 오버레이 밝기)를 실측해 고정한 테스트가 설치된 0.7.2에서 통과하고, 각 docstring이 SKILL.md 문장 또는 `graphic --help` 문구를 가리킴. 커밋 `test: 그래픽 합성·배치에 관한 FilmCraft 사실` |
| 5 | `graphic` 골격 | `chrome/`·`graphic/` 스텁(literal `__all__`), `KINDS` 갱신, `cli.py graphic` 파서·`--help` 초안, Playwright 지연 import. 구조 테스트 green, 기존 테스트 green(파이썬 환경에 Playwright 없이). `test_graphic.py`의 첫 테스트가 "동작 없음" 이유로 red |
| 6 | 영상 렌더 (TDD) | 프레임 수 worked example, 여러 fps·크기(기술 조건 범위), straight 알파·네 색 태그·출력 검증, FilmCraft 왕복 색(MOV), HLG 시퀀스(사실 테스트 24의 실측에 따라), CSS·seek·혼합 시간, 결정성, 원자적 교체 테스트가 red→green |
| 7 | 정지 PNG·보고·실패·소리 없는 배치 (TDD) | PNG(왕복 색 포함), coverage, 폰트 보고, 네트워크 차단, 실패 분류·제한 시간, 종료 코드, `replaced`, 소리 없는 렌더의 `next` 실행(위치·길이·시퀀스·A1 보존) 테스트 green |
| 8 | 소리 (TDD) | `renderAudio` → MOV의 48 kHz PCM, 시작 시각 ±1 ms·레벨 ±0.2 dB·샘플 수 worked example·자르기/채우기 테스트 green. 소리 없는 페이지는 오디오 트랙 없음. 소리 있는 렌더의 두 단계 `next`를 실행하면 그래픽 소리가 새 오디오 트랙에 같은 위치·길이로, A1 대사는 그대로인 테스트 green |
| 9 | `--help` 확인 | `cli.py --help`와 `graphic --help`를 실행해 줄바꿈이 깨지지 않고, 인자·페이지 계약·출력·종료 코드를 혼자 설명함 |
| 10 | SKILL.md·README | 위 섹션 구조 충족, 신규 문장은 차이 표의 행에만 대응, description 1024자 이내이고 모든 턴에 드는 목록 비용을 늘리는 만큼만 길게(skill-doctor의 context 열: 지금 약 220 토큰, 단계 11에서 다시 재서 기록), 약 170줄. README는 한국어로 그래픽·효과음·단독 모션·`graphic`·`data/`·새 경로 반영 |
| 11 | 형식·전체 검증 | `claude plugin validate --strict .claude/skills` exit 0, 전체 `pytest -ra` exit 0이고 skip은 기존 Whisper 1건뿐(graphic·사실 테스트가 실제로 돌았음), `claude -p "/skill-doctor"`를 이 레포와 `~/💎Obsidian/🐝Work`에서 실행해 트리거 겹침 없음(겹치면 양쪽 description에 경계). 렌더 속도 별도 측정(조건 고정, 3회 중앙값) 기록 |
| 12 | 스킬 포함 재실험 | 부록의 g1–g3 과제 문장 그대로 + g1 후속(`--resume`: "빨간 박스 대신 헤드라인에 형광펜") + g4 단독 인트로. **격리**: 과제 폴더의 `.claude/skills/video`는 레포 스킬을 `data` **없이** 복사한 것(`rsync -a --exclude data`)이고 그 안의 `data/`는 빈 폴더 — 사용자의 실제 작업 폴더를 읽거나 쓰지 않게. 과거 작품을 읽는 동작은 g5로 따로: 그 과제의 `data/`에만 이전 작품 한 편을 넣는다 — g3 재실험의 결과를 작품 폴더 관례 그대로(루트의 프로젝트·결과 영상, `assets/`, `graphics/`, `etc/`) g5 폴더의 `data/<작품>/`로 복사하고, 프로젝트의 미디어 참조를 복사본으로 다시 연결해(`media.relink`) `inspect project`의 오프라인 0건을 확인한 것. 사용자의 실제 작업 폴더를 가리키는 경로가 하나도 없어야 한다. 과제는 3일차 컷편집을 새 회차로 주며 "지난번 숏츠와 같은 스타일로 만들어 줘". `--safe-mode` 없이 `--restricted`. 판정: 디자인 그래픽은 `graphic` 경로, 렌더러 작성·색 재인코딩·작업 폴더 밖 쓰기 0건, `permission_denials`는 따로 집계, FilmCraft 렌더로 확인, A1 보존, 후속 요청은 페이지 수정·제자리 재렌더, g5는 이전 페이지를 읽고 출발, 비용·턴을 기준선과 표로 비교, 프레임 시트를 성진님께 보임. 나빠진 항목은 원인을 추적해 수정 |
| 13 | 브리지 실측 | 성진님 동의 후 앱을 `--control`로 띄워 `graphic --bridge`, 얹기, 같은 경로 재렌더가 앱에 반영되는지 1회 확인. 결과에 따라 SKILL.md 17번 절 처리. 앱은 원래 상태로 |
| 14 | 독립 리뷰 | codex(`gpt-6.1-sol`, `medium`)에 SKILL.md 전문·코드·테스트·`--help` 출력·재실험 표를 보내 네 속성(Principle over rail, Interface over document, For the model, Dense)과 계약을 리뷰받음. 지적은 재현해 채택하거나 이유와 함께 기각, 결정을 바꾸는 것은 성진님께 |
| 15 | 사용자 승인 | SKILL.md 전문(영어) + 한국어 요약을 보이고 전체 텍스트 승인. 승인은 텍스트에 대한 것이지 여러 실제 세션에서의 성능 증거가 아님을 밝힘 |
| 16 | 커밋·PR·머지 | 논리 단위 커밋(refactor, test facts, chrome/ffmpeg 유닛, graphic 기능, 소리, docs) → 푸시 → PR(템플릿 없음: 무엇을 바꿨나/왜/영향/검증) → `gh pr merge --squash`. 스테이징은 경로 지정만(`.tmp/`, `.claude/plans/`, `data` 금지) |

## 검증 (end-to-end)

- 번들 코드: `uv run --with pytest --with pillow pytest -ra` exit 0, skip은 기존 Whisper 1건뿐. 각 새 테스트를 먼저 실패로 본 기록, 뮤테이션 확인(`setparams`를 빼면 태그 테스트 실패, 행렬을 BT.601로 바꾸면 왕복 색 실패, `audioTrack`을 빼면 배치 테스트 실패, 원자적 교체를 빼면 보존 테스트 실패)을 보고에 남긴다.
- 진짜 진입점: `uv run ".claude/skills/video/scripts/cli.py" graphic …`을 실제 4일차 컷편집 사본 위에서 1회(형광펜 자료 화면 + 효과음) → `frames --project` → `qc --target shorts`.
- 스킬 형식: `claude plugin validate --strict /Users/seongjin/Coding/video/.claude/skills` exit 0.
- 스킬 효과: 단계 12 표(기준선 대비 비용·턴·경로·결함). 수치와 개발 기록은 PR 본문에.
- 브리지: 단계 13.
- 독립 리뷰: 단계 14의 지적과 처리 내역.

## Git

- 브랜치 `feat/video-graphics`. PR 제목 `feat: video 스킬로 개명하고 코드 그래픽·효과음 추가`(50자 이내로 조정).
- 커밋 예: `refactor: 스킬 이름을 video로 변경` / `test: 그래픽 합성·배치에 관한 FilmCraft 사실` / `feat: chrome 시스템 유닛과 알파 ProRes 인코딩` / `feat: graphic 렌더 명령` / `feat: graphic 효과음` / `docs: SKILL.md 그래픽 절과 README`.
- PR 본문 개발 기록: 기준선 표(g1–g3)와 재실험 표, 버린 대안(HyperFrames 의존, 네이티브 우선, 선호 메모 파일, 일반 그래픽 원칙, ffmpeg 예외 조항, 디자인 자막·썸네일 영역은 다음으로), 기준 모델·버전·날짜(Opus 5.5 / FilmCraft 0.7.2 / 2026-10-14).

## skill-maker 준수 대조

| skill-maker 요구 | 이 계획에서 |
|---|---|
| 모델이 이미 하는 것은 빼고 차이만 | 기준선 g1–g3, "차이 → 자리" 표와 '넣지 않음' 행, 일반 그래픽 원칙 제외(성진 결정) |
| Principle over rail | 경계 원칙에 이유(디자인 폭, 키프레임 시행착오, 인계)와 뒤집히는 조건(사용자가 FilmCraft에서 고치려 할 때) |
| Interface over document | 페이지 계약·출력·종료 코드는 `graphic --help`, 본문엔 언제·경계·실패만 |
| For the model, not the maintainer | 출처·측정 기록은 PR 본문. 본문의 선형 광 문장은 다음 결정을 바꾸는 이유로만 |
| Dense | 신규 약 10줄 + 수정 5곳, 클라이언트 소유 값(수치)은 도구·사실 테스트에 |
| 취향과 사실의 권위 구분 | 취향은 사용자와 `data/`의 과거 결과물, 사실은 사실 테스트, 결정은 성진님 |
| 기본값과 대조해 결과를 사용자에게 보이고 반대를 이유까지 | g1–g3를 보여 드림 → 어떤 영상이든 틀린 문제 없음(성진). 단계 12의 재실험 결과도 프레임 시트로 보임 |
| 다듬은 원칙은 새 사례로 경계 확인 | 계획 세션에서 새 사례로 판정을 보임 → 사례별 규칙은 두지 않고 애매한 경우는 대화로(성진). 단계 12의 g4·g1 후속·g5로 실제 행동도 확인 |
| 위치·언어 결정 | 프로젝트 스킬 유지(이번 세션), 영어 SKILL.md(이전 결정) |
| 지식은 작동할 곳에 | 색 행렬·fps·알파·폰트·네트워크·소리 배치는 `graphic`이 숨김. 모델이 직접 할 수 있는 디자인은 감싸지 않음(템플릿·스타일 명령 없음) |
| 파일은 로드 시점으로 | references 없음(그래픽 경로가 대부분의 작업에 쓰임) |
| 코드 트리 | `cli.py` 하나, 패키지 `video` 하나, 기능 `graphic`·시스템 `chrome`, 상태는 `data/`, 테스트는 레포 `tests/`, 구조 테스트 갱신 |
| `uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py"` + PEP 723 | allowed-tools 유지, PEP 723에 playwright |
| stdout JSON 한 문서·싼 신호 먼저·0/2 | `graphic` 출력 계약, 종료 코드 0/1/2 |
| 외부 시스템 형식은 그 이름의 유닛 하나에 | Playwright·CDP는 `chrome/`, ffmpeg 인자는 `ffmpeg/`, FilmCraft 출력은 `filmcraft_cli/` |
| 새 스킬이 이웃에 주는 비용 | 계획 세션에서 skill-doctor(레포·`🐝Work`) 실행, k-politics 겹침은 성진 결정으로 그대로. description 경계(썸네일·포스터·슬라이드·다운로드), 목록 비용 측정(단계 10·11) |
| 완료: 전체 텍스트 승인, 다른 계열 리뷰, validate, 개발 기록은 스킬 밖 | 단계 15·14·11·16 |

## 수용한 가정 (구현 때 확인)

- 다른 사용자도 Google Chrome이 설치돼 있다. 없으면 `graphic`이 안내하고, Playwright Chromium 다운로드(약 150 MB)는 사용자에게 먼저 묻는다.
- `timeline.place`의 기본 소리 트랙은 오디오 타깃(`targeting().audio_dest`)이고 기본 상태에서 A1이다. 사실 테스트 21은 기본 상태만 고정하고, SKILL.md 문장은 "타깃 트랙(바꾸지 않았으면 A1)"으로 쓴다.
- sRGB로 캡처한 그래픽에 BT.709 태그를 다는 것이 FilmCraft 왕복에서는 맞고(FilmCraft가 BT.709 전달 함수를 sRGB 곡선으로 처리), Premiere 같은 다른 플레이어에서 미세한 감마 차이가 있을 수 있다. 미검증으로 PR에 적는다.

## codex 계획 리뷰 반영 내역 (`gpt-6.1-sol`, `medium`, 2026-10-14 23:24)

17건. 재현할 수 있는 것은 재현했다(①⑨는 ffprobe로, ⑤는 Chrome 실측으로, ⑦은 FilmCraft 실측으로).

| # | 등급 | 지적 | 처리 |
|---|---|---|---|
| 1 | blocker | 출력 검증이 `yuva444p10le`를 요구하지만 ProRes 4444는 `yuva444p12le`로 디코드됨 | 재현·채택: 검증을 codec·profile·알파 유무·태그·프레임 수로 |
| 2 | major | 제자리 재렌더 실패가 쓰던 렌더를 망가뜨림 | 채택: 임시 파일 → 검증 → `os.replace`, 보존 테스트, `--out` = 페이지 거부 |
| 3 | major | CSS와 `seek` 혼합의 시간 계약 모호 | 채택: 순서 명시, CSS 트랜지션은 오류, 혼합·결정성 테스트 |
| 4 | major | 끝나지 않는 로드·폰트·seek·소리의 계약 없음 | 채택: 단계별 제한 시간과 실패 분류, 테스트 |
| 5 | major | `document.fonts.check`로 설치 여부를 알 수 없음 | 재현(없는 폰트도 true)·채택: CDP로 실제 그린 폰트 보고 |
| 6 | major | 프레임 반올림과 소리 길이 불일치 | 채택: 반올림 규칙·최소 1프레임·샘플 수 규칙, worked example |
| 7 | major | `next`가 실행 가능한 계약이 아님, `graphics.newFromFile`은 소리를 버림 | 재현·채택: 늘 import + place, 자리표시자, 브리지는 저장 없음, 배치 테스트 확장 |
| 8 | major | 제자리 재렌더가 길이·스트림 변화까지 보장하지 않음 | 채택: `replaced` 보고, 사실 테스트 23으로 실측 고정 |
| 9 | major | 색 태그가 실제로 기록되지 않고 검증이 원색에 치우침 | 재현(primaries·transfer `unknown`)·채택: `setparams`, 회색·중간톤·가장자리·PNG 왕복 |
| 10 | major | PEP 723 의존성과 pytest 실행 방식 불일치 | 채택: Playwright 지연 import, graphic 테스트는 `uv run` 진입점 |
| 11 | major | 필수 통합 테스트가 skip돼도 완료, 단계 순서 | 채택: skip 금지 판정, 소리 배치를 단계 8로, 속도는 별도 측정 |
| 12 | major | 재실험이 사용자의 실제 `data/`로 연결 | 채택: `data` 없는 스킬 사본, 과거 작품 읽기는 g5로 분리 |
| 13 | major | A1 경고가 측정보다 강함 | 채택: "타깃 트랙(기본 A1)"으로 |
| 14 | minor | 새 본문에 rail·인터페이스 중복 | 채택: 과거 작품 읽기에 조건, FilmCraft 판단은 최종 합성으로 한정, 형식 재서술·청취 불가·단독 영상 납품 반복 삭제 |
| 15 | minor | 차이 표와 본문의 대응 누락 | 채택: 사용자 결정·인계 호환성 행 추가, 실험 경위는 PR로 |
| 16 | minor | 이름 변경 완료 조건이 약함 | 채택: 수집 목록·`--help` 대조, 넓은 grep, 외부 링크 실제 읽기 |
| 17 | minor | 유닛 인터페이스·보고값 미정 | 채택: `__all__`·함수 서명, coverage를 painted/opaque로, 무음 레벨 `null` |

같은 스레드의 좁은 재확인(23:32): 11건 해소, 6건 부분 → 아래로 마저 반영.

| 남은 지적 | 처리 |
|---|---|
| 동적 애니메이션의 소유자가 둘(렌더러가 `seek`가 만든 애니메이션을 덮어씀), 순서 바꾼 캡처는 CLI로 관찰 불가 | 렌더러는 처음부터 있던 애니메이션만 맞추고 `seek`가 만든 것은 `seek` 소유. 결정성·제한 시간 테스트는 `chrome` 인터페이스(`Page.frames`)를 이음매로 |
| 차단된 네트워크 이미지가 decode 실패로 exit 1이 되어 테스트와 모순, 폰트·`renderAudio` 미완료 테스트 없음 | 차단된 네트워크 이미지는 decode 판정에서 제외, 로컬 실패만 exit 1. `chrome` 이음매에서 `renderAudio`·폰트(FIFO) 미완료 테스트 |
| 파일 교체만으로 "이미 놓임"을 알 수 없음, fps·소리 유무 변화 누락 | `next`에 "이미 놓았다면" 조건문, `fps_changed` 추가, 사실 테스트 23에 무음↔유음 |
| 재실험 격리가 부록에서 반대(레포 스킬 링크) | 부록도 `data` 없는 복사로, g5는 미디어 복사·`media.relink`·오프라인 0 확인 |
| 개명 grep이 계획 파일 자신 때문에 빈 결과가 될 수 없음 | 검색 범위를 스킬·tests·README·pytest.ini·.gitignore로 한정 |
| `AlphaWriter`에 WAV 전달 경로 없음, 오디오 샘플 수 검증 불가, probe 필드 오기 | `AlphaWriter(…, audio_wav)`로 처음부터 넘김(소리를 프레임보다 먼저 만듦), `AudioStream.samples` 추가, 이미 있는 `profile`·`pix_fmt`는 유지로 정정 |

---

## 부록: 근거 원장

### 사실 (실측·코드·기록 근거, 2026-10-14)

**FilmCraft 0.7.2 합성 (scratchpad 실측 + codex `gpt-6.1-sol` 소스 조사)**
- 알파가 합성되는 형식: ProRes 4444 MOV, VP9/VP8 WebM 알파, PNG 정지·시퀀스, GIF/APNG. PNG-in-MOV·QuickTime Animation(qtrle)은 디코더 없음(오프라인 처리). Apple HEVC 알파는 알파를 버림(불투명). 실측: 640×360, 파랑 위 빨강 100/50/0%.
- 알파는 straight로 기대한다. premultiplied를 넣으면 두 번 곱해져 가장자리가 어두워진다(`crates/frame/src/lib.rs:454`). Chrome 스크린샷은 straight.
- 합성은 항상 선형 광. "Composite in Linear Color"는 켜진 채 잠겨 있다(`crates/ui-egui/src/panels/sequence_settings.rs:17`). 실측: 50% 빨강 over 파랑 = (188,0,187), sRGB 블렌딩이면 (128,0,127). 1080×1920 검정→투명 그라디언트(같은 HTML): y=150에서 FilmCraft 61 vs 브라우저 27, y=300에서 86 vs 54. 92% 파란 카드도 옅어짐. 4일차의 "그라디언트 도형이 60%까지 오르다 100%로 튄다"는 코드 결함이 아니라(codex: 연속 보간 확인) 선형 합성의 지각 효과로 보인다.
- 색 태그 없는 ProRes: SD 크기는 BT.601, HD 이상은 BT.709로 해석(`crates/codecs/src/stream_color.rs:74`). 태그 없는 SD 실측 빨강 (255,25,10) → BT.709 태그 후 (255,0,10).
- 이미지 시퀀스(`file.importImageSequence`)는 `media.indeterminateTimebase` 기본 29.97df. 일반 `import`는 번호 PNG를 정지 이미지로 받는다.
- 100% 속도에서 fps가 다르면 프레임을 반복·누락(floor/hold), 블렌딩 없음. `timeline.place`는 양 끝을 시퀀스 프레임에 반올림.
- 기본 미디어 스케일링 없음(원본 크기로 가운데). `timeline.place` 기본은 덮어쓰기, `"track":"new"`는 맨 위에 비디오 트랙 추가.
- 소리 있는 클립을 `timeline.place {"track":"new"}`로 놓으면 소리가 A1에 덮어쓰기로 들어간다: talk A1 0–4 s 위에 0.5 s에 3 s 클립 → A1이 talk 0–0.5, 클립 0.5–3.5, talk 3.5–4로 잘림. `"audioTrack":"new"`면 A1 그대로, 소리는 A2(실측). `graphics.newFromFile {"path","time"}`은 같은 클립을 V2에 놓되 소리 클립을 만들지 않는다(실측).
- 같은 경로로 다시 렌더한 오버레이는 헤드리스 `render`·`export`가 새 내용으로 읽는다(실측: 카드 색 (35,44,166) → (200,0,0)). 실행 중인 앱의 캐시 동작은 미확인.
- 네이티브 그래픽: 텍스트·도형 레이어, 2색 선형 그라디언트, 글자 범위 스타일(`graphics.setCharStyle`), 키프레임(`effects.setParam keyframe:true`), 애니메이션되는 마스크, 블렌드 모드, 트랙 매트(V1–V4), 조정 레이어, 중첩, 전환 다수. 템플릿 8개(롤·크롤 외 정적). 글자·단어 단위 애니메이터 없음. HTML·SVG·Lottie 렌더러 없음. 캡션 트랙 스타일은 font·size·color·background·align·anchor·margin뿐(그림자·외곽선 없음), `graphics.upgradeCaption`이 캡션을 그래픽으로 바꾼다.
- FCP7 XML 인계: 네이티브 그래픽은 넘어가지 않고 경고만, 렌더한 오버레이 미디어는 일반 클립으로 넘어간다.

**HTML → 알파 영상 (scratchpad 실측)**
- Playwright(uv 캐시 1.63) + 설치된 Google Chrome(`channel="chrome"`), `window.seek(t)` 페이지, `omit_background` 캡처 → ffmpeg ProRes 4444 `yuva444p10le` BT.709 태그. 1080×1920 30fps 3초: 캡처 39–44 ms/프레임, 기동 1.3–6.4 s, 인코딩 1.3 s, 18 MB. Paperlogy 한글 정상. FilmCraft 합성 확인.

**HyperFrames 0.8.157 (codex 조사, `.tmp/hyperframes`)**
- `render --format mov` = ProRes 4444 `yuva444p10le`, BT.709 태그, 정확한 유리수 fps. 길이는 루트 `data-duration`.
- 비용: Node ≥22, Chrome 확보, 렌더 컴파일 중 CDN(GSAP)·Google Fonts 네트워크, 프레임워크 계약 실수 시 빈 프레임·멈춘 애니메이션, 릴리스가 하루 여러 번(10/12–14에 .150→.157), 21개 스킬과 라우터. NLE용 투명 오버레이 절차·FilmCraft 어댑터 없음.
- 인기의 이유: 편집기 없이 HTML로 영상 전체(장면·오디오 믹스·자막·TTS·전환)를 만드는 틀, 블록 210개, Studio, 클라우드 렌더, Apache-2.0, 에이전트용 CLI·스킬, Opus 5.5 코드 모션 열풍과 시기.

**prompt-motion.com (ultra-search로 236개 항목 전수)**: 스택을 밝힌 약 58개 중 순수 HTML/Canvas/JS/Three.js(+Playwright/ffmpeg) 약 30, Remotion 13, HyperFrames 10. 개선 프롬프트 패턴: HTML 한 파일, `window.seek(t)` 안에서 시간으로 계산, Playwright 캡처, 전체 렌더 전 박자별 스틸 확인.

**awesome-opus5-5-videos (`.tmp/awesome-opus5-5-videos`, 703개, 성진 제공)**: 태그 canvas 267 · svg 183 · threejs 131 · shader 92 · gsap 86, 본문 언급 Remotion 98 · HyperFrames 24 · Playwright 32. 편집 영상 그래픽 사례(@stokebuilder)는 "35–50개 과감하게"를 원함 → 그래픽 밀도는 취향이라는 반례.

**사용자의 실제 작업 기록**
- 3일차 숏츠(HyperFrames Studio, 10/12): 교정 — 자막 간 전환 불필요, 상단 타이틀 애니메이션 불필요, 이름표·"'가품'이었다" 강조 효과 삭제("촌스러워 보여"), 데이터 PPT 대신 문제를 직관적으로 보여 주는 기사·UI 이미지만, 이미지는 앞 자막부터 충분히 길게, "(보도에 따르면)" 회색, 테두리 없는 자막, 헤드라인은 확대보다 형광펜. "`simple is the best` 원칙을 고수하면서도 필요한만큼의 애니메이션".
- 4일차 숏츠(FilmCraft 스킬, 10/14): 상단 검정 그라디언트, 하단 `#0018A8` 그라디언트(PNG 대신 직접), 타이틀(빨간 바)·태그·로고, 그림자 자막(그래픽 텍스트로 28개 재작성), 핵심 자막 빨강, 레퍼런스 위치 픽셀 측정, 아웃트로 qtrle → ProRes 4444, 흰색 딥. 협업 리듬은 스킬대로 작동.
- `data/` → `~/💎Obsidian/.tmp/유튜브`(에피소드 폴더 + `assets/`), 미추적. 스킬은 `~/💎Obsidian/🐝Work/.claude/skills/filmcraft`로도 링크. 이웃 스킬: `design`(모델 호출 비활성, `data/`에 작업 기록), `ppt`(HTML 슬라이드), `k-politics`.

**기준선 대조 (스킬 없음, `claude -p --safe-mode --restricted --strict-mcp-config --tools Bash Read Write Edit Glob Grep`, `claude-opus-5-5`, effort xhigh, 2026-10-14)**

| 과제 | 비용·턴·시간 | 고른 방식 | 잘한 것 | 헛걸음·결함 |
|---|---|---|---|---|
| g1 | $4.90 · 89턴 · 22분 | FilmCraft 네이티브(중첩 시퀀스 카드 + Motion 키프레임 확대 + 빨간 박스) | 단어 타이밍에 맞춘 확대·박스, 얼굴 회피, 절제 | 키프레임 시간 기준·이징·중첩 시행착오(t1–t10·easetest), faster-whisper 설치, `/tmp` 쓰기·Read 거부, 저해상도 캡처 확대로 흐림 |
| g2 | $4.40 · 97턴 · 20분 | FilmCraft 네이티브 그래픽(바·텍스트 키프레임) | 방송 자막을 덮고 퇴장, Noto Sans KR, −14 LUFS | Whisper 설치 시도, `/tmp` 쓰기·Read 거부 4회 |
| g3 | $2.33 · 58턴 · 10.5분 | HTML → puppeteer-core(npm) 투명 캡처 → ProRes 4444 → V2 | 단어별 칸 채우기, 얼굴 회피, 컷에 맞춘 진입, PSNR 검증 | 렌더러 작성, 무태그 BT.601로 빨강 밝아짐→재인코딩, ffmpeg(sRGB) 미리보기, faster-whisper 버전 충돌, 작업 폴더 밖 쓰기 |

### 추론
- 렌더 명령 하나는 자리를 번다: 프레임마다 seek, 폰트 대기, 투명 캡처, straight 알파 ProRes 4444, 네 색 태그, 시퀀스와 같은 크기·정확한 fps, 원자적 교체는 매번 같은 방식이고 조금만 어긋나도 조용히 틀린다(g3의 렌더러 작성·색 재인코딩).
- 그래픽이 화면에 앉는 모양은 브라우저가 아니라 FilmCraft 합성으로 판정해야 한다(선형 광 실측).
- 기준선이 디자인·타이밍을 잘했고 성진님이 "어떤 영상이든 틀린 문제는 없다"고 판정했으므로, 장르·디자인 지식을 더하면 모델을 좁히기만 한다.

### 열린 질문
- 없음. 구현 중 실측으로 정할 것: 사실 23(같은 경로에서 길이·소리 유무가 바뀐 파일과 놓인 클립), 사실 24(HLG 시퀀스의 BT.709 오버레이), 브리지에서 같은 경로 재렌더 반영(단계 13). 각 결과에 따라 `next` 문구·`graphic` 변환·SKILL.md 17번 절이 정해지며, 결정이 바뀌는 결과면 성진님께 묻는다.

**재실험용 과제 문장** (단계 12, scratchpad는 다음 세션에서 사라지므로 여기 보존)
- 공통 꼬리: "도구: 이 맥에는 FilmCraft(어도비 프리미어 프로를 클론한 오픈소스 영상 편집기)가 설치되어 있고, 그 CLI `filmcraft-cli`가 PATH에 있어. ffmpeg/ffprobe, Python(uv), Node.js(npx), Google Chrome도 있어. FilmCraft GUI 앱은 띄우지 말고 CLI로 작업해. 끝나면 무엇을 했고 결과물이 어디 있는지 짧게 보고해."
- g1 (`media/`: `~/.hyperframes-studio/숏츠 레퍼런스 디자인 재현/assets/`의 `컷편집.mp4`·`컷편집.srt`·`아기 발진.png`·`아이템 위너.png`): "`media/컷편집.mp4`는 내가 컷편집을 마친 국정감사 질의 숏츠야(자막 원고는 `media/컷편집.srt`). 아기 발진 보도 얘기가 나오는 대목에 `media/아기 발진.png` 기사 캡처를, 아이템 위너 얘기가 나오는 대목에 `media/아이템 위너.png`를 띄워서 문제의 심각성이 직관적으로 보이게 해 줘. 그냥 띄우기만 하면 밋밋하니까 말하는 포인트에 맞춰 주목할 수 있는 효과를 넣되, 너무 번잡하지 않게. 결과 영상과 FilmCraft 프로젝트 파일을 `out/`에 남겨 줘."
- g1 후속(`--resume`): "아기 발진 기사는 확대보다는, 말하는 타이밍에 헤드라인에 형광펜을 긋듯이 강조하는 게 좋겠어."
- g2 (`media/`: `.tmp/etc/국회 회의 영상.mp4`): "`media/국회 회의 영상.mp4`는 국정감사 질의 영상이야. 앞 1분만 써서 유튜브용 영상으로 만들되, 시작 부분에 질의하는 의원을 소개하는 하단 자막(로워서드)을 애니메이션으로 넣어 줘. 이름은 "김형연 의원", 소속은 "조국혁신당 · 정무위원회". 결과 영상과 FilmCraft 프로젝트 파일을 `out/`에 남겨 줘."
- g3 (`media/`: `~/💎Obsidian/.tmp/유튜브/261013_국정감사 4일차/`의 `컷편집2.mp4`·`컷편집2.srt`): "`media/컷편집2.mp4`는 국정감사 숏츠 컷편집본이야(자막 원고는 `media/컷편집2.srt`). "문안 만드는 데 두 달, 설문 돌리는 데 두 달, 분석하는 데 두 달, 총 6개월짜리 조사" 대목에 그 내용을 한눈에 보여주는 모션 그래픽을 만들어 얹어 줘. 결과 영상과 FilmCraft 프로젝트 파일을 `out/`에 남겨 줘."
- g4 (소재 없음, 선택 `media/로고_김형연의 국정감사.png`): "유튜브 채널 '김형연의 국정감사' 영상 앞에 붙일 3초짜리 인트로를 만들어 줘. 로고(`media/로고_김형연의 국정감사.png`)가 나오고, 어울리는 효과음도 넣어 줘. 결과 영상과 FilmCraft 프로젝트 파일을 `out/`에 남겨 줘."
- 실행: 과제 폴더 = `task.md`, `media/`(`cp -c`), `out/`, `.fcdata/`. 기준선은 `cd <폴더> && FILMCRAFT_DATA_DIR="$PWD/.fcdata" claude -p --safe-mode --restricted --strict-mcp-config --tools Bash Read Write Edit Glob Grep --allowedTools Bash Read Write Edit Glob Grep --permission-mode acceptEdits --model claude-opus-5-5 --effort xhigh --max-budget-usd 15 --output-format json "$(cat task.md)"`. 스킬 포함은 `--safe-mode`를 빼고, 폴더의 `.claude/skills/video`에 레포 스킬을 **`data` 없이 복사**한다(`rsync -a --exclude data .claude/skills/video/ <폴더>/.claude/skills/video/` 후 빈 `data/`; 링크는 사용자의 실제 `data/`로 이어지므로 쓰지 않는다). `.mcp.json`은 두지 않는다. 전사에서 `Skill` 호출로 스킬 사용을 확인. 분석은 `result.json`의 비용·턴·`permission_denials`, `~/.claude/projects/*/<session_id>.jsonl`의 도구 호출 순서.

## 구현 기록 (2026-10-15)

- 재실험 명령은 `--restricted` 대신 `--setting-sources project`(+ `--tools … Skill`): `--restricted`는 프로젝트 스킬까지 꺼서 스킬 실험이 성립하지 않음(실측). 유저 스킬·전역 CLAUDE.md는 로드되지 않음을 확인.
- 재실험 결과(스킬 사본 a26bb6a, exp12b): g1 $3.02·63턴·16분(+후속 $3.84·17턴·7분, 페이지 수정·제자리 재렌더), g2 $2.40·58·12.9, g3 $2.19·56·10.6, g4 $1.33·29·5.6, g5 $2.40·45·11.4(이전 페이지·프레임을 먼저 읽고 같은 카드 스타일). 전부 graphic 경로, 렌더러 작성·색 재인코딩·permission_denials 0, 폴더 밖 쓰기는 g1 후속의 보조 스크립트 2개(../tools, 끝에 삭제) 1건, FilmCraft 렌더로 확인, A1 보존. 프레임 시트는 scratchpad exp12b/sheets/all.png.
- 브리지 실측: 실행 중인 앱은 열어 둔 렌더를 계속 디코드함(refreshChanged로도 안 됨) → media.replaceFootage(같은 경로)로 반영. graphic의 --bridge next.if_placed에 넣고 SKILL.md는 그대로.
- 사실 24: HLG/PQ 시퀀스에서 BT.709 오버레이는 SDR 클립과 같게 BT.2408 기준 백색으로 변환됨 → graphic은 HDR 전용 변환 없음.
- 렌더 속도: 1080×1920·3초·30fps·효과음, Chrome 기동 포함 3회 중앙값 8.7 s.
- codex 리뷰 1차 15건(14 채택, 1 기각→재리뷰에서 범위 확장해 채택), 2차 3건 채택, 3차 2건(1 한계로 기록, 1 수동 확인).
