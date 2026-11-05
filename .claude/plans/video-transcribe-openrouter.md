# video 스킬: OpenRouter 전사 추가와 skill-maker 정합성 재정비

이 문서만 읽고 다음 세션이 구현한다. API 키는 이 파일에 적지 않는다.

## Context

### 내가 이해한 성진의 의도

성진은 영상 편집을 Claude와 여러 턴에 걸쳐 함께 하는 비엔지니어이고, `video` 스킬은 그 동료의 전문성을 담는다. 자막 일은 "Whisper로 받아 적고, Claude가 단어 시간을 음파와 대조하며 싱크를 맞춘다"는 흐름인데, 어떻게 좋은 자막을 만드는지는 Claude가 알기 때문에 레일로 정할 일이 아니다. 이 일을 하는 Claude에게 더 좋은 재료와 도구를 주고 싶고(OpenRouter 전사), 스킬이 skill-maker 프레임에 정말 맞는지(인터페이스로 갈 내용이 문서에 있지 않은지, 밀도 높은 원칙인지) 확인하고 싶다. 성공 기준은 품질뿐이며, 다음 세션이 이 계획만으로 구현한다.

### 측정이 바꾼 것

처음 가정은 "더 좋은 전사 모델이 글자를 더 정확히 받아 적는다"였다. 성진이 지적한 대로 글자 오류는 Claude가 맥락으로 고친다. 측정해 보니 차이는 **시간**에 있었다. 시간은 Claude가 문맥으로 고칠 수 없다. 현재 Whisper+snap은 구절 시작의 21%가 0.5초 넘게 어긋나고, 소문으로 최고라던 Nemotron은 OpenRouter 경로에서 단어 시간이 깨진다. 그래서 이 계획의 축은 다음 셋이다.

1. `transcribe`에 Scribe v2를 기본 모델로 하는 `openrouter` 엔진을 더한다. 로컬 Whisper는 그대로 둔다.
2. Claude가 음파와 직접 대조할 `waveform` 명령을 만든다. 지금은 이 일을 할 도구가 없다.
3. SKILL.md에서 `--help` 사본과 낡은 줄을 걷어 내고, 코드도 프레임에 맞춘다. `references/`는 만들지 않는다.

## 합의 원장

### 사용자 결정

| 항목 | 결정 |
|---|---|
| 방향 | Scribe를 선택 엔진으로 추가, 로컬 Whisper 유지 |
| 후보 모델 | Nemotron, Scribe, Gemini 중 측정으로 판단. Gemini는 400이라 제외 |
| 측정 음성 | Bernie Sanders 다큐만. 한국어 실제 음성은 따로 검증하지 않는다 |
| `.env` 위치 | `.claude/skills/video/scripts/video/openrouter/.env` (쓰는 코드 바로 옆). 트리 규칙의 예외로 승인됨 |
| 외부 전송 행동 | SKILL에 레일로 정하지 않는다. 사실만 쓰고 판단은 Claude가 한다 |
| 추가 범위 | `waveform`, 프로젝트 없는 자막, 영어 자막 규칙, 화자 바뀜 자막 보정 |
| 문서 구조 | `references/` 만들지 않음. SKILL.md 한 파일 |
| SKILL.md 분량 | 줄별 재점검 결과를 그대로 적용해 약 12KB. 길이 자체가 목표는 아니고 "그 줄이 행동을 바꾸는가"가 기준이다. 앞선 "약 17KB" 결정을 대체한다(그 결정은 새 실험이 필요하다는 내 잘못된 설명에 기댔다) |
| 점검 방식 | 스킬을 읽고 판단한다. 서브에이전트가 실제 영상을 만드는 무거운 대조는 하지 않는다 |
| `doctor` | 이번에 넣는다. 점검과 고칠 명령 제시만 하고 설치는 하지 않는다. 처음엔 미뤘다가 interface over document 대조 후 바꿈 |
| 미룸 | `beats` (후보로 핸드오프에 기록) |
| 릴리스 | 구현 후 GitHub 릴리스까지 한다. 첫 릴리스이고 `v0.1.0` |
| 라이선스 | MIT. 저작권 표기는 `Copyright (c) 2026 성진` (GitHub 프로필 이름) |
| 추적 정리 | `.tmp/filmcraft`(1,364개, 38MB)와 `.claude/histories` 심볼릭 링크를 릴리스 전에 추적 해제. 로컬 파일은 유지, 이력은 다시 쓰지 않음 |

### 측정 사실 (2026-11-03)

대상은 86분 영어 다큐와 합성 한국어 `say` 10초다.

| 항목 | Whisper turbo + snap | Nemotron 3.5 | Scribe v2 |
|---|---|---|---|
| 86분 통째 요청 | 해당 없음(5분에 37초, 약 11분 추정) | HTTP 502 | HTTP 200, 73초, $0.317 |
| 50분 요청 | | HTTP 200, 본문 7973단어인데 `words[]` 297개, 시간이 음성 길이 초과 | |
| 길이 임계값 | | 280초까지 정상, 300초부터 `words[]` 잘림 | |
| 270초 분할 | | 59초, $0.176. 12,446단어 중 902개(7.2%)가 0.5초 초과 오차, 최대 76.9초, 어떤 청크는 66%가 어긋남 | |
| 단어 신뢰도 | 있음 | 없음(세그먼트 확률도 전부 0) | 있음 |
| 화자 분리 | 없음 | 400 (`provider.options`의 프롬프트도 무시됨) | 동작, 추가 요금 없음(600초 $0.0367) |
| keyterms | 없음 | 400 | 400 |
| `zdr: true` | 해당 없음 | 통과 | 통과 |
| 10초 창 최대 단어 수/초 | 5.3 | 10.5 | 5.7 |

구절 시작점 오차, Scribe와 Nemotron이 0.1초 안에 합의한 1,077단어 기준:

| 변형 | 중앙값 | 0.25초 초과 | 0.5초 초과 |
|---|---|---|---|
| Whisper 원본 | 0.447 | 81.4% | 40.5% |
| Whisper + level snap(현재) | 0.109 | 40.1% | 21.3% |
| Whisper + Silero VAD snap | 0.264 | 50.6% | 28.9% |

- 0.5초 넘게 갈린 구절 시작 411건에서 혼자 튄 쪽: Whisper+snap 302, Nemotron 56, Scribe 4, 셋 다 다름 49.
- 스펙트로그램 확인(137.5~140초, 음악 없음): `sanders`, `ran`의 배음 시작에 Scribe와 Nemotron이 맞고 Whisper는 약 0.5초 이르다. 음악 위에서는 눈으로 확인하지 않았다.
- 합성 음성 구절 경계 오차(진실값 있음): Whisper 0.34 → snap 0.024, Scribe 0.082 → snap 0.024, Nemotron 0.057 → snap 0.041.
- Scribe에 level snap을 걸면 끝 경계 284곳이 0.15초 넘게 안쪽으로 당겨진다. 스펙트로그램에서 `youthful`의 `-ful`이 잘리는 것을 확인했다(피해). 반대로 `enough`처럼 무음까지 늘어난 시작은 고친다(이득, 36곳). 진짜 무음만 고치는 변형은 구절 시작 1곳만 움직여 효과가 없었다. 그래서 Scribe는 snap을 끈다.
- 글자: 이전 세션에서 Claude가 화면 자막을 보고 고친 Zohran, Benen, El-Sayed, Platner를 Scribe는 처음부터 맞혔다. 신뢰도 0.5 미만은 Whisper 160개 대 Scribe 24개이고, Scribe 쪽에 틀린 이름(Mondaine, Kirios, Forsteg, Chasen, Michel)이 모인다.
- Scribe 응답 형태: 세그먼트가 파일 전체 1개, 언어 코드 `eng`/`kor`, `type: audio_event` 76개(`[gentle music]` 등), 길이 0 단어 233개(그중 단독 `...` 78개), 필러 유지(`Um,`), 단어 사이에 실제 틈이 있음(틈 0 비율 1.1%, Whisper 88.6%).
- 현재 `core.snap`의 소속 판정은 길이 0 단어를 어느 구간에도 넣지 못한다. Scribe에서 `unmatched` 247개 중 233개가 길이 0 단어다.
- 화자 분리와 현재 `captions`(10분 구간, `en` 수치, 구두점 토큰 제거):

| 조건 | 큐 | `short` 위반 | 한 단어 자막 |
|---|---|---|---|
| 화자 분리 안 함 | 168 | 1 | 0 |
| 화자 분리, 현재 코드 | 196 | 23 | 13 |
| 2단어 이하이고 `min_s` 미만 턴 무시 | 182 | 11 | 3 |
| **`min_s`(5/6초) 미만 턴 무시(채택)** | 174 | 5 | 2 |
| 1.5초 미만 턴 무시 | 172 | 4 | 2 |
| 2.5초 미만 턴 무시 | 171 | 2 | 2 |

  1.5초 이상으로 올리면 "It was right here in California" 같은 진짜 답변까지 앞 화자에 붙고 이득은 거의 없다. `min_s`는 "혼자서는 자막이 될 수 없는 길이"라는 이유가 있어 채택한다.
- `captions` 휴리스틱: `is_clause_end`가 `understand`, `also`, `demand`에서 True이고(접미 매칭), `is_sentence_end`가 `Mr.`, `U.S.`에서 True다.
- FilmCraft 0.14.0 확인:
  - `transcript.set`의 `speakers`와 `words[].speaker`가 `transcript.inspect`까지 흐르고 문단이 화자에서 나뉜다.
  - `"confidence": null`과 `"item": null`은 거부된다. 키를 빼면 통과한다.
  - `transcript.removeFillers`는 `Um,`처럼 구두점 붙은 단어도 지운다.
  - `file.import`는 FCP7 XML을 받는다.
  - `exec file.exportMedia`는 `wait` 없이도 완성된 파일을 쓴다.
- ffmpeg: `showspectrumpic`은 `legend` 기본값이 true라 끄지 않으면 축 여백 때문에 시간→픽셀 대응이 틀어진다.
- 기존 상태: `tests/video_skill` 193 통과 1 건너뜀. `tests/filmcraft_facts` 23 통과 1 실패(`test_18`, 위의 export 변화). `claude plugin validate --strict .claude/skills` 통과.
- OpenRouter 문서: `pricing.prompt`의 단위가 모델마다 다르다(MAI는 시간당). 실제 비용은 `usage.cost`로 본다. JSON 요청은 OpenAI·Groq 외 공급자에서 25MB를 넘으면 거부된다고 적혀 있다. 측정에서 Scribe는 15.7MB(base64 21MB)를 받았고 그 이상은 재지 않았다.
- Netflix English Timed Text Style Guide: 줄당 42자, 성인 프로그램 초당 20자.

### 받아들인 가정과 한계

- 시간 기준값은 사람이 정답 처리한 것이 아니라 두 독립 시스템의 합의다. 일부 구간은 스펙트로그램으로 눈으로 확인했다.
- 실제 음성 근거는 영어 다큐 1편이다. 한국어 실제 음성은 사용자 결정으로 측정하지 않으며, SKILL과 완료 보고에 그렇게 적는다.
- Gemini는 원인 미확인 상태로 제외한다. `--model`로 호출할 수 있지만 검증되지 않았다.
- `--engine`에 기본값을 두지 않는다. 대안은 `local`을 기본으로 두고 OpenRouter만 명시하게 하는 것이며, 승인 때 뒤집을 수 있다. 사용자의 "레일처럼 정의해야 하나"는 SKILL 문장에 대한 답이었고 이 플래그를 직접 정한 것은 아니다.
- Opus를 담은 `.ogg`는 측정에서 Scribe와 Nemotron 모두 받았지만, OpenRouter 문서는 `ogg`를 Vorbis로 적고 있다. `extract_audio`가 여기에 기대므로 8단계의 실제 실행에서 다시 확인한다.

## 설계

### 트리

```
.claude/skills/video/
├── SKILL.md
├── data/                          (기존, git 제외)
└── scripts/
    ├── cli.py                     waveform 추가, transcribe·captions 인자 변경, 그래픽 도움말 이동
    └── video/
        ├── recognition.py         신규(shared): RawWord, Segment, Recognition
        ├── subrip.py              신규(system): captions/srt.py를 옮김. captions와 waveform이 함께 씀
        ├── openrouter/            신규(system): __init__.py, .env(git 제외)
        ├── whisper/               Recognition을 recognition.py에서 가져옴
        ├── ffmpeg/                extract_audio, speech_spans(transcribe에서 이동), 파형·스펙트로그램 그림 추가
        ├── filmcraft/             read_transcript_line, versions, install_steps 추가
        ├── whisper/               model_cached 추가
        ├── chrome/                installed 추가 (기존 탐색 로직을 내보냄)
        ├── transcribe/            엔진 분기, chunks.py 신규, review.py 확장
        ├── captions/              --transcript, 규칙 프로파일, 짧은 화자 턴 처리
        ├── waveform/              신규(feature)
        └── doctor/                신규(feature)
```

`tests/video_skill/test_structure.py`의 `KINDS`에 `"openrouter": "system"`, `"subrip": "system"`, `"waveform": "feature"`, `"doctor": "feature"`, `"recognition": "shared"`를 넣는다. 구조 테스트가 feature 간 import를 막으므로 `waveform`이 쓰는 측정·형식 읽기는 모두 system으로 옮긴다. `plan_chunks`는 `transcribe.__all__`로 내보낸다. `speech_spans`는 `transcribe.__all__`에서 빼고 `ffmpeg.__all__`에 넣는다. 테스트는 이 이름을 `transcribe`에서 가져오지 않으므로 다시 내보낼 필요가 없다.

### `openrouter` 시스템 유닛

그 API가 바뀌면 이 폴더만 고친다. 기능 코드에는 `verbose_json`, `audio_event`, `eng` 같은 이름이 새지 않는다.

```python
__all__ = ["DEFAULT_MODEL", "KEY_FILE", "Reply", "load_key", "transcribe", "read"]
DEFAULT_MODEL = "elevenlabs/scribe-v2"
KEY_FILE = Path(__file__).parent / ".env"
def load_key(env=os.environ, file=KEY_FILE) -> str | None
def transcribe(audio: Path, model, language, diarize, zdr) -> Reply      # raw dict, Recognition, cost_usd
def read(raw: dict | Path) -> Recognition                                 # 응답 → 스킬의 용어
```

- 요청은 표준 라이브러리 `urllib`와 base64 JSON으로 보낸다. 새 의존성은 없다. 요청 타임아웃은 600초다.
- 기본 URL은 `OPENROUTER_BASE_URL`로 바꿀 수 있어 테스트의 로컬 서버가 받는다. loopback 또는 https만 허용해 키가 평문으로 나가지 않게 한다.
- 보내는 값: `input_audio`, `response_format: verbose_json`, `timestamp_granularities: ["word", "segment"]`, `provider: {"zdr": true}`(`--no-zdr`로 끔), 선택적으로 `language`, `diarize`.
- 키: 환경변수 `OPENROUTER_API_KEY`가 **설정돼 있으면 빈 값이어도 그것을 쓴다**(빈 값은 키 없음). 없으면 `.env`를 읽는다(`KEY=VALUE`, 주석 무시, 따옴표 제거). 그래서 테스트는 실제 `.env`를 건드리지 않고 "키 없음"을 재현한다. 공급자 메시지를 내보내기 전에 키 문자열을 치환한다. 키는 어떤 출력·파일·오류에도 나가지 않는다.
- 실패 처리:

| 상황 | 처리 |
|---|---|
| 키 없음 | `ToolError`, `.env` 절대 경로를 알림. 로컬로 자동 전환하지 않음 |
| 408, 429, 5xx | `Retry-After`를 따라 3회 재시도. 소진되면 `ToolError`에 `--chunk` 안내 |
| 401, 402 | `ToolError`, 공급자 메시지 |
| 그 밖의 4xx(화자 분리 미지원, 모델 오타 등) | `InputError`(종료 2), 공급자 메시지 |
| 연결 실패, 타임아웃, 200인데 JSON 아님 | `ToolError`. traceback을 내지 않음 |

- 재시도 코드에 `성진:` 주석으로 "분할 실행 재개 없음, 실패하면 다시 돌린다(비용이 작아서). 비용이 커지면 재개를 넣는다"를 남긴다.
- 응답 해석:
  - `type: audio_event`는 `Recognition.events`로 분리한다.
  - 글자나 숫자가 없는 토큰(`...`)은 단어에서 뺀다.
  - `confidence`는 `prob`(없으면 `None`), `speaker`는 정수, `eng`/`kor`/`jpn`/`zho`는 2글자로 바꾼다.
  - 세그먼트가 단어를 담지 않으면(Scribe, Nemotron) 문장 끝, 0.7초 이상 틈, 화자 변경에서 줄로 나눈다.
  - `no_speech_prob`·`avg_logprob`가 0으로 비어 있으면 Whisper 신호로 읽지 않는다.
  - `duration`이 없으면 호출자가 준 미디어 길이를 쓴다.
- 응답 거부(공급자가 200을 줘도): `text`가 있는데 `words`가 비었거나, `len(words) < 0.9 * len(text.split())`이거나, 마지막 단어 끝이 `duration + 1`을 넘으면 `ToolError`다. 메시지에 "N단어 중 M개만 시간이 있다"와 `--chunk N`으로 다시 돌리라는 안내를 담는다. 측정으로 확인한 판정값: Nemotron 50분 0.037, 300초 0.064, 360초 0.18은 거부되고, Scribe 0.997, 화자 분리 0.996은 통과한다. 모델별 표는 두지 않는다. `text`도 `words`도 비었으면 말이 없는 미디어이므로 단어 0개로 정상 종료하고 `notes`에 적는다.

### `transcribe` 명령 계약

```
transcribe MEDIA --out X.jsonl (--engine {local,openrouter} | --from-json RAW.json) [--item ID] [--model M]
           [--language CODE] [--diarize] [--no-zdr] [--snap {auto,on,off}] [--max-shift S] [--chunk S]
```

- `--engine`과 `--from-json`은 상호 배타이고 하나가 필수다. 기본 엔진이 없어야 오디오가 실수로 나가지 않는다. `--from-json`은 모양으로 엔진을 판단한다(최상위 `words`는 OpenRouter, `segments[].words`는 Whisper). 이미 쌓인 `.whisper.json`도 계속 읽힌다.
- `--diarize`, `--no-zdr`, `--chunk`를 `local`과 함께 쓰면 종료 2다.
- `--item`은 선택이다. 없으면 `X.jsonl`의 `item`이 `null`이라 FilmCraft에 적용되지 않고, `captions --transcript`는 그대로 읽는다. 이때 `next`는 다시 돌리라고 하지 않고 **`X.jsonl`의 `params.item`을 채워 `run`하라고 안내한다.** 재실행을 안내하면 교정한 글자가 RAW로 덮이기 때문이다. `--help`에 이 사실을 적는다. 버니 작업의 `--item 0` 우회를 없앤다.
- 이미 있는 `--out`은 덮어쓰지 않고 종료 2다. 교정한 전사와 돈 들인 원본 응답이 다음 호출로 조용히 사라지지 않게 하기 위해서다. 메시지는 다른 경로를 쓰거나 파일을 지우라고 안내한다.
- `--snap auto`: Whisper는 켜고 OpenRouter는 끈다. 끄면 `snapped`는 0이고, 순서·비겹침·최소 한 프레임 정리와 발화 구간 측정은 그대로 해서 `unmatched`를 낸다. `core.py`의 `snap`에서 마지막 정리를 공용 함수로 분리하고, 길이 0 단어는 "시작이 구간 안"이면 그 구간에 속하게 고친다.
- 원본 응답: `local`은 `<stem>.whisper.json`, `openrouter`는 `<stem>.openrouter.json`. 분할이면 시간을 더해 합치고 `text`, `duration`, 비용을 합산한다. 합친 파일을 다시 읽어도 거부 규칙이 오탐하지 않아야 한다.
- 오디오 준비: `ffmpeg.extract_audio`로 모노 16kHz Opus 24kbps를 `--out` 옆 임시 파일에 만들고 `finally`로 지운다.
- 분할: `--chunk`, 또는 base64 본문이 24MB를 넘으면(파일 약 18MB, 약 100분) 분할한다. 측정한 86분은 분할 없이 통과한다. `transcribe/chunks.py`의 순수 함수 `plan_chunks`가 한도 직전 30초 안에서 가장 긴 무음의 가운데를 고르고, 무음이 없으면 그 자리에서 자르고 `notes`에 알린다. 동시 요청 4개. 화자 분리와 분할이 겹치면 청크마다 화자 번호가 달라지므로 `notes`에 알린다.
- 검토 신호(`transcribe/review.py`):
  - `low_prob`: 신뢰도가 있을 때만.
  - `unmatched`: 측정된 발화 없는 단어.
  - `repeat`: 줄 기준(분할된 줄에도 동작).
  - `no_speech`: Whisper만.
  - `compressed`(신규): 10초 창에서 초당 7단어 초과. 어떤 모델이든 시간이 뭉친 응답을 알리는 값싼 점검이다. 측정에서 실패한 Nemotron은 최대 10.5, Scribe 5.7, Whisper 5.3이다. 나쁜 단어의 약 절반만 잡으므로 통과가 시간을 보증하지 않는다.
- 출력 파일: `X.jsonl`(화자 있으면 `speakers`는 최대 번호+1 크기의 `{"name": "Speaker N"}`, `words[].speaker`, `source`. 신뢰도가 없으면 `confidence` 키를 뺀다), `X.txt`(줄 단위, 화자 표시, 오디오 이벤트 시각 포함), 원본 응답, 검토 파일.
- stdout(값싼 신호 먼저):

```json
{"engine","model","item","language","words","seconds","speech_seconds","cost_usd","speakers","audio_events","snapped","unmatched","has_confidence":true,"review":[],"review_total":0,"review_file":"","out":"","text":"","raw":"","next":"","notes":[]}
```

- 종료: 0 기록됨. 2 미디어 없음·오디오 없음·알 수 없는 `--from-json`·이미 있는 `--out`·공급자가 거부한 인자. 1 ffmpeg·uvx·mlx-whisper 실패, 키 없음, 잔액 없음, 재시도 소진, 시간이 깨진 응답. 깨진 응답에는 `X.jsonl`을 쓰지 않는다.
- `--help`가 소유하는 내용. 엔진 비교와 모델 안내도 **이 한 인터페이스의 선택지이므로 SKILL이 아니라 여기에 둔다.** `--engine`이 필수라 호출을 빠뜨리면 오류가 이 도움말을 가리킨다.
  - 엔진 비교(초안, 구현 때 문장 조정):

    ```
    --engine local: Whisper on this machine. Nothing leaves it and it is free, but it is the slower engine and downloads a large model on first use (`doctor` says whether it is cached). Its word starts run early, often half a second in the middle of speech, and snapping only corrects edges next to real silence: a caption can rise before the voice, and a cut on a word boundary can clip the word.
    --engine openrouter: sends the audio to the provider (a zero-retention route unless --no-zdr) and costs money (cost_usd). Word edges sit on the voice, --diarize labels speakers, fillers are kept, and the low_prob list is short and holds the misheard names.
    That comparison was measured on one English documentary, not on Korean speech.
    --model: for openrouter, any model at https://openrouter.ai/api/v1/models?output_modalities=transcription (default elevenlabs/scribe-v2). Word timing belongs to the route, not the model's reputation: models that rank well on recognition have returned truncated word lists and drifting times here. A truncated reply is refused and says what to try; passing that does not prove the times.
    ```

    값(길이 한도, 청크 크기, 속도 배수, 다운로드 크기)과 특정 모델 이름은 낡으므로 쓰지 않는다. 필요한 값은 거부 메시지가 그때의 응답을 근거로 안내하고, 측정한 모델 이름은 PR 본문에 남긴다.
  - 키 위치, `cost_usd`의 뜻
  - **적용 전 교정 절차**: `X.jsonl`의 `text`를 고치되 시간은 유지하고, 음악 위 `repeat`·`no_speech` 줄은 지운 뒤 `next`로 적용한다
  - 검토 신호 각각의 뜻, `--snap auto`의 이유
- "먼저 물어라" 같은 행동 지시는 `--help`에 쓰지 않는다.

### `waveform` 명령 계약

성진이 말한 "음파와 비교대조"의 실체다. 소리를 듣지 못하는 Claude에게 프레임 시트에 해당한다. 이번 세션에서 Whisper가 이르다는 사실도 임시 스크립트로 그린 같은 그림으로 판정했다.

```
waveform MEDIA --at A-B [A-B …] [--words FILE …] --out SHEET.png
```

- `FILE`은 `transcript.set` JSONL 또는 SubRip이고, 최대 4개까지 줄로 겹쳐 비교한다(라벨은 파일 이름). 원본 응답을 비교하려면 `transcribe --from-json`으로 JSONL을 만든다(비용 없음). 시간은 초 또는 타임코드.
- 그림: 창마다 파형, 0~8kHz 스펙트로그램(`s`, `ㅅ` 같은 무성음까지 보임), 1초 격자, 파일별 단어/자막 칸. `ffmpeg`의 `showwavespic`, `showspectrumpic`(`legend=0`, `stop=8000`)과 Pillow로 그린다(새 의존성 없음).
- stdout: `{"sheet", "windows": [{"start", "end", "speech": [[a, b]…], "rows": [{"source", "items"}]}], "notes"}`. `speech`는 `transcribe`와 같은 측정이라 그림 없이도 먼저 판단할 수 있다.
- 종료: 0 기록됨. 2 창 없음, 8개 초과, 창이 60초 초과, 미디어 범위 밖, 읽을 수 없는 `--words`. 1 ffmpeg 실패.
- `--help`의 읽는 법: 유성음은 층층이 쌓인 배음으로, `s`나 `f` 같은 무성음은 높은 대역의 잡음으로 보인다. 단어 칸은 그 단어의 첫 에너지에서 시작해야 한다. 음악이나 군중 소리 위에서는 칸과 에너지가 맞아도 목소리를 증명하지 못한다.

### `doctor` 명령 계약

SKILL.md 34행의 버전 비교와 설치 절차를 도구로 옮긴다. 앱 버전만 바꿔 같은 순서로 반복되는 기계적 작업이기 때문이다. FilmCraft는 최근 12일에 6번 릴리스했고(v0.12~v0.17), 설치본은 0.14.0이다. 릴리스 파일 이름(`filmcraft-cli-<ver>-macos-universal.zip`, `SHA256SUMS.txt`)은 v0.14.0에서 확인했다.

```
doctor
```

- 인자가 없다. 설치하지 않고 네트워크도 쓰지 않는다. 고칠 명령은 Claude가 실행하므로 평소처럼 권한 확인을 거친다.
- stdout: `{"ok", "checks": [{"name", "ok", "required", "value", "why"}], "next": []}`.
- 점검 항목:

| 이름 | 필수 | 내용 |
|---|---|---|
| `filmcraft_cli` | 예 | 설치 여부와 앱 버전 일치. `why`: 앱보다 새 CLI로 저장한 프로젝트는 앱이 못 열 수 있다. 앱이 없으면 헤드리스는 되므로 통과하고 `value`에 적는다 |
| `ffmpeg`, `ffprobe`, `uvx` | 예 | 설치 여부 |
| `whisper_model` | 아니요 | 기본 모델이 받아져 있는지. 없으면 첫 `local` 실행에서 큰 모델을 받는다 |
| `openrouter_key` | 아니요 | `env`, `file`, `none` 중 하나. **키 값과 일부 문자도 출력하지 않는다** |
| `chrome` | 아니요 | `graphic`에 필요한 Chrome 유무 |

- `next`는 버전을 채운 명령이다. 앱 버전으로 `gh release download`, `shasum -a 256 -c --ignore-missing`, `unzip`, `install -m 755 … ~/.local/bin/filmcraft-cli`를 준다(`filmcraft.install_steps`가 소유). 임시 폴더에서 실행하도록 쓴다.
- 종료: 0 필수 항목 모두 정상. 1 필수 항목 실패. 2 인자 오류.
- `filmcraft.binary()`의 오류 메시지가 "SKILL.md 'Before the first command'"를 가리키는 것을 `doctor`로 바꾼다.
- `doctor/__init__.py`의 판정은 사실을 받아 결과를 내는 순수 함수로 두어 테스트가 닿게 한다. 사실 수집은 각 시스템 유닛이 맡는다.

### `captions` 변경

- `--transcript X.jsonl`을 `--project`·`--bridge`·`--cues`와 배타적인 네 번째 소스로 추가한다. `--fps`, `--frame`은 `--cues`처럼 쓴다. 프로젝트가 없으면 `next`는 SRT 경로만 주고 가져오기 명령은 안내하지 않는다.
- `--rules {ko,en}`: `rules.py`에 프로파일을 둔다.
  - `ko`: 현재 규칙.
  - `en`: 줄당 42자(현재 단위로 21), 초당 20자, 2프레임 간격. 줄 끝 구두점을 유지한다. 구현 시 지침 원문으로 길이 규칙(5/6~7초)을 확인해 `HELP`에 근거 표시와 함께 적는다.
  - `--cps`, `--lines`, `--min`, `--max`의 파서 기본값을 `None`으로 바꿔야 프로파일 값을 덮어쓸 수 있다. `--help`의 기본값 문구도 프로파일 기준으로 고친다.
- 영어 휴리스틱:
  - 절 끝 판정의 `and|but|so|because`는 단어 전체 일치로 바꾼다. 한국어 어미는 접미 매칭을 유지한다.
  - 문장 끝 판정은 `Mr.`, `Mrs.`, `Ms.`, `Dr.`, `St.`, `U.S.`, `Jr.`, `Sr.`를 제외한다(버니 작업의 `make_cues.py`와 같은 목록).
- 짧은 화자 턴: `layout.py`에서 `min_s`보다 짧은 턴은 화자 경계로 치지 않는다. 그런 턴은 혼자서는 자막이 될 수 없기 때문이다. 그 이상의 화자 변경은 그대로 끊는다.
- 설명과 도움말의 "Korean captions"를 규칙 선택이 가능한 설명으로 고친다. 87행 사본을 지운 뒤에도 이 도움말이 `violations` 처리법을 소유한다. 도움말의 "Use it instead of transcript.createCaptions…" 문장은 지운다. FilmCraft 명령과의 선택은 두 도구에 걸치므로 SKILL이 소유하고, 두 곳에 두지 않는다.

### 코드의 프레임 정합성

- `graphic/help.py`의 산문 계약을 `cli.py`로 옮긴다. `qc.HELP_TABLE`, `frames.HELP_TABLE`, `captions.HELP`처럼 숫자를 한곳에서 관리하는 표는 그대로 둔다(근거 있는 예외, 커밋 본문에 기록).
- `cli.py` 최상위 설명의 "This file is the whole command surface…"는 유지보수자 문장이라 지운다. `--help`가 바뀌므로 구조 커밋이 아니라 동작 커밋에서 한다.
- `graphic --help` Placing 문단의 "(timeline.place without audioTrack overwrites A1; graphics.newFromFile drops the sound)"는 SKILL 51행과 겹치므로 지운다. FilmCraft 사실이고 그래픽 외 소재에도 적용되어 SKILL이 소유한다. 같은 이유로 구조 커밋 뒤 동작 커밋에서 한다.
- `_exit` 키, `captions`·`frames`에 `--sequence`가 없는 것은 이번 경로 밖이다. 고치지 않고 핸드오프에 적는다.

## SKILL.md 구조와 처분

한 파일을 유지하고 영어로 쓴다. 약 12KB를 예상한다(현재 21,449바이트, 추정). 기준은 skill-maker의 "그 줄이 모델의 행동을 바꾸는가"이고, 모든 줄을 불필요하다고 가정한 뒤 근거가 있을 때만 남겼다.

남기는 근거는 네 가지다.

1. 기록된 실행에서 모델이 실제로 틀렸고 도구가 막아 주지 않는다(PR #1, PR #3 대조표).
2. 도구가 조용하거나 메시지가 오해를 부른다(재현함).
3. 사용자 몫, 되돌리기 비용, 결과가 보여 주지 않는 것을 구체적으로 짚는다.
4. 사용자가 남기기로 결정했다(`filmcraft-skill.md`의 "스킬의 성격": FilmCraft 함정, 플랫폼 사양·qc, 화면 글자 정확성, 발언 왜곡 금지, 플랫폼 UI 영역).

판정은 Sonnet 작업자의 줄별 재점검(다른 모델 계열 아님)에 내 재현을 더한 것이다. 기록이 없는 줄의 "Claude가 이미 안다"는 추정이고, 기록은 과제당 1회 실행이다.

### 절 구조

```
frontmatter
# Making video with FilmCraft
## Working with the user
## Before you hand something over
## Before the first command
## Headless or the running app
## How the CLI fails quietly
## Seeing and hearing the edit
## What does not depend on taste
## Speech as material
## Graphics and motion graphics
## Delivery
## Working files
## Working in the running app
```

독립 절에서 없어지는 것: `Command families by job`, `On-screen text`, `Many clips and music`, `Color`, `Changing the frame shape`.

### SKILL.md 초안 전문 (구현 때 사실 확인 후 사용자가 전체 문안을 승인)

````markdown
---
name: video
description: >-
  Make and edit video with FilmCraft, the open-source Premiere-style editor installed locally, through `filmcraft-cli` (headless) or the running app (bridge), with graphics designed in code (HTML/CSS/SVG/Canvas) and rendered onto the edit: cuts and transcript-based edits, vertical Shorts/Reels/TikTok, montages, titles and motion graphics, sound effects, audio mix and loudness, color, word-timed transcripts and captions (with or without an edit), QC-checked exports, and handoff to Premiere or Resolve. Use whenever the user wants a video cut, transcribed, captioned, reframed, graded, mixed, given graphics, or exported, or mentions FilmCraft or a .fcproj. Triggers include: 영상 편집, 컷편집, 자막, 전사, 받아쓰기, 화자 구분, SRT, 쇼츠, 릴스, 몽타주, 모션 그래픽, 타이틀, 효과음, 색보정, 내보내기, .fcproj, FilmCraft. Not for downloading or summarizing a video, still images such as thumbnails or posters, slide decks, or developing FilmCraft's own source code.
allowed-tools:
  - Bash(filmcraft-cli *)
  - Bash(uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" *)
  - Bash(ffprobe *)
  - Bash(ffmpeg -i * -c copy -movflags +faststart *)
---

# Making video with FilmCraft

`filmcraft-cli commands <filter>` and `filmcraft-cli describe <id>` own FilmCraft's commands and parameters. This skill holds what those do not say, and tools FilmCraft lacks, called as `uv run "${CLAUDE_SKILL_DIR}/scripts/cli.py" <tool> …`; its `--help` lists them and each `<tool> --help` owns its numbers, outputs and exit codes.

## Working with the user

- You edit together with the user, usually over many turns. Taste is theirs to decide and yours to offer: cut rhythm, transitions, how much pause or filler to keep, caption and title design, graphics, the look, how music ends, shot order. Say in a line what you chose and why. When they choose otherwise do theirs, and what they tell you about how they work outranks this skill; when a choice collides with a platform requirement or a fact below, say so once with the consequence.
- With no idea behind the order, shots end up cycling through the sources in file order, which gives the user nothing to judge: choose shots by what is in them and say the idea.
- `${CLAUDE_SKILL_DIR}/data/`, when it exists, is the user's own record of work: each earlier piece there (its project, the pages in its `graphics/`, the exported video) is what they chose. When you propose something taste decides and an earlier piece resembles this one, read their taste from it; it informs your proposal and does not bind it. Unless the user names another folder, a new piece goes in `data/<piece>/`, so it becomes the record for the next one.
- Cheap to change (a trim, a transition, a caption style, a title's wording): make the call, show it, and move on.
- Costly to undo, or setting what the piece is (which segments a highlight or summary keeps, the overall look, a long export, a model download, overwriting a project you were handed, since `--save` has no undo across calls): show candidates and your reasons, and ask first.

## Before you hand something over

- A rendered deliverable passes `qc` for its target.
- Read the final cut's words (`transcript.inspect`) for a sentence cut off or a splice that changes what someone said; `timeline --project` on the saved `.fcproj` matches what you report.
- Each graphic was seen in FilmCraft's render (`frames --project`) entering, at its fullest and leaving; `fallback` fonts and `blocked` requests in `graphic`'s output are fixed or accepted by the user.
- Say what changed, the calls you made that the user did not, and what you could not verify. You cannot hear the cut, so how its audio flows is always unverified.
- Edit picture and sound only in FilmCraft, so the user can open the project and change it; graphics are pages rendered with `graphic` and placed there. ffmpeg otherwise only measures, except the lossless remux `qc` names, which changes no picture or sound.

## Before the first command

- Run `doctor` and fix what it marks required; an optional item matters only when the task needs it.
- FilmCraft changes often; where this skill, `describe` and what happens disagree, trust what happens and say so.

## Headless or the running app

- Work headless by default (`filmcraft-cli --project P.fcproj --save …`); there is no autosave, so saving is yours.
- Never edit on disk a `.fcproj` the app has open: whichever saves second throws the other's work away.

## How the CLI fails quietly

- Every call is a fresh session: selection, track targeting and the Source monitor do not carry over, so pass ids (`clips`, `items`) wherever `describe` offers them, and use `timeline.*` rather than `trim.*` or `source.*` headless. A failing line stops a `run` before anything is saved.
- Unknown keys and unknown CLI options are ignored without an error. A float in `time` (ticks are integers; use `seconds`) or a misspelt key gives `cuts:0`; a misspelt `--bridge` or an unsplit `$OPTS` (zsh does not split) runs on an empty "Untitled" session and exits 0. Read every result for a no-op: `cuts:0`, `null`, an unchanged `durationFrames`, `path:null`.
- `timeline.place` puts a clip's sound on the targeted audio track (A1 by default), overwriting the speech there: pass `"audioTrack": "new"` or a free track. `graphics.newFromFile` leaves the sound out.
- `graphics.*` take `track` as a 0-based index, and a string like `"V2"` is silently ignored. `timecode` ignores the sequence's start timecode; Mark Out includes its frame.
- `clip.speedDuration` without `reverse` turns reverse playback off. Time-remapping keyframes do not render.
- Narration (`tts.*`) has English voices only; Korean text is refused with a message that does not say why.
- Text layers default to Inter, which has no Hangul: set an installed Korean family (`fonts.list`) and look at a render.
- Lumetri and FilmCraft-only effects do not travel in a handoff; say which. Importing an FCP7 XML merges it into the open project.

## Seeing and hearing the edit

- You cannot play anything. Picture: `frames`. Sound: `waveform`, which draws the audio with word boxes over it. The edit: `timeline`, not raw `inspect sequence`, whose output grows with every clip.
- Rendering 10-bit AV1/HEVC is slow per frame: ask `frames --project` only for the frames you need.

## What does not depend on taste

- When unsure of a name or term on screen, keep your best guess and list it for the user.
- Never splice speech into something the speaker did not mean: an answer shown without its question can read as answering something else, so keep the question when it does.
- Before showing anything check text collisions: captions over burned-in subtitles or broadcast supers, text and faces inside the target platform's UI (`frames --overlay <platform>`). How to resolve one is a choice to offer.
- A sequence takes the delivery's size and, unless the user wants otherwise, the source's frame rate: converting 60p to 30p throws motion away.

## Speech as material

- Transcribe with `transcribe`; its `--help` compares the engines and covers correcting and applying the result.
- A transcript's times are a claim about the audio, and no check in `transcribe` proves them. When timing decides something (a cut, a caption start you doubt, a `compressed` range, two transcripts that disagree, a model or language you have not checked), look with `waveform`.
- `transcript.removeFillers` removes English fillers only unless given a list, and still reports success: pass Korean ones (음, 어, 아, 그, 저, 뭐 standing alone; discourse markers such as 그러니까, 이제, 약간 only if the user wants them gone). Remove fillers before pauses; the other order leaves a gap where each filler was.
- `transcript.removePauses` keeps `keepSeconds` on both sides of each pause, so set it to half the gap you want.
- Speaker labels are the engine's clustering and nothing here checks them. A wrong attribution puts words in someone's mouth, so list what you attributed for the user before captions name or colour a speaker.
- Captions come from `captions`, then its `next` commands: not `transcript.createCaptions` (it runs a short sentence into the next and does not measure width) and not `captions.add`/`setTimes` (they refuse overlaps; import is lenient).

## Graphics and motion graphics

When: a title, lower third, callout, number or chart, how an inserted image is shown, an intro, or a motion graphic on its own.

- Design them as HTML pages and render them with `graphic`; read its `--help` before the first page. FilmCraft does the cut, timing, placement and track order, anything worked on the footage's own pixels (blurring or reframing the picture behind a graphic, color), sound, transitions between shots, and captions. Its native graphics are keyframed text and shape layers that take repeated test renders to get right and are dropped in an FCP7 XML handoff. When the user wants to adjust a graphic themselves in FilmCraft, make it there instead.
- Two that look alike: pushing in on the person speaking works on the footage's pixels, so it is FilmCraft's Motion; pushing in on one spot of an image shown on screen is movement inside the graphic, so it belongs to the page. Where the line is unclear, say which side you chose and why.
- Judge how a graphic sits in the picture from FilmCraft's render (`frames --project`), not a browser or ffmpeg composite: FilmCraft blends in linear light, so anything partly transparent comes out lighter over the picture, a dark layer weaker and a light one stronger.

## Delivery

- Every export: `range: "entire"` (the default is In to Out when marks are set), `burnCaptions` and `captionSidecar` as intended (a render shows captions an export drops), loudness at the `qc` target.
- Fix offline media with `media.findMissing`; `--allow-offline` is for previews, not deliverables.
- YouTube chapters go in the description as timestamps, not into the MP4.

## Working files

- Every piece has the same shape, so a later session can find its way in: the project and its deliverables at the piece's root; `assets/` for material brought in, copied in with `cp -c` from wherever it came, so the piece's folder alone opens the project; `graphics/` for pages and their renders, kept because the project plays them; `etc/` for the rest (tool outputs, transcripts and caption drafts worth keeping), with throwaway files such as frame sheets removed at the end. Write nothing outside the user's folders: a file in `/tmp` may be unreadable to you in a restricted session.
- No global installs besides `filmcraft-cli`; tools run through `uv run` and `uvx`.
- FilmCraft keeps `FilmCraft Previews/`, its render cache, next to every saved project with a sequence. It is not an output; say so rather than leaving the user to wonder.

## Working in the running app

When: the user wants to watch or work along, or the project is open in the app.

- Connect: `nc -z 127.0.0.1 9876`. If the app is not running, `open -a FilmCraft --args --control 9876` (arguments reach only a fresh launch). If it runs without the port, ask the user to save and quit it; never quit it yourself. The project's `filmcraft` MCP server appears once approved at session start.
- Commands: `filmcraft-cli --bridge 127.0.0.1:9876 …`. `render` is headless only: use MCP `render_frame {seconds}`. Use the MCP `ui_*` tools only for actions with no command.
- `--save` or `file.save` on an app project with no path opens a macOS save dialog, and every request then times out after 60 s with no reason given. Send `file.saveAs {path}` first. Already stuck: ask the user to click Cancel.
- The project file on disk can lag the app's unsaved edits.
- Do not drive the UI while the user is typing, and leave saving the open project to them. Leave the app open when done.
````

### 초안에서 구현 때 확인할 문장

스킬에 남길지를 실행으로 정한다. 틀리면 지우고, 도구가 분명히 말하면 지운다. 렌더는 작은 합성 클립으로만 한다.

| 문장 | 확인 방법 |
|---|---|
| Time-remapping keyframes do not render | 작은 프로젝트에서 키프레임을 걸고 프레임 비교 |
| Importing an FCP7 XML merges it into the open project | `file.import` 전후 `inspect project` |
| are dropped in an FCP7 XML handoff | `graphics.newText` 프로젝트를 내보내 XML 확인 |
| `graphics.*` … `"V2"` is silently ignored | 결과와 `inspect` 확인 |
| HEIC·EXIF 회전 미지원 (초안에는 없음) | 가져오기 시도. 조용히 틀리면 `How the CLI fails quietly`에 한 절 추가 |

### 지운 것과 이유 (현재 SKILL.md 행 번호)

| 행 | 이유 |
|---|---|
| 17 | 18행과 중복 |
| 25, 27의 프레임 확인 | 전원 잘함(`--save`, 사후 프레임 확인) |
| 26 뒷부분, 137, 140 | `qc --help` 사본 |
| 34 레시피 | `doctor`로 이동 |
| 35 pytest 문장 | 유지보수자용 |
| 40, 45 | 중복, 수치가 낡음(92,519바이트) |
| 48, 136의 `wait` | 0.14.0에서 거짓. FilmCraft `--help`가 소유 |
| 50의 razor·새 id·`addTracks` | 도구가 거부하거나 결과로 드러남. 추정 포함 |
| 52의 `audioGain`, `linkedSelection` | 결과에 `mode`, 상태가 찍힘 |
| 57-59, 62의 포맷 대응 | id 접두사가 지도이고 일반 지식. `scopes.read`는 `commands lumetri`에 나옴(확인) |
| 68 | `frames --help`, `describe`의 `burnCaptions=false` |
| 73, 77 | 일반 지식(추정), 기록된 실패 없음 |
| 84, 88 | `.txt`와 `describe`가 소유. 표시 중복은 논리적 귀결 |
| 94의 자막 부분, 95 | `captions --help` 소유 |
| 104, 105 | `graphic --help`가 재렌더와 `renderAudio`를 소유. 첫 페이지 전에 읽으라는 말만 남김 |
| 112, 113, 115의 업스케일 | R1 잘함. `auto_reframe` 품질 주장은 측정한 적 없음. PR #3에서 업스케일은 "판단의 문제"로 넣지 않기로 함 |
| 114 뒷부분 | `frames --help` 소유. 세이프존 자체는 "not taste" 절로 합침 |
| 121, 123, 124, 125 | `describe`가 기본값을 보여 줌, M1 "스스로 해냄", 덕킹 실패 기록 없음(추정) |
| 131, 132 (Color 전체) | C1 "넣지 않음: 잘함". 룩은 18행 |
| 138의 프리셋·AV1·H.265·`hardwareEncoding` | `export --list-presets`, 도구 거부, `describe`. H.265는 실제로 동작함(직접 확인, 작업자의 "거부" 판정은 샌드박스 탓이라 기각). `hardwareEncoding`의 속도와 대가는 측정한 적 없음 |
| 141의 세부 규칙 | 공개 지식(추정). "MP4에 넣지 않는다"만 남김(T4·R2) |
| 154, 156, 157의 사본 | 각 `--help`, MCP 스키마 소유 |
| 155의 Escape | 앞에 있는 다른 앱으로 갈 수 있음 |
| 158의 앱 종료 방법 | 미검증이고 틀리면 작업을 잃는다. 사용자가 직접 닫으면 된다 |

작업자 판정을 바꾼 것: 102행의 두 사례는 남긴다(프레임이 원하는 "비슷한 두 경우가 갈리는 사례"이고 PR #3의 경계 혼란에서 나왔다). Color 절은 작업자의 한 줄 안도 지운다(C1 기록, 18행이 룩을 말함). `references/` 제안은 사용자 결정으로 기각한다.

**지우면 조용히 작업을 망치므로 꼭 남기는 줄:** `timeline.place`의 A1 덮어쓰기(재현: exit 0, 경고 없음), 알 수 없는 옵션·키 무시와 zsh 분할(빈 세션에서 성공처럼 끝남), `removeFillers` 기본 영어(재현: `removed:1`인데 `음`·`어`가 남음), `range` 기본값(2초 파일이 "exported"), 소스 fps, 선형 광, 브리지 저장 대화상자, 앱이 연 파일 디스크 편집, ffmpeg로 편집 금지.

### Interface over document 점검

**판정 기준:** 도구가 소유한 입력·출력·실패는 도구에 둔다. 스킬은 어느 한 인터페이스도 말할 수 없는 것만 갖는다. 우리 CLI는 고칠 수 있고 FilmCraft는 고칠 수 없으므로 둘을 다르게 본다. 같은 사실을 두 곳에 두지 않는다.

| 내용 | 사는 곳 | 이유 |
|---|---|---|
| 엔진 비교, `--model` 안내, 잘림 거부 | `transcribe --help`, 오류 메시지 | 한 명령의 선택지이고 실패 방식이다 |
| 키 위치 | 오류 메시지, `--help`, `doctor` | SKILL에 쓰지 않는다 |
| 교정·적용 절차 | `transcribe --help`, 출력의 `next` | |
| 파형 읽는 법 | `waveform --help` | |
| 자막 규칙과 `violations` 처리 | `captions --help` | |
| 라우드니스 절차 | `qc --help` | 이중 표기가 있던 곳 |
| CLI 버전 맞춤과 설치 절차 | `doctor`의 `checks`, `next` | 같은 순서로 반복되는 기계적 작업이다 |
| `createCaptions` 대신 `captions`, `waveform`으로 언제 확인할지 | SKILL | 여러 도구에 걸친 선택이다 |
| FilmCraft가 조용히 틀리는 경우 | SKILL | 고칠 수 없는 남의 도구가 말해 주지 않는다 |
| 한국어 TTS 불가 | SKILL | 도구의 오류가 `the script has nothing to say`라 원인을 말하지 않는다 |
| `wait` 동작, 전사 비활성 이유, 프리셋, 포맷 | FilmCraft `--help`와 오류 | 도구가 말하므로 SKILL에서 뺀다 |

**프레임에서 벗어나지만 남기는 것(알고 남김):**

- `qc.HELP_TABLE`, `frames.HELP_TABLE`, `captions.HELP`: `cli.py`가 도움말을 조립하지만 표는 판정 상수에서 생성된다. 숫자를 판정 코드와 한곳에 두기 위해서이고, 산문인 `graphic` 도움말만 옮긴다. 승인 때 사용자에게 알린다.
- `.env`가 트리 밖 항목인 것: 사용자 승인 예외.
- `references/` 없음: 프레임은 분리를 강제하지 않지만("can move"), 한 갈래용 내용(앱, 그래픽)이 매번 로드된다. 사용자 결정으로 받아들인다.

SKILL과 도구가 다시 어긋나지 않게 문장이 아니라 테스트로 지킨다. 6단계의 `test_skill_text.py`가 그 역할을 한다.

### 계획 리뷰 처리

Sonnet의 조항별 대조(지적 14건, 전부 읽어서 판단). 내 판단을 함께 적는다. 구현 세션은 이 처리를 뒤집을 근거가 있으면 뒤집어도 된다.

| 지적 | 처리 |
|---|---|
| 재실행이 교정한 전사를 덮음 | 채택. `--out` 덮어쓰기 거부, `--item` 없을 때 `next` 변경 |
| 한국어 미측정 경고가 SKILL에 없음 | 채택. "a model or language you have not checked" |
| 화자 귀속을 아무도 확인 안 함 | 채택. 측정하지 않았고 틀리면 말을 지어내는 셈이다 |
| 음악 위에서 `waveform`은 증거가 못 됨 | 채택. `waveform --help` |
| "act on what it reports"에 조건 없음 | 채택. 필수만 고치고 선택은 필요할 때 |
| `transcript.generate` 괄호 | 채택. 도구 오류가 말함 |
| 값이 낡음(1.6GB, 주기) | 채택 |
| 파일 순서 줄이 구호 | 일부 채택. 실패를 쓰도록 고침. T2의 실제 실수라 지우지는 않음 |
| 저자 전제 | 일부 채택. "this Mac"만 고침. `data/`와 폴더 관례는 사용자가 정한 것이고 "Unless the user names another folder"와 18행이 덮음 |
| 인터페이스 사본 | 일부 채택. 도구 열거, `moov_position`, `--keep-going`, 휴지 계산은 삭제. `fallback`·`blocked`는 넘기기 전 점검이라, `--overlay`는 도구 간 안내라 유지 |
| `hardwareEncoding`에 대가 없음 | 채택하되 더 나아가 줄 삭제. 측정한 적 없음 |
| 앱 종료 문장 미검증 | 채택. 삭제 |
| Nemotron 이름 | 채택. 이름과 수치를 PR 본문으로. 원리와 거부 규칙이 판단을 대신한다 |
| 프레임 이탈 기록 | 채택. 도움말 표는 승인 때 사용자에게 알림 |
| `waveform`의 원본 JSON 판별 | 채택. 입력에서 뺌 |

### skill-maker 대조표

| 프레임 항목 | 계획에서의 처리 |
|---|---|
| Principle over rail | 절대 금지는 이유가 있는 것만(앱이 연 파일, 발언 왜곡, ffmpeg 편집). 외부 전송 행동은 정하지 않음 |
| Interface over document | 위 점검표, `test_skill_text.py` |
| For the model, not the maintainer | 측정 수치·모델 이름의 내력은 PR 본문으로. 유지보수 문장 삭제 |
| Dense | 위 처분. 공급자 소유 값(길이 한도 등)은 쓰지 않고 실패와 오류 메시지로 |
| Colleague over autopilot | 사용자 몫, 되돌리기 비싼 것, 소리를 못 듣는다는 것, 한국어 미측정(`--help`) |
| 대조로 차이 찾기 | 기존 기록 사용. 무거운 실제 편집 대조는 사용자 요청으로 하지 않음. 7단계의 가벼운 판단 대조만 |
| 기존 스킬에서 시작: 지켜야 할 동작 먼저 | 위 "꼭 남기는 줄" |
| 새 스킬 비용: 이웃과 경계 | 설명 범위가 바뀌므로 `/skill-doctor` 실행(6단계) |
| 코드 트리·`--help` 두 단계·stdout 한 문서·종료 코드 | 설계 절. 새 명령마다 자체 `--help`에 출력과 실패 |
| 구조 테스트 | `KINDS` 갱신, `.env` 제외 확인 |
| 완료: 전체 문안 승인, 다른 계열 리뷰 후 제시, `plugin validate`, 개발 기록은 PR | 6~8단계 |

## 구현 단계

파일을 바꾸는 단계가 많으므로 구현 세션은 `TaskCreate`로 아래 단계를 그대로 열고, 각 `description`에 완료 판정을 적는다. 코드 작업 전에 `coding` 스킬을 연다. 줄바꿈은 CLAUDE.md 규칙대로 산문·docstring·`--help` 모두 한 덩어리 한 줄이다.

### 0. 준비

먼저 **정리 PR**을 별도로 머지한다. 브랜치 `chore/release-prep`, 제목 `chore: 릴리스 준비로 추적 파일 정리`.

- `.gitignore`에 `.env`와 `.claude/histories`를 넣는다. 레포가 PUBLIC이므로 키 파일을 만들기 전에 머지되어야 한다.
- `git rm -r -q --cached .tmp/filmcraft`와 `git rm -q --cached .claude/histories`로 추적만 해제한다. 심볼릭 링크와 로컬 파일은 그대로 두고, 이력은 다시 쓰지 않는다(그래서 클론 크기는 줄지 않는다).
- 루트에 MIT `LICENSE`(`Copyright (c) 2026 성진`)를 추가한다.
- README에서 151행의 `.tmp/filmcraft/` 줄과 176행의 `.tmp/etc/` 줄을 지운다. 추적 해제가 건드리는 다른 참조는 없다(`git grep`으로 확인함).

정리 PR 완료 판정: `git archive HEAD | tar -t`에 `.tmp`와 `.claude/histories`가 없고, 압축본이 1MB 미만이며, `tests/video_skill`이 그대로 통과한다. 로컬의 `.claude/histories` 링크가 남아 있다.

그다음 이 작업을 준비한다.

- 갱신된 `main`에서 `feat/transcribe-openrouter` 브랜치를 판다.
- 앱과 `filmcraft-cli` 버전을 확인한다. 측정은 0.14.0에서 했으므로, 앱이 더 새 버전이면 CLI를 맞추고 `tests/filmcraft_facts`와 이 계획의 FilmCraft 사실을 먼저 다시 확인한다. 달라진 사실은 처분 표를 고치고 진행한다.
- **스테이징은 경로를 지정해서만 한다. `git add -A` 금지.** 미추적 `.claude/plans/`는 이 작업과 무관하다.
- 사용자에게 키 재발급을 권한다. 이번 키는 대화 기록에 평문으로 남았다. 재발급한 키는 클립보드에 복사한 뒤 사용자가 다음을 실행한다(대화에 키를 다시 붙이지 않기 위해서다): `! (umask 077; { printf 'OPENROUTER_API_KEY='; pbpaste; echo; } > ".claude/skills/video/scripts/video/openrouter/.env")`. 폴더가 먼저 있어야 하므로 2단계에서 유닛 폴더를 만든 뒤 안내한다.
- `.claude/plans/users-seongjin-coding-agentic-video-cla-compiled-rainbow.md`는 이름 변경 때 남긴 심볼릭 링크라 지운다.

완료 판정: `git check-ignore`가 `.env` 경로를 잡고, 키 파일을 만든 뒤에도 `git status`에 보이지 않는다.

### 1. 구조 커밋 (동작 변화 없음)

`recognition.py` 신설과 `whisper` 이전, `captions/srt.py`를 `subrip.py`로 이동, `speech_spans`를 `ffmpeg`로 이동, `graphic/help.py` 산문을 `cli.py`로 이동, `KINDS` 갱신.

완료 판정: 이전 전후 모든 `--help` 출력이 바이트 단위로 같고, `tests/video_skill` 전체 통과.

### 2. `openrouter` 유닛과 `transcribe` 엔진

먼저 실패하는 테스트를 쓰고 이유를 읽는다. 다음을 한 묶음씩 진행한다.

- 응답 해석과 거부 판정(기록된 실제 응답)
- 요청 경로와 실패 표 전체(로컬 가짜 서버)
- `--engine`/`--from-json`, `--snap auto`, `--item` 선택, `snap`의 길이 0 소속과 정리 분리
- 분할(`plan_chunks`), 검토 신호

기존 테스트 수정: `test_missing_media_is_a_usage_error`, `test_real_whisper_path`에 `--engine local`을 붙인다. 앞의 테스트는 미디어 누락 때문에 2가 나는지 메시지까지 확인한다. `--from-json` 기존 테스트의 `snapped` 값은 그대로 유지되어야 한다.

완료 판정: 아래 테스트 통과, 실제 경로 게이트 테스트 통과, `say` 클립이 `transcript.set`에서 `transcript.inspect`까지 단어와 화자를 그대로 왕복.

### 3. `waveform`

완료 판정:

- 톤 버스트를 렌더해 파형과 스펙트로그램 두 패널의 에너지 시작 열이 계산된 열과 ±1px로 맞는다. 칸 위치만 보는 테스트는 그림과 칸이 어긋나도 통과하므로 충분하지 않다.
- 같은 파일의 `speech` 구간이 생성 조건과 0.02초 안에서 맞는다.
- 실제 다큐 137.5~140초 그림에서 이번 측정과 같은 판정을 Claude가 눈으로 내릴 수 있다.

### 4. `captions`

완료 판정:

- `--transcript`로 프로젝트 없이 SRT가 나온다.
- `en` 규칙의 손으로 계산한 예제가 통과하고, `understand`는 절 끝이 아니며 `Mr.` 뒤에서 끊기지 않는다.
- 사용자가 넘긴 `--cps 12`가 `en` 프로파일의 20을 덮어쓴다.
- 손으로 만든 회귀 테스트: 한 단어 턴은 경계가 아니고 일반 화자 변경은 여전히 끊는다.
- 다큐 10분 구간 재실행 결과가 원장의 채택 행과 같은 수준이다(`short` 5, 한 단어 자막 2, 화자 분리 없음 대비 `short` +4 이내). 레포에 넣지 않고 표를 PR 본문에 남긴다.

### 4-1. `doctor`

순수 판정 함수를 먼저 실패하는 테스트로 만들고, 이 컴퓨터에서 실제 진입점을 한 번 돌린다.

완료 판정:

- 직접 쓴 예제가 통과한다: CLI 0.14.0과 앱 0.17.0이면 `ok: false`, 종료 1, `next`에 `filmcraft-cli-0.17.0-macos-universal.zip`이 들어간다. 버전이 같으면 `next`가 비고 종료 0이다. 앱이 없어도 필수 항목은 통과한다. 선택 항목이 빠져도 종료 0이다.
- 키를 넣은 상태의 stdout, stderr에 키 문자열과 그 일부가 없다. `value`는 `env`, `file`, `none` 중 하나다.
- 실행 중 네트워크 요청과 파일 쓰기가 없다.
- 실제 실행 결과가 이 컴퓨터의 상태와 맞는다.

### 5. 사실 테스트

SKILL.md에서 지우는 문장이 있으므로 테스트도 함께 맞춘다. docstring이 가리키는 문장을 하나씩 확인해 다음 셋 중 하나로 처리하고, 그 대응을 PR 본문에 적는다. 조용히 지우지 않는다.

- 문장이 남음: 그대로 둔다.
- 문장은 지웠지만 스킬 코드나 `--help`가 그 사실에 기댐(`captions`의 자막 크기 계산 등): docstring을 그 근거로 고친다.
- 어디도 기대지 않음(`test_18`의 `wait` 등): 지운다.

추가: 화자 왕복과 문단 분할, 목록 없는 `removeFillers`가 한국어 필러를 남김, 구두점 붙은 필러 제거, `null` 거부. "초안에서 구현 때 확인할 문장" 표를 확인해 테스트를 넣거나 문장을 지운다.

완료 판정: `tests/filmcraft_facts` 전체 통과. 각 테스트 docstring이 가리키는 문장이 SKILL.md나 지정한 `--help`에 실제로 있다.

### 6. SKILL.md와 README

프레임 순서대로 진행한다. **초안, 다른 모델 계열 리뷰, 사용자에게 제시** 순서이고, 승인을 먼저 받지 않는다.

1. 계획의 초안 전문을 SKILL.md에 넣고 확인한 사실을 반영한다.
2. `tests/video_skill/test_skill_text.py`를 새로 만든다. SKILL.md가 언급하는 `cli.py` 하위 명령과 `--플래그`는 파서에 실제로 있어야 하고, 코드 표기된 FilmCraft 명령 id는 `filmcraft-cli describe`로 풀려야 한다. 사실 테스트 docstring이 가리키는 절 이름은 SKILL.md에 있어야 한다. 일부러 없는 플래그를 넣은 작은 텍스트로 이 테스트가 실패하는지도 확인한다.
3. 설명 범위가 바뀌므로 이 프로젝트에서 `claude -p "/skill-doctor"`를 돌려 이웃 스킬과 트리거가 겹치는지 본다. 겹치면 양쪽 설명에 경계를 긋는다.
4. Codex(`gpt-6.1-terra`, `high`, 쿼터가 11월 4일 17:09에 풀림)가 초안을 다섯 속성에 대해 읽는다. 쓸 수 없으면 Sonnet으로 하되 다른 모델 계열의 시각이 없다고 말하고 그 위험을 밝힌다. 지적은 재현해서 받아들이거나 이유를 들어 기각한다.
5. 사용자에게 전체 문안과 리뷰 처리 결과를 보여 승인받는다.

README는 엔진·`.env`·`waveform`·`doctor`·표·레포 구조를 갱신하고, "화자를 구분하지 못합니다" 한계를 고치며, 라이선스를 한 줄 적는다. 저장소 이름이 `Agentic-Video`로 바뀌었으므로 제목의 `Claude-Video`와 PR 링크도 맞춘다. 표의 "FilmCraft 0.7.2" 같은 측정 조건은 당시 사실이므로 그대로 둔다.

완료 판정: 사용자가 전체 문안을 승인했다. `test_skill_text.py`가 통과한다. "Interface over document 점검" 표의 각 행이 실제 파일과 맞고, 같은 사실이 두 곳에 없다. 초안의 모든 줄에 "지운 것"이나 "꼭 남기는 줄"과 모순이 없다.

### 7. 가벼운 대조와 코드 리뷰

무거운 실제 편집 대조는 하지 않는다(사용자 결정). 기존 기록 위에 새 판단만 빠르게 본다.

- 영상을 만들지 않는 판단 대조: 빈 디렉터리와 `claude -p --safe-mode --restricted --permission-mode acceptEdits --model claude-opus-5-5 --output-format json`에 소재 없이 "OpenRouter에 Nemotron이 최고라고 들었는데, 86분 다큐의 자막 싱크용으로 어떤 전사를 쓸까? Whisper도 있다."를 묻는다. 스킬 없는 Claude가 평판을 따르는지 본다. 스킬 있는 쪽은 레포에서 같은 질문을 하고, `transcribe --help`를 읽어 시간 문제를 말하는지 본다. 엔진 비교를 `--help`로 옮긴 결정이 맞는지 이것으로 확인한다. 읽지 않으면 SKILL에 "엔진을 고르기 전에 `--help`를 읽는다"는 한 절을 더한다.
- `transcribe`와 `waveform`을 만든 코드 변경은 Codex(안 되면 Sonnet)로 리뷰한다. 지적은 재현해서 처리한다.
- `.claude/plans/filmcraft-skill.md`의 "대조 실험의 차이 → 스킬 안의 자리" 표와 `video-graphics.md`의 같은 표를 다시 읽어, 이번에 자리를 잃은 항목마다 새 자리나 뺀 이유를 적는다. skill-maker 완료 조건이고, PR 본문에 넣는다.

완료 판정: 대조 결과에 대한 처리 기록이 있고, 기존 표의 모든 항목에 자리나 뺀 이유가 있으며, 리뷰 지적의 채택과 기각 이유가 PR 본문에 있다.

### 8. 종단 검증과 PR

- 실제 다큐로 CLI 전체 경로를 한 번 돌린다: `transcribe --engine openrouter --diarize` → `captions --transcript --rules en` → `waveform`으로 큐 시작 몇 곳 확인. 비용 약 $0.32.
- 작은 구간으로 프로젝트 경로도 돈다: `transcribe --item` → `run` → `captions --project` → `captions.import` → `frames --project`.
- `--model nvidia/nemotron-3.5-transcribe`로 긴 구간을 보내 거부되는 것과, 거부 메시지가 알려 준 `--chunk`로 통과하는 것을 한 번 확인한다.
- `claude plugin validate --strict .claude/skills`가 0으로 끝나는지 확인한다. `.env`가 스킬 폴더 안에 있는 상태로도 돌린다.
- 커밋은 논리 단위로, 제목은 `<타입>: <한국어 제목>` 50자 이내. PR 제목은 `feat: 전사 엔진에 OpenRouter 추가하고 스킬 문서 정비`. 본문은 `## 무엇을 바꿨나` / `## 왜` / `## 영향` / `## 검증`으로 쓰고 측정 원장, 버린 대안, 사실 테스트 대응, 대조 표 갱신을 넣는다. 스킬 안에는 개발 기록을 두지 않는다. `gh pr merge --squash`.

### 9. GitHub 릴리스 `v0.1.0`

공개 작업이고 태그와 압축본은 되돌려도 복제되었을 수 있으므로, 만들기 전에 정확히 무엇이 나가는지 확인한다.

**전제:** 8단계 PR이 머지되었고, `main`의 머지 커밋에서 `tests/video_skill`과 `tests/filmcraft_facts`가 통과하며, 사용자가 SKILL.md 전체 문안을 승인했다. 다른 모델 계열의 리뷰를 못 한 상태라면 그 위험을 말하고 그대로 낼지 사용자에게 한 번 묻는다.

**공개 전 점검(머지 커밋 기준):**

- `git archive <sha> | tar -t`에 `.env`, `data/`, `.tmp/`, `.claude/histories`, `.claude/plans/`, `.claude-runs/`, `.codex-runs/`가 없다.
- `git archive <sha> | tar -xO | grep -c 'sk-or-v1'`이 0이고, `git log --all -G 'sk-or-v1' --oneline`도 비어 있다.
- 압축본 안의 `/Users/seongjin` 문자열을 확인한다. 테스트 픽스처와 문서에 개인 경로가 없어야 한다.
- 압축본이 1MB 미만이고 `LICENSE`가 들어 있다.

**릴리스 노트(한국어, `--notes-file`):**

- 무엇인가: 이 스킬이 하는 일 한두 문장.
- 이번에 들어간 것: `transcribe`의 `openrouter` 엔진(Scribe v2 기본, 화자 분리), `waveform`, `doctor`, 프로젝트 없는 자막과 영어 규칙.
- 왜: 측정 요약. 구절 시작 0.5초 초과가 Whisper+snap에서 21%였다는 사실과 기준이 영어 다큐 1편의 모델 간 합의라는 조건을 함께 적는다.
- 쓰는 법: 이전과 달라진 점(`transcribe`에 `--engine`이 필수), 키 위치, 시작은 `doctor`.
- 필요한 것과 확인한 버전: macOS, 확인한 FilmCraft 버전, `uv`, `ffmpeg`.
- 알려진 한계: 실제 한국어 음성 미측정, Gemini 미검증, 브리지 모드 미검증, 오디오가 공급자에게 나간다는 사실.

노트에 키, 개인 경로, 사용자 영상의 전사를 넣지 않는다.

**실행:** `gh release create v0.1.0 --target <머지 커밋 sha> --title "v0.1.0" --notes-file <파일>`. 별도 첨부 파일은 두지 않는다. 정리 후 소스 압축본이 작고, 스킬 폴더가 그대로 들어 있기 때문이다.

**공개 후 확인:** `gh release download v0.1.0 --archive=zip`을 빈 폴더에 받아 풀고, 그 안의 `.claude/skills/video/scripts/cli.py`로 `--help`와 `doctor`를 실행한다. `data/`와 `.env`가 없어도 동작해야 하고 `openrouter_key`는 `none`이어야 한다.

완료 판정: 위 점검이 모두 통과했고 릴리스 URL을 사용자에게 알렸다.

## 테스트 이음새

| 이음새 | 무엇을 검증 | 기대값의 출처 | 남는 미검증 |
|---|---|---|---|
| CLI 프로토콜(`tests/support`의 `skill()`), `--from-json` + 기록된 실제 응답 | 해석, 거부, 출력 필드, 파일, 종료 코드 | `say` 구절 경계, 톤 버스트 생성 조건, 실제로 기록한 깨진 응답 | |
| CLI + 로컬 가짜 HTTP 서버(`OPENROUTER_BASE_URL`, `OPENROUTER_API_KEY=sk-test-…`) | 요청 본문, 재시도, 실패 표, 분할과 시간 합산, 키가 어디에도 새지 않음 | 서버가 받은 요청, 알려진 청크 경계 | 실제 서버와의 합치는 아래 게이트 테스트로만 |
| 순수 함수: `transcribe.snap`, `transcribe.plan_chunks`, `captions.layout`, `openrouter.read`, `openrouter.load_key`, `doctor` 판정 | 경계 계산, 키 파일 해석, 점검 판정 | 손으로 계산한 예제, 실제 릴리스 파일 이름 | `gh` 설치 명령을 실제로 끝까지 실행하지는 않음 |
| 게이트 테스트 `FILMCRAFT_TEST_OPENROUTER=1` | 실제 API 왕복 | `say` 구절 경계, 약 1센트 | 공급자의 이후 변화 |
| `tests/filmcraft_facts` | FilmCraft 사실 | 실제 실행 | 브리지 모드 |
| `test_structure.py` | 트리, 임포트 방향, `.env`가 git에서 제외됨 | 구조 규칙 | |
| `test_skill_text.py` | SKILL.md의 명령·플래그·FilmCraft id가 실재함 | 실제 파서와 `describe` | 문장의 의미가 맞는지는 잡지 못함 |

기록 픽스처는 합성 음성에서만 만든다(`tests/video_skill/fixtures/say_ko.scribe.json`, `say_ko.nemotron.json`, 5분 이상 `say`의 잘린 Nemotron 응답). 레포가 공개이므로 사용자 영상의 전사는 넣지 않는다. 화자 픽스처는 서로 다른 `say` 목소리 둘로 만들어 기록하고, Scribe가 나누지 못하면 손으로 쓴 최소 JSON을 쓰되 그 사실을 테스트 docstring에 적는다.

꼭 넣을 테스트:

- 테스트는 항상 가짜 키를 주입해 진짜 키가 localhost로 가지 않는다. 실패 경로까지 포함해 키 문자열이 stdout, stderr, 생성 파일 어디에도 없다.
- 키 없음은 `OPENROUTER_API_KEY=""`로 재현하고, 로컬로 넘어가지 않고 종료 1이다.
- `OPENROUTER_BASE_URL`이 http 원격이면 거부한다.
- 이미 있는 `--out`은 종료 2이고 내용이 그대로다. `--item` 없는 실행의 `next`가 재실행을 안내하지 않는다.
- 잘린 응답은 종료 1이고 `X.jsonl`을 쓰지 않는다. 분할해 합친 원본을 `--from-json`으로 다시 읽으면 거부되지 않는다.
- 연결 실패, 200인데 JSON 아님, 404에서 traceback이 없고 약속한 종료 코드가 나온다.
- `audio_event`와 `...`가 단어로 들어가지 않는다. `eng`가 `en`이 된다.
- 길이 0 단어는 `unmatched`가 아니고 한 프레임 이상이 된다. snap을 끄면 `snapped`는 0이다.
- 신뢰도 없는 응답의 `X.jsonl`이 FilmCraft에 적용된다(`confidence` 키 없음).
- `--engine`과 `--from-json` 둘 다 없으면 종료 2이고 네트워크 요청이 없다.
- 임시 오디오는 실패해도 남지 않는다.
- 말이 없는 미디어는 종료 0, 단어 0개, `notes`에 사유.

## 완료 보고에 반드시 적을 것

- 어떤 테스트를 변경 전에 실패로 봤는지, 스위트 종료 코드, 실제 진입점 실행 여부.
- 가짜 서버 뒤에 있는 계약과 끝내 실행하지 못한 것.
- **미검증:** 실제 한국어 음성에서의 Scribe 품질(사용자 결정), 음악 위 단어 시간의 육안 확인, Gemini, 브리지 모드, Scribe의 base64 24MB 초과 동작.
- skill-maker 완료 조건: 사용자 전체 문안 승인, 대조 차이 처리, `plugin validate`, 다른 모델 계열 리뷰 여부(못 했으면 위험을 명시). 승인은 많은 실제 세션에서의 성능 증거가 아니다.
- 릴리스 URL, 공개 전후 점검 결과.
- 핸드오프 후보: `beats`, `doctor`의 자동 설치, `captions`·`frames`의 `--sequence`, `_exit` 키, 이력에 남은 `.tmp/filmcraft`(클론 크기), 로컬 강제 정렬(측정 안 함).
