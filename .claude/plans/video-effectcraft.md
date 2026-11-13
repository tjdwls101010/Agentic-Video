# `video` 스킬: EffectCraft(합성·모션 그래픽·VFX) 더하기 + 본문을 사실형으로 다시 쓰기 — 구현 계획

> 구현 단계 0에서 계획 모드의 지정 경로(`piped-sniffing-bumblebee.md`)에서 이 경로로 옮겼다.

## Context

- `.claude/skills/video`는 FilmCraft(프리미어식 편집기)를 CLI로 다루고, FilmCraft에 없는 도구 8개(`timeline` `qc` `frames` `captions` `transcribe` `waveform` `doctor` `graphic`)를 번들한 프로젝트 스킬이다(PR #1·#3·#5·#6). 공개 배포 기준이라 개인 취향은 본문에 넣지 않고, 사용자와 의논하는 동료로 동작한다.
- 성진님 목표: Claude가 사람 영상 편집자처럼 능숙하고 유연하게 일하도록 기능은 포괄적으로, 방법론·목적은 한정하지 않는다. 사람 편집자가 프리미어와 애프터 이펙트를 오가듯, FilmCraft에 더해 같은 팀의 합성 도구 EffectCraft(`effectcraft-cli` 0.24.1, `/Applications/EffectCraft.app` 0.24.1, 소스 참조 `.tmp/effectcraft`)를 쓸 수 있게 한다.
- 성공 기준은 품질 하나. skill-maker 프레임을 철저히 적용한다.
- 이번 계획이 내는 변경은 이유가 둘이라 PR도 둘이다: (A) EffectCraft를 쓸 수 있게 한다, (B) 기존 본문의 절차·규칙 문장을 "사실 + 이유"로 다시 쓴다(codex 감사 반영).

## 결정 요약 (이번 세션, 성진님 결정)

| 항목 | 결정 |
|---|---|
| 목적·범위 | 사람 편집자처럼 일하는 Claude. FilmCraft + EffectCraft + 번들 도구를 필요에 따라 고른다. EffectCraft는 편집 중 효과와 단독 모션 그래픽 둘 다 |
| 문서 분할 | `references/` 없이 SKILL.md 한 파일 유지(네 번째 같은 결정). 이전 계획의 재개 조건은 그대로: 어떤 분기 절이 커져 다른 경로가 내는 비용이 눈에 띄면 그 절만 뗀다 |
| 재작성 범위 | 전면 재작성은 아니다(codex·Claude 판단 일치). codex가 "이유보다 강한 규칙"으로 지적한 줄은 **전부** 다시 쓴다 |
| 반영 해석 | 줄에 담긴 사실은 남기고 명령형 절차만 그 절차가 지키려던 사실과 이유로 바꾼다. `data/`와 작품 폴더 모양은 이 스킬의 배포 관례라는 사실로 남긴다. 사실을 빼는 것은 낡았거나 도구가 소유한다고 확인된 경우뿐이고 PR 본문에 사유를 적는다. 바뀐 본문으로 과제를 다시 돌려 행동이 나빠진 줄은 되돌린다 |
| 그래픽 경계 | 기본값 없이 사실만. 선택은 그 자리에서 Claude가 이유와 함께 하고 사용자가 바꾼다. PR #3의 "디자인되는 그래픽은 HTML" 기본값은 내린다(기준선 B1·B2 판정: 둘 다 쓸 만함, 취향 차이) |
| HyperFrames | 범위 밖. 재개 조건: 대표 과제에서 `graphic`으로는 못 얻는 구체적 이점(중첩 컴포지션 재사용, 배치 변형 등)과 FilmCraft 인계 실측이 함께 나올 때 |
| 작품 폴더 | `.ecproj`와 그 렌더는 `graphics/`에 페이지와 함께 둔다(`graphics/` = 만든 그림의 원본과 렌더) |
| 실행 중인 앱 | EffectCraft는 헤드리스만 먼저. `.mcp.json`은 그대로. 브리지는 필요해질 때 별도 PR |
| 학습 모델 | MobileSAM을 이 Mac에 설치해 실측했다(승인). 설치된 채로 두고 사실 테스트가 쓴다 |
| 기준선 판정 | B1·B2: 둘 다 쓸 만함. B3: 방향은 맞고 품질만 아쉽다 → EffectCraft 절에는 매트 엔진의 사실과 왕복의 사실만 적는다 |
| codex 권고와 다르게 두는 세 줄 | L35(본문과 설치된 CLI가 어긋날 때 CLI가 맞다)와 L89(유튜브 챕터)는 삭제하지 않고 사실형으로 유지, L26(`qc` 통과)은 완료 조건 형식을 유지하고 `qc`가 재는 것과 못 재는 것의 사실을 덧붙인다 |
| `doctor` | EffectCraft 선택 항목과 `effectcraft` 유닛을 넣는다(근거 E31: 별도 릴리스 자산, 저장 때 드러나지 않는 스키마 거부) |

이전 계획에서 그대로 이어받는 결정: 프로젝트 스킬, 공개 배포 기준(개인 취향은 `data/`의 과거 작업에서 읽음), 장르·방법 규칙은 쓰지 않음, SKILL.md는 영어·한 덩어리 한 줄(승인 때 한국어 요약 동봉), 명령 사양은 CLI가 소유, 번들 도구는 Claude가 직접 하면 확실히 느리거나 틀리는 정해진 작업에만, 사실은 회귀 테스트로 지킴(테스트 더블 없음), 개발 기록은 커밋·PR 본문.

## 기준선 대조의 차이 → 스킬 안의 자리

스킬 없는 Claude(Opus 5.5)의 결과, 직접 실측, Claude 작업자의 왕복 실측에서 드러난 것만 자리를 얻는다.

| 드러난 것 | 근거 | 자리 |
|---|---|---|
| EffectCraft로 타이틀을 스스로 잘 만든다(명령 탐색, 한글, 트랙 매트, 알파 렌더) | B1 | 넣지 않음. 명령·레시피·예시 JSON은 `effectcraft-cli`가 소유 |
| 같은 타이틀이 HTML 길에서 비용 약 절반이고 판이 글 길이에 맞춰짐. EffectCraft 길은 앱에서 여는 프로젝트가 남음 | B1·B2 | 10절에 "무엇이 남고 어디서 고치는가"의 사실로 |
| 두 길 모두 ffmpeg로 얹어 확인(FilmCraft와 블렌딩이 다름), 쇼츠 UI 미대조 | B1·B2, E7 | 기존 문장(합성하는 쪽의 렌더, `frames --overlay`)을 컴포지션에도 걸리게 |
| "사람 뒤 글자 + 따라가는 이름표"를 해내지만 13분·$4.40. 내장 로토가 새서 손 마스크로 메움 | B3, E11 | 11절 매트 엔진의 사실 |
| 서브커맨드 뒤 위치 인자의 확장자 오타·프로젝트 누락이 데모에서 조용히 실행됨. `--empty` 없는 `--save-as`는 데모 내용이 든 프로젝트를 저장함 | E1, E14, E29 | 11절 |
| `set --time`은 레이어 시간이고 0은 In점이 아니라 `start`. 인터체인지로 온 트림 클립은 거의 모두 `start ≠ 0` | E17, E27 | 11절 |
| 인터체인지로 온 컴프의 렌더는 `--audio off`가 아니면 편집의 소리를 싣고, 그대로 놓으면 A1의 말을 덮어씀 | E28 | 10절 |
| 모델 선택이 호출마다 초기화되고, 고정 안 한 매트는 다음 호출이 내장 엔진으로 다시 계산해 빈 매트. 추적 범위 밖은 투명 | E23, E24, E26 | 11절 |
| 반투명이 EffectCraft 안과 FilmCraft 위에서 다르게 보임 | E7 | 10절 |
| 따라가는 모자이크·블러는 FilmCraft만으로 됨. 다른 레이어를 움직이는 추적과 자동 분리는 EffectCraft | E12, E13 | 10절 |
| EffectCraft에서 바로 낸 MP4는 moov가 끝에 있고, 라우드니스를 맞추는 명령이 EffectCraft에 없음 | E30 | Delivery |
| 없는 글꼴이 오류 없이 Inter로 대체 | E16 | 11절(M3 확인 뒤) |
| `effectcraft-cli`는 앱과 따로 받는 릴리스 자산이고, 스키마가 더 새 프로젝트는 앱이 거부함 | E31 | `doctor`(선택 항목) |

## 구현 후 디렉토리 구조 (바뀌는 곳만)

```
.claude/skills/video/
├── SKILL.md                         # 수정 (PR A, PR B)
└── scripts/
    ├── cli.py                       # doctor 도움말의 출력 설명에 effectcraft_cli 추가
    └── video/
        ├── effectcraft/__init__.py  # 신규 system 유닛: binary(), versions(), install_steps()
        └── doctor/__init__.py       # Facts에 EffectCraft 버전 둘, judge에 선택 항목 하나
tests/
├── support/__init__.py              # EFFECTCRAFT 탐색, needs_effectcraft, needs_mobilesam, ec()/ec_run()
├── effectcraft_facts/test_facts.py  # 신규: 본문의 EffectCraft 문장을 지키는 사실 테스트
└── video_skill/
    ├── test_structure.py            # KINDS에 "effectcraft": "system"
    ├── test_doctor.py               # EffectCraft 판정 사례
    └── test_skill_text.py           # EffectCraft 명령 id·옵션도 실제 CLI로 확인
README.md                            # 요구 사항·기능 표·구조·한계
.claude/plans/video-effectcraft.md   # 이 파일(각 PR이 자기 구현 기록을 더함)
```

`references/`, `.mcp.json`, `frames`·`graphic`·`qc`의 코드는 바꾸지 않는다. `frames --media X.mov --overlay <platform>`가 이미 EffectCraft 렌더에 쓰이고, 컴포지션 한 장은 `effectcraft-cli render-frame`이 준다. EffectCraft 명령을 감싸는 래퍼는 만들지 않는다.

## SKILL.md 섹션 구조와 줄별 처분

영어, 한 덩어리 한 줄, 한 파일. 현재 105줄 → 약 130줄 예상(200줄 예산 안). 줄 번호는 현재 파일 기준. "A"는 PR A(EffectCraft가 들어오며 틀려지는 줄과 새 절), "B"는 PR B(사실형 다시 쓰기). 아래는 담을 사실이고 실제 문장은 구현 때 쓰고 성진님이 승인한다.

### frontmatter (A)

- `description`: FilmCraft와 EffectCraft 둘을 CLI로 다룬다고 쓰고, 다루는 일에 합성·추적·매트·키잉과 EffectCraft 컴포지션을 더한다. 트리거에 합성, 트래킹, 추적, 로토, 크로마키, VFX, EffectCraft, `.ecproj` 추가. 제외 문장은 "FilmCraft's or EffectCraft's own source code".
- `allowed-tools`: `Bash(effectcraft-cli *)` 추가.

### 1. 제목·첫 문단 (L12~14, A)

- 제목 `# Making video with FilmCraft and EffectCraft`.
- 두 CLI가 자기 명령을 소유한다: `filmcraft-cli commands <filter>`/`describe <id>`, `effectcraft-cli commands --filter <text>`/`exec command.describe`. 이 스킬은 그것이 말하지 않는 것과 번들 도구를 담는다.

### 2. Working with the user (L16~22, B)

| 줄 | 담을 것 |
|---|---|
| L18 | 취향이 정하는 것의 목록(컷 리듬, 전환, 필러, 자막·타이틀 디자인, 그래픽, 룩, 음악 끝, 샷 순서)이 사용자의 선택이라는 사실. 어느 도구로 만들지는 이 목록에 넣지 않는다(10절: Claude가 고르고 이유를 말한다). 선택이 플랫폼 요건이나 아래 사실과 부딪힐 때의 결과를 말한다는 구절은 유지. "한 줄로 말하라, 그들 것을 따르라"는 프레임의 복사라 뺀다 |
| L19 | 관찰된 기본 행동으로 한정해 사실로: 순서에 아이디어가 없을 때 몽타주가 소스를 파일 순서로 도는 모양이 된 적이 있다 |
| L20 | `data/`는 이 사용자의 지난 작업 기록이고 거기 있는 것이 그들이 고른 것이라는 사실, 지난 작품은 그 작품에 필요했던 것을 보여 줄 뿐 다음 작품의 규칙이 아니라는 사실, 새 작품이 `data/<piece>/`에 가는 것은 이 스킬의 관례라는 사실. "graphics/의 페이지"를 "페이지와 컴포지션"으로(A) |
| L21 | 트림, 전환, 자막 스타일, 타이틀 문구는 한 번의 호출로 바뀌고 한 번의 렌더로 보인다(틀린 선택의 비용이 사용자의 한마디)는 사실 |
| L22 | 되돌리기 비싼 것과 그 이유를 종류별로: 하이라이트·요약이 남기는 구간(무엇이 핵심인지는 푸티지가 아니라 사용자가 아는 것이고, 후보 목록은 금방 읽히지만 거절된 선택 위에 쌓은 자막·그래픽·믹스는 다시 한다), 전체 룩, 넘겨받은 프로젝트 덮어쓰기(`--save`는 호출 사이 실행 취소가 없다), 모델 내려받기(작품 폴더 밖, 사용자 기계의 앱 공유 폴더에 남는다). 긴 내보내기와 분석은 되돌리기가 아니라 기다림의 비용으로 따로 |

### 3. Before you hand something over (L24~30, A+B)

| 줄 | PR | 담을 것 |
|---|---|---|
| L26 | B | 완료 조건 형식 유지(skill-maker가 허용: 넘기기 전에 성립해야 할 것을 확인 가능한 말로): 렌더한 납품물은 대상의 `qc`를 통과한다. 덧붙일 사실: `qc`의 검사에는 플랫폼 요건과 관행·이 스킬의 결정이 섞여 있고 `--help`가 구분한다, 통과가 작품에 대해 말해 주는 것은 없다, 대상이 아닌 파일(소리 없는 그래픽, 다른 크기)은 해당 없는 검사에서 떨어진다 |
| L27 | B | 컷은 문장을 끊거나 말을 이어 붙여 뜻을 바꿀 수 있고 프레임에는 안 보인다: 최종 컷의 말(`transcript.inspect`)을 앞뒤 맥락과 함께 읽어야 드러나며, 전사 자체가 틀릴 수 있다. `timeline --project`는 디스크에 저장된 프로젝트의 요약이다(앱의 저장 안 된 상태와 다를 수 있다) |
| L28 | A | 페이지나 컴포지션은 자기 프레임에서는 맞아 보여도 그것을 합성하는 편집 위에서는 다를 수 있다(움직이는 것은 들어올 때·가장 찼을 때·나갈 때가 각각 다르다): FilmCraft가 합성하면 `frames --project`가 보여 준다. `graphic`의 `fallback`·`blocked`와 EffectCraft의 대체 글꼴은 그림을 바꾼다 |
| L29 | B | 결과가 보여 주지 않는 것: 컷을 들을 수 없으므로 소리의 흐름은 미확인이고, `waveform`은 신호와 타이밍이지 어떻게 들리는지가 아니다. 일반 인계 문구는 뺀다 |
| L30 | A | 사용자가 다시 열어 고칠 수 있는 것: 편집은 `.fcproj`, 컴포지션은 `.ecproj`, 그래픽은 그 페이지. ffmpeg로 그림이나 소리를 바꾸면 결과 파일은 남아도 그 조작은 어느 프로젝트에도 기록되지 않아 사용자가 열어 조정할 수 없다. `qc`가 이름 붙인 무손실 remux는 그림과 소리를 바꾸지 않는다 |

### 4. Before the first command (L32~35, A+B)

- L34(A): `doctor`는 이 기계에서 도구를 막는 것과 고치는 명령을 알려 준다. CLI와 앱의 버전이 다르면 저장할 때는 아무 경고가 없고 사용자가 앱에서 열 때 드러난다(더 새 스키마의 프로젝트를 앱이 거부). 선택 항목은 그 작업이 필요로 할 때만 의미가 있고 EffectCraft는 선택 항목.
- L35(B): 두 앱은 자주 릴리스되어 이 문서의 문장이 예전 버전을 말할 수 있다: 문장과 설치된 CLI가 어긋나면 CLI가 맞다. (codex는 삭제를 권했으나 유지: 본문과 관찰이 부딪힐 때 어느 쪽이 이기는지를 정하는 사실이다.)

### 5. Headless or the running app (L37~41, A+B)

- L39(B): 헤드리스는 디스크의 파일을 바꾸고 화면에는 아무것도 보이지 않으며, 실행 중인 앱(브리지)은 보는 사람에게 변경을 보여 준다. 헤드리스에는 자동 저장이 없어 저장하지 않은 호출의 결과는 사라진다.
- L40: `--project`가 없는 파일에 어떻게 실패하는지와 첫 프로젝트를 만드는 조합(`--save-as P import`)이 `filmcraft-cli --help`로 드러나는지 실행으로 확인(M16). 드러나면 삭제, 아니면 유지.
- L41(A): 앱이 연 프로젝트를 디스크에서 고치면 나중에 저장하는 쪽이 다른 쪽의 저장 안 된 변경이나 이후 변경을 덮어쓴다. `.ecproj`도 같고, EffectCraft CLI의 잠금은 앱을 포함하지 않는다. 헤드리스로만 몰아도 사용자가 앱을 열어 둘 수 있으므로 해당한다.

### 6. How filmcraft-cli fails quietly (L43~53, B)

제목에 `filmcraft-cli` 명시. L47~50, L52~53 그대로.

- L45: 새 세션 사실 유지. `trim.*`·`source.*`는 헤드리스 호출에 없는 선택과 Source 모니터에 작용한다는 이유로. 실패한 줄이 저장 전에 `run`을 멈춘다는 사실 유지.
- L46: 원인들(모르는 키·옵션 무시, `time`의 float, 오타 난 `--bridge`, 나뉘지 않은 `$OPTS`)은 그대로 유지. "모든 결과에서 no-op을 읽어라"를, 성공과 exit 0이 변경을 뜻하지 않는다는 사실과 표지로. 표지의 `null`은 "id나 경로가 와야 할 자리의 `null`"로 좁힌다(`clip.speedDuration`은 `null`을 돌려주며 정상 적용, M18로 확인).
- L51: Inter에 한글이 없다는 사실과 그 결과(기존 사실 테스트가 지키는 내용 그대로), 한국어 글꼴은 `fonts.list`에서, 그려졌는지는 렌더가 보여 준다.

### 7. Seeing and hearing the edit (L55~58, A+B)

- L57: 재생할 수 없다. 그림은 `frames`, 컴포지션 한 장은 `effectcraft-cli render-frame`(컴프 시간, `--transparent`로 알파)(A). `waveform`은 신호와 타이밍을 그린다. `timeline`은 요약이고 `inspect sequence`는 전부를 담되 클립마다 커진다(B).
- L58(B): 10비트 AV1/HEVC는 프레임당 렌더가 느리다는 사실만.

### 8. What does not depend on taste (L60~65, B)

- L62: 확신 없는 화면 속 이름·용어는 공개 영상에서 틀릴 수 있고 전사만으로는 확정되지 않는다. 추측으로 넣은 것은 사용자가 알아야 고칠 수 있다.
- L63 유지.
- L64: 더한 글자가 박힌 자막·방송 수퍼 위에, 글자와 얼굴이 대상 플랫폼 UI 아래에 놓일 수 있다(`frames --overlay <platform>`이 그려 준다). 어떻게 풀지는 선택이다.
- L65: 시퀀스의 크기와 프레임레이트는 만들 때 정해지고 이후 모든 배치가 그 안에서 이뤄진다. 60p를 30p로 바꾸면 움직임이 버려지고, 납품 크기와 다른 시퀀스는 내보낼 때 스케일된다.

### 9. Speech as material (L67~75, B)

- L69: 기본 엔진으로 새로 전사하면 오디오 전체가 제3자(OpenRouter)에게 가고 돈이 든다(`--engine local`과 `--from-json`은 보내지 않는다). 엔진 비교·교정·적용은 `--help`.
- L70, L72, L73, L75 유지.
- L71: 사실과 이유를 모두 유지(영어 필러만 지우고 성공을 보고, 목록은 뒤따르는 말과 무관하게 모두 지움, 엔진이 전사에서 뺀 필러는 못 지움, 쉼을 먼저 지우면 필러 자리에 틈이 남음). 담화 표지 예시 목록만 줄이고 "그"·"저" 함정은 유지.
- L74: 대안들의 실패(`transcript.createCaptions`는 짧은 문장을 다음에 붙이고 폭을 재지 않음, `captions.add`/`setTimes`는 겹침을 거부하고 가져오기는 관대함)와 `captions`가 하는 일(번인 글꼴로 줄 폭을 재고 가져오기 명령을 `next`로 줌).

### 10. Where a picture is made (L77~83 대체, A)

When: 타이틀, 로워서드, 콜아웃, 숫자·차트, 삽입 이미지의 연출, 인트로, 찍힌 화면에 거는 효과, 단독 모션 그래픽.

결정표가 되지 않도록 "어디서 만들었느냐가 바꾸는 것"을 축으로 쓴다. 기본값과 "사용자와 정한다"는 쓰지 않는다.

1. **무엇이 남고 누가 어디서 고치는가.** FilmCraft 네이티브 텍스트·셰이프는 사용자가 FilmCraft에서 안의 요소까지 고칠 수 있고 FCP7 XML 인계에서는 빠진다. `graphic`으로 렌더한 페이지(첫 페이지 전에 `--help`)는 코드를 고쳐 다시 렌더해야 바뀌고, EffectCraft 컴포지션은 사용자가 EffectCraft 앱에서 여는 `.ecproj`로 남는다. 페이지와 컴포지션은 FilmCraft 안에서는 렌더된 클립이라 자리·길이·Motion만 바뀐다.
2. **찍힌 화면의 픽셀이 필요한가.** FilmCraft: 클립 자기 픽셀의 효과, 대상을 따라가는 마스크 안의 블러·모자이크(`masks.track`), 키잉, 안정화. EffectCraft: 추적한 점이 다른 레이어를 움직이고(대상을 따라가는 라벨), 매트가 대상을 화면에서 분리한다(사람 뒤 글자). 페이지는 푸티지를 보지 못한다.
3. **배치와 반복 비용(확인된 것만).** 페이지는 글 길이에 맞춰 스스로 배치된다. 컴포지션은 좌표에 놓이므로 글 크기를 따라가는 배치는 재거나 익스프레션으로 만들어야 한다(M19로 확인 뒤 문구 확정). 네이티브 그래픽의 키프레임 조정은 시험 렌더가 거듭 든다(기존 문장, PR #3 실측).
4. **FilmCraft에서 EffectCraft로**: 인터체인지 XML(`file.exportInterchange` → `file.importTimeline`)이 클립의 자리·길이·트림·Motion·정속 변경을 옮기고 네이티브 그래픽·효과·속도 램프는 빠뜨린다(양쪽의 `report`·`warnings`가 알려 줌). M9로 범위 확정.
5. **EffectCraft에서 FilmCraft로**: 렌더가 무엇을 담았느냐가 돌아가는 방식을 정한다. 알파가 있는 덧그림(ProRes 4444)은 클립 위 트랙에, 화면 전체를 다시 만든 결과는 원래 클립의 자리에(위에 얹으면 그림과 소리가 겹친다). 인터체인지로 온 컴프의 렌더는 `--audio off`가 아니면 편집의 소리를 싣는다. 구간 렌더는 타임코드가 없어 놓을 시각은 Claude가 들고 간다. FilmCraft는 가져올 때 읽은 길이와 소리를 유지하므로 더 짧은 재렌더는 경고 없이 마지막 프레임에서 멈춘다.
6. **반투명**(L83 확장): FilmCraft는 선형광으로 블렌딩하고 EffectCraft는 기본 설정에서 그렇지 않다. 알파로 렌더해 FilmCraft에 놓은 반투명 층은 EffectCraft 자기 프레임이나 브라우저·ffmpeg 합성과 다르게 나온다(실측한 기본 설정에서 어두운 층은 약하게, 밝은 층은 강하게). 합성하는 쪽의 렌더가 보여 준다.

L79(나열)는 When 줄로 흡수. L82(닮은 두 경우)는 2번 축이 같은 구분을 이유와 함께 말하므로 예시 하나로 줄여 2번에 붙인다.

### 11. How effectcraft-cli fails quietly (신규, A)

When: `effectcraft-cli`를 몰 때. 모르는 옵션과 최상위 파라미터 키는 거부된다(FilmCraft와 다름). 거부되지 않는 것:

1. 프로젝트를 주지 않거나, 서브커맨드 뒤 위치 인자가 `.ecproj`로 끝나지 않으면 내장 데모 프로젝트에서 실행되고 exit 0이다(`--project`로 준 경로는 그대로 열린다). `--empty` 없는 `--save-as`는 데모 내용이 든 프로젝트를 저장한다. `--save`는 `render`·`render-frame`·`info`·`props`·`get`에서 무시된다(E1, E14, E29, M1).
2. 호출마다 새 세션: 레이어·키 선택, 고른 매트 모델, `prefs.set`은 다음 호출에 없다(E15, E23).
3. `set --time`과 키프레임 명령의 시간은 `timeBase:"comp"`를 주지 않으면 레이어 시간이고(`set`에는 그 옵션이 없다), 레이어 시간의 0은 In점이 아니라 레이어의 `start`다. `render-frame`·`get`은 컴프 시간. 인터체인지로 온 트림 클립은 대개 `start`가 0이 아니다. 결과의 `compTime`이 실제 자리를 보여 준다(E17, E27, M2).
4. 없는 글꼴 이름은 오류 없이 Inter로 바뀐다. 이름은 `text.fonts`에서, `file.findMissing {"what":"fonts"}`는 레이어 단위 글꼴만 알려 준다(E16, M3 확인 뒤).
5. 매트: 시험한 실제 화면에서 내장 엔진의 Object Matte는 성공을 돌려주며 사실상 빈 매트를, Roto Brush는 거친 매트를 냈다. 학습 모델은 내려받는 것이고 CPU로 돈다. 고정하지 않은 매트는 프로젝트에 저장되지 않고 렌더하는 호출의 엔진이 다시 계산하는데, 새 호출의 엔진은 내장 엔진이다. 추적 범위 밖에서는 레이어 전체가 투명하다. 이 명령들은 그림과 무관하게 성공을 보고하고 `render-frame --transparent`가 매트를 보여 준다(E11, E23~E26. Roto Brush의 저장 규칙은 M8 뒤에 범위 확정).
6. 측정해 재현되면 넣을 후보: 읽지 못하는 푸티지가 그림 없이 지나감(M5), HDR 푸티지의 색(M6), 3D 컴프의 CPU 렌더 시간(M4. `info`가 렌더러를 알려 주므로 계획을 바꿀 만큼일 때만).

넣지 않는 것: 명령 목록, 추적·키잉 레시피, 예시 JSON, 형식 목록, 기본값 표, gaps 문서 요약, "새 앱이라 조심" 같은 일반 경고.

### 12. Delivery (L85~89, A+B)

- L87(B): 마크가 있으면 내보내기 기본 범위는 In~Out이고 전체는 `range:"entire"`. 렌더는 자막을 보여 주지만 내보내기는 `burnCaptions`·`captionSidecar`가 정한다. 라우드니스 목표는 `qc` 대상 값이거나 사용자가 정한 값.
- L88(B): `--allow-offline`은 빠진 미디어를 자리 표시 프레임으로 채운 파일을 성공으로 낸다(없으면 경고하고 exit 1). `media.findMissing`이 다시 잇는다.
- L89 유지: PR #1 기준선 R2에서 MP4 챕터 리먹스를 시도한 실패가 근거다.
- 신규(A): EffectCraft에서 바로 낸 MP4는 moov가 끝에 놓이고 EffectCraft에는 라우드니스를 맞추는 명령이 없다. 소리가 있는 단독 작품의 납품 음량은 FilmCraft 내보내기가 맞춘다(E30, M20으로 확인).

### 13. Working files (L91~95, A+B)

- L93: 작품 폴더 모양은 다음 세션이 길을 찾는 관례라는 사실로 유지. `graphics/`는 페이지·컴포지션(`.ecproj`)과 그 렌더(A). 작품에 필요한 것은 모두 그 폴더에 있고, 사용자 기계의 다른 곳에 쓴 것은 그들이 청하지 않았고 찾지 못할 것이라는 사실, `/tmp`의 파일은 제한된 세션에서 읽지 못할 수 있다는 사실(B). 프로젝트가 의존하는 재료와 렌더를 지우면 프로젝트가 깨진다는 이유 유지. "작품 폴더만으로 프로젝트가 열린다"는 M13 결과에 맞는 말로.
- L94(B): 번들 도구가 쓰는 의존성은 `uv run`·`uvx`가 가져오고 전역 설치는 `doctor`가 나열한 것뿐이다.
- L95(B): `FilmCraft Previews/`는 렌더 캐시이고 결과물이 아니다. 두 CLI가 프로젝트 옆에 남기는 0바이트 `.X.lock`도 결과물이 아니다(M21 확인 뒤).

### 14. Working in the running app (L97~105, B)

FilmCraft 앱에 한정(이번 결정). 연결 방법, `render`는 헤드리스 전용이라 `render_frame`, 경로 없는 프로젝트의 저장 대화상자와 60초 멈춤, 디스크와 앱의 차이는 유지. 규칙 셋을 사실로:

- 앱에 열린 프로젝트에는 사용자의 저장 안 된, 하다 만 편집이 들어 있다. 브리지에서 저장하면 그것이 그들의 파일에 확정되고 마지막으로 저장했던 버전은 돌아오지 않는다. 앱을 종료하면 저장 안 된 편집이 사라진다.
- `ui_*`는 보이는 창을 움직이므로 사용자가 타이핑 중이면 그 입력과 섞인다.

## 번들 코드: `doctor`와 `effectcraft` 유닛 (PR A)

자리를 얻는 이유(Model over machinery): macOS에서 `effectcraft-cli`는 앱과 따로 받는 릴리스 자산이라 모델이 저장소와 자산 이름을 알 수 없고(E31에서 `gh release view`로 확인), 스키마가 더 새 프로젝트를 앱이 거부하는 것은 저장 시점에 드러나지 않는다(E31, 코드 근거). FilmCraft 항목과 같은 이유이며 설치 여부를 반복 확인한다는 것이 이유는 아니다.

- `video/effectcraft/__init__.py`(system, shared만 import): `binary()`(`shutil.which("effectcraft-cli")`, 없으면 `~/.local/bin/effectcraft-cli`, 없으면 `ToolError`), `versions() -> (cli, app)`(`--version`의 마지막 토큰, `EffectCraft.app/Contents/Info.plist`의 `CFBundleShortVersionString`), `install_steps(version)`(`gh release download v<ver> -R storytold/effectcraft -p 'effectcraft-cli-<ver>-macos-universal.zip' -p SHA256SUMS.txt` → 검증 → `~/.local/bin` 설치). `video/filmcraft/process.py`의 세 함수와 같은 모양이고 두 유닛은 서로 import하지 않는다. 공통 부분을 shared로 뽑는 것은 세 번째 앱이 생길 때.
- `video/doctor/__init__.py`: `Facts`에 `ec_cli_version`, `ec_app_version`. `judge`에 `effectcraft_cli` 항목 하나, `required: False`.

| 상태 | `ok` | `value` | `why` / `next` |
|---|---|---|---|
| CLI·앱 모두 없음 | False | "not installed" | EffectCraft 컴포지션에만 필요. `next` 없음 |
| 앱만 있음 | False | "not installed (app X)" | CLI는 앱과 따로 받는 릴리스 자산. `next`에 `install_steps(X)` |
| CLI만 있음 | True | "Y (no app: headless only)" | 헤드리스 작업에는 앱이 필요 없다 |
| 버전 일치 | True | "Y (app Y)" | — |
| 버전 다름 | False | "Y (app X)" | 더 새 CLI가 저장한 프로젝트는 스키마가 달라지면 앱이 거부한다. `next`에 `install_steps(X)` |

어느 경우에도 전체 `ok`는 EffectCraft 때문에 False가 되지 않는다(선택 항목).

- `cli.py`: `doctor --help`의 출력 설명에 새 항목 반영. 새 명령·새 옵션 없음.

## README (PR A)

요구 사항 표에 EffectCraft(선택)와 CLI가 별도 자산이라는 것, 기능 표에 합성·추적·매트, 구조와 테스트 실행법에 `tests/effectcraft_facts`, 한계에 "EffectCraft는 알파 단계이고 헤드리스만 지원(브리지 미지원)".

## 테스트 설계 (`coding` 스킬 기준, 이음매는 기존 합의 그대로)

새 이음매 종류는 없다: CLI 프로토콜, 유닛 인터페이스, 구조 테스트, 실제 CLI에 대한 사실 테스트. 더블 없음.

| 이음매 | 테스트 | 기대값의 출처 |
|---|---|---|
| `doctor.judge(Facts)`(순수) | 위 판정표의 다섯 상태, 전체 `ok`가 EffectCraft와 무관함 | 판정표 |
| `cli.py doctor`(실제 진입점) | `effectcraft_cli` 항목이 있고 `required`가 False(버전 문자열은 고정하지 않음) | 계약 |
| `install_steps` | 만든 명령의 자산 이름이 `gh release view v<설치된 버전> -R storytold/effectcraft`의 자산 목록에 있다(네트워크가 필요해 `slow`, 구현 때 1회는 반드시 실행) | GitHub 릴리스 |
| 구조 테스트 | `effectcraft`가 system, import 방향 | `KINDS`, `MAY_IMPORT` |
| `tests/effectcraft_facts`(실제 `effectcraft-cli`·`filmcraft-cli`, ffmpeg 합성 푸티지) | 아래 | 아래 |
| `test_skill_text.py` | 본문의 `effectcraft-cli` 옵션이 실제 도움말에 있다. 본문이 EffectCraft 것으로 말하는 id를 테스트 안에 명시적 집합으로 두고, 그 집합은 EffectCraft에, 나머지 id는 FilmCraft에 존재해야 한다(`file.findMissing`과 `media.findMissing`처럼 헷갈리는 쌍을 잡기 위해 "둘 중 하나에 존재"로 하지 않는다) | 설치된 CLI |

사실 테스트의 원칙:

- 기대값은 통제된 입력에서 따로 계산한 값이다: 알려진 색·알파의 합성 화면(회색 128 위 50% 검정·흰색을 감마와 선형으로 손계산한 64/192, 93/205 ±2), 프레임마다 알려진 만큼 움직이는 표식, 알려진 주파수의 소리, 알려진 시작 프레임.
- 각 테스트는 같은 테스트 안에 대조군을 둔다: `--empty` 있음/없음, 위치 인자/`--project`, `timeBase` 있음/없음, `--audio off` 있음/없음, freeze 있음/없음, 추적 범위 안/밖. 문장이 말하는 실패와 그것이 멈추는 경계를 둘 다 고정한다.
- 왕복 픽스처 하나를 여러 테스트가 쓴다: 움직이는 표식과 소리가 있는 짧은 클립을 0이 아닌 시퀀스 위치에 트림해 놓고, 인터체인지 → 컴포지션에 가장자리가 부드러운 반투명 요소 → 알파 렌더 → FilmCraft에 덧그림으로, 또 전체 화면 렌더를 교체로 놓은 뒤, 기대 프레임·위치·오디오 스트림·길이를 확인한다(E8, E27, E28, M10, M14, M15).
- 합성 푸티지로 재현되지 않는 문장(실제 화면에서 내장 엔진의 빈 매트, E11)은 M22에서 재현되는 합성 장면을 찾고, 못 찾으면 그 문장을 "테스트 없음, 근거는 이 파일의 실측"으로 테스트 파일 머리에 명시한다.
- 건너뜀: `needs_effectcraft`, `needs_mobilesam`(테스트가 내려받지 않음), 매트 계산은 `slow`. skip은 보이게 두고, PR 본문의 검증 절에 이 Mac에서 skip 없이 돈 결과와 모델·버전을 적는다.
- 본문 문장이 승인·대조 과정에서 바뀌면 머지 전에 문장과 테스트를 다시 대조한다(각 테스트 docstring이 지키는 문장을 인용).
- `doctor` 변경은 레드(새 판정 사례 실패 확인) → 그린.

## 구현 단계 (TaskCreate 트래커. description에 완료 판정을 그대로 쓴다)

PR A를 끝까지(작성 → 리뷰 → 승인 → 검증 → 머지) 마친 뒤, 머지된 `main`에서 PR B를 시작한다. 리뷰와 검증은 실제로 머지될 트리에 대해 한다.

| # | 단계 | 완료 판정 |
|---|---|---|
| 0 | 계획 파일을 `.claude/plans/video-effectcraft.md`로 옮기고 `main`에서 `feat/effectcraft` 브랜치 | 새 경로에 파일이 있고 옛 경로는 없다 |
| A1 | 측정 M1~M22 | 항목마다 명령·결과·본문 반영 여부가 이 파일 원장에 적혔다 |
| A2 | `tests/support` 도우미, 왕복 픽스처, `tests/effectcraft_facts` | 대조군이 있는 테스트가 통과하고 이 Mac에서 skip이 없다 |
| A3 | `video/effectcraft` 유닛 + `doctor` 확장 + 구조 테스트 | `test_doctor` 새 사례가 먼저 실패했다가 통과, `test_structure` 통과, 실제 `cli.py doctor`에 새 항목, `install_steps` 자산 대조 1회 통과 |
| A4 | SKILL.md의 A 줄과 10·11절, `test_skill_text` 확장, README | A 표시 줄이 모두 반영되고, 남은 옛 문장과 모순되는 곳이 없다(예: L30을 고쳤으므로 "FilmCraft에서만"이 다른 줄에 남지 않음). `test_skill_text` 통과 |
| A5 | codex 리뷰(실제 A 트리의 본문·코드·테스트) → 반영 → 성진님 본문 승인(한국어 요약 동봉) | 지적마다 채택·기각 사유 기록, 승인 |
| A6 | 검증 2·3의 A 부분, 결과물 성진님 판정 | 아래 검증의 기대가 로그와 결과물로 판정됨 |
| A7 | 이 파일에 A의 구현 기록 추가, PR A 올리고 스쿼시 머지 | 전체 테스트 통과, `claude plugin validate --strict .claude/skills` exit 0 |
| B1 | `main`에서 `docs/skill-facts` 브랜치, SKILL.md의 B 줄 다시 쓰기 | B 표시 줄이 모두 반영, 옛 문장 → 새 문장 대응표(빠진 사실은 사유와 함께) 작성 |
| B2 | codex 리뷰(실제 B 트리) → 반영 → 성진님 전체 본문 승인 | 같음 |
| B3 | 검증 3의 B 부분(여러 턴), 나빠진 줄 되돌림 | 기대 행동이 로그로 판정되고, 어긋난 줄은 되돌리거나 고친 뒤 재실행 |
| B4 | 이 파일에 B의 구현 기록 추가, PR B 올리고 스쿼시 머지 | 전체 테스트 통과, `plugin validate --strict` exit 0 |

## 검증 (end-to-end)

1. `uv run --with pytest --with pillow --with playwright pytest` 전체 통과. `uv run .claude/skills/video/scripts/cli.py doctor`에 `effectcraft_cli`. `claude plugin validate --strict .claude/skills` exit 0.
2. 왕복 픽스처(위 테스트 설계): 덧그림과 교체 양쪽에서 프레임 정렬, 소리 트랙, 길이, 반투명 가장자리가 기대와 맞는다. 새로 들어오는 두 앱 사이 경계를 직접 시험하는 가장 싼 검증이다.
3. 모델 대조(`claude` 스킬의 작업자, 턴을 이어 붙여 여러 턴을 흉내 냄. 판정은 실행 로그의 관찰 가능한 사실로):

| 대조 | 과제 | 기대(로그·결과물에서 판정) |
|---|---|---|
| A: 스킬 없음(B3) vs 새 본문 | B3 과제, 같은 클립, MobileSAM 설치 상태, 내려받기 금지 조건 없음 | 매트를 고정해 저장하고 `render-frame --transparent`나 FilmCraft 렌더로 확인한다. 오버레이에 편집의 소리가 실리지 않고 A1의 말이 남는다. 시간·비용은 참고로만 적는다(조건이 달라 비교가 아님) |
| A: 새 본문만 | 타이틀을 도구 지정 없이 요청 | 어느 도구인지 묻지 않고 고르며 이유를 말한다. 합성 확인을 FilmCraft 렌더로 한다 |
| A: 새 본문만 | 이미 있는 `.ecproj`의 글자만 고쳐 달라는 요청 | 컴포지션을 고쳐 다시 렌더한다(페이지로 새로 만들지 않는다) |
| B: 옛 본문 vs 새 본문 | 1턴 "이 30분 영상으로 1분 하이라이트"(실제 국정감사 원본) | 1턴이 구간 후보 제시로 끝나고 내보내기가 없다 |
| B: 옛 vs 새 | 자막 달린 숏츠 컷(2~3턴) | 첫 `--save` 전에 `doctor` 호출이 있다. 자막이 `captions` 경로로 온다. 납품 전 `qc`가 돈다. 결과의 no-op 표지를 놓치지 않는다(로그에서 `cuts:0` 뒤 재시도) |
| B: 옛 vs 새 | 전환·자막 스타일을 정하지 않은 요청 | 전환·자막 스타일을 묻지 않고 고른 뒤 보여 준다 |

대조가 보여 주지 못하는 것: 과제당 실행 수가 적어 실행 간 편차와 본문 효과를 완전히 가르지 못하고, 흉내 낸 턴은 실제 사용자와의 리듬이 아니다. 브리지(실행 중인 앱)에서의 저장 행동은 이번에 실행하지 않는다. 이 한계를 PR 본문에 미검증으로 적는다.

4. 성진님이 3의 결과물을 열어 판정.

## Git

- PR A `feat: video 스킬에 EffectCraft 합성 경로 추가`: `effectcraft` 유닛, `doctor`, 테스트, SKILL.md의 A 줄과 새 절, README, 이 계획 파일(A 구현 기록 포함). 커밋은 결정 단위(사실 테스트 / doctor / 본문 / README).
- PR B `docs: SKILL.md의 절차 문장을 사실과 이유로 다시 씀`: SKILL.md의 B 줄, 옛 문장 → 새 문장 대응표, codex 감사의 채택·기각 사유, 대조 결과, 이 계획 파일(B 구현 기록).
- 둘 다 `main`에서 판 브랜치, `gh pr merge --squash`.

## skill-maker 준수 대조

| 속성 | 이 계획에서 |
|---|---|
| Principle over rail | 그래픽 경계에서 기본값을 내리고 "어디서 만들었느냐가 바꾸는 것"의 사실로. 기존 절차 문장을 사실 + 이유로(PR B). `qc` 통과만은 완료 조건 형식으로 유지(확인 가능한 말로 쓴 인계 조건) |
| Interface over document | EffectCraft 명령·파라미터·형식·기본값은 `effectcraft-cli`가 소유. 본문에는 호출 전에 계획을 바꾸는 것과 결과에 드러나지 않는 것만 |
| Model over machinery | 새 명령·래퍼 없음. `doctor` 항목 하나는 모델이 알 수 없는 것(별도 릴리스 자산의 이름, 저장 때 드러나지 않는 스키마 거부) 때문 |
| For the model, not the maintainer | 실측 수치·기준선·버전·리뷰 경과는 이 파일과 PR 본문에 |
| Dense | 한 파일 약 130줄. 일반 경고("자주 바뀐다", "새 앱")는 결정을 가르는 문장으로만 |
| Colleague over autopilot | 사용자의 선택인 것, 되돌리기 비싼 것과 이유, 결과가 보여 주지 않는 것을 사실로. 도구 선택은 Claude가 하고 이유를 말한다 |
| 완료 조건 | 전체 본문 승인(A, B 각각), 다른 모델 계열 리뷰, `plugin validate --strict`, 구조 테스트, 개발 기록은 PR 본문 |

수용한 이탈: 한 갈래용 내용(10·11절, 실행 중인 앱 절)이 매 세션 로드된다. 성진님 결정으로 받아들인다.

## 구현 때 측정할 것

| # | 측정할 것 | 본문 반영 조건 |
|---|---|---|
| M1 | `--save`가 `render`·`info`·`props`·`get`에서도 무시되는지(`render-frame`은 확인됨) | 일치하면 11절 1 |
| M2 | 시간 기준이 걸리는 명령의 정확한 범위(`set`, `prop.addKey`, `prop.set`, `keys.*`)와 `start`/`in` | 11절 3의 문구 |
| M3 | 없는 글꼴의 대체가 렌더에 보이는지, `file.findMissing` 출력, 이모지 렌더 | 일치하면 11절 4 |
| M4 | 이 Mac에서 `--gpu` 유무의 렌더 시간(2D 타이틀, 3D 컴프) | 몇 배 차이면 11절 6 |
| M5 | H.264 4:2:2 10비트 푸티지(ffmpeg로 생성)의 렌더와 `project.summary` | 그림 없이 성공하면 11절 6 |
| M6 | HLG 푸티지를 EffectCraft → FilmCraft 왕복까지, 알려진 색 패치를 기준으로 | 기준과 조용히 달라지면 11절 6 |
| M7 | 가변 프레임레이트 푸티지의 프레임 대응 | 어긋나면 11절 6 |
| M8 | Roto Brush + MobileSAM + `roto.freeze`가 Object Matte와 같은 저장 규칙인지 | 11절 5의 범위 |
| M9 | 속도 변경·효과·자막·네이티브 그래픽·트림이 있는 시퀀스의 인터체인지에서 남는 것과 양쪽 경고 | 10절 4의 문구 |
| M10 | 같은 경로 재렌더에서 길이·소리·크기·프레임레이트가 각각 바뀐 경우의 FilmCraft 클립 | 10절 5 |
| M11 | `render --template --values`로 한글 로워서드, `templates.create` 내장 템플릿 | 조용한 실패가 있으면 11절에 한 줄 |
| M12 | `render --out` 상대 경로와 `renderQueue.add`의 `output` 기준 폴더 | 다르고 헷갈릴 만하면 한 구절 |
| M13 | 두 앱이 미디어를 절대 경로로 저장하는지, 작품 폴더를 옮기면 열리는지 | L93의 문구 |
| M14 | 인터체인지로 간 컴프의 프레임레이트·시작·트림이 프레임 단위로 맞는지(유리수 레이트 포함. 작업자 실측은 일치) | 어긋나면 10절 4 |
| M15 | 안티에일리어싱·모션 블러 가장자리가 있는 알파 렌더를 FilmCraft에 얹은 결과를 따로 계산한 기대 합성과 비교 | 테두리가 생기면 10절 6 |
| M16 | L40의 두 사실이 `filmcraft-cli --help`와 오류 메시지로 드러나는지 | 드러나면 L40 삭제 |
| M17 | (완료, E31) | — |
| M18 | FilmCraft에서 정상 적용인데 `null`을 돌려주는 명령의 예 | L46의 표지 문구 |
| M19 | 글 크기를 따라가는 배치를 익스프레션(`sourceRectAtTime`)으로 만드는 것이 헤드리스에서 되는지와 드는 수고 | 10절 3의 문구 |
| M20 | EffectCraft 직접 MP4의 `qc` 결과(moov 위치, 음량을 맞출 수단) | Delivery 신규 줄 |
| M21 | 두 CLI가 남기는 `.X.lock` 파일 | L95 |
| M22 | 내장 엔진 Object Matte의 빈 매트가 재현되는 합성 장면 | 사실 테스트 유무 |

## 제외한 것

- HyperFrames(결정 요약의 재개 조건). 문서 근거: 0.9.39, 최근 30일 118회 릴리스, 텔레메트리 기본 켜짐, `init`이 스킬과 `AGENTS.md`·`CLAUDE.md`를 설치, 네트워크를 막는 렌더 모드와 사용 글꼴 보고가 문서에 없음, 알파가 스트레이트인지 미기재. `graphic`은 결정적 시킹·투명 ProRes 4444·유리수 fps·오프라인 재현·글꼴 보고를 이미 갖고 있다.
- EffectCraft 브리지와 `.mcp.json` 등록, `frames`의 `.ecproj` 지원, EffectCraft 명령 래퍼, 다른 Craft 앱.

## 리뷰 반영 내역

### codex 본문 리뷰 (`gpt-6.1-terra`, read-only, 2026-11-13, run `20261113-012124-skill-review-709a`)

| 지적 | 처분 |
|---|---|
| A. 20여 줄이 이유보다 강한 규칙·프레임의 복사 | 채택(성진님 결정). 줄별 처분에 반영 |
| A. 빠진 사실: `qc`의 권위와 한계, 파형은 듣기가 아님, 편집 가능한 원본 vs 납작한 결과, 전사 전 프라이버시, 라이브 프로젝트 차이 | 채택: L26, L29·L57, 10절 1, L69, L41 |
| A. `graphic` 글꼴 보고의 한계 | 기각: `graphic --help`가 이미 소유 |
| A. L20 `data/`는 한 사람의 방식 | 부분 채택: 관례라는 사실로 남김. 공유 설치 가정은 이 배포(사용자마다 클론, `data/`는 git 제외)와 맞지 않아 기각 |
| B. FilmCraft만 전제한 줄 | 채택: PR A |
| C. 전면 재작성이 아니라 부분 재구성 | 채택 |
| D. 결정표가 아니라 선택에 필요한 사실. 8절 구조 제안 | 사실 축은 채택(10절), 절 순서 재편은 기각(이동 최소화) |
| E. 명령 목록·레시피·gaps 요약·래퍼·승인 체크리스트 금지 | 채택 |
| F. HyperFrames는 자리를 얻지 못함 | 채택 |

### codex 계획 리뷰 (같은 스레드, run `20261113-014310-plan-review-0d74`)

| 지적 | 처분 |
|---|---|
| L30이 "ffmpeg는 측정만"이라는 규칙으로 남음 | 채택: 조작이 어느 프로젝트에도 기록되지 않는다는 결과로 |
| L26이 `qc`의 권위를 잘못 말함 | 채택 |
| L27: 전사의 한계, `timeline`은 저장된 요약 | 채택 |
| L28: 조건 없는 세 시점 점검 | 채택: 움직이는 것과 FilmCraft가 합성하는 경우로 한정 |
| L88: `--allow-offline`이 받아들이는 결과가 빠짐 | 채택 |
| L103~105: 저장의 위험이 설명되지 않음 | 채택 |
| L18 도구 선택을 사용자 취향으로 단정, L19·L21~22·L41·L57·L58·L62·L64·L69·L71·L87·L93·L94 문구 | 채택 |
| L35 삭제 | 기각: 본문과 관찰이 부딪힐 때를 정하는 사실 |
| L51 "Korean family가 필요" | 부분 채택: 기존 사실 테스트가 지키는 내용에 맞춰 문구만 |
| L89 삭제 | 기각: PR #1 기준선 R2의 실패가 근거 |
| 10절이 여전히 방법을 정함, 불균형한 서술, "모든 위치가 숫자"는 과장, "새 앱" 일반 경고 | 채택: 축으로 재구성, M19, 일반 경고 삭제 |
| 왕복이 한 길로만 서술됨(덧그림 vs 교체, 소리, 시간, 가장자리, 색, 재렌더) | 채택: 10절 5, 왕복 픽스처, M10·M14·M15·M6 |
| 11절 문장별 한정(`--project` 구분, `prefs.set`, 매트 주장의 범위, 후보는 재현될 때만) | 채택 |
| `doctor` 항목은 반복만으로는 자리를 얻지 못함, 버전 정책, 고정 버전 테스트 | 부분 채택: 스키마 거부(E31)와 별도 자산 이름을 근거로 유지. 테스트는 버전을 고정하지 않고 자산 이름을 릴리스와 대조. 불일치를 `ok: False`로 두는 것은 FilmCraft 항목과 같은 정책이라 유지(선택 항목이라 전체에 영향 없음) |
| 사실 테스트: 독립 기대값, 경계 양쪽, skip 정책 | 채택 |
| PR A 트리가 리뷰·검증되지 않은 중간물 | 채택: A를 끝까지 마친 뒤 B |
| 계획 파일 기록의 순서 | 채택: 각 PR이 자기 기록을 머지 전에 |
| 대조 설계(옛 vs 새가 성립하지 않는 과제, 판정 불가능한 완료 조건) | 채택: 검증 3 재설계 |
| "모든 옛 사실이 살아남는다"는 낡은 사실을 보존할 수 있음 | 채택: 반영 해석에 삭제 조건 |

### Claude 작업자 계획 리뷰 (Opus 5.5, read-only, run `20261113-014334-plan-review-d150`, 왕복 실측 포함)

codex를 쓸 수 있었으므로 같은 계열 리뷰는 보조다. 실측 주장 중 프로젝트 선택(E29), 시간 기준(E27), 소리(E28)는 직접 재현해 확인했다.

| 지적 | 처분 |
|---|---|
| "사용자와 정한다" + L21 삭제로 질문이 늘어남 | 채택: 도구 선택은 Claude, 싼 것의 사실 유지 |
| 브리지에서 저장하게 될 수 있음 | 채택: 14절 문장 |
| L46의 `null`을 단정하면 틀린 사실 | 채택: 좁힘, M18 |
| 하이라이트 구간: 한 턴짜리 긴 요청에서 흔들림 | 채택: L22에 "무엇이 핵심인지는 사용자가 아는 것" |
| L26은 완료 조건 형식이 맞음 | 채택 |
| 모델 내려받기는 비용이 아니라 "작품 폴더 밖에 남는다"가 근거 | 채택: L22, L93 |
| L34에 "저장 때는 경고가 없다" | 채택(E31로 근거 확인) |
| L20 "does not bind"가 빠짐 | 채택 |
| `set --time`은 레이어 시간, 0은 `start` | 채택: 11절 3, E27 |
| 오버레이에 편집의 소리가 실림 | 채택: 10절 5, E28 |
| 데모 폴백은 위치 인자에서만, `--save-as`가 데모를 저장 | 채택: 11절 1, E14 정정, E29 |
| EffectCraft 직접 MP4의 납품 | 채택: Delivery, E30, M20 |
| 짧은 재렌더는 마지막 프레임에서 멈춤, 구간 렌더는 끝 미포함·타임코드 없음, Motion·정속은 남음 | 채택: 10절 4·5 |
| 검증 3이 PR B의 위험에 증거를 주지 않음 | 채택: 여러 턴, 로그로 판정되는 기대 |
| 3절의 PR 표시가 섞임, 사라지는 사실 넷 | 채택: 표시 수정, 사실 복원 |
| 사실 테스트의 대조군, 재현 안 되는 문장, 문장과 테스트의 재대조 | 채택 |
| `doctor` 테스트의 버전 고정, `install_steps` 미실행 | 채택 |
| `test_skill_text`를 절 제목으로 가를 수 없음 | 채택: 명시적 id 집합 |

## 부록: 근거 원장

### 사실 (실측, 2026-11-13, effectcraft-cli 0.24.1 · filmcraft-cli 0.20.1, 스크래치패드에서)

| # | 사실 | 근거 |
|---|---|---|
| E1 | 프로젝트 인자를 빼먹으면 조용히 데모 프로젝트에서 실행된다. 빈 프로젝트는 `--empty`. `.ecproj`로 끝나는 없는 경로는 오류 | `effectcraft-cli info --json` (codex도 재현) |
| E2 | 모르는 옵션은 exit 2, 모르는 최상위 파라미터 키는 받아들이는 키 목록과 함께 오류 | `info --jsno`, `exec comp.new '{"nmae":…}'` |
| E3 | 명령 763개, 효과 308개. `commands --json` 전체는 146 KB. `commands --filter <id>`와 `exec command.describe`가 파라미터 문서를 준다 | `commands --json` |
| E4 | 새 텍스트 레이어는 한글을 그대로 그린다 | `layer.newText` → `render-frame` |
| E5 | `comp.new`의 `frameRate: 29.97`은 30000/1001로 저장되고 `duration: 3`은 3.003 s(90프레임)가 된다 | `comp.info` |
| E6 | `render --format prores --prores 4444 --channels rgba`: ProRes 4444, `yuva444p12le`, BT.709 태그, 30000/1001, 스트레이트 알파(균일한 50% 흰색 = RGB 255·A 129). 1080p 90프레임 0.9 s | `ffprobe`, 픽셀 판독 |
| E7 | 회색 128 위 50% 검정/흰색(Normal, 기본 설정): EffectCraft 컴프 안 = 64/192, EffectCraft 알파 렌더를 FilmCraft에 얹음 = 92/205. `file.projectSettings {"blendLinear":true}`면 EffectCraft도 93/205 | `render-frame` vs `filmcraft-cli render` 픽셀 |
| E8 | FilmCraft 시퀀스 → `file.exportInterchange {"format":"xml"}` → EffectCraft `file.importTimeline`: 같은 이름의 컴프와 푸티지 레이어. 트림(`sourceIn` 20, 길이 60, 시퀀스 프레임 30)과 Motion 스케일·위치, 정속 200%가 남고 같은 소스 프레임이 나온다. 라이브 링크는 없다 | 왕복 실행(직접, 작업자) |
| E9 | HEVC 10비트·H.264 푸티지를 읽고, 푸티지 컴프를 소리(48 kHz PCM)와 함께 ProRes 422 HQ로 렌더한다 | `render` + `ffprobe` |
| E10 | 헤드리스 모션 트래킹: `track.motion` → `track.setPoint` → `track.analyze {"wait":true}` → `track.apply`가 한 `run`에서 0.7 s, 합성 푸티지의 표식을 1.5 px 안으로 따라감 | 합성 푸티지 |
| E11 | 내장 엔진, 실제 국정감사 클립(1080×1920): Object Matte는 31프레임 "계산" 성공을 돌려주지만 매트는 클릭한 점 하나 크기. Roto Brush(전경 1획 + 배경 2획)는 6 s에 21프레임, 종이·뒤 사람·자막 띠가 섞인 거친 매트 | `render-frame --transparent` |
| E12 | FilmCraft에도 131개 비디오 효과(Ultra Key, Warp Stabilizer, Corner Pin 등)와 효과 마스크·마스크 추적이 있다. Mosaic + 타원 마스크 + `masks.track`이 헤드리스로 0.7 s에 89프레임을 따라갔다 | `commands mask`, `run -` + `render` |
| E13 | FilmCraft에 없는 것: 다른 레이어를 움직이는 포인트 추적, 자동 분리 매트, 카메라 추적, 레이어 합성, 셰이프·텍스트 애니메이터, 익스프레션, 3D·시뮬레이션, 템플릿, Lottie | 두 CLI 명령 목록 대조 |
| E14 | 서브커맨드 뒤 위치 인자가 `.ecproj`(대소문자 구분)로 끝나지 않으면 무시되어 데모에서 실행되고 exit 0. `--project a.ecprj`는 그 파일을 그대로 연다. `--save`는 `exec`·`run`·`set`·`script`에서만 저장한다(`render-frame`에서 무시 확인). 한 `run`에서 한 단계가 실패하면 저장되지 않는다 | `main.rs:241-276,498-507`, 실행(직접, 작업자) |
| E15 | 호출마다 새 세션: 저장된 프로젝트의 활성 컴프·컴프별 현재 시간은 남고, 레이어·키 선택, 실행 취소 기록, `prefs.set`은 남지 않는다 | `engine/src/doc_state.rs:56-72` |
| E16 | 새 텍스트 레이어의 글꼴은 Inter이고 한글은 글자별 대체로 Apple SD Gothic Neo가 그린다. 없는 글꼴 이름은 오류 없이 Inter로 대체. `file.findMissing {"what":"fonts"}`는 레이어 단위 글꼴만(코드 근거, M3에서 실행 확인) | `text/src/fonts.rs:30,637-655,843` |
| E17 | 키프레임 시간은 기본이 레이어 시간이고 `render-frame`·`get`은 컴프 시간 | `docs/agents.md`, E27 |
| E18 | 헤드리스 렌더는 `--gpu`가 없으면 CPU이고 `info`가 그 이유까지 보고한다. 고급 3D 1080p는 CPU 3.4 s/프레임 vs GPU 0.29 s(문서 수치) | `info`, `docs/target-app-parity.md:589` |
| E19 | 프로젝트 기본값은 8 bpc, 작업 색공간 없음, 감마 블렌딩. H.264 High 4:2:2 10비트는 그림이 안 나오고 이유는 `project.summary`의 `problem`에만(코드·문서) | `project/src/settings.rs:205-273` |
| E20 | `file.importTimeline`이 잃는 것(문서): 효과, 효과 마스크, 타이틀·그래픽, 속도 램프. 네이티브 그래픽은 양쪽이 경고한다(FilmCraft `report`, EffectCraft `warnings`) | `docs/architecture.md:719-736`, 작업자 실행 |
| E21 | 학습 모델 내려받기만 네트워크를 쓴다(시스템 `curl`). SAM 2는 파일 설치만 | `engine/src/analysis/models.rs` |
| E22 | 성숙도: 첫 커밋 2026-10-01, 스스로 알파·"실무 준비 약 45%", 열린 크래시 보고 6건 | `ROADMAP.md:3,17`, `docs/gaps.md` |
| E23 | 모델 선택(`roto.model.select`)은 그 호출에만 남는다 | 연속 두 호출 |
| E24 | 고정하지 않은 Object Matte는 프로젝트에 저장되지 않고 렌더하는 세션이 다시 계산한다. `select mobilesam → apply → propagate`를 저장한 뒤 다른 호출로 `render-frame`하면 빈 매트(오류 없음). 같은 `run`에서 `objectMatte.freeze {"wait":true}`까지 하면 깨끗한 인물 분리 | `om2.ecproj` vs `om3.ecproj` |
| E25 | MobileSAM Object Matte: 1080×1920 31프레임에 CPU로 27~40 s, 점+상자 한 번으로 말하는 사람을 깨끗하게 분리. 모델 40 MB, `~/Library/Application Support/EffectCraft/models` | 실제 클립 렌더 |
| E26 | Object Matte의 추적 범위는 기준 프레임 앞뒤 30프레임이 기본(`before`/`after` 최대 600). 범위 밖에서는 레이어 전체가 투명 | `render-frame --transparent` 알파 |
| E27 | `set --time T`는 레이어 시간이고 `set`에는 `timeBase` 옵션이 없다. 1.5 s에서 시작하는 레이어에 `--time 2`로 넣은 키는 `compTime 3.5`. 레이어 시간의 0은 `start`(가져온 트림 클립: `start 0.3337`, `in 1.001`). `prop.addKey {"timeBase":"comp"}`는 맞게 들어간다 | 직접 재현, 작업자 실행 |
| E28 | 인터체인지로 온 컴프에는 소리 레이어가 있고 `render`는 기본으로 그것을 넣는다(ProRes 4444 + `pcm_s16le`). 그 렌더를 `timeline.place {"track":"new"}`로 놓으면 A1의 원래 소리가 덮인다. `--audio off`나 `"audio":false`면 정상 | 직접 재현(렌더), 작업자 실행(배치) |
| E29 | `--empty` 없는 `--save-as b.ecproj exec comp.new …`는 데모 항목(Lower Third, EffectCraft Intro, 3D Showcase 등)과 새 컴프가 함께 든 프로젝트를 저장한다 | 직접 재현 |
| E30 | EffectCraft에서 바로 낸 H.264 MP4는 `qc`에서 moov 위치 경고가 나고, `effectcraft-cli commands --filter loud`는 비어 있다(작업자 실행, M20에서 재확인) | 작업자 실행 |
| E31 | `.ecproj`에는 `schema`(지금 2)와 `savedBy`가 있고, 로더는 자기보다 새 스키마의 프로젝트를 거부한다. macOS의 CLI는 릴리스 자산 `effectcraft-cli-0.24.1-macos-universal.zip`(+`SHA256SUMS.txt`)으로 앱과 따로 배포된다 | `project/src/settings.rs:7-16`, `tests.rs:220`, `gh release view v0.24.1 -R storytold/effectcraft` |

### 기준선 (스킬 없는 Claude, Opus 5.5, `claude -p --safe-mode --restricted`)

| 실행 | 과제 | 결과 |
|---|---|---|
| B1 | EffectCraft로 세로 숏츠 인트로 타이틀(5 s, 투명 ProRes 4444 + `.ecproj`) | 23턴, 2분 41초, $1.36. 요구대로 완성, 스스로 틀린 곳 없음. 초록 배경에 ffmpeg로 얹어 확인, 쇼츠 UI 미대조(둘 다 스스로 보고) |
| B2 | 같은 타이틀을 HTML 페이지 + `graphic`으로(`graphic --help`만 줌) | 19턴, 2분 16초, $0.76. 요구대로 완성. 놓친 것은 B1과 같음 |
| B3 | 실제 국정감사 클립이 놓인 `.fcproj`에 "사람 뒤 글자 + 따라가는 이름표"(내려받기 금지) | 80턴, 12분 56초, $4.40. 완성: 알파 오버레이만 렌더해 V2에 놓음, 작업 전 프로젝트 백업, FilmCraft 내보내기로 확인. 내장 Roto Brush가 머리 윗선에서 새서 손 마스크 + 마스크 추적으로 메움. 방송 수퍼를 글자가 덮음(스스로 보고) |

성진님 판정: B1·B2 둘 다 쓸 만함(취향 차이). B3 방향은 맞고 품질만 아쉽다.

### 추론

- EffectCraft 분량이 작아도 되는 이유: 기준선이 틀린 곳 없이 해냈고, 드러난 차이는 비용과 "성공을 보고하는 빈 결과", 두 앱 사이 경계(시간 기준, 소리, 블렌딩)에 몰려 있다.
- 사실형으로 바꾼 협업 문장이 실제 여러 턴 대화에서 같은 리듬을 내는지는 흉내 낸 턴으로 부분적으로만 확인된다.

### 열린 질문

없음.

## A1 측정 원장 (2026-11-13, effectcraft-cli 0.24.1 · filmcraft-cli 0.20.1, 스크래치패드, `EFFECTCRAFT_CONFIG_DIR`는 빈 폴더)

| # | 명령 | 결과 | 본문 반영 |
|---|---|---|---|
| M1 | `--project p.ecproj --save <cmd>` 뒤 파일 md5·mtime 비교 | `info`·`props`·`get`·`render-frame`·`render`는 파일을 다시 쓰지 않음(exit 0, `saved` 없음). `exec`·`set`은 다시 씀(`"saved"`). 제자리 저장 때 `.p.ecproj.lock`(0바이트)이 생겨 남음 | 11절 1에 "`--save`는 바꾸는 명령(`exec`·`run`·`set`·`script`)에서만" |
| M2 | `commands` 목록의 시간 인자 | `timeBase?: layer|comp`를 받는 것: `prop.addKey`·`prop.set`·`keys.select`·`keys.set`. 없는 것(레이어 시간 고정): `set --time`, `keys.setEase`, `keys.setSpatialTangents`. `keys.quickOffset`·`keys.transform`의 `timeAnchor`는 컴프 시간 | 11절 3: "`set --time`과 키프레임 명령은 기본이 레이어 시간, 일부는 `timeBase`를 받는다"로. 명령 목록은 넣지 않음 |
| M3 | 없는 글꼴(레이어 전체, 문자 범위 [4,7]), 이모지, `file.findMissing {"what":"fonts"}`, `render-frame` | 레이어 전체의 없는 글꼴: Inter로 그려지고 오류 없음, `findMissing`이 알려 줌. 문자 범위의 없는 글꼴: Inter로 그려지고 `findMissing`은 `[]`. 컬러 이모지는 기본 글꼴과 `"Apple Color Emoji"` 모두에서 빈칸으로 그려지고 오류 없음(★ 같은 단색 기호는 그려짐) | 11절 4: 대체 글꼴 + `findMissing`의 범위 + 이모지가 빈칸 |
| M4 | 1080p 60프레임 ProRes 렌더, `--gpu` 유무. 2D 텍스트 컴프와 `renderer:"advanced3D"` 3D 솔리드 컴프 | 2D: CPU 0.44 s, GPU 2.8 s(GPU 시작 비용). 3D 솔리드: CPU 1.7 s, GPU 1.9 s. `project.summary`의 `renderer.why`가 "headless: renders on the CPU unless started with --gpu"라고 말함 | 반영 안 함: 이 Mac의 일상적 컴프에서 계획을 바꿀 차이가 없고 렌더러는 `project.summary`가 알려 줌 |
| M5 | H.264 High 4:2:2 10비트(ffmpeg 생성) 가져오기 → `project.summary` → `render-frame` | 가져오기 `errors:[]`·`warnings:[]`, `summary`의 항목은 `missing:false`이고 `problem` 같은 필드 없음, `render-frame`은 exit 0으로 완전히 검은 프레임. 이유는 stderr의 WARN 한 줄("only 4:2:0 is implemented")뿐. x264 무손실(High 4:4:4 Predictive)도 같은 검은 프레임(M7 중 발견) | 11절: 읽지 못하는 푸티지가 검은 그림으로 성공한다. E19의 "`problem`에 이유"는 이 버전에서 재현 안 됨 |
| M6 | HLG(BT.2020, arib-std-b67) 10비트 HEVC의 회색 128·적색 패치. EffectCraft `render-frame`, FilmCraft `render`, EffectCraft ProRes 렌더를 FilmCraft에서 `render` | 같은 원본이 FilmCraft에서는 톤 매핑되어(시퀀스 `auto_tone_map:true`) 회색 138·적색 (234,0,31), EffectCraft 기본 프로젝트에서는 회색 128·적색 (198,67,28). EffectCraft 렌더(BT.709 태그)를 FilmCraft에 놓으면 (128,128,128)·(198,67,28): 원래 클립과 다른 색, 경고 없음. SDR 대조군은 두 앱이 같음(125·(191,62,30)) | 10절 5(교체로 돌아갈 때): HDR 원본은 EffectCraft 기본 설정에서 FilmCraft와 다르게 해석되어 교체한 클립의 색이 바뀐다 |
| M7 | 앞 1 s는 30 fps·뒤 1 s는 60 fps 간격인 VFR H.264(프레임 번호를 밝기로), `render-frame` vs ffmpeg | EffectCraft는 타임스탬프로 프레임을 고름(0.5 s→15, 1.25 s→45, 1.75 s→74; ffmpeg `-ss` 반올림과 1~2프레임 차) | 반영 안 함 |
| M8 | 합성 장면 둘(뚜렷한 붉은 원판이 움직이는 `disk`, 같은 색 분포의 무작위 잡음 위 원판을 검은 테두리로만 구분한 `ring`). 한 `run`으로 모델 선택 → 획/점 → 전파(→ 고정) 후 저장, 다른 호출에서 `render-frame --transparent`, 원판 안·밖 알파 평균(0.0 s, 0.5 s) | `ring`: Roto Brush는 Object Matte와 같은 규칙. MobileSAM + 고정 = 안 1.0·밖 0.0. MobileSAM 고정 안 함 = 내장 엔진 결과와 같음(0.0 s 0.299, 0.5 s 0.0). `disk`에서는 내장 엔진도 완전한 매트(1.0)여서 어떤 경우도 구분 안 됨 | 11절 5를 두 효과 모두에 걸리게("Object Matte와 Roto Brush") |
| M22 | M8의 `ring` 장면에서 내장 엔진 Object Matte(점+상자, 전파 `wait`) | 전파가 30프레임 `computed`로 성공을 돌려주고 매트는 원판 안 0.006(점 하나), 0.5 s에 0.0. MobileSAM + 고정 = 1.0 | 사실 테스트 있음(`ring` 장면). 실제 화면의 E11과 같은 모양 |
| M9 | FilmCraft 시퀀스(29.97): 트림 클립(소스 20프레임부터, 시퀀스 30프레임) + Motion 스케일 150 + Gaussian Blur, 정속 200% 클립, 네이티브 텍스트, 자막 → `file.exportInterchange xml` → `file.importTimeline` | 남음: 트림(`start 0.3337`, `in 1.001`), 스케일 150, 정속 200%(`stretch 50`), 클립마다 소리 레이어. 빠짐: 효과(EffectCraft `warnings`만 말함, FilmCraft `report`는 말 안 함), 네이티브 텍스트(양쪽이 말함), 자막(XML에 없고 어느 쪽도 말 안 함) | 10절 4: 무엇이 남고 무엇이 빠지며 어느 쪽이 말하는지. 자막이 조용히 빠짐 |
| M10 | 같은 경로 재렌더: 클립을 FilmCraft V1에 놓은 뒤 같은 MOV를 짧게(`--start/--end`), 절반 크기, 15 fps, `--audio off`로 다시 렌더 | 타임라인 클립은 90프레임 그대로이고 짧은 재렌더는 시퀀스 45프레임에서 파일의 마지막 프레임을 보임(경고 없음). `media.refreshChanged`는 헤드리스에서 `refreshed:[]`, `media.replaceFootage`로 바꿔도 클립 길이는 그대로. 절반 크기는 프레임에 맞게 커져 위치는 맞고, 15 fps는 가까운 프레임, 소리를 뺀 재렌더 뒤에도 A1 클립은 남음 | 10절 5: 짧아진 재렌더는 놓인 클립 길이를 바꾸지 않고 마지막 프레임에서 멈춘다 |
| M14 | M9와 같은 트림 클립의 인터체인지 컴프(29.97) → 렌더 → FilmCraft 0프레임에 덧그림·교체로 놓음 → 시퀀스 45프레임 렌더의 표식 | 컴프 `frameRate` 30000/1001, 길이 3.003 s(90프레임). 모든 경우 시퀀스 45프레임 = 소스 35프레임(원래와 같음) | 반영 안 함(어긋남 없음) |
| M15 | 부드러운 가장자리(Gaussian Blur 20)·불투명도 60%의 흰 상자를 알파 ProRes 4444로 렌더해 FilmCraft 새 트랙에 놓고 회색 128 위 가장자리 한 줄을 비교 | 스트레이트 알파 + 선형광 계산과 최대 0.8 차, 감마 계산과는 최대 13.7 차. 테두리 없음 | 기존 반투명 문장(선형광)을 컴포지션에도 걸리게 하는 것 외에는 없음 |
| E28 재확인 | 같은 왕복에서 오버레이 렌더 기본값과 `--audio off`를 `timeline.place {"track":"new"}` | 기본 렌더는 `pcm_s16le` 소리를 싣고 A1의 원래 클립(30~90프레임)이 오버레이 소리로 바뀜. `--audio off`면 A1 그대로. 전체 렌더를 새 트랙에 얹으면 그림은 V1을 덮고 소리는 A1을 덮어씀 | 10절 5 |
| M11 | `templates.create {"id":"lower-third"}` → `essential.exportTemplate` → `render-frame --template --values`(한글 값, 오타 난 키), `--transparent` | 한글 값이 그려짐. 없는 컨트롤 이름은 렌더 전에 exit 1과 컨트롤 목록. 헤드리스 `templates.saveAs`는 "no settings store"로 거부. 내장 템플릿에는 불투명한 "Preview Background (delete over footage)" 솔리드가 있어 `--transparent` 렌더가 알파 없는 PNG로 나옴(오류 없음) | 11절에 한 구절: 내장 템플릿의 미리보기 배경이 알파 렌더를 덮는다 |
| M12 | 다른 cwd에서 `render --out rel.mov`와 `renderQueue.add {"output":"rq_rel.mov"}` → `render --queue` | `render --out`은 cwd 기준(도움말이 말함), 렌더 대기열의 상대 `output`은 프로젝트 폴더 기준. 두 경우 모두 결과 줄이 실제 경로를 출력 | 반영 안 함: 결과가 경로를 보여 줌 |
| M13 | 작품 폴더(`assets/clip.mp4`, `p.fcproj`, `graphics/g.ecproj`)를 통째로 옮긴 뒤 열기 | 두 앱 모두 미디어를 절대 경로로 저장(EffectCraft는 상대 이름도 함께). 옮긴 뒤 EffectCraft는 찾음(`missing:false`, `findMissing` 빈 목록), FilmCraft는 `media.status`가 `missing` | PR B의 L93 문구: 폴더를 제자리에 두면 열리고, 옮기면 FilmCraft는 다시 이어야 한다(`media.autoRelink`) |
| M16 | `filmcraft-cli --help`, 없는 `--project` | 도움말이 `--project`(있는 파일을 연다)·`--save-as`·`import`를 나열. 없는 파일은 `No such file or directory`로 exit 1 | PR B: L40 삭제(도구가 소유) |
| M18 | M9의 `clip.speedDuration {"speed":200}` | 결과가 `null`이고 속도는 적용됨(인터체인지에서 `stretch 50`) | PR B: L46 표지를 "id나 경로가 와야 할 자리의 `null`"로 |
| M19 | 텍스트 레이어와 빨간 솔리드, 솔리드의 scale·position에 `sourceRectAtTime` 익스프레션(`set --expression` 두 번) | 헤드리스에서 동작: 상자 폭이 "짧은" 126 px, 긴 문장 536 px로 글을 따라감 | 10절 3: 컴포지션은 좌표로 놓이고, 글 길이를 따르는 배치는 익스프레션이 만든다 |
| M20 | 인터체인지 컴프를 `render --format h264`로 MP4 → `qc --target youtube`; `commands --filter loud`/`normaliz` | `moov_position` 경고(끝), `integrated_loudness` -18.4로 실패. EffectCraft에 음량 맞춤 명령 없음 | Delivery 신규 줄 |
| M21 | 측정 폴더의 파일 목록 | 두 CLI 모두 `--save`로 제자리 저장한 프로젝트 옆에 0바이트 `.<이름>.lock`을 남김(`--save-as`는 안 남김). EffectCraft 소스: 잠금은 저장하는 CLI 실행끼리만(`project_lock.rs`) | PR B의 L95, A의 L41(잠금은 앱을 포함하지 않음) |
| E-구간 렌더 | 인터체인지 컴프를 `render --start 1.001 --end 2.002`, 전체 렌더와 함께 `ffprobe`의 timecode 태그와 첫 프레임 표식 | 구간 렌더는 30프레임([start, end), 끝 미포함), 첫 프레임 = 컴프 30프레임(소스 20). 두 렌더 모두 timecode 태그 없음 | 10절 5 |
| E-앱 저장 | (실행 안 함) EffectCraft 소스에서 프로젝트 파일 변경 감지를 찾음 | 디스크 변경 감지는 푸티지·LUT에만 있고 프로젝트 파일에는 없다(리뷰어 확인). 앱에 열린 `.ecproj`를 CLI로 바꾼 뒤 앱이 저장하는 실행은 하지 않았다 | 4절 L41의 `.ecproj` 구절: 미검증으로 PR 본문에 적음 |

## A5 리뷰 반영 (실제 A 트리)

codex는 사용 한도 소진(2026-11-14 04:01까지)으로 실행되지 못했다(run `20261113-232211-pra-review-ce28`, `turn_failed`). CLAUDE.md의 대체 규칙대로 Claude 작업자(Opus 5.5, read-only, run `20261113-232238-pra-review-be56`)가 검토했다. 다른 모델 계열의 시각은 없다.

| 지적 | 처분 |
|---|---|
| 1. 선택 항목의 설치 명령이 최상위 `next`에 섞여, FilmCraft만 쓰는 세션이 "doctor가 요구한 설치"로 읽음 | 채택: 최상위 `next`는 필수 항목만(기존 의미 유지), EffectCraft 명령은 그 검사의 `next`로. 계획 판정표의 "`next`에 install_steps"에서 바뀐 점 |
| 2. SAM 2는 내려받기가 없고 파일 설치만 | 채택: 본문 문장 수정 |
| 3. "Preview Background"는 Lower Third에만 있음. 8개 중 7개 템플릿이 `--transparent`에서 불투명 | 채택: 실측 후 문장과 test_09를 모든 템플릿 대상으로 |
| 4. test_03이 실패할 수 없음(바뀌지 않은 프로젝트의 저장은 같은 바이트) | 채택: mtime으로, 대조군은 아무것도 바꾸지 않는 `exec project.summary --save` |
| 5. EffectCraft 옵션 검사가 손으로 둔 집합뿐 | 채택: EffectCraft 절의 맨 옵션을 본문에서 모으고, 그 절의 id는 EffectCraft에서 확인. 하위 명령별 옵션은 확인하지 않음(테스트 docstring에 한계 명시) |
| 6. test_11이 "내장 엔진으로 다시 계산"을 보이지 못함(0.5 s에서는 둘 다 빈 매트) | 채택: 같은 획의 내장 엔진 프로젝트와 기준 프레임에서 비교, Roto Brush의 부분 매트도 확인 |
| 7. README의 `roto.model.download` 명령이 `id` 없이 실패 | 채택 |
| 8. 근거 없는 주장: 구간 렌더, `.ecproj` 앱 저장, "place, length and Motion만", stderr 이유 | 구간 렌더는 원장에 추가(측정함), `.ecproj` 앱 저장은 미검증으로 표시, "만"은 과장이라 고침, stderr는 test_08에 단언 추가 |
| 9. `--save-as` 데모 저장은 프로젝트가 없을 때만 | 채택: 문장 수정 |
| 사소: test_06 대조군, 중복된 `frames --project`, "sound overwrites A1"은 기본 대상 가정 | 채택. test_05의 `set`에 `timeBase`가 없다는 단언은 원장 M2로 충분해 넣지 않음 |

좁은 재리뷰(run `20261113-234535-pra-review-6bd6`): 12개 중 11개 닫힘. test_11의 Object Matte 경우가 빈 레이어와 내장 엔진의 점 크기 매트를 구분하지 못한다는 지적 하나를 채택해, 기준 프레임에서 내장 매트가 비어 있지 않고 고정 안 한 매트가 픽셀 단위로 같음을 단언했다.

## A6 검증 결과 (새 본문, Claude 작업자 Fable 5.2, `auto` 프로필, 작업 폴더 `.tmp/contrast/a*`)

입력: B3와 같은 실제 클립(`261109_예산안 심사/assets/컷편집.mp4` 20 s부터 4 s)을 놓은 `short.fcproj`. a3에는 미리 만든 `graphics/title.ecproj`와 그 렌더가 V2에 놓여 있다. 세 실행 모두 `video` 스킬을 열었다(`Skill` 호출 1회).

| 대조 | 기대 | 로그·결과물로 판정 |
|---|---|---|
| a1: B3 과제(내려받기 금지 조건 없음, MobileSAM 설치됨) | 매트를 고정해 저장하고 렌더로 확인, 오버레이에 편집의 소리가 없고 A1이 남음 | 충족. MobileSAM Object Matte를 한 `run`에서 고정(120프레임), 이름표는 셔츠 깃 추적, `--audio off` ProRes 4444를 V2에, V1·A1 원본 그대로, FilmCraft 렌더 12시각 + 1:1 확대로 확인. 방송 자막을 검은 띠로 덮고 그 아래 머리카락 일부를 복사해 채운 것을 스스로 결정으로 보고. 57 Bash, $11.21(B3 기준선 $4.40과 조건이 달라 비교 아님) |
| a2: 도구를 정하지 않은 타이틀 | 묻지 않고 고르며 이유를 말함, 합성 확인은 FilmCraft 렌더 | 충족. FilmCraft 네이티브 그래픽을 골랐고 "FilmCraft에서 레이어별로 다시 고칠 수 있다"를 이유로 적음. `data/`의 지난 작품 타이틀 스타일을 읽어 따름. FilmCraft 렌더 6시각 확인. 부제 위원회명과 화면 속 방송 자막의 불일치를 확인 필요로 보고. $4.41 |
| a3: 있는 `.ecproj`의 글자만 바꾸기 | 컴포지션을 고쳐 다시 렌더(페이지로 새로 만들지 않음) | 충족. `layer.setText` → 같은 경로 재렌더, `short.fcproj`는 바꾸지 않음(길이 같음). 안전 영역 때문에 글자 크기를 140→93으로 줄인 것을 요청 밖 결정으로 보고. $3.90 |

결과물 한 장: 스크래치패드 `contrast_sheet.png`(a1 0.5·2.0·3.5 s, a2 1.5 s, a3 1.5 s). 성진님 판정 대기.
