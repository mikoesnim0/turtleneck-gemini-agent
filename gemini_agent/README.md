# TurtleNeck Gemini Live Agent 🦒

거북목(FHP) 실시간 감지 → Gemini Live API 음성 코칭

## Architecture

```
카메라
  ↓
fhp_visualizer.py  (MediaPipe 자세 감지)
  ↓ posture_hook.update_posture()
posture_hook.py    (상태 공유 + 트리거 판단)
  ↓ should_trigger() → get_alert_message()
main.py            (Gemini Live API 연결)
  ↓ 음성 응답
스피커 (실시간 코칭)
```

## Setup

```bash
pip install -r requirements.txt
export GOOGLE_API_KEY="your_gemini_api_key"
```

## Run

```bash
# 터미널 1: 자세 감지
cd ../swarm/results/idea_13_wave/results/viz
python fhp_visualizer.py

# 터미널 2: Gemini Agent
cd gemini_agent
python main.py
```

## Trigger Logic

| 단계 | FHP 점수 | 동작 |
|------|---------|------|
| NORMAL | 0~25 | 대기 |
| CAUTION | 25~50 | 대기 |
| WARNING | 50~75 | **Gemini 음성 알림 발동** |
| CRITICAL | 75~100 | **긴급 음성 알림 발동** |

- 쿨다운: 30초 (같은 알림 반복 방지)

## GCP Deployment

```bash
gcloud run deploy turtleneck-agent \
  --source . \
  --region asia-northeast3 \
  --set-env-vars GOOGLE_API_KEY=$GOOGLE_API_KEY
```
