"""FR-5: 방제 후 사후관리(closed-loop).

로컬 데모용 인메모리 저장소. 실제 서비스에서는 DB + 알림 발송(푸시/문자)으로 대체.
"""
import uuid
from datetime import date, timedelta

from app.classifier import classify_image
from app.db import is_healthy

_CASES: dict[str, dict] = {}


def create_case(crop: str, disease_class: str, followup_days: int = 4):
    case_id = str(uuid.uuid4())[:8]
    due_date = date.today() + timedelta(days=followup_days)
    _CASES[case_id] = {
        "case_id": case_id,
        "crop": crop,
        "original_class": disease_class,
        "created_at": date.today().isoformat(),
        "followup_due": due_date.isoformat(),
        "status": "awaiting_followup",
        "followup_result": None,
    }
    return _CASES[case_id]


def get_case(case_id: str):
    return _CASES.get(case_id)


def submit_followup_photo(case_id: str, image_bytes: bytes):
    case = _CASES.get(case_id)
    if case is None:
        return None

    predictions = classify_image(image_bytes, top_k=1)
    top = predictions[0]

    if is_healthy(top["class_name"]):
        verdict = "improved"
        message = "재사진 분석 결과 건강한 상태로 확인되었습니다. 방제가 효과가 있었습니다."
    elif top["class_name"] == case["original_class"]:
        verdict = "not_improved"
        message = "재사진에서도 동일한 병징이 남아 있습니다. 재방제 또는 원인 재진단이 필요합니다."
    else:
        verdict = "changed"
        message = f"이전과 다른 소견({top['class_name']})이 감지되었습니다. 재진단을 권장합니다."

    case["status"] = "completed"
    case["followup_result"] = {
        "verdict": verdict,
        "message": message,
        "new_prediction": top,
    }
    return case
