"""
main.py — TurtleNeck Gemini Live Agent

거북목(FHP) 감지 시 Gemini Live API로 실시간 음성 코칭.

실행:
  export GOOGLE_API_KEY="your_key"
  python main.py

의존: posture_hook.py가 fhp_visualizer.py와 같은 프로세스에서 import되어야 함.
     (또는 별도 실행 후 shared memory / socket으로 연결 가능)
"""

import asyncio
import os
import sys
import threading
from pathlib import Path

# HTTP 서버 (Cloud Run 헬스체크용)
from http.server import HTTPServer, BaseHTTPRequestHandler

# Gemini SDK (신규 패키지)
from google import genai
from google.genai import types

# 자세 상태 브릿지
sys.path.insert(0, str(Path(__file__).parent))
from posture_hook import should_trigger, get_alert_message, posture_state

# ── 설정 ─────────────────────────────────────────────────────────
API_KEY = os.environ.get("GOOGLE_API_KEY", "")
MODEL   = "gemini-2.0-flash-live-001"

SYSTEM_PROMPT = """
당신은 사용자의 자세를 실시간으로 모니터링하는 건강 코치 AI입니다.
이름은 '목이'입니다.

거북목(FHP, Forward Head Posture)이 감지되면:
1. 친근하고 따뜻한 톤으로 알림
2. 구체적인 교정 동작 하나 안내 (예: "턱을 당기고 어깨를 펴세요")
3. 20초 이내로 간결하게
4. 한국어로 말하기

정상 자세일 때는 칭찬과 격려 메시지 제공.
"""


async def run_agent():
    """Gemini Live Agent 메인 루프"""
    if not API_KEY:
        print("[WARNING] GOOGLE_API_KEY 없음 — agent 비활성화, HTTP 서버만 유지")
        while True:
            await asyncio.sleep(60)

    client = genai.Client(api_key=API_KEY)

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore")
            )
        ),
        system_instruction=SYSTEM_PROMPT,
    )

    print("[목이] 거북목 모니터링 시작...")

    async with client.aio.live.connect(model=MODEL, config=config) as session:
        while True:
            await asyncio.sleep(1)  # 1초마다 상태 체크

            if should_trigger():
                msg = get_alert_message()
                print(f"[목이] 트리거 발동 → stage={posture_state['stage']}")

                # Gemini에 자세 상태 전송 → 음성 응답 받기
                await session.send(input=msg, end_of_turn=True)

                # 음성 응답 수신 및 재생
                async for response in session.receive():
                    if response.data:
                        _play_audio(response.data)
                    if response.text:
                        print(f"[목이] {response.text}")


def _play_audio(audio_bytes: bytes):
    """오디오 바이트를 시스템 스피커로 재생 (macOS/Linux)"""
    try:
        import pyaudio
        p = pyaudio.PyAudio()
        stream = p.open(format=pyaudio.paInt16, channels=1,
                        rate=24000, output=True)
        stream.write(audio_bytes)
        stream.stop_stream()
        stream.close()
        p.terminate()
    except ImportError:
        # pyaudio 없으면 파일로 저장
        out = Path("/tmp/posture_alert.pcm")
        out.write_bytes(audio_bytes)
        print(f"[목이] 오디오 저장됨: {out}")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        stage = posture_state.get("stage", "UNKNOWN")
        self.wfile.write(f"TurtleNeck Agent running | stage={stage}\n".encode())
    def log_message(self, format, *args):
        pass  # suppress access logs


def start_http_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    print(f"[서버] HTTP 헬스체크 포트 {port} 시작")
    server.serve_forever()


if __name__ == "__main__":
    # HTTP 서버를 백그라운드 스레드로 먼저 실행 (Cloud Run 헬스체크)
    import time
    t = threading.Thread(target=start_http_server, daemon=True)
    t.start()
    time.sleep(1)  # HTTP 서버가 포트 점유할 때까지 대기
    asyncio.run(run_agent())
