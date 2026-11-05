# video 스킬 개선: 자막 도구 결함 수정

## Context

Ossoff 연설 번역 자막을 만들며 `video` 스킬을 실측했다. 자막 품질은 좋았고 전사·파형·규칙 검사도 잘 작동했다. 문제는 기존 도구 몇 곳이 틀렸거나 Claude의 판단을 덮어쓰는 것이다. `captions --cues`는 Claude가 정한 줄바꿈을 버리고 `도널드 J.`에서 큐를 쪼갰다. 그래서 스킬을 켠 대조 실행도 이 도구를 시도한 뒤 버렸고, 그 결과 FilmCraft 폭 측정과 규칙 검사까지 쓰지 못했다.

원칙: 도구는 Claude가 Bash·Read·Write로 직접 하면 확실히 비효율적이거나 틀리기 쉬운 정해진 작업에만 둔다. 이번 변경은 새 역량을 더하지 않고 기존 도구의 결함만 고친다. 자막 조립 스크립트는 Claude가 세 번 모두 제대로 만들었고 작업마다 판단이 달랐으므로(시간을 직접 지정한 큐, 청중 표기 등) 그대로 Claude의 몫으로 둔다.

## 합의 장부

사실(측정·코드):
- `captions --cues`: 줄바꿈을 버린다(`layout.py:180` `" ".join(c.lines).split()`). 약 102개 2줄 큐 중 36개가 손으로 정한 줄바꿈과 달랐다. 한 줄에 들어가는 두 화자 대사도 합쳤다.
- `is_sentence_end`: `도널드 J.`와 `Donald J.`를 문장 끝으로 본다(`rules.py`).
- `Rules.max_units`만 플래그가 없다. `--cps`, `--lines`, `--min`, `--max`는 있다. 샌더스 작업(18), 성진의 Vrew 자막, 대조 실행 모두 16보다 긴 줄을 썼다.
- `doctor`: `shutil.which`만 봐서 실행 불가능한 ffmpeg를 정상으로 판정했다(`ffmpeg/probe.py:26`, 호출자는 `doctor`뿐).
- `filmcraft-cli --project`는 없는 파일을 거부한다. 새 프로젝트는 `run`의 `file.import`→`file.saveAs`로 만든다. 스킬에 없다.
- 대조 실행의 번역 품질은 양호했다. 번역 지침의 근거는 없다.
- 격리 대조 실행은 `--plugin-dir P --setting-sources ""`로 한다. `--safe-mode`는 플러그인 스킬도 끈다.

성진의 결정:
- 공개 배포 기준. 성진 개인 취향은 스킬에 넣지 않는다.
- 줄바꿈은 모델이 판단한다. 자동 줄바꿈 휴리스틱과 의존성을 늘리지 않는다.
- 납품 형태별 점검 항목을 스킬에 정의하지 않는다.
- 범위는 결함 수정만이다. 이름·용어 확인 지침은 넣지 않는다. Claude가 알아서 잘 한다.

## 제외한 것

`--sheet`와 시트 파일, 대조 파일, `frames --captions`, `--media`, 번역 명령, `kiwipiepy`, 번역 문체 지침, `references/`. 이유는 Context의 원칙이다. 시트는 시간을 직접 지정한 큐 같은 판단을 막고, `frames --captions`는 스킬 한 줄로 충분하며, `--media`는 `ffprobe`로 바로 읽을 수 있다.

## 기대하는 차이

"이전"은 이번 세션의 실측이고, "이후"는 구현 전의 기대다. 기대는 검증 절에서 확인한다.

| 장면 | 이전 | 이후(기대) | 확인 방법 |
|---|---|---|---|
| 직접 쓴 SRT를 `--cues`에 넣을 때 줄바꿈 | 약 102개 2줄 큐 중 36개가 달라지고, 상당수가 "우리 운명의 / 주도권을"처럼 어구 중간에서 끊김 | 규칙에 맞는 큐는 줄과 경계를 그대로 유지 | Ossoff 초안 복사본 재실행 |
| 두 화자 대사 | `- 사랑해요, 존 - 저도 사랑합니다`로 한 줄에 합쳐짐 | 두 줄 유지 | CLI 테스트 |
| 이니셜이 든 이름 | "도널드 J" / "트럼프를요!"로 큐가 쪼개짐 | 쪼개지지 않음. 대신 문장 끝의 `A.`도 문장 끝으로 보지 않음 | CLI 테스트 |
| 도구를 쓰기 위한 우회 | 공백을 `~`로 묶고 `sed`로 풀며, 두 화자 줄은 Python으로 후처리 | 우회 불필요 | Ossoff 초안 복사본 재실행 |
| 스킬을 켠 모델의 `--cues` 사용 | 한 번 시도한 뒤 버리고 자체 스크립트로 검사 | 끝까지 사용해 FilmCraft 글꼴 기준 폭과 프레임 맞춤, 규칙 검사를 받음 | 대조 재실행(1회라 경향만 확인) |
| 줄 길이를 16자보다 길게 쓰려 할 때 | 도구가 16 단위에 맞춰 다시 나눠서 쓸 수 없음(샌더스는 18을 쓰려고 자체 스크립트 사용) | `--units 18`로 해결 | CLI 테스트 |
| 번역 없는 한국어 자막의 줄바꿈 | 도구의 길이 기준 줄바꿈을 그대로 넘길 수 있고, 어구 중간 끊김을 고치라는 안내가 없음 | 도구 출력은 그대로지만, 스킬 안내에 따라 모델이 읽고 SRT를 고친 뒤 `--cues`로 맞춤. 품질은 나아지고 그만큼 토큰을 더 씀 | 미측정. 이번 검증에 없으므로 효과는 추정으로 보고 |
| 실행되지 않는 ffmpeg | `doctor`는 정상으로 판정하고, 첫 ffmpeg 호출에서 비로소 실패 | `doctor`가 `ok:false`와 사유, 재설치 명령을 줌 | 스텁 `PATH`로 실제 진입점 실행 |
| 렌더 확인용 새 프로젝트 | `--project`가 없는 파일을 거부해 시행착오 | 스킬 한 줄을 보고 처음부터 올바른 명령을 씀 | `filmcraft_facts` 테스트, 문구 검사 |

달라지지 않는 것:
- **번역 품질과 문체.** 지금도 양호하고 이번 변경은 번역을 건드리지 않는다.
- **조립 스크립트.** 필요하면 Claude가 계속 직접 쓴다. 쓰는 것을 실패로 보지 않는다.
- **전사와 파형.** 비용, 시간 정확도, 사용법 모두 그대로다.
- **세션 비용.** 큰 절감을 기대하지 않는다. 대부분이 번역을 읽고 쓰는 토큰이라 이번 변경의 영향이 작다.

전체 효과는 작다. 결과물이 크게 달라지는 개선이 아니라, 기존 도구가 Claude의 판단을 망치거나 틀린 판정을 내던 곳을 고치는 변경이다.

## 변경

### `captions --cues` 줄바꿈 보존

입력 큐의 줄 수, 줄 단위, 측정 폭, 표시 시간(`--max` 이내)이 모두 맞으면 그 큐의 줄과 경계를 유지한다(`clean_line`만 적용). 하나라도 어긋난 큐만 지금처럼 다시 나눈다. 유지하는 큐도 시간은 기존 규칙대로 원래 범위 안의 프레임에 맞춘다.

`relayout`(`captions/layout.py`)에서 큐별로 그룹을 만들어 `time_cues`에 넘긴다. 유지하는 큐는 한 그룹, 다시 나누는 큐는 기존 `group` 결과다. 큐를 자기 시간 안에 두는 계약은 유지하고, `--help`에 이 사실을 한 절로 적는다. 번역 큐를 침묵으로 늘리는 일은 큐를 쓰는 쪽의 몫이다.

### 이니셜

`is_sentence_end`에서 `^[A-Z]\.$`는 문장 끝이 아니다. `I chose A. Next`의 `A.`처럼 진짜 문장 끝은 문맥 없이 구별할 수 없다. 이름이 쪼개지는 것이 더 나쁘고 큐는 SRT에서 고칠 수 있으므로 이니셜로 본다. `성진:` 주석으로 한계를 남긴다. 인용 부호가 붙은 `J.”`는 문장 끝으로 둔다.

### `--units N`

`captions`의 줄당 단위 상한. 기본값은 규칙 그대로이고 `--cps` 등과 같은 방식으로 `RULE_PROFILES`를 덮어쓴다. 측정 폭 검사는 그대로 적용한다.

### `doctor`

`ffmpeg.installed()`를 상태 함수로 바꾼다: 각 도구가 `ok`, `missing`, 또는 실행 실패 사유(오류 끝줄, 타임아웃 포함)를 돌려준다. `<tool> -version`을 실행해 판단한다. `Facts`가 상태를 담고 `judge`가 나눈다: `missing`→`brew install ffmpeg`, 실행 실패→`value`에 사유, `next`에 `brew reinstall ffmpeg`. 재설치가 빠진 의존성을 복구하는지는 고장 상태를 다시 만들어야 확인되므로 미검증으로 보고한다(이번 복구는 `brew install opus x264`였다).

## 문서 구조

### `SKILL.md`

섹션 구조는 그대로 두고 표시한 곳만 바꾼다.

1. Working with the user
2. Before you hand something over
3. Before the first command
4. Headless or the running app
   - 추가: `--project` opens a file that exists; start one with `filmcraft-cli run` lines `file.import` then `file.saveAs`.
5. How the CLI fails quietly
6. Seeing and hearing the edit
7. What does not depend on taste
8. Speech as material
   - 추가: `captions` breaks lines by length and cannot tell a phrase, so a break can part a modifier from its noun: read its lines and correct them in the SubRip; `--cues` keeps the lines and cues that fit.
9. Graphics and motion graphics
10. Delivery
11. Working files
12. Working in the running app

### `references/`

없음.

### `--help`

`captions --help`: `--cues` 보존 조건과 자기 시간 안의 계약, `--units`, 이니셜. 규칙 설명(`rules.HELP`)의 약자 목록에 이니셜을 더한다. `SKILL.md`에 복제하지 않는다.

### `README.md`

`captions` 행에 `--cues`가 맞는 줄바꿈을 유지한다는 내용을 반영한다. 다른 내용은 바꾸지 않는다.

## 테스트 접점

기대값은 손으로 계산한 프레임 시간과 직접 쓴 입력에서 온다. 현재 출력을 복사하지 않는다.

- `captions` CLI(`tests/video_skill/test_captions.py`, 실제 `cli.py`):
  - `--cues`: 맞는 줄바꿈 유지, 한 줄에 들어가는 두 화자 두 줄 유지, 프레임 사이에서 시작·끝나는 입력의 정렬, 넘치는 큐만 재배치, 줄은 맞지만 9초인 큐는 다시 나눔, 기존 시간 계약
  - 이니셜: `J. Trump`가 `--transcript`와 `--cues`에서 큐를 쪼개지 않음, `A.`와 `J.”`의 동작, 두 프로필
  - `--units 18`: 16을 넘는 줄 유지, 위반 없음. 18을 넘으면 재배치
- `doctor`: `judge`의 손 계산 사례(미설치→install, 실행 실패→reinstall과 사유), 실제 진입점을 `exit 1` 스텁·타임아웃 스텁·stderr 없는 실패 스텁이 있는 `PATH`로 실행.
- `filmcraft_facts`: 없는 `--project` 거부, `run`의 `file.import`→`file.saveAs`로 새 프로젝트 생성. docstring이 `SKILL.md › Headless or the running app`을 가리킨다.
- 구조·문구: `test_structure`, `test_skill_text`가 그대로 통과한다. 기존 `relayout` 테스트의 시간 계약은 유지하고, 줄바꿈 계약이 바뀌는 단언만 의도된 변경으로 고친다.

기준선: `uv run --with pytest --with pillow pytest tests/video_skill/test_captions.py tests/video_skill/test_doctor.py tests/video_skill/test_structure.py tests/video_skill/test_skill_text.py -q` 126 통과.

## 구현 단계

코드 전에 `coding` 스킬을, `SKILL.md` 수정 전에 `skill-maker` 스킬을 연다. 파일을 바꾸는 단계가 3개 이상이므로 `TaskCreate`로 아래 단계를 열고 완료 판정을 `description`에 쓴다. 시작할 때 `.claude/plans/video-curried-cookie.md` 링크를 지운다. 브랜치 `fix/captions-cues-breaks`.

1. **`doctor`.** 재현 테스트 먼저. 판정: 스텁 PATH에서 `ok:false`, 미설치와 실행 실패의 `next`가 구별됨.
2. **이니셜.** 판정: 해당 테스트의 실패를 먼저 본 뒤 통과.
3. **`--units`.** 판정: 같음.
4. **`--cues` 줄바꿈 보존.** 판정: 위 테스트 통과, Ossoff 초안 복사본(공백 그대로, `~` 우회 없음)을 넣었을 때 손으로 정한 줄바꿈이 모두 유지되고 위반 0건.
5. **문서 초안.** `SKILL.md`, `--help`, `README.md`. 판정: `test_skill_text` 통과.
6. **독립 검토.** 초안을 보여 주기 전에 다른 모델 계열(Codex `gpt-6.1-terra`, high; 한도 초과 시 Sonnet이며, 그 경우 다른 계열 시각이 없음을 알림)이 코드와 `SKILL.md`를 skill-maker의 5가지 속성으로 검토한다. 판정: 발견 처리 내역 정리, 재현된 결함 수정 후 재실행. 이어서 성진이 `SKILL.md` 전문을 승인한다. 승인 전에는 머지하지 않는다.
7. **PR·머지.** `gh pr merge --squash`. 개발 기록(측정, 버린 대안)은 커밋 본문과 PR에 남기고 스킬에는 넣지 않는다.
8. **`plans` 저장.** 별도 브랜치 `chore/track-plans`에서 `.claude/plans/`의 계획 4개를 원문 그대로 커밋하고 PR로 머지한다(성진의 결정, 공개 레포). 커밋 전에 API 키 패턴(`sk-`)이 없는지 다시 검사한다. 판정: `git status`에 `.claude/plans/`가 추적되지 않은 상태로 남지 않고, 키 패턴 검색 결과가 0건.
9. **GitHub 릴리스.** 머지된 `main`에서 `v0.2.0`을 만든다(`--units`가 새 플래그이고 `--cues` 동작이 바뀌므로 마이너 버전). 본문은 `v0.1.0`과 같은 구조(`## 이번에 들어간 것`, `## 왜`, `## 쓰는 법`)로 한국어로 쓰고, 달라진 동작과 측정 조건을 적는다. 판정: `gh release view v0.2.0`에서 태그와 본문 확인, `latestRelease`가 `v0.2.0`.
10. **메모리.** 성진이 준 원칙을 feedback 메모리에 저장한다: 스킬의 도구는 Claude가 네이티브 도구로 직접 하면 확실히 비효율적이거나 틀리기 쉬운 정해진 작업에만 둔다. 작은 스크립트가 반복된다는 것은 도구가 필요하다는 근거가 아니다.

## 검증

- 스위트: `uv run --with pytest --with pillow pytest tests/video_skill`, FilmCraft 사실은 `tests/filmcraft_facts`. 종료 코드 그대로 보고.
- `claude plugin validate --strict .claude/skills`가 종료 0(스킬 폴더의 부모 경로 기준).
- 대조 재실행(개선 전과 같은 조건): `--plugin-dir P --setting-sources ""`, Opus 5.5, 같은 프롬프트, 전사 원본 재사용, 복사본 사용. 판정 항목: 모델이 `--cues`를 끝까지 쓰고 줄바꿈이 유지되는가, 규칙 위반 수. 임시 스크립트를 쓰는 것은 실패가 아니다. 한 번의 실행이라 경향만 보여 준다고 명시한다.
- 보고에 남길 미검증: 소리는 듣지 못했고, `brew reinstall ffmpeg`의 복구 효과는 재현하지 않았으며, 많은 실제 세션에서의 성능은 이 검증으로 보장되지 않는다.
