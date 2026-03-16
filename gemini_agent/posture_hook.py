"""
posture_hook.py — fhp_visualizer 상태를 Gemini Agent에 전달하는 브릿지

fhp_visualizer.py의 루프에서 posture_state를 공유 딕셔너리로 업데이트.
Gemini Agent는 이 상태를 폴링하여 트리거 판단.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

# ── 공유 상태 (fhp_visualizer → gemini agent) ───────────────────
posture_state: dict = {
    "fhp_score": 0.0,
    "stage": "NORMAL",          # NORMAL / CAUTION / WARNING / CRITICAL
    "forward_cm": 0.0,
    "neck_load_kg": 0.0,
    "timestamp": 0.0,
}

# ── 트리거 설정 ──────────────────────────────────────────────────
TRIGGER_STAGE = "WARNING"       # 이 단계 이상이면 Gemini에 알림
TRIGGER_COOLDOWN_SEC = 30       # 같은 알림 최소 간격 (초)

_last_trigger_time: float = 0.0
_last_triggered_stage: str = "NORMAL"


def update_posture(fhp_score: float, stage: str,
                   forward_cm: Optional[float], neck_load_kg: Optional[float]):
    """fhp_visualizer 메인 루프에서 매 프레임 호출"""
    posture_state.update({
        "fhp_score": fhp_score,
        "stage": stage,
        "forward_cm": forward_cm or 0.0,
        "neck_load_kg": neck_load_kg or 0.0,
        "timestamp": time.time(),
    })


def should_trigger() -> bool:
    """Gemini 알림을 발송할 타이밍인지 판단"""
    global _last_trigger_time, _last_triggered_stage

    stage = posture_state["stage"]
    now = time.time()
    stage_order = ["NORMAL", "CAUTION", "WARNING", "CRITICAL"]

    is_bad = stage_order.index(stage) >= stage_order.index(TRIGGER_STAGE)
    cooldown_ok = (now - _last_trigger_time) > TRIGGER_COOLDOWN_SEC

    if is_bad and cooldown_ok:
        _last_trigger_time = now
        _last_triggered_stage = stage
        return True
    return False


def get_alert_message() -> str:
    """Gemini에게 전달할 자세 상태 메시지 생성"""
    s = posture_state
    stage_kr = {"NORMAL": "정상", "CAUTION": "주의",
                "WARNING": "경고", "CRITICAL": "심각"}.get(s["stage"], s["stage"])
    return (
        f"사용자의 현재 자세 상태입니다.\n"
        f"- FHP 점수: {s['fhp_score']:.0f}/100\n"
        f"- 단계: {stage_kr} ({s['stage']})\n"
        f"- 전방 편차: {s['forward_cm']:.1f}cm\n"
        f"- 목 하중: {s['neck_load_kg']:.1f}kg\n\n"
        f"이 사용자에게 자세 교정을 유도하는 짧고 친근한 음성 메시지를 한국어로 말해주세요. "
        f"20초 이내로 구체적인 교정 방법 하나를 포함해주세요."
    )
