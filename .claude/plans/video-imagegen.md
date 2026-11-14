# `video` 스킬: gpt-image 생성(`imagegen`)과 컨택트 시트 더하기 — 구현 계획

> 이 파일은 계획 모드가 정한 이름(`claude-skills-video-imagen-dynamic-star.md`)으로 쓰였다. 계획 모드는 이 파일 하나만 고칠 수 있어서 쓰는 동안에는 이름을 바꾸지 못했다. 계획이 승인되면 그 세션에서 바로 `mv`로 `.claude/plans/video-imagegen.md`로 바꾼다(형제 계획 `video-graphics.md`·`video-effectcraft.md`와 같은 이름 규칙. 아직 git에 올리지 않은 파일이라 `git mv`가 아니라 `mv`). 구현 세션이 이 파일을 아직 원래 이름으로 보면 첫 동작으로 그렇게 바꾼다. 커밋은 하지 않는다: 계획 파일은 구현 PR에 함께 들어간다.

## Context

- 성진님의 요청: 영상에 이미지·아이콘·일러스트 같은 요소를 넣고 싶을 때 "사용자에게 맘에 드는 걸 찾아오라거나 일러스트 등으로 그리는 것보다는" gpt의 이미지 생성 모델을 쓸 수 있게 한다. 지금의 `video` 스킬에는 그림을 생성하는 길이 없다.
- 성진님 작품에는 이미 생성 그림이 쓰였다: 이태원 4주기 작품의 `graphics/밤하늘.png`는 Codex 내장 `image_gen`의 출력과 바이트가 같다(`~/.codex/generated_images/01a18682-…/exec-89996b40-….png`, 2026-10-29 생성, sha256 일치). 누가 어떤 흐름으로 만들었는지는 확인하지 않았다(그 세션 기록은 zstd로 압축돼 있어 이 세션에서 읽지 못했다). 작품 폴더에는 그 그림의 프롬프트나 고른 이유를 담은 장부가 없다.
- 성진님의 다른 스킬 `design`(`/Users/seongjin/Coding/Agentic Design/.claude/skills/design`, 이 레포의 `.tmp/design`이 그 링크)은 Codex CLI의 내장 `image_gen`으로 gpt-image를 부르고, 모든 시도를 장부(`job.json`)와 컨택트 시트(HTML)에 남긴다. 50개 넘는 버전의 실제 작업에서 쓰인 부품이다.
- 목표: `video` 스킬에 "생성한다"는 길을 더한다. 명령은 용도를 가리지 않고(프롬프트 + 참조 이미지 + 투명 배경 여부 → PNG), 본문은 허용 용도 목록 대신 어떤 용도에서든 참인 사실을 적는다. design에서는 Codex 어댑터와 장부·시트의 방식을 가져오고, 포스터 제작 흐름(브리프·문서 버전·내보내기·플랫폼 검사)과 포스터 작업에서 나온 판단 줄은 가져오지 않는다.
- 성공 기준은 품질 하나다. 이번 계획 세션은 성진님 결정으로 읽기 전용이었으므로(새 생성 호출 없음), 계획이 기대는 사실은 로컬 기록·공식 문서에서 왔고, 실제 호출이 필요한 확인은 "구현 때 측정할 것"에 모았다.

## 결정 요약 (이번 세션, 성진님 결정)

| 주제 | 결정 | 버린 대안과 이유 |
|---|---|---|
| 범위 | 기능은 넣되 활용을 한정하지 않는다. 명령은 용도 중립, 본문은 사실만 | "소재 생성만"으로 한정: 받은 프레임 다시 그리기 같은 쓰임을 막을 이유가 없음 |
| 스킬 경계 | description의 `Not for … still images such as thumbnails or posters` 유지. 트리거도 늘리지 않음 | 경계 넓힘: 완성 이미지에 필요한 지식(규격 검사 등)이 본문에 없어 design보다 못한 결과가 나오고 두 스킬이 겹침 |
| 엔진 | Codex 내장 `image_gen` 하나 | OpenRouter Images API(크기 지정·최신 모델·문서화된 HTTP, 장당 과금) 단독 또는 병행: 성진님이 Codex만 선택. 다시 열 조건은 "제외한 것" |
| 명령 이름 | 생성 명령은 `imagegen` | `imagen`: 구글 이미지 모델 상표와 같아 오해. `image`: '생성'이라는 뜻이 없음 |
| 기록 | design처럼 폴더마다 장부 하나 + 컨택트 시트 하나. 시트는 생성 이력 **과 판정 기록**(선택, 사용자가 한 말, Claude의 평가)을 담음 | 그림마다 옆에 JSON: 성진님이 시트 방식을 요청. 이력만: 성진님이 판정 기록까지 선택 |
| 폴더 관례 | `<작품>/graphics/imagegen/` (명령은 어느 폴더든 받음) | 작품 루트의 `imagegen/`: 페이지에서 `../`로 불러야 하고 작품 폴더 관례 문장이 바뀜 |
| 시트 언어 | 한국어 라벨(design 시트와 같음) | 영어 |
| 실사 생성물 규정 | 본문에 넣지 않음(README에도 쓰지 않는다) | 사실만 적기 / 금지 규칙: 성진님이 넣지 않기로 함. 조사한 원문은 부록에 남김 |
| 문서 분할 | `references/` 없음(다섯 번째 같은 결정). 프롬프트 경향은 `imagegen --help`, 생성물의 성질은 SKILL.md 새 절 | `references/imagegen.md`: 기존 결정·테스트를 바꾸고 포인터를 놓치면 통째로 안 읽힘 |
| design 유래 판단 줄 | **사실만 남기고 나머지는 뺀다**(두 리뷰 뒤 결정). 코드 그림과 생성 그림의 차이는 사실로 적고, "소재가 없다고 빼지 마라", "분위기 주제는 남색 밤·금빛·보케로 쏠린다", "고치는 순서", "세트는 첫 승인 그림을 참조로"는 넣지 않음 | 옮겨 넣기(처음 고른 안): 성진님 영상의 평면 그래픽·글자 태그를 결함으로 적게 되고, `밤하늘.png`가 쏠림 줄의 반례에 가까움 |
| 계획 세션 실측 | 읽기 전용만(웹 조사, 파일·로컬 기록 읽기, codex·claude 읽기 전용 검토) | — |
| 구현 세션 실측 | 실제 Codex 호출(측정·검증 21회 + 대조 6~12장, 구독 한도)과 합성 실측. 35회를 넘기게 되면 그 전에 알림 | 15회 안으로 줄이기: 동시 6개가 미확인으로 남음 |
| 기준선 대조 | **구현 때 작은 대조를 한다**(마지막 결정. 처음에는 생략을 골랐으나, skill-maker 프레임을 철저히 따르기로 하면서 되살림). 도구는 주고 새 본문 줄만 뺀 Claude에게 영상 과제 2~3개, 결과를 성진님께 보이고 줄을 거른다 | 생략: 모델이 이미 아는 줄이 본문에 들어가고, 정말 틀리는 것은 찾지 못함 |
| 테스트 | 실제 진입점(`cli.py`) + 가짜 codex 실행 파일. 여기에 실제 Codex로 1장 만드는 게이트 테스트 하나 | 가짜만: Codex 형식이 바뀌면 실제 작업 중에 처음 알게 됨 |

내가 정하고 진행한 것(관례·코드·기존 결정으로 정해지는 것). 계획 승인 때 바꿀 수 있다.

- 판정 기록 명령의 이름은 `imagenote`(질문 미리보기에서는 `imagegen-note`라고 보여 드렸다. 기존 명령이 모두 한 단어라 맞췄다).
- design에 있던 `--aspect`(비율 확인과 프롬프트 첫 문장 경고)는 가져오지 않는다. 명령이 나온 크기를 출력하므로 비율이 맞는지는 모델이 스스로 볼 수 있고, 그런 일은 skill-maker의 Model over machinery에서 `--help` 한 줄의 몫이다.
- 명령 둘은 `cli.py`의 하위 명령이고 세 번째 단계는 두지 않는다. 프롬프트는 design처럼 stdin으로 받는다.
- 시트는 design과 같이 그 폴더에서 처음으로 열기에 성공할 때 한 번 브라우저에 열린다(`--no-open`으로 끔).
- 게이트 테스트는 이 레포의 기존 방식(`FILMCRAFT_TEST_OPENROUTER=1 … -k real_openrouter`)을 따라 `FILMCRAFT_TEST_CODEX=1 … -k real_codex`(질문 때 말한 `-m codex`가 아니라 레포 관례).
- 생성할지 코드로 그릴지는 기존 결정(`video-effectcraft.md` "그래픽 경계": 기본값 없이 사실만, 선택은 그 자리에서 Claude가 이유와 함께 하고 사용자가 바꾼다)을 그대로 따른다.
- 장부는 skill-maker 트리대로 store 유닛으로 둔다(아래 "유닛"). 구조 테스트에 kind `store`가 생긴다.
- Codex의 모델·추론 강도는 사용자 설정을 따르고 스킬이 덮어쓰지 않는다.
- 검증에서 실존 인물이 찍힌 영상 프레임을 `--ref`로 OpenAI에 보내지 않는다(성진님이 따로 말하지 않는 한). 참조 경로 확인은 생성한 그림이나 페이지 렌더로 한다.
- 검증 7번에서 `claude` 스킬의 읽기 전용 작업자를 한 번 돌린다(장부만 보고 이어 갈 수 있는지. 생성 호출은 없고 Claude 사용량이 든다. 빼려면 승인 때 말씀해 주시면 된다).

## 읽기 전용으로 확인한 사실 → 설계에 주는 것

| 사실 (근거) | 설계 |
|---|---|
| 설치된 Codex 0.167.1의 도구 정의(이번 codex 리뷰 세션의 rollout `additional_tools`): `image_gen__imagegen(args: {prompt: string; referenced_image_paths?: string[]; transparent_background?: boolean; num_last_images_to_include?: number})` → `{image_url, output_hint?}`. 안내문: "imagegen needs a few minutes to finish", 참조는 "use `referenced_image_paths` when every target image has a local file path" | 명령의 생성 인자는 `--ref`, `--transparent`뿐. 크기·품질·시드·마스크 인자는 없다고 `--help`가 말함. `num_last_images_to_include`(대화 속 이미지)는 `exec` 한 번짜리 호출에서 쓸 일이 없음 |
| Codex 0.166.0의 생성 45건(2026-11-06~08, `~/.codex/sessions`)에서 실제 호출에 나타난 인자는 `prompt` 45, `referenced_image_paths` 43, `transparent_background` 20 | 위 정의와 일치. 참조를 경로로 넘기는 길은 문서의 보장이 아니라 이 기록의 관찰이다 → M3 |
| 같은 기간의 PNG 크기: 16:9 = 1672×941, 9:16 = 941×1672, 4:5 = 1122×1402, 3:1 = 2172×724 (모두 약 1.57MP) | 본문 한 줄(1080p 프레임보다 작다)과 `--help`의 크기 표("측정값, 모델이 바뀌면 달라짐") |
| `transparent_background: true` 20건은 모두 RGBA. 그중 4장의 알파는 최소 0·최대 255(ffmpeg `alphaextract,signalstats`) | `--transparent`는 진짜 알파. 명령이 알파 유무와 완전 투명 비율을 보고(design과 같음) |
| 생성 한 번(도구 호출 자체)은 16~47초, 중앙값 29초. design `--help`의 "호출당 40~180초"는 Codex 에이전트 왕복 포함 | `--help`에 시간과 Bash 타임아웃 안내. 기본 타임아웃은 M6 뒤에 정함 |
| **rollout에는 실제 호출이 기록된다**: `custom_tool_call`(`tools.image_gen__imagegen({...})`)과 `Extension` 항목 `image_gen.generation`(`revisedPrompt`, `savedPath`, `transparentBackground`, `failure`, `inputImages[{path, sha256}]`, `generationId`; 시작·완료 시각은 항목 바깥 payload에). 호출 프롬프트와 `revisedPrompt`는 비교 가능한 36건 모두 일치(모두 design 봉투를 쓴 실행) | design 어댑터는 Codex의 자기 보고(`prompt_passed`)에 기댄다. design 실행 로그 하나에서 `codex exec --json` 스트림에는 도구 호출이 없었지만 rollout에는 있으므로, **관측을 1순위**로 하고 자기 보고는 "바꿨다"는 자백으로만 쓴다(아래 "codex 유닛"). 관측은 공식 인터페이스가 아니라 내부 기록이다 |
| rollout의 `failure`는 45건 모두 `null`. 0.166 이후 거부(모더레이션)의 실제 모양은 로컬 기록에 없다. design의 `Some(…)` 해석은 0.160대 형식 | 거부 형식은 M4에서 측정. 못 재면 단계는 `unknown`으로 두고 메시지를 원문 그대로 전함 |
| Codex 실행 한 번은 입력 약 6.9만 토큰(사용자 AGENTS.md·스킬 목록 포함)을 쓰고, 내장 생성은 "counts toward your general Codex usage limits"(developers.openai.com/codex/image-generation) | 본문: 생성은 사용자의 다른 Codex 작업과 같은 한도를 쓴다 |
| 내장 생성은 `gpt-image-2`를 쓴다(같은 문서). API에서는 이 모델이 2027-02-10 종료로 공지됨 | 모델 이름을 본문·`--help`에 값으로 적지 않는다("gpt-image through Codex") |
| Codex에 들어 있는 `imagegen` 스킬은 프롬프트를 `Use case:` 같은 라벨 필드로 재구성하라고 지시한다. 도구 안내문은 "If you have not seen a local image yet, use `view_image`…"라고도 한다 | design의 "원문 그대로, 정확히 한 번" 봉투를 유지한다(M5는 봉투를 없앨지를 정하지 않는다) |
| Codex는 그림을 `$CODEX_HOME/generated_images/<스레드>/`에 저장하고 세션마다 rollout을 남긴다. `codex exec --ephemeral`은 세션을 저장하지 않는다. 오래된 rollout은 `.jsonl.zst`로 압축된다(10/29 폴더: 압축 67, 평문 5. 11/08 폴더: 평문 24) | `--ephemeral`을 쓰지 않는다(관측이 사라짐). 관측은 실행 직후(평문일 때) 한 번 읽어 장부에 옮기고, 나중에 rollout을 다시 읽는 설계는 하지 않는다. 사용자의 Codex 폴더에 사본과 세션이 남는다는 것은 본문의 사실 한 줄. 스킬은 그 사본을 지우지 않는다 |
| 이전 작품의 페이지는 그림을 같은 `graphics/` 폴더에서 부른다(`sky.html`의 `url("밤하늘.png")`, `src="소방관.jpg"`). `graphic`은 `file:` 요청을 폴더 제한 없이 허용 | 관례 폴더 `graphics/imagegen/`, 페이지에서는 `imagegen/sky-1.png` |
| `sky.html`은 941×1672 그림을 1080×1920에 `cover`로 놓는다(1.15배). 다른 페이지는 사진을 1.9배 안팎으로 민다(Claude 리뷰 실측) | "1080p에서 조금 확대됨"은 성진님 작품에서 이미 일어난 일. 확대 정도는 C2에서 눈으로 확인 |
| `doctor`는 네트워크·쓰기 없이 같은 결과를 내야 한다(`test_it_uses_no_network_and_writes_nothing`) | `codex --version`·`codex login status`를 그 정책 아래에서 재고(M8), 안 되면 doctor는 설치 여부만 보고 로그인 확인은 `imagegen`이 실행 때 한다 |
| `test_skill_text`의 `check_tool_flags`는 **도구 이름으로 시작하는 코드 스팬**의 플래그만 검사한다. 맨 플래그(`` `--ref` ``)나 맨 도구 이름은 검사하지 않는다 | 본문에서 플래그는 `` `imagegen --ref` ``처럼 도구 이름과 함께 쓴다 |

## 구현 후 디렉토리 구조 (바뀌는 곳만)

```
.claude/skills/video/
├── SKILL.md                         # 고침: description 한 구절, 4개 절 수정, 1개 절 신설
└── scripts/
    ├── cli.py                       # 고침: 모듈 docstring, ROOT_EPILOG의 exit 1 목록, imagegen·imagenote 하위 명령과 두 DESC, doctor DESC
    └── video/
        ├── codex/                   # 신설(시스템): codex exec의 image_gen. design에서 이식 + rollout 관측
        │   ├── __init__.py          #   Run, run, executable, version, login_status, home
        │   ├── envelope.py          #   원문 전달 봉투와 자기 보고 스키마
        │   └── rollout.py           #   스레드의 생성 기록(관측)과 실패 사유
        ├── imageledger/             # 신설(스토어): imagegen.json
        │   ├── __init__.py          #   읽기·잠금 편집·요청 열기·시도 열기/닫기·판정 쓰기
        │   ├── schema.py            #   스키마 1 전체 검사(모르는 키는 오류)
        │   └── store.py             #   잠금, 원자적 교체, 죽은 시도 닫기
        ├── imagegen/                # 신설(기능): 생성 큐, 시트, 판정 기록
        │   ├── __init__.py          #   __all__ = ["generate", "note"]
        │   ├── sheet.py             #   contact-sheet.html과 .sheet-stamp.js
        │   └── facts.py             #   PNG 크기·알파, 새 파일로만 놓기
        └── doctor/__init__.py       # 고침: codex 선택 항목
tests/
├── support/__init__.py              # 고침: skill()이 stdin(input=)과 env를 받게
├── support/fake_codex.py            # 신설: design의 가짜 codex 이식(rollout에 측정한 모양의 생성 기록까지 씀)
├── video_skill/test_imagegen.py     # 신설: 두 명령을 실제 진입점으로
├── video_skill/test_structure.py    # 고침: KINDS에 codex(system)·imageledger(store)·imagegen(feature), MAY_IMPORT에 store
├── video_skill/test_doctor.py       # 고침: codex 항목
└── video_skill/test_skill_text.py   # 고침: 본문에 복사되면 안 되는 값에 "megapixel", "1672" 추가
README.md                            # 고침
.claude/plans/video-imagegen.md      # 이 파일(이름 바꿈)
```

`references/`, `.mcp.json`, `graphic`·`frames`·`qc`·`transcribe`의 코드, `pytest.ini`는 바꾸지 않는다. 생성물을 화면에 놓는 래퍼(자동 배치, 자동 확대, 누끼)는 만들지 않는다: 놓는 일은 페이지·FilmCraft·EffectCraft가 이미 하고, 어디에 어떻게 놓을지는 모델과 사용자의 일이다.

## 번들 코드 계약

### `imagegen`

```
imagegen NAME --dir DIR [--ref IMG]… [--transparent] [--label TEXT] [--n K] [--timeout S] [--no-open]   < 프롬프트(stdin)
imagegen NAME --dir DIR --again IMAGE [--n K] [--timeout S] [--no-open]
```

- `NAME`: 그림이 무엇인지의 이름(`mic`, `sky`). 파일은 `DIR/NAME-k.png`이고 k는 그 이름의 모든 시도를 세므로(요청이 달라도, 실패해도) **어떤 실행도 생성 PNG의 이름을 다시 쓰거나 내용을 바꾸지 않는다.** NFC로 정규화한다. 거부(exit 2): 빈 이름, 제어 문자·경로 구분자, 맨 앞의 점, `-숫자`로 끝나는 이름(시도 id와 헷갈림), 장부에 이미 있는 이름과 대소문자만 다른 이름(macOS 파일 시스템에서 같은 파일이 됨).
- `--dir DIR`: 그림 폴더. 없으면 만든다. 생성 PNG는 한 번 쓰이면 바뀌지 않는 파일이고, 장부 `imagegen.json`·시트 `contact-sheet.html`·`.sheet-stamp.js`·잠금 파일은 **도구가 갱신하는 관리 파일**이다. 처음 쓸 때 DIR에 이 스키마가 아닌 `imagegen.json`이 있거나, 장부 없이 `contact-sheet.html`이 있으면(남의 파일) 아무것도 쓰지 않고 exit 2.
- 요청: stdin 프롬프트가 있는 호출 하나가 요청 하나다(프롬프트, 참조, 투명 여부, 라벨). 같은 이름 아래 요청이 쌓이고, 출력의 `request`는 그 이름 안에서의 요청 번호(1부터)다.
- `--again IMAGE`: `IMAGE`(예: `mic-2`)를 만든 요청으로 시도를 더 만든다. 이때 stdin은 무엇이든 읽지 않고, `--ref`·`--transparent`·`--label`을 함께 주면 exit 2. 그 요청의 참조 파일을 다시 읽어 장부의 sha256과 비교하고, 없거나 달라졌으면 생성 전에 exit 2로 어느 파일인지 말한다(참조가 그대로 있어야 같은 요청이다).
- `--ref IMG`(반복): 프롬프트와 함께 모델에 가는 그림. 없는 파일은 exit 2. 장부에는 DIR 기준 상대 경로(`os.path.relpath`, 심볼릭 링크는 풀지 않음)와 sha256을 남기고, 관측된 `inputImages`의 해시가 이와 다르면 그 시도의 `detail`에 적는다.
- `--transparent`: 투명 배경 요청. 결과에 알파 유무와 완전 투명 비율을 보고.
- `--label TEXT`: 이 요청이 무엇을 시도하거나 앞 요청에서 무엇을 바꾸는지 한 줄. 시트에서 접힌 프롬프트 대신 사람이 읽는 줄이다.
- `--n K`: 이 요청의 시도 수, 1~6(기본 1). 한 번의 명령 실행 안에서 최대 6개가 동시에 돈다(명령을 두 번 겹쳐 실행하면 각자 6개까지).
- `--timeout S`: 시도 하나의 제한(기본값은 M6 측정 뒤 정한다. design은 호출당 300). 원문 불일치로 한 번 다시 부르는 것도 같은 제한 안에서 한다(design은 호출마다 따로라 시도 하나가 600초까지 갈 수 있고, 그것은 Bash 포그라운드 상한과 같다). 넘으면 codex의 프로세스 그룹 전체를 끝내고 `timeout`으로 기록.
- 중단: codex는 자기 세션으로 뜨므로 `cli.py`가 죽어도 따라 죽지 않는다. `cli.py`는 SIGTERM·SIGINT를 받으면 살아 있는 codex 프로세스 그룹을 모두 끝내고, 끝나지 않은 시도를 `interrupted`로 닫고 나간다. SIGKILL은 막을 수 없으므로 그때 남은 codex는 제 호출을 마칠 때까지 돌고(한도를 씀), 장부의 시도는 다음 읽기 때 `interrupted`로 닫힌다.
- `--no-open`: 시트를 브라우저에 열지 않는다. 주지 않으면, 장부에 `sheet_opened`가 없을 때 macOS `open`(이름으로 호출, `webbrowser` 모듈 아님)을 부르고 **성공했을 때만** `sheet_opened`를 적는다. 열지 못하면(샌드박스 세션 등) stderr에 시트 경로를 알리고 다음 실행 때 다시 시도한다.
- stdout(JSON 한 문서): `{"summary": "3 requested · 2 ok · 1 refused", "name", "request", "results": [{"image": "mic-3", "file": <절대 경로>?, "status", "w"?, "h"?, "alpha"?, "verbatim"?, "error"?}], "sheet": <절대 경로>, "ledger": <절대 경로>}`. stderr: 시도가 끝날 때마다 한 줄(상태, 크기, 걸린 시간, 실패면 사유와 다음에 할 일).
- 종료 코드(이 스킬의 기존 규약): 0 한 장 이상 `ok`(일부가 실패해도 0이므로 `summary`와 각 `status`를 읽어야 한다); 1 codex가 없거나 로그인돼 있지 않음(아무것도 시도하지 않음. 메시지는 `codex login`이 사용자의 브라우저 로그인을 요구한다고 말함), 또는 `ok`가 하나도 없음(JSON에 `error`); 2 명령줄을 바꿔야 함.

시도의 상태(장부 `status`):

| 상태 | 뜻 | 그림 파일 | 고를 수 있나 |
|---|---|---|---|
| `running` | 열렸고 아직 닫히지 않음(큐에서 기다리는 것 포함). 장부의 `pid`는 `cli.py`의 것 | 없음 | — |
| `ok` | 그림이 놓임. `verbatim`은 `exact`·`normalized`·`unverified` | 있음 | 예 |
| `prompt_altered` | 한 번 다시 불러도 간 프롬프트가 쓴 것과 다름. 그림은 시트에 보임 | 있음 | 아니오 |
| `refused` | 생성이 모더레이션에 막힘. `detail.stage`는 `input`(프롬프트)·`output`(만든 그림)·`unknown` | 없음 | — |
| `no_image` | codex는 끝났는데 그림이 없음. 찾은 실패 문구가 있으면 `detail.message`에 원문 그대로 | 없음 | — |
| `executor_error` | codex 자체가 실패(비정상 종료, 마지막 메시지 없음, 시도 처리 중 예외) | 없음 | — |
| `timeout` | 제한 시간을 넘어 프로세스 그룹을 끝냄 | 없음 | — |
| `interrupted` | 명령이 중단됐거나 죽음. 죽기 직전에 파일이 놓였다면 다음 읽기 때 `file`이 채워져 시트에 보이되 출처를 확인하지 못한 그림이다 | 있을 수 있음 | 아니오 |

`verbatim`(간 프롬프트와 쓴 프롬프트의 비교): `exact`, `normalized`(공백만 다름), `mismatch`(한 번 재시도하고, 그래도 다르면 상태가 `prompt_altered`), `unverified`(관측이 없음). `exact`·`normalized`는 관측에서만 나온다. design의 `path_mismatch`·`silent_no_image`는 위 표로 대체한다.

### `imagenote`

```
imagenote TARGET --dir DIR [--choose | --unchoose] [--note TEXT]… [--critique TEXT]
```

- `TARGET`: 그림 id(`mic-2`) 또는 이름(`mic`). `--choose`·`--unchoose`·`--critique`는 그림에만, `--note`는 둘 다에 붙는다.
- `--choose`: 사용자가 고른 그림 표시(이름 하나에 여러 장 가능). `ok`인 시도만. 이미 고른 그림에 다시 주거나 고르지 않은 그림에 `--unchoose`를 줘도 성공이다(같은 상태로 끝남).
- `--note TEXT`(반복): 사용자가 한 말을 한 그대로(또는 Claude가 남겨야 하는 사실). 덧붙기만 한다.
- `--critique TEXT`: 그 그림에 대한 Claude의 현재 평가. 이전 평가를 대체한다.
- stdout: `{"written": [...], "sheet", "ledger"}`. 종료 코드: 0 기록함(또는 이미 그 상태); 2 인자가 하나도 없음, 장부가 없음, 대상이 장부에 없음, `ok`가 아닌 시도에 `--choose`, 이름에 `--choose`/`--unchoose`/`--critique`.
- 이 명령이 있는 이유: 장부는 잠금 아래에서만 고쳐야 하고(백그라운드로 도는 `imagegen`이 같은 파일을 쓴다) 고칠 때마다 시트가 따라가야 한다. 모델이 JSON을 직접 고치면 둘 다 깨진다.
- 기록을 읽는 명령은 만들지 않는다. 모델은 `imagegen.json`을 직접 읽고(스키마는 `imagegen --help`가 설명), 사람은 시트를 본다.

### 장부 `imagegen.json` (스키마 1)

```
{"schema": 1, "created", "sheet_opened"?,
 "names": [{"name", "notes": [{"text", "at"}],
   "requests": [{"r", "created", "prompt", "refs": [{"path", "sha256"}], "transparent", "label"?,
     "attempts": [{"id": "mic-2", "status", "started", "pid"?, "elapsed_s"?, "file"?, "w"?, "h"?,
                   "alpha"?: {"has_alpha", "transparent_share"}, "verbatim"?, "retried"?, "thread_id"?, "detail"?,
                   "chosen"?: true, "critique"?, "notes"?: [{"text", "at"}]}]}]}]}
```

- design `ledger/store.py`·`schema.py`의 방식을 옮긴다: 폴더당 잠금 하나(`flock`, 스레드 포함), 쓰기 전 전체 스키마 검사(모르는 키는 오류), 임시 파일 뒤 `os.replace`, 읽을 때 죽은 프로세스의 `running` 시도를 `interrupted`로 닫기(PID가 살아 있어도 시도보다 늦게 시작한 프로세스면 재사용된 PID로 봄), 진행 중 시도는 결과로 정확히 한 번만 바뀜.
- 직렬화: 요청 추가·번호 예약·시도 열기는 **장부 잠금 하나 안에서** 한다(겹쳐 도는 두 명령이 같은 번호를 받지 않는다). 시트는 **시트 잠금을 잡은 뒤 장부를 읽어** 발행한다(오래된 스냅숏이 새 시트를 덮지 않는다). 잠금은 겹쳐 잡지 않는다: 장부 잠금을 놓은 뒤에 시트를 그린다.
- 죽기 직전의 틈: 순서는 PNG 놓기 → 장부 닫기다. 그 사이에 죽으면 `running` 행과 파일이 함께 남는다. 다음 읽기가 그 행을 `interrupted`로 닫을 때 `DIR/NAME-k.png`가 있으면 `file`에 적는다. 이름은 행이 이미 차지했으므로 다른 시도가 그 파일을 덮지 않는다.
- 새 파일 놓기(design `paths.place_new`·`link_new`): 임시 파일을 같은 폴더에 쓰고 하드링크로 제자리에 놓아, 있는 파일은 바꾸지 않고 반쯤 쓰인 파일이 제 이름을 갖지 않게 한다. 하드링크가 안 되는 볼륨의 복사 경로가 도중에 실패하면 자기가 만든 부분 파일을 지운다. 장부에 없는 `NAME-k.png`가 이미 있으면(남의 파일) 그 시도는 그 사실을 말하며 `executor_error`로 닫힌다.
- 빼는 것: 브리프, 문서 버전, `finals`, `exports`, `scope`(재사용 메모), 이전 스킬 장부 읽기. video에서 취향 기록의 단위는 작품이고, 최종 여부는 편집이 그 파일을 쓰는지가 말한다.

### 시트 `contact-sheet.html`

- design `sheet/__init__.py`를 옮긴다: 고정 레이아웃, 장부에서 매번 다시 그림, 그림은 상대 경로 링크(URL 인코딩, 인라인 안 함), 모든 문자열 HTML 이스케이프, 클릭 확대·←/→·Esc, 2초마다 `.sheet-stamp.js`를 읽어 스탬프(시트 내용의 해시)가 바뀌면 스크롤을 지킨 채 새로 고침, 원자적 쓰기, 투명 그림 뒤 체커보드.
- 구성: 머리(폴더 경로) → 이름마다 한 구역(이름, 성공 수, 이름에 붙은 메모) → 요청마다 한 줄(라벨, 만든 시각, 시도 그림들) → 그림마다 캡션(id, 크기, `선택`, 투명 비율/`알파 없음`, verbatim 경고, 고를 수 없는 상태) → 그림의 평가와 메모 → 접힌 `프롬프트 (N자)`, `참조 N장`(썸네일), `실패 N건`(상태·단계·메시지). 생성 중인 시도는 점선 자리표시. `prompt_altered`·파일이 있는 `interrupted`도 그림으로 보인다.
- 라벨은 한국어. 사용자의 말과 프롬프트는 원문 그대로.

### 유닛

- **`codex`(시스템).** design `codex/`(design 레포 커밋 `837be2f`)의 `run`·`envelope`·`rollout`을 복사해 들여온다(`prompt.py`의 비율 경고는 가져오지 않는다)(스킬은 자기 폴더만으로 돌아야 하므로 design을 import하지 않는다). 유지: `codex exec --json --skip-git-repo-check -s read-only --output-schema … -o … -`, 봉투를 stdin으로, 자체 세션으로 띄워 프로세스 그룹에 SIGTERM 뒤 SIGKILL, `CODEX_HOME` 존중. `--ephemeral`은 쓰지 않는다. 실행 로그(봉투·이벤트·마지막 메시지)는 임시 폴더에 두고 실패한 시도의 것만 `detail`이 가리키는 곳에 남긴다(M1에서 rollout만으로 충분한지 보고 정한다).
  - 관측 1순위: 실행이 끝나면 `thread.started`의 스레드 id로 rollout을 찾아 그 스레드의 `image_gen.generation` 항목들을 순서대로 읽는다. 결과는 **`status`가 완료이고 `savedPath`의 파일이 실제로 있는 마지막 항목**이고, 그 항목의 `revisedPrompt`로 verbatim을 판정한다. 완료 항목이 둘 이상이면(봉투는 정확히 한 번을 요구한다) 그 수를 `detail.generations`에 남긴다. 완료 항목이 없고 `failure`가 있으면 그것이 실패 사유다.
  - 관측이 없을 때(스레드 id가 없음, rollout을 못 찾음, 항목이 없거나 필드가 빠짐, 파싱 실패): 그림은 `generated_images/<스레드>/`에 PNG가 **정확히 하나** 있을 때만 그것으로 하고(여럿이면 고르지 않고 `no_image`와 사유), verbatim은 `unverified`다. 자기 보고(`prompt_passed`)는 일치해도 `unverified`를 `exact`로 올리지 못하고, 불일치할 때만 재시도와 `prompt_altered`의 근거가 된다. 실패 사유는 design의 구조 기반 해석(오류 코드를 모르고도 메시지를 건짐)으로 찾되, 이것도 rollout 형식에 기대는 것이므로 못 찾으면 `no_image`다.
  - `Run`은 스킬의 말로 결과를 준다(그림 파일, 간 프롬프트와 그것이 관측인지, 입력 그림의 해시, 거부 여부와 단계). Codex의 이벤트·파일 배치·오류 표기는 이 유닛 밖으로 나가지 않는다.
  - 먼저 깨질 것: rollout 항목의 이름·필드, 세션 저장 설정, `generated_images` 경로. 그래서 2순위 경로가 있고, 게이트 테스트가 Codex 업데이트 뒤 이것을 한 번에 알려 준다.
- **`imageledger`(스토어).** 위 "장부". 인터페이스는 읽기, 잠금 편집, 요청 열기, 시도 열기·닫기, 판정 쓰기. skill-maker 트리의 `<store>/`이고 구조 테스트에 kind `store`가 생긴다: 기능은 시스템·스토어·공용을, 스토어는 공용만 import한다.
- **`imagegen`(기능).** `generate(...)`: 인자 검사 → 장부에 요청과 시도들을 열기 → `ThreadPoolExecutor(6)` → 시도마다 codex 실행, verbatim 판정(불일치면 더 강한 봉투로 남은 시간 안에서 한 번 재시도), 새 파일로 놓기, 크기·알파, 장부 닫기, 시트 다시 그리기, stderr 한 줄. 시도 하나가 예외로 죽어도 그 시도는 `executor_error`로 닫히고 시트는 다시 그려진다. `note(...)`: 판정을 장부에 쓰고 시트를 다시 그린다. 시트는 이 유닛의 내부 모듈이다(장부를 그리는 곳이 여기 하나).
- **`doctor`.** 선택 항목 `codex` 추가: 값은 `installed, logged in` / `installed, not logged in` / `not installed`, `why`는 "Needed only by imagegen …". 필수가 아니므로 전체 판정을 바꾸지 않고 `next`에도 들어가지 않는다. M8에서 로그인 확인이 네트워크나 쓰기를 쓰면 값은 설치 여부뿐.

### `--help` 구조 (이 텍스트가 인터페이스다)

`imagegen --help`:
1. 무엇을 하나: gpt-image 그림을 사용자의 Codex 로그인으로 만든다. 프롬프트와 `--ref` 그림은 OpenAI로 나가고, 생성은 사용자의 Codex 사용 한도를 쓴다. Codex는 자기 폴더에 그림 사본과 세션을 남긴다.
2. 폴더: 그림·장부·시트가 `--dir`에 있다. 생성 PNG는 한 번 쓰이면 바뀌지 않고, 장부와 시트는 실행마다 갱신된다. 시트는 처음 한 번 브라우저에 열린다.
3. 요청과 `--again`(참조 파일이 그대로 있어야 한다).
4. `image_gen`이 프롬프트와 무관하게 못 하는 것: 픽셀 크기 지정(비율별 측정 크기 표, 측정값임을 밝힘), 품질, 시드, 마스크. 참조를 준 요청은 인페인팅이 아니라 전체를 다시 그린다.
5. 시간: 한 장에 걸리는 시간(M6 측정값), 한 실행에 최대 6개 동시, `--timeout`, Bash 타임아웃을 그보다 크게 잡거나 백그라운드로 돌릴 것, 중단하면 무엇이 남는지.
6. 모델이 프롬프트를 읽는 방식: design `add --help`의 경향 목록을 옮긴다("법칙이 아니라 이 경로에서 관찰된 경향, 결과가 다르면 결과를 믿어라" 머리말 포함) — 영어 산문, 비율을 첫 문장에, 먼저 말한 것이 화면을 더 차지, 여러 매체를 나열하면 일부만 남음, 주지 않은 글자·기관명·날짜는 지어냄(보여야 하는 글자는 큰따옴표 안에 정확히, 끝에 "no other text"), 읽을 수 없는 표시를 달라고 하면 그럴듯한 가짜 한글을 씀, 짧은 한글은 대체로 맞음, 평평한 바탕은 hex 색으로, 정답이 하나인 모양은 구조로 설명, 합성용 소재는 놓일 장면의 빛 방향·색을 말하고 투명 배경이나 깨끗이 분리되는 단색 바탕을 요청. `--ref` 인자 설명에: 참조의 팔레트·글자·레이아웃이 '화풍만'이라고 해도 따라온다, 참조로 고칠 때는 바꿀 하나를 말하고 남길 것을 모두 나열해야 한다("keep everything else"만으로는 안 지켜짐). 거부는 시도마다 결과가 다를 수 있다는 것과 stderr 줄이 말하는 단계의 뜻.
7. Prints(일부 실패해도 exit 0이라는 것 포함) / stderr 줄 / 상태 표 / `verbatim` / `alpha`.
8. 장부 스키마(모델이 `imagegen.json`을 직접 읽도록).
9. Exits.

`imagenote --help`: 대상(그림 id와 이름), 각 인자가 장부의 무엇을 바꾸는지(덧붙임인지 대체인지, 같은 상태면 성공), 시트에 어떻게 보이는지, Prints, Exits.

`doctor --help`: Checks 문장에 `codex` 항목 추가. `cli.py`의 모듈 docstring(도구 목록)과 `ROOT_EPILOG`의 exit 1 설명(외부 도구 목록)에 Codex를 더한다.

## SKILL.md 섹션 구조와 줄별 처분

원칙: 줄 하나는 "모델이 볼 수 없는 사실 + 이유"다. 허용 용도 목록, 생성 절차, 고치는 순서, 취향을 사실처럼 적은 문장, `--help`가 가진 값(크기 수치, 동시 6개, 타임아웃, 상태 이름)은 넣지 않는다. 아래 영어 문장은 **초안**이고, 구현 6~8단계에서 측정과 대조 결과로 거르고 고친 뒤 성진님이 전문을 승인한다(어느 줄이 대조 결과에 달려 있는지는 "skill-maker 프레임 적용" 절). 플래그는 도구 이름과 함께 쓴 스팬으로만 적는다(`test_skill_text`가 그런 스팬만 실제 `--help`와 대조한다).

| # | 절 | 처분 |
|---|---|---|
| frontmatter | description | 한 구절 추가(ⓐ). `Not for …`, Triggers, `allowed-tools`는 그대로(두 명령은 기존 `cli.py` 패턴에 들어감) |
| 1 | 제목·첫 문단 | 그대로 |
| 2 | Working with the user | 2줄 수정(ⓑⓒ) |
| 3 | Before you hand something over | 1줄 추가(ⓓ) |
| 4 | Before the first command | 그대로("An optional item … matters only when the task needs it"가 codex 항목을 덮음) |
| 5 | Headless or the running app | 그대로 |
| 6 | How filmcraft-cli fails quietly | 그대로. C4에서 PNG 스틸이 조용히 틀리는 점이 나오면 그 줄만 추가 |
| 7 | Seeing and hearing the edit | 그대로 |
| 8 | What does not depend on taste | 그대로(실사 생성물 규정은 넣지 않기로 결정) |
| 9 | Speech as material | 그대로 |
| 10 | Where a picture is made | When 줄 수정(ⓔ), "What is left" 줄에 한 문장(ⓕ), 줄 하나 추가(ⓖ), "Partial transparency" 줄에 한 구절(ⓗ, C1이 확인하면) |
| 11 | **Generated pictures (신설)** | "Where a picture is made" 바로 뒤. `When:` 줄과 4줄(ⓘ) |
| 12 | How effectcraft-cli fails quietly | 그대로. C3에서 나오면 그 줄만 |
| 13 | Delivery | 그대로 |
| 14 | Working files | 1줄 수정(ⓙ) |
| 15 | Working in the running app | 그대로 |

줄 초안:

- ⓐ description: "…with graphics designed in code (HTML/CSS/SVG/Canvas) or as EffectCraft compositions**, and pictures generated with gpt-image through the user's Codex CLI,** rendered onto the edit".
- ⓑ (2절, `data/` 줄) 기록 목록에 추가: "…the pages and compositions in its `graphics/`, **the generated pictures with what they chose and said about them (`imagegen.json` beside the pictures),** the exported video".
- ⓒ (2절, 되돌리기 비싼 것 줄의 마지막 문장을 넓힘) "A long export or analysis costs waiting, not undoing; **a round of generations costs waiting and part of the Codex allowance the user's other Codex work draws on.**"
- ⓓ (3절) "`imagegen` reports a picture's size and alpha, not what is in it, and a `frames` tile is a fraction of the size the picture plays at (`frames --width`): lettering nobody asked for, or the edge a transparent cut left, shows only at full size over the footage." (C1·C2 결과로 조정)
- ⓔ (10절 When 줄) "…how an inserted image is shown, **a generated picture,** an intro…".
- ⓕ (10절 "What is left" 줄 끝) "A generated picture is one flat PNG with no layers behind it: its parts cannot be moved or changed apart, and it changes only by being generated again."
- ⓖ (10절 새 줄) "A prop, an icon, an illustration or a background can be drawn in code or generated: drawn as HTML/SVG shapes it stays sharp at any size and every value in it stays editable; generated (`imagegen`), it can carry light, texture and perspective that code shapes do not, which counts most when it has to sit inside the scene rather than over it, and it is fixed once made." (기본값 없이 차이만. 선택은 Claude가 이유와 함께 하고 사용자가 바꾼다는 기존 결정 그대로)
- ⓗ (10절 "Partial transparency" 줄) FilmCraft 밖에서 본 모습이 다르다는 목록에 시트를 더함: "…than in EffectCraft's own frame, a browser **(the contact sheet included)** or an ffmpeg composite". C1에서 차이가 보일 때만.
- ⓘ (11절 전체)

  ```
  ## Generated pictures

  When: running `imagegen`, or placing, fixing or matching what it made.

  - `imagegen` asks gpt-image for a picture through the user's Codex login: the prompt and every `imagegen --ref` image leave this machine for OpenAI, a frame of the footage or someone's photo included, and each picture draws on the allowance the user's other Codex work shares. Codex keeps its own copy of each picture and a session for each call in the user's Codex folder, outside the piece. How the model reads a prompt is in `imagegen --help`.
  - Nothing reopens a generated picture. The same prompt draws a different one, and a request with the picture as a reference redraws the whole of it, so parts meant to stay can change too. Wording, a number or a logo drawn into a picture is corrected only by drawing the picture again, while on a page or a composition over it they stay editable; a small defect can be covered the same way, where the picture is placed.
  - The model, not the request, sets the pixel size, and what it gives is smaller than a 1080p frame of the same shape: how far a picture is scaled up depends on how much of the frame it fills and on any push-in. `imagegen` prints the size it got.
  - Every try, with its prompt and references, is in the folder's `imagegen.json` and on its `contact-sheet.html`, where the user sees the candidates at full size; `imagenote` adds which picture they chose, what they said about it in their words, and your assessment, which is where a later session reads how a picture was made and why it was picked.
  ```
- ⓙ (14절) 관례 문장에 추가: "`graphics/` for pages, compositions (`.ecproj`) and their renders, **with generated pictures, their ledger and contact sheet in `graphics/imagegen/`**".

넣지 않기로 한 줄과 이유(개발 기록용): "소재가 없다고 빼거나 글자로 대신하지 마라"(성진님 영상의 글자 태그·평면 그래픽은 고른 양식이다), "분위기 주제는 남색 밤·금빛·보케로 쏠린다"(design에서는 '신뢰가 목표일 때'라는 조건이 붙은 줄이고, 영상에서의 근거가 없으며, `밤하늘.png`는 보라 계열이다), "구성이 틀리면 새 요청·한 요소면 참조"(작업 순서를 고정하는 규칙. 필요한 사실은 ⓘ 둘째 줄에 있다), "세트는 첫 승인 그림을 참조로"(방법을 고정. 참조가 무엇을 끌고 오는지는 `--help`), 거부에 대한 단정(M4 전에는 근거가 없다. `--help`가 가짐).

## README

"무엇을 할 수 있나"에 행 하나(이미지 생성: 소품·아이콘·일러스트·배경을 gpt-image로 만들어 페이지·타임라인에 얹기, 후보를 컨택트 시트에서 고르고 판정을 남기기), "준비"에 선택 항목(Codex CLI와 ChatGPT 로그인, `doctor`가 점검), "번들 도구"에 `imagegen`·`imagenote` 두 행, "작업 폴더 `data/`"에 `graphics/imagegen/`, "레포 구조"의 유닛 목록(스토어 줄 추가), "테스트"에 `FILMCRAFT_TEST_CODEX=1 … -k real_codex`(구독 한도로 1장), "한계"에 크기를 정할 수 없음·Codex 내부 기록 형식 의존·Codex 폴더에 사본이 남음. 실사 생성물의 공개 규정은 README에도 쓰지 않는다. "스킬이 있을 때와 없을 때" 표는 이번 대조가 표에 실을 만한 비교(같은 과제의 두 실행에서 드러난 차이)를 냈을 때만 한 행을 더한다.

## 테스트 설계 (`coding` 스킬 기준, 이음매는 이번에 합의)

이음매는 둘이다. ① 스킬의 실제 진입점(`tests/support`의 `skill(...)`로 `cli.py imagegen`/`imagenote`를 부름. 이를 위해 `skill()`이 `input=`과 `env=`를 받게 고친다) + PATH에 놓은 가짜 `codex`·가짜 `open` + 임시 `CODEX_HOME`. ② 디스크에 남는 것(`imagegen.json`, `contact-sheet.html`, 그림 파일): 모델이 장부를 직접 읽고 사람이 시트를 보므로 저장된 모양 자체가 약속이다. 유닛 내부 함수를 직접 부르는 테스트는 두지 않는다.

| 무엇 | 어디서 관찰 | 기대값의 출처 |
|---|---|---|
| 성공: 그림이 `DIR/NAME-1.png`로, 장부 행(`ok`, 크기, `verbatim: exact`), JSON, exit 0 | CLI + 가짜 codex | 가짜가 쓴 PNG의 크기·알파(테스트가 정한 값) |
| 덮어쓰지 않음: 다시 부르면 k가 이어짐, 실패도 번호를 씀, 기존 PNG의 바이트 불변, 장부에 없는 `NAME-k.png`가 있으면 그 시도만 실패 | CLI, 파일 해시 | 호출 순서에서 손으로 센 번호 |
| 관리 파일: 남의 `imagegen.json`·`contact-sheet.html`이 있는 폴더에서는 아무것도 쓰지 않고 exit 2 | CLI, 폴더의 전후 바이트 | — |
| 이름: 빈 이름, 경로 구분자, `-숫자` 끝, 대소문자만 다른 이름은 exit 2. 한글·공백 이름은 됨 | CLI | — |
| `--again`: 같은 요청에 시도가 붙음, 생성 인자와 함께면 exit 2, 참조가 없어지거나 바뀌면 생성 전에 exit 2 | CLI, 장부, 가짜의 호출 기록(호출 없음) | 장부의 요청 수·시도 수 |
| 상태: 거부(`input`/`output`/`unknown` 단계), 시간 초과(자식 프로세스까지 죽음, 재시도 포함 한 제한 안), 비정상 종료, 그림 없음 — 각각 장부 `status`·`detail`, stdout `status`, stderr 줄, 종료 코드 | 가짜 codex 시나리오 | 시나리오가 넣은 사유 문자열과 단계 |
| 프롬프트 변형: 한 번 재시도 뒤 성공이면 `ok`+`retried`, 두 번 다 다르면 `prompt_altered`(그림 파일 있음, 시트에 보임, `--choose` 거부) | 가짜 `rewrite_ok`·`rewrite_twice` | 시나리오 |
| 관측과 보고: 관측과 자기 보고가 다르면 관측을 따름. 관측이 없으면 자기 보고가 일치해도 `unverified`, 불일치면 재시도. 관측 항목은 있는데 `savedPath` 파일이 없음, 완료 항목이 둘, rollout 줄 하나가 깨짐, `thread.started` 없음 — 각각 정해진 상태와 `detail` | 가짜가 rollout과 마지막 메시지를 다르게 씀 | 시나리오마다 어느 파일이 놓이고 `verbatim`이 무엇인지 표로 고정 |
| 중단: 실행 중인 `cli.py`에 SIGTERM → 가짜 codex와 그 자식이 모두 죽고 시도가 `interrupted`. SIGKILL → 다음 읽기에서 `interrupted` | 가짜 `hang`·`hang_stubborn`, 프로세스 목록, 장부 | — |
| 동시성: 한 실행에서 6개까지만 동시에. **같은 폴더에 `imagegen` 둘과 `imagenote` 하나를 겹쳐 실행해도** 행이 빠지지 않고 번호가 겹치지 않고 장부가 스키마를 통과 | 가짜의 호출 기록(시작·끝 시각), 장부 | 겹침 수, 손으로 센 행 수 |
| 사실: 크기, 알파 유무와 투명 비율 | CLI | 가짜 PNG의 생성 조건 |
| 참조: 없는 파일 exit 2, 장부에 상대 경로와 sha256, 관측 해시가 다르면 `detail` | CLI, 장부 | hashlib으로 따로 계산 |
| codex 없음 / 로그아웃: exit 1, 시도 없음, 메시지에 `codex login` | PATH 조작, 가짜 `logged_out` | — |
| 시트: 장부가 바뀌면 내용과 스탬프가 바뀌고, 바뀌지 않으면 스탬프도 그대로. 이름·그림 링크(한글·공백 파일 이름이 URL 인코딩되고 링크 대상이 실제로 있음)·한국어 라벨·접힌 프롬프트·실패 목록. 프롬프트의 `<script>`가 이스케이프됨 | HTML 파일 | 장부에 넣은 값 |
| 시트 열기: 처음 한 번만 `open` 호출, `--no-open`이면 안 부르고 다음 실행에서 부름, `open`이 실패하면 `sheet_opened`를 적지 않고 다음 실행에서 다시 부름 | 가짜 `open`의 호출 기록, 장부 | 호출 횟수 |
| `imagenote`: 선택·해제(같은 상태면 성공)·메모(덧붙음)·평가(대체)가 장부와 시트에, 잘못된 대상·`ok` 아닌 그림 선택은 exit 2 | CLI, 장부, HTML | 넣은 문자열 |
| 장부 보호: 손상된 JSON·모르는 키면 쓰지 않고 실패(파일 바이트 불변), 죽은 프로세스의 `running`은 `interrupted`로, 그때 파일이 있으면 `file`이 채워짐 | 장부 파일을 손으로 고쳐 놓고 CLI | — |
| doctor: codex 항목의 세 값, 전체 판정에 영향 없음, 네트워크·쓰기 없음 | 기존 `judge(Facts)` 이음매와 실제 진입점 | — |
| 구조: `codex` system, `imageledger` store, `imagegen` feature, 유닛 밖에서 `__all__`만, 스토어가 기능·시스템을 import하면 잡힘 | `test_structure.py`(깨뜨린 트리 포함) | — |
| 본문: `` `imagegen --ref` `` 같은 스팬의 플래그가 실제로 있음, 본문에 크기 수치가 없음 | `test_skill_text.py` | 실제 `--help` |
| **실제 Codex 1장**(`FILMCRAFT_TEST_CODEX=1`, `-k real_codex`): 참조 1장과 `--transparent`로 한 번 → `ok`, PNG가 RGBA, verbatim이 `exact`/`normalized`(관측이 살아 있다는 뜻), 관측된 입력 해시가 참조 파일의 해시 | 실제 진입점 | 보낸 프롬프트, hashlib |

- 가짜 codex 뒤에 숨은 계약(실제 Codex의 이벤트·rollout 형식)은 게이트 테스트와 M1~M4가 맡는다. 가짜는 M1~M4에서 **측정한** 모양을 쓴다. 게이트 테스트가 보장하는 것은 성공 경로뿐이고, 거부·중단·동시 실행의 실제 Codex 쪽 모양은 측정 한 번(M4·M9·M10) 뒤로는 자동으로 다시 확인되지 않는다.
- 확인하지 못하는 것으로 남기는 것: PNG를 놓은 직후·장부를 닫기 전의 정확한 순간에 죽는 경우는 CLI 이음매에서 결정적으로 재현할 수 없다. 복구 규칙(다음 읽기 때 `file`을 채움)은 장부를 손으로 그 상태로 만들어 놓고 검사한다.
- 순서는 동작 하나에 red → green 한 번씩. 새 모듈은 먼저 import만 되게 만들어, red가 "동작이 없다"는 단언이 되게 한다.
- 진입점 배선은 `uv run`으로 한 번(`skill(..., via_uv=True)`): PEP 723 의존성(Pillow)이 실제 실행에서 풀리는지.

## 구현 때 측정할 것 (실제 호출, 구현 1단계와 6단계)

결과는 이 파일의 "측정 원장" 절에 적는다. Codex 실제 호출의 배분(성진님 승인: 측정·검증 약 20회, 그리고 대조가 만드는 몇 장):

| 언제 | 묶음 | 호출 | 겸하는 물음 |
|---|---|---|---|
| 1단계(명령이 생기기 전. 스크래치패드에서 design의 봉투로 `codex exec`를 직접 부름) | 봉투 있는 단일 호출 | 4 (기본 1, 투명 1, 참조 1장·경로에 공백과 한글 1, 참조 2장 1) | M1, M2, M3, M5(봉투 쪽), M6 |
| 1단계 | 봉투 없는 호출 | 2 (그중 1은 첫 문장에 비율 없음) | M5, M7 |
| 1단계 | 거부 유도 | 2 | M4 |
| 6단계 첫머리(만든 `imagegen`으로, E2E용 작품 사본의 `graphics/imagegen/`에) | 한 요청 `--n 6`(투명 아이콘) | 6 | M9(한 실행의 6개 동시), E2E 2번, C1의 재료 |
| 6단계 첫머리 | 겹쳐 실행하는 세 명령(세로 배경, 가로 배경, 부드러운 그림자가 있는 투명 소품) | 3 | 같은 폴더의 다중 프로세스를 실제 Codex로, C1~C4의 재료, E2E 6번 |
| 6단계 첫머리 | 실행 중 강제 종료(SIGTERM 한 번, SIGKILL 한 번) | 2 | M10 |
| 10·11단계 | 게이트 테스트 1, 한 요소 바꾸기 1 | 2 | 구현 10단계, E2E 4번 |
| 7단계 | 기준선 대조의 과제들(과제당 생성 2장까지) | 6~12 | 대조 |

측정·검증 21회에 대조 6~12장을 더해 약 30회다(35회를 넘기게 되면 그 전에 알린다). 측정의 우선순위는 M1 > M3 > M2 > M4 > M9 > M10 > M5 > M7이다. 한도가 막히면 뒤에서부터 빼고, 뺀 물음은 "수용한 가정"에 미확인으로 남긴다.

| # | 물음 | 이것이 정하는 것 |
|---|---|---|
| M1 | 설치된 Codex에서 성공 한 번의 `--json` 스트림과 rollout 모양. `image_gen.generation` 항목과 필드가 0.166.0 기록과 같은가. 실행 로그 없이 rollout만으로 충분한가 | 관측 코드, 가짜 codex의 모양, 실행 로그를 남길지 |
| M2 | `--transparent` 결과가 RGBA이고 알파가 진짜인가 | `alpha` 보고 |
| M3 | `--ref` 1장·2장이 `inputImages`에 해시와 함께 남는가. 경로에 공백·한글·이모지가 있어도 되는가 | 참조 전달. 안 되면 호출마다 참조를 임시 ASCII 경로로 복사해 넘기고 장부에는 원래 경로를 남긴다 |
| M4 | 거부를 일으켰을 때(입력 단계, 가능하면 출력 단계) rollout의 `failure`와 이벤트 모양 | 거부 분류와 단계. 재현하지 못하면 `stage: unknown`과 원문 메시지만 다루고, 가짜의 거부 시나리오는 "모양 미확인"이라고 적는다 |
| M5 | 봉투 없이 주면 Codex가 프롬프트를 재구성하는가. 호출마다 쓴 프롬프트, rollout의 도구 호출 입력, `revisedPrompt` 셋을 나란히 비교(`revisedPrompt`가 Codex가 넘긴 값인지 이미지 쪽이 고쳐 쓴 값인지 가리기 위해) | verbatim 판정을 어느 값에 걸지. 봉투는 결과와 무관하게 유지 |
| M6 | 호출 하나의 전체 시간(사용자 설정 그대로, 위 호출들에서 얻음) | `--help`의 시간, `--timeout` 기본값 |
| M7 | 프롬프트 첫 문장에 비율을 말하지 않으면 비율이 어떻게 되는가(한 번의 관찰, 참고용) | `--help`의 비율 문장(비율은 프롬프트로만 정해지고, 나온 크기는 명령이 출력한다) |
| M8 | `codex --version`과 `codex login status`가 `test_it_uses_no_network_and_writes_nothing`의 바로 그 sandbox-exec 정책 아래에서 같은 답을 내는가. 생성 호출 없음 | doctor 항목의 값 |
| M9 | 6개 동시 실행이 실패 없이 도는가 | 동시성 상한(실패하면 낮춘다) |
| M10 | 실행 중인 `cli.py`를 SIGTERM으로, 한 번은 SIGKILL로 끝냈을 때 codex 자식이 어떻게 되는가 | 중단 계약의 문구 |
| C1 | 투명 PNG(부드러운 가장자리·그림자)를 FilmCraft에서 영상 위에 놓았을 때의 가장자리와, 같은 그림이 시트(브라우저)에서 보이는 모습의 차이 | 줄 ⓓ·ⓗ |
| C2 | 1672×941 그림을 1920×1080 전체 화면과 2배 푸시인으로 놓았을 때의 선명도 | 줄 ⓘ 셋째 줄의 표현 |
| C3 | 같은 PNG를 페이지(`graphic`)와 EffectCraft 컴포지션에 넣었을 때 색·알파가 FilmCraft 직접 배치와 다른가 | 10절·12절에 줄이 필요한지 |
| C4 | FilmCraft의 PNG 스틸 가져오기에서 조용히 틀리는 것(길이 기본값, 알파 해석, 프레임보다 큰·작은 그림의 배치 크기) | 6절에 줄이 필요한지 |

## 구현 단계 (TaskCreate 트래커. description에 완료 판정을 그대로 쓴다)

0. **이름과 브랜치.** `main`을 최신으로 맞추고 작업 트리에 이 계획 파일 말고 다른 변경이 없는지 본다(있으면 건드리지 않고 보고). 계획 파일이 아직 원래 이름이면 `mv`로 `video-imagegen.md`로 바꾸고 `feat/imagegen` 브랜치를 판다. 완료: `.claude/plans/video-imagegen.md`가 있고 원래 이름의 파일이 없다, 현재 브랜치가 `feat/imagegen`.
1. **Codex 측정(M1~M8).** 스크래치패드에서 design의 봉투를 써서 `codex exec`를 직접 부른다(명령은 아직 없다). 완료: M1~M8 각 물음에 결과(또는 "재현 못 함")가 "측정 원장"에 적혀 있고, 그 결과로 정해지는 설계 항목(관측 필드, verbatim을 거는 값, 타임아웃 기본값, doctor 값, 참조 경로 처리)이 한 줄씩 확정돼 있다.
2. **가짜 codex와 뼈대.** `tests/support/fake_codex.py`를 측정한 모양으로 쓰고, `skill()`에 `input=`·`env=`를 더하고, 세 유닛을 import만 되게 만들고, `cli.py`에 두 하위 명령의 파서를 넣고, 구조 테스트에 kind와 유닛을 넣는다. 완료: `imagegen --help`·`imagenote --help`가 뜨고, 구조 테스트 green, 첫 동작 테스트(성공 경로)가 "그림이 없다"는 단언으로 red.
3. **생성 경로.** 테스트 표의 행 순서대로 red → green: 성공 → 덮어쓰지 않음·이름·관리 파일 → `--again` → 상태 → 프롬프트 변형 → 관측과 보고 → 중단 → 동시성 → 사실·경고 → 참조 → codex 없음. 완료: 해당 테스트가 runner 종료 코드 0, 각 테스트를 먼저 실패로 본 기록.
4. **장부 보호와 시트.** 완료: 해당 테스트 green, 실제 브라우저에서 시트를 한 번 열어 확대·화살표·자동 갱신을 확인한 스크린샷.
5. **`imagenote`와 doctor.** 완료: 해당 테스트 green, `doctor` 실제 실행 결과에 codex 항목.
6. **실제 명령으로 측정(M9·M10)과 합성 측정(C1~C4).** "검증"의 작품 사본을 만들고, 만든 `imagegen`으로 M9·M10과 겹쳐 실행을 돌린다(이 그림들이 검증 2·6번의 그림이다. M9가 실패하면 동시성 상한을 낮추고 해당 테스트와 `--help`를 고친다). 그 생성물로 C1~C4를 잰다. 완료: 측정 원장에 M9·M10·C1~C4와, 각 결과가 정하는 줄(ⓓⓗ, ⓘ 셋째 줄, 6·10·12절 추가 여부)의 처분.
7. **기준선 대조.** "skill-maker 프레임 적용"의 절차대로 과제 2~3개를 새 본문 줄 없이 돌리고, 결과(프레임 시트, 컨택트 시트, 모델이 한 말의 요약)를 성진님께 보여 판정과 그 이유를 받는다. 여기서 세션은 답을 기다리며 멈춘다. 완료: 이 파일의 "대조 원장"에 과제마다 실행 조건·결과·성진님의 판정이 있고, 대조에 달린 줄(ⓓⓕⓖ, ⓘ 둘째·셋째 줄)마다 넣음/뺌/고침과 그 근거, 대조가 새로 드러낸 것마다 본문·`--help`의 자리 또는 넣지 않는 이유가 적혀 있다.
8. **본문과 `--help` 확정.** 6·7단계의 처분대로 SKILL.md와 두 `--help`를 쓴다. 줄마다 "skill-maker 프레임 적용"의 물음에 답이 있어야 한다. 완료: `test_skill_text` green, `claude plugin validate --strict ".claude/skills"` 종료 코드 0, `--help`의 인자·출력·종료 코드를 한 번씩 실행으로 대조, 넣은 줄마다 근거(측정 번호, 대조 과제, 성진님 결정 중 하나)가 이 파일에 있다.
9. **README.** 완료: 위 "README" 항목이 모두 반영.
10. **게이트 테스트와 전체 실행.** `FILMCRAFT_TEST_CODEX=1 … -k real_codex` 통과, 전체 스위트 종료 코드 0. 완료: 두 명령의 출력을 PR에 그대로.
11. **끝에서 끝까지.** 아래 "검증"의 시나리오. 본문이나 `--help`가 여기서 바뀌면 8단계의 검사를 다시 돌린다. 완료: 시나리오의 각 줄에 실제 결과.
12. **독립 리뷰.** `codex` 스킬로 다른 모델 계열에 **최종** 텍스트와 코드를 보낸다: (a) 새 SKILL.md 줄과 두 `--help`를 skill-maker의 여섯 성질에 비춰(대조 원장을 함께 준다), (b) 코드와 테스트를 계약(덮어쓰지 않음, 장부 일관성, 프로세스 정리, 관측 규칙)에 비춰. 완료: 지적마다 채택/기각과 이유가 이 파일의 "리뷰 반영 내역"에, 채택으로 바뀐 곳의 테스트가 다시 green.
13. **승인과 머지.** 성진님이 SKILL.md 전문을 승인한다(부분 승인이나 무응답은 승인이 아니다. 여기서 세션은 답을 기다리며 멈춘다) → PR → 스쿼시 머지 → 릴리스. 완료: `gh release view v0.4.0`.

## 검증 (end-to-end)

실제 작품의 사본에서(원본 `data/`는 건드리지 않는다. 스크래치패드에 한글·공백 이름의 작품 폴더 하나를 `cp -c`로 복사하고 `media.autoRelink`):

1. `doctor`에 codex 항목이 `installed, logged in`.
2. `imagegen mic --dir graphics/imagegen --transparent --n 6`(구현 6단계 첫머리의 M9 실행이 이것이다) → 6장, 시트가 브라우저에 열림, 장부에 요청 1개·시도 6개. 프롬프트를 heredoc으로 넣은 이 호출에 권한 프롬프트가 뜨는지 본다.
3. `imagenote mic-2 --dir … --choose --note "…"` → 열려 있는 시트에 선택 표시와 메모가 새로 고침 없이 나타남.
4. `imagegen mic --dir … --ref graphics/imagegen/mic-2.png --label "…"`(한 요소만 바꾸기) → `mic-7.png`, 기존 여섯 장의 해시 불변, 장부에 참조의 상대 경로와 해시.
5. 고른 그림을 페이지에 넣어 `graphic`으로 렌더하고(`fallback`·`blocked` 없음), FilmCraft 타임라인에 올려 `frames --project --overlay shorts --width <실제 폭>`으로 영상 위 모습을 확인.
6. 6단계 첫머리에 겹쳐 실행으로 만든 세로 배경을 전체 화면으로 놓고 `frames`로 확대 상태 확인(C2). 그 겹쳐 실행 뒤 장부에 세 이름의 행이 모두 있고 번호가 겹치지 않는지 본다.
7. 장부만으로 이어 갈 수 있는가: `claude` 스킬의 읽기 전용 작업자에게 `imagegen.json`과 `imagegen --help`만 주고 "mic-2와 같은 그림을 하나 더 만들려면 어떤 명령을 치겠는가, 사용자는 왜 mic-2를 골랐는가"를 묻는다(구현 세션은 답을 이미 알므로 스스로는 확인할 수 없다). 작업자 실행 한 번, 생성 호출 없음.
8. 전체 스위트와 게이트 테스트, `claude plugin validate --strict`.

## Git

- PR 하나, 이유 하나: "영상에 필요한 그림을 생성해 쓰고 그 이력과 판정을 남긴다". 제목 `feat: video 스킬에 imagegen 이미지 생성과 컨택트 시트 추가`. 이 계획 파일(이름 바꿈 포함)과 README, SKILL.md가 같은 PR에 들어간다.
- 커밋은 결정 하나에 하나: 계획 파일 / codex 유닛(관측 우선, 버린 대안: 자기 보고만) / 장부 스토어와 구조 테스트의 `store` kind / imagegen 생성 / 시트 / imagenote(직접 편집 대신 명령인 이유) / doctor / SKILL.md(대조의 과제·결과·성진님의 판정, 줄마다 넣거나 뺀 근거, design 유래 줄을 넣지 않은 이유, 줄을 썼을 때의 모델) / README.
- 구현 중 하던 일을 막는 기존 버그가 나오면 main에서 따로 PR·머지하고 브랜치를 그 위로 옮긴다.
- 머지 뒤 릴리스: `gh release create v0.4.0 --target <main sha>`. 본문은 한국어, 이전 릴리스(`gh release view v0.3.0`)와 같은 제목 순서 — 소개 문단, `## 이번에 들어간 것`, `## 왜`, `## 쓰는 법`("이전과 달라진 점" 포함), `## 필요한 것과 확인한 버전`, `## 알려진 한계`, 끝에 `라이선스: MIT`. 올리기 전에 `git archive HEAD`에 `.tmp`·`data/`·실행 로그가 없는지 본다.

## skill-maker 프레임 적용

구현 세션은 시작할 때 `Skill`로 `skill-maker`와 `coding`을 연다(읽지 말고 호출한다). 이 절은 그 프레임을 이 작업에 댄 결과이고, 구현 중 여기 없는 판단이 생기면 프레임 원문이 이 계획보다 우선한다. 이 스킬은 대화 속에서 쓰이고(예약 실행 없음), 성진님과 공개 레포의 다른 사용자가 쓴다. 그래서 취향·작업 방식은 본문이 정하지 않고 그 자리의 사람이 정한다.

### 여섯 성질

| 성질 | 이 계획에서 |
|---|---|
| Principle over rail | 본문 줄은 사실과 이유. 용도 목록·생성 절차·고치는 순서·금지 없음. 행동을 지시하는 줄은 대조에서 "사실을 줬는데도 사람이 알아채지 못할 곳에서 틀렸다"가 확인될 때만, 그 이유보다 세지 않게 쓴다 |
| Interface over document | 프롬프트 경향, 크기 표, 상태, 장부 스키마, 거부의 뜻은 `--help`. 본문은 호출 전에 계획을 바꿔야 하는 것(되돌릴 수 없는 전송, 함께 쓰는 한도)과 어느 인터페이스도 말하지 못하는 것(두 길이 어떻게 다른가)만 |
| Model over machinery | 아래 "명령과 인자" 표 |
| For the model, not the maintainer | 어느 실험·어느 Codex 버전·어느 대조에서 나온 줄인지는 커밋·PR·이 파일에. 본문·`--help`에는 없음 |
| Dense | 모델 이름·크기 수치처럼 남이 가진 값은 쓰지 않고 그 값이 일으키는 일(확대됨, 한도를 씀)을 씀. 다시 말하기, 규칙을 변호하는 문장, 모델이 계산할 수 있는 귀결은 뺌 |
| Colleague over autopilot | 어느 후보·어떤 화풍은 사용자의 취향. 생성할지 코드로 그릴지는 기존 결정대로 Claude가 이유와 함께 고르고 사용자가 바꾼다. 본문은 이 영역에서 되돌리기 비싼 것(밖으로 나간 그림, 쓴 한도), 결과가 보여 주지 않는 것(ⓓ), 모델이 틀린 것으로 확인된 곳(대조가 내면)을 사실로 적는다. "먼저 물어라"류의 일반 지시 없음 |

### 명령과 인자 (Model over machinery를 하나씩)

| 무엇 | 자리를 얻는 이유 / 뺀 이유 |
|---|---|
| `imagegen` | 모델의 도구가 닿지 못하는 곳(이미지 생성, 사용자의 Codex 로그인) |
| 원문 전달 확인(verbatim) | Codex가 프롬프트를 바꿨는지는 결과만 봐서는 알 수 없다 |
| 덮어쓰지 않는 번호, 장부, 6개 동시 | 여러 값을 함께 맞춰야 하는 쓰기. 매번 같은 방식이어야 한다 |
| 알파 보고 | 그림을 읽는 것으로는 알파 채널의 유무와 비율이 보이지 않는다 |
| `--again` | 같은 프롬프트를 다시 타이핑하면 글자가 바뀔 수 있다. 바이트가 같은 요청으로 시도를 더하는 일 |
| `--label` | 호출하는 쪽만 아는 한 줄을 시트로 옮길 뿐, 판단이 없다 |
| 컨택트 시트 | 터미널에서 그림을 못 보는 사용자에게 후보를 보여 주는 닿음. 매번 같은 모양 |
| `imagenote` | 잠금 아래에서 장부와 시트를 함께 맞춰 써야 한다 |
| (뺌) `--aspect`와 비율 경고 | 명령이 크기를 출력하므로 모델이 스스로 본다. `--help` 한 줄 |
| (뺌) 장부를 읽는 명령 | 모델이 JSON을 읽고 필요한 질의를 스스로 쓴다 |
| (뺌) 배치·확대·누끼·업스케일 래퍼 | 놓는 일은 기존 경로가 하고, 어떻게 놓을지는 판단이다 |

### 본문 줄이 자리를 얻는 근거

줄마다 묻는 것: 이 줄 때문에 모델이 다르게 행동하는가. 모델이 볼 수 없는 사실인가, 아니면 보면 스스로 할 일인가. `--help`가 가져야 할 값인가. 취향이나 방법을 사람 대신 정하는가.

| 줄 | 근거의 종류 | 확정되는 곳 |
|---|---|---|
| ⓐ description, ⓑ 기록의 자리, ⓙ 폴더 관례 | 이 스킬을 쓰는 사람들이 정한 것(산출물 자리, 일하는 방식)은 모델이 볼 수 없는 사실 | 성진님 결정(이번 세션) |
| ⓒ 한도, ⓘ 첫 줄(밖으로 나감, 한도, Codex 폴더의 사본) | 호출 전에 계획을 바꿔야 하는 비용과 되돌릴 수 없는 효과. `--help`는 호출할 때 읽히므로 본문에 | 문서와 로컬 기록(부록) |
| ⓘ 넷째 줄(장부·시트·`imagenote`) | 기록이 어디 있고 무엇을 담는지는 스킬의 관례 | 성진님 결정 |
| ⓗ 시트와 FilmCraft 합성의 차이 | 측정으로만 보이는 사실 | C1 |
| ⓓ 결과가 보여 주지 않는 것 | 모델이 확인 없이 넘기는지가 관건 | **대조** T2·T3 + C1·C2 |
| ⓕ 레이어 없는 한 장, ⓘ 둘째 줄(다시 만들면 다른 그림, 참조로 고치면 전체가 다시 그려짐, 그림 속 글자) | 모델이 이미 알 수 있는 내용. 알면서도 글자를 그림에 구워 넣거나 승인된 그림을 다시 만드는지가 관건 | **대조** T2 |
| ⓖ 코드로 그리기와 생성하기의 차이 | 모델이 이미 알 수 있는 내용. 도구가 있는데도 생성이 맞는 자리에서 빼거나 글자로 대신하는지가 관건(성진님의 처음 요청) | **대조** T1 |
| ⓘ 셋째 줄(크기) | 크기는 결과에 찍힌다. 계획 단계에서 확대를 고려하지 않는지가 관건 | **대조** T3 + C2 |

"대조"에 달린 줄은 대조에서 모델이 그 줄 없이도 맞게 했으면 뺀다. 모델이 경고 없이 틀렸고 성진님이 그 결과를 물리친 이유가 그 과제 밖에서도 성립하면 넣는다(필요하면 그 사실을 준 채로 한 번 더 돌려 사실만으로 충분한지 본다). 모델이 스스로 불확실하다고 밝힌 것은 이미 아는 것이므로 줄이 아니다. 대조가 초안에 없던 것을 드러내면 같은 기준으로 자리를 정한다.

### 기준선 대조 (구현 7단계)

- 무엇을 가리나: 판단만 가린다. 도구와 사실은 준다. 대조용 스킬 사본은 **새 코드(`imagegen`·`imagenote`와 그 `--help`) + 옛 SKILL.md 본문**(main의 본문에서 `cli.py --help`가 새 명령을 보여 주는 상태)이다. 새 본문 줄 ⓐ~ⓙ만 없다. 7단계 시점의 작업 트리가 바로 이 상태이므로(코드는 끝났고 본문은 아직 안 고쳤다) 그 상태를 복사해 쓴다. 과제 문장은 도구 이름을 말하지 않는다: 모델이 `cli.py --help`에서 도구를 찾지 못해 쓰지 않았다면 그것은 판단의 실패가 아니라 ⓐ(description)와 본문이 도구의 존재를 알려야 한다는 근거이고, 그때는 "그림을 생성하는 도구가 있다"는 사실만 준 채로 다시 돌려 판단을 본다.
- 어떻게 돌리나: `video-effectcraft.md`의 대조와 같은 방식 — `claude` 스킬의 작업자, 이 스킬이 서빙할 모델, `auto` 프로필, 작업 폴더는 `.tmp/contrast/<과제>/`에 그 과제에 필요한 입력만 복사. 실행이 파일·도구·권한이 없어 실패했으면(`permission_denials`) 전문성에 대해 아무것도 말해 주지 않으므로 빠진 것을 채워 다시 돌린다.
- 입력: 실존 인물이 찍힌 영상을 쓰지 않는다. ffmpeg와 macOS `say`로 만든 합성 소재(테스트가 쓰는 방식)나 사람 없는 화면으로 한다. 과제 문장에 "생성은 2장까지"를 넣는다(Codex 한도).
- 과제(성진님의 실제 일에서 고른 것. 문장은 구현 때 확정하고 대조 원장에 그대로 남긴다):
  - T1 그림 소재가 필요한 숏츠: 말하는 내용에 맞는 그림 요소 하나를 넣어 달라고 한다. 보는 것: 생성·코드·요청·생략 중 무엇을 골랐고 이유를 말했는가.
  - T2 글자가 들어간 그림: 한글 제목이 적힌 간판(또는 현수막) 그림으로 3초 인트로. 보는 것: 글자를 그림에 구워 넣었는가 위에 얹었는가, 틀린 글자를 알아챘는가, 고칠 때 무엇을 했는가.
  - T3 화면 전체 배경과 푸시인: 세로 화면 전체를 덮는 배경을 만들고 천천히 밀어 들어간다. 보는 것: 확대를 고려했는가, 영상 위에서 실제 크기로 확인했는가.
- 판정: 결과를 성진님께 보여 드리고(프레임 시트, 컨택트 시트, 모델이 한 말) 무엇이 문제인지와 그 이유를 묻는다. "모델이 이렇게 해야 하나요"가 아니라 결과에 대한 판정을 묻는다. 성진님이 받아들인 결과는, 방법이 달랐더라도 스킬에 넣을 것이 없다는 뜻이다.
- 비용: Claude 작업자 3~6회(회당 $1~3 예상), Codex 생성 6~12장. 측정·검증의 21회와 합쳐 약 30회이고, 35회를 넘기게 되면 그 전에 알린다.
- 결과는 이 파일의 "대조 원장"에 남긴다.

### skill-maker의 완료 조건 → 단계

| 완료 조건(원문 요지) | 만족시키는 곳 |
|---|---|
| 사용자가 스킬 텍스트 전문을 승인(일부나 침묵이 아님) | 13단계 |
| 스킬이 싣는 판단이 적혀 있고, 모델이 그르칠 경계가 정리돼 있고, 불확실한 것이 밝혀져 있음. 승인은 실제 세션에서의 성능 증거가 아님 | 8단계의 줄별 근거, "수용한 가정", PR 본문 |
| 사용자가 고수한 이의와 모델이 못 잡았을 실수마다 스킬 안의 자리 또는 뺀 이유. 행동 줄은 Principle over rail을, 명령은 Model over machinery를 통과 | 대조 원장(7단계), 위 두 표, 8단계 |
| `claude plugin validate --strict`가 스킬 폴더의 부모에서 0 | 8단계(`.claude/skills`. 스킬 폴더는 링크가 아니라 실제 폴더) |
| 만든 코드를 그 계약(입력·출력·실패)으로 확인, `--help`가 동작과 같음, 구조 테스트 통과 | 3~5단계, 8단계, 10단계 |
| 초안을 보이기 전에 다른 모델 계열이 여섯 성질에 비춰 검토, 그 검토를 따져서 반영 | 12단계(13단계 앞) |
| 개발 기록(출처, 면담, 버린 대안, 줄을 쓴 모델)은 스킬 밖에 | 커밋 본문, PR, 이 파일 |

남는 위험: 대조는 과제 2~3개의 한 번씩이다. 거기서 드러나지 않은 실수는 본문에 없고, 거기서 한 번 본 실수가 늘 일어나는 것도 아니다. 본문 승인은 여러 실제 세션에서의 성능 증거가 아니다.

## 제외한 것 (다시 열 조건)

- **OpenRouter Images API 엔진.** 공식 문서로 확인한 것: `POST /api/v1/images`, 크기·비율·투명 배경(gpt-image-2.5/2.6)·참조 16장, 한 변 최대 3840, 장당 과금(1536×1024 high 약 $0.04, 4K 약 $0.10), 이 스킬에 이미 키와 `openrouter` 유닛이 있음. 다시 열 조건: 화면 전체 배경의 확대가 실제 작품에서 문제로 드러날 때(C2), Codex 한도가 작업을 막을 때, 또는 Codex 내부 기록 형식이 자주 깨질 때. 그때는 `--engine`을 `transcribe`처럼 더한다.
- **실사 생성물 규정 줄.** 조사한 원문은 부록. 다시 열 조건: 성진님 결정.
- **design 유래 판단 줄.** 다시 열 조건: 대조(7단계)나 그 뒤의 실제 세션에서 같은 실수가 영상 작업에서 확인될 때. 그때도 design의 문장이 아니라 확인된 사례에서 줄을 쓴다.
- **재사용 메모(`--scope reusable`), 최종 표시(`finals`), 내보내기.** design에만 있는 포스터 흐름.
- **호출마다 참조 파일의 스냅숏 사본을 보관하기**(codex 리뷰 제안). 관측된 입력 해시를 장부에 남기는 것으로 "무엇이 실제로 갔는가"는 확인되고, 사본은 작품 폴더를 키운다. 다시 열 조건: `--again`이 참조가 바뀌어 막히는 일이 실제로 불편할 때.
- **Codex 폴더의 그림 사본 지우기.** Codex 자신의 문서가 원본을 그대로 두라고 하고, 사용자의 `codex resume` 이력과 이어져 있다.
- **생성물을 자동으로 놓거나 키우는 명령, 누끼(`cutout`), 업스케일.**
- **`references/`.** 재개 조건은 이전 계획과 같다: 어떤 분기 절이 커져 다른 경로가 내는 비용이 눈에 띄면 그 절만 뗀다.

## 수용한 가정 (구현 때 확인)

- 설치된 Codex(0.167.1)의 rollout이 0.166.0 기록과 같은 모양이다 → M1.
- 6개 동시 실행이 지금도 실패 없이 돈다(design 주석: "Six calls have run together without failures; more is unmeasured") → M9.
- `codex login status`는 로컬 파일만 읽고 쓰지 않는다 → M8.
- design의 봉투가 지금 모델에서도 원문 전달을 지킨다(36/36 일치는 봉투가 있는 0.166.0 실행이었다) → M1~M3의 네 호출.
- `revisedPrompt`는 Codex가 도구에 넘긴 프롬프트다(이미지 쪽이 고쳐 쓴 값이 아니다) → M5.
- FilmCraft가 RGBA PNG 스틸의 알파를 그대로 합성한다(`graphic`의 PNG 스틸 경로가 이미 쓰는 길) → C1·C4.
- 프롬프트를 heredoc으로 stdin에 넣은 호출이 `allowed-tools`의 `Bash(uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" *)` 사전 승인에 들어간다(design 스킬이 같은 패턴으로 써 왔다) → E2E 2번. 권한 프롬프트가 뜨면 프롬프트를 파일로 받는 인자를 더한다.
- 샌드박스 없는 세션에서 `open`이 시트를 연다(성진님의 주 세션 설정에는 sandbox 블록이 없다). 열지 못하는 세션에서는 경로를 알리는 것으로 끝난다.

## 리뷰 반영 내역

### codex 계획 리뷰 (`gpt-6.1-terra`, read-only, 2026-11-14, run `20261114-203931-imagegen-plan-review-b30f`)

| # | 지적 | 처분 |
|---|---|---|
| 1 | 프로세스가 죽으면 파일과 장부가 어긋남, 부모 사망 시 자식 처리 없음 | 채택. SIGTERM·SIGINT 처리, SIGKILL의 한계, PNG 놓기와 장부 닫기 사이의 복구 규칙, `pid`가 누구 것인지를 계약에 넣음. `queued` 상태는 만들지 않음(기다리는 것과 도는 것을 구별해서 달라지는 행동이 없다) |
| 2 | "어떤 실행도 기존 파일을 바꾸지 않는다"가 장부·시트의 갱신과 충돌 | 채택. 불변 약속을 생성 PNG로 한정, 관리 파일 구분, 남의 파일이 있는 폴더는 거부, 복사 경로의 부분 파일 정리 |
| 3 | 동시 실행의 직렬화 범위가 없음 | 채택. 번호 예약은 장부 잠금 하나 안, 시트는 잠금 뒤 읽기, 잠금을 겹쳐 잡지 않음, 6개는 실행당, 열기 성공 때만 기록, 다중 프로세스 테스트 |
| 4 | 관측 항목이 여럿이거나 필드가 빠질 때의 규칙이 없음 | 채택. "완료이고 파일이 있는 마지막 항목", 여럿이면 수를 기록, 필드 결손은 2순위 경로 |
| 5 | 인자·관측에 대한 주장이 표본보다 넓음. `num_last_images_to_include` 2건 | 부분 채택. 주장을 표본 범위로 좁힘. 2건은 리뷰 세션 자신의 명령 문자열이 잡힌 것이었으나(직접 확인), 그 세션의 도구 정의에서 0.167.1의 인자 넷을 확인해 사실 표에 넣음 |
| 6 | 자기 보고를 검증으로 취급하면 안 됨 | 채택. 자기 보고는 `unverified`를 올리지 못하고 불일치의 근거로만 씀. `--ephemeral` 금지 명시 |
| 7 | 상태 전이·필수 필드·선택 가능 여부가 불명확, 거부 단계 단정 | 채택. 상태 표, `stage: unknown`, `--choose`/`--unchoose`의 멱등성 |
| 8 | `--again`이 원래 요청을 재현한다는 보장이 없음 | 부분 채택. 호출 전 참조 재해시와 거부, 관측 해시 기록. 호출별 스냅숏 사본은 기각("제외한 것") |
| 9 | 테스트 행에 기대값과 이음매가 덜 정해짐 | 채택. `skill()` 확장, 행 추가(다중 프로세스, 관리 파일, 참조 변조, 이스케이프·URL 인코딩, 부분 rollout, `--no-open` 뒤 재호출), 스탬프는 내용 해시 |
| 10 | 한 장 게이트로는 부족 | 부분 채택. 게이트 한 번에 참조와 투명을 묶어 입력 해시와 알파까지 확인. 보장 범위가 성공 경로뿐임을 명시 |
| 11 | 측정 예산과 우선순위 | 채택. 배분표, 우선순위, 낮은 추론 강도 비교는 뺌(사용자 설정을 덮어쓰지 않음), 강제 종료 측정 M10 추가 |
| 12 | ★ 줄(⑤⑨⑩⑪)의 범위가 넓음 | 채택(성진님 결정). 차이만 남긴 ⓖ, 나머지는 넣지 않음 |
| 13 | 나머지 줄의 중복·과장, `--help`의 "추가 요금 없음" | 채택. 줄을 줄이고 값을 `--help`로, "추가 요금 없음" 삭제, 일부 실패에도 exit 0임을 `--help`에 |
| 14 | 장부를 기능 안에 두는 것은 skill-maker 트리와 다름 | 채택. `imageledger` 스토어 유닛으로 |
| 15 | 릴리스 구조·브랜치 시작점·`--again`의 stdin·이름 검증·승인 지점 | 채택. 각각 계약과 단계에 적음 |

### Claude 작업자 계획 리뷰 (Opus 5.5, read-only, 2026-11-14, run `20261114-203946-imagegen-plan-review-7e54`)

| # | 지적 | 처분 |
|---|---|---|
| 1 | Context가 이전 작품을 잘못 읽음(`mic_off`는 의도한 태그, `밤하늘.png`는 gpt-image 생성물), ⑤가 그 오독에 기댐 | 채택. `밤하늘.png`의 크기와 C2PA 청크를 직접 확인. Context를 고치고 ⑤를 차이만 남긴 ⓖ로 |
| 2 | "생성할지 그릴지"를 누가 정하는지 두 가지로 적힘 | 채택. 기존 결정(Claude가 이유와 함께 고르고 사용자가 바꿈)으로 통일 |
| 3 | ⑪은 design의 조건을 떼었고 영상 근거가 없음 | 채택(성진님 결정). 넣지 않음 |
| 4 | 새 절의 `When:` 문안이 없음, "nobody supplied"가 받은 프레임 다시 그리기를 배제 | 채택. `When:` 초안, ⓔ를 "a generated picture"로. 실존 인물 프레임을 검증에서 보내는 것은 하지 않음(위 "내가 정한 것") |
| 5 | 본문 줄끼리, 본문과 `--help`의 중복 | 채택. ⓕ와 ⓘ로 정리, 크기 수치는 `--help`만, 복사 금지 값 테스트에 추가 |
| 6 | 레일과 근거 없는 단정 | 채택. "never regenerated"·고치는 순서·세트 만드는 법·거부 단정을 뺌 |
| 7 | 빠진 사실: 시트(브라우저)와 FilmCraft의 합성 차이, `frames` 타일 크기, Codex 폴더의 사본, 한 장짜리 레이어, `codex login`은 브라우저가 필요 | 채택. ⓗ(C1 뒤), ⓓ, ⓘ 첫 줄, ⓕ, exit 1 메시지 |
| 8 | 실행할 수 없는 단계(`git mv`, `skill()`의 stdin, 맨 플래그는 검사되지 않음, `cli.py` docstring·epilog) | 채택. 각각 고침 |
| 9 | 측정 예산 | 채택(codex 11과 같음) |
| 10 | 모순·정의되지 않은 말(단계 번호, M4 재현 실패, M8의 쓰기, verbatim 값, `R`, M3·M6의 결과) | 채택. 각각 정의 |
| 11 | `open`을 이름으로 불러야 가짜로 바꿀 수 있음, 샌드박스 세션에서는 열리지 않음 | 채택 |
| 12 | E2E 7번은 구현 세션이 스스로 확인할 수 없음, 리뷰가 E2E보다 먼저라 최종 텍스트가 리뷰되지 않음 | 채택. 7번은 읽기 전용 작업자로, 리뷰를 E2E 뒤로 |

리뷰가 확인해 준 것: 새 절의 위치와 제목 형식, ⑥(밖으로 나감)과 SKILL.md의 전사 줄의 대응, `graphics/imagegen/` 관례, 4절을 그대로 두는 것, `imagegen`과 시트가 Model over machinery를 통과한다는 것, 성진님의 여덟 결정 중 일곱이 지켜졌다는 것(범위 중립은 4번 지적으로 고침).

## 부록: 근거 원장

### 사실 (읽기 전용 실측, 2026-11-14)

- 설치: `codex-cli 0.167.1`, `Logged in using ChatGPT`. `codex features list`에 `image_generation stable true`.
- 0.167.1의 `image_gen__imagegen` 도구 정의와 안내문: rollout `sessions/2026/11/14/rollout-…-01a1d9db-055c-77e0-8623-1b30ab65b35b.jsonl`의 `additional_tools` 항목(위 표에 인용).
- `~/.codex/generated_images`의 PNG 66장 크기 분포(`file`): 941×1672 RGB 20, 2172×724 RGBA 20, 1122×1402 RGB 16, 1672×941 RGB 7, 2172×724 RGB 2, 940×1672 RGB 1.
- `~/.codex/sessions/2026/1[01]`의 rollout에서 `image_gen.generation` 항목 45건(codex 리뷰가 독립적으로 45건·필드·상태·투명 수를 재확인): 모두 `cli_version 0.166.0`, `status completed`, `failure null`, `transparentBackground` true 20·false 25. 항목의 키: `failure, generationId, id, inputImages, kind, result, revisedPrompt, savedPath, status, transparentBackground, type`. 소요(바깥 payload의 `completed_at_ms − started_at_ms`): 최소 16초, 중앙 29초, p90 42초, 최대 47초. 호출 프롬프트와 `revisedPrompt` 일치 36, 불일치 0, 호출문에서 프롬프트를 못 뽑은 것 9. (크기 분포·알파·36건 일치·시간 통계는 리뷰가 재계산하지 않았다.)
- 호출문 모양: `custom_tool_call` `name: exec`, `input: "// @exec: {…}\nconst r = await tools.image_gen__imagegen({prompt:"…",referenced_image_paths:["…"],transparent_background:true}); …"`. 출력 텍스트: "Generated images are saved to …/generated_images/<스레드> as …/exec-<uuid>.png by default."
- design 실행 로그 하나(`…/웹포스터_261109_소방의 날/etc/runs/20261108-131853-43c0/events-v48-1.jsonl`): `--json` 스트림에 `thread.started`, 설정 경고 `error` 항목, `agent_message`, `turn.completed`(입력 68,968 토큰)만 있고 도구 호출은 없다. 한 실행의 관찰이다.
- 투명 PNG 4장의 알파(`ffmpeg … alphaextract,signalstats`): YMIN 0, YMAX 255, 평균 71~118.
- 생성 PNG에는 C2PA 매니페스트 청크가 들어 있다. 영상으로 렌더하면 이 메타데이터는 남지 않는다.
- `data/김형연/261029_이태원참사 4주기/graphics/밤하늘.png`: 941×1672 RGB, C2PA 청크에 `ChatGPT`·`gpt-image`·`OpenAI Media Service API`·`trainedAlgorithmicMedia`. sha256 `8dce4203…3abc8`이 `~/.codex/generated_images/01a18682-2b29-7882-a697-53aad850911a/exec-89996b40-….png`(2026-10-29 16:14)와 같다. 그 스레드의 rollout은 `sessions/2026/10/29/rollout-…-01a18682-….jsonl.zst`로 압축돼 있고, 이 맥에 `zstd`가 없어 읽지 못했다. `sky.html`이 `url("밤하늘.png")`로 `cover` 배치. `소방관.jpg`는 1600×1066 JPEG.
- 위 45건의 생성 기록은 평문으로 남아 있는 rollout에서만 센 것이다. PNG 66장 중 나머지는 압축된 10월 세션의 것이라 세지 못했다.
- `data/김형연/261019_국정감사 6일차/graphics/mic_off.html`은 "(마이크 OFF)" 회색 태그이고 주석이 "값만 바꿔 다시 렌더하면 된다"고 말한다. 같은 작품에 다른 회색 태그가 있다(Claude 리뷰: `etc/16_answer_gray.jsonl`). 그림의 대용이 아니라 고른 양식이다.
- Codex 내장 `imagegen` 스킬 문서(`~/.codex/skills/.system/imagegen/`): 내장 도구는 크기·품질·마스크·출력 경로 인자가 없고 `$CODEX_HOME/generated_images/…`에 저장, 프롬프트를 라벨 필드로 재구성하도록 지시, 생성물을 다른 곳에 쓰려면 복사하고 원본은 두라고 함.

### 문서 (ultra-search, 2026-11-14 열람)

- developers.openai.com/codex/image-generation: "Built-in image generation uses `gpt-image-2` and counts toward your general Codex usage limits."
- platform.openai.com/docs/deprecations: `gpt-image-2` 종료 2027-02-10(공지 2026-11-10), 대체 `gpt-image-2.6-sunburst`/`-flare`.
- openrouter.ai/docs/features/multimodal/image-generation, `/api/v1/images/models`: 전용 Images 엔드포인트, `resolution`/`aspect_ratio`/`size`, `background`(모델별), `input_references`, "Failed or cancelled generations are not billed."
- support.google.com/youtube/answer/14328491: 사실적으로 보이는 AI 생성·변형 콘텐츠의 공개 요구, 비사실적 콘텐츠와 경미한 편집(썸네일·인포그래픽 포함)은 면제. TikTok Community Guidelines(2026-09-24 시행): 사실적 장면·인물의 AI 생성물 라벨. 공직선거법 제82조의8(NEC 2025-04-15 보도자료로 확인, law.go.kr은 점검 중이라 직접 열지 못함): 선거일 전 90일부터 선거운동용 딥페이크영상등 금지, 그 외 기간 표시 의무. AI 기본법 제31조의 의무자는 인공지능사업자(검색 발췌로만 확인). 이 묶음은 본문·README에 쓰지 않기로 했고 기록으로만 둔다.

### 추론

- rollout 관측이 자기 보고보다 낫다: 자기 보고는 프롬프트를 바꾼 그 에이전트가 쓰는 것이고, 관측은 도구 쪽 기록이다. 단 rollout은 내부 형식이라 예고 없이 바뀐다.
- 화면 일부를 차지하는 소재(아이콘·소품)에는 지금 크기가 충분하고, 문제는 전체 화면 배경과 푸시인에 한정된다 → C2.
- design의 "Codex 호출당 40~180초"와 도구 호출 16~47초의 차이는 에이전트 왕복이다 → M6.
- `밤하늘.png`의 보라색은 추모의 보라 리본에서 왔을 수 있다(Claude 리뷰의 추론, 확인하지 않음).

### 열린 질문

- 0.166 이후의 거부 기록 모양(M4). 출력 단계 거부를 의도적으로 재현할 수 있는지.
- Codex 내장 생성이 쓰는 모델이 바뀌면 크기·비율 규칙이 어떻게 달라지는지(바뀐 뒤에만 알 수 있음).

## 측정 원장

(구현 1단계와 6단계에서 채운다)

## 대조 원장

(구현 7단계에서 채운다: 과제 문장, 실행 조건과 run id, 결과, 성진님의 판정과 이유, 줄마다의 처분)
