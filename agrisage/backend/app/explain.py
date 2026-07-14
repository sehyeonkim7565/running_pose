"""FR-2: 진단 결과 설명 생성.

확정된 분류 결과(작물명, 질병명)만 LLM에 전달하고, LLM은 새로운 진단을 내리지
않는다. ANTHROPIC_API_KEY가 설정되어 있으면 Claude API를 호출하고, 없으면
템플릿 기반 설명으로 폴백한다 (오프라인/키 없이도 로컬 테스트 가능).
"""
import json
import os

_client = None


def _get_client():
    global _client
    if _client is None and os.environ.get("ANTHROPIC_API_KEY"):
        from anthropic import Anthropic
        _client = Anthropic()
    return _client


SYSTEM_PROMPT = (
    "당신은 AgriSage의 농업 설명 도우미입니다. 이미 확정된 이미지 분류 결과"
    "(작물명, 질병명)를 근거로만 설명을 작성하세요. 스스로 새로운 진단을 내리거나"
    "분류 결과를 바꾸지 마세요. 초보 재배자가 이해할 수 있는 쉬운 말로 작성하고,"
    "반드시 JSON으로만 응답하세요. 키: diagnosis_summary, symptoms, causes, "
    "recommended_actions(배열)."
)


def generate_explanation(crop: str, disease_name: str, confidence: float, is_healthy: bool):
    client = _get_client()
    if client is None:
        return _template_explanation(crop, disease_name, confidence, is_healthy)

    user_prompt = (
        f"작물: {crop}\n질병명: {disease_name}\n분류 신뢰도: {confidence:.1%}\n"
        f"건강 여부: {'건강함' if is_healthy else '병징 있음'}\n"
        "위 확정된 분류 결과만을 근거로 진단 결과 요약, 병의 특징, 발생 원인, "
        "추천 대응법을 JSON으로 작성해줘."
    )
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = resp.content[0].text
        start, end = text.find("{"), text.rfind("}")
        data = json.loads(text[start:end + 1])
        data["source"] = "llm"
        return data
    except Exception as e:
        fallback = _template_explanation(crop, disease_name, confidence, is_healthy)
        fallback["llm_error"] = str(e)
        return fallback


def _template_explanation(crop: str, disease_name: str, confidence: float, is_healthy: bool):
    if is_healthy:
        return {
            "diagnosis_summary": f"{crop} 잎은 병징 없이 건강한 상태로 분류되었습니다 (신뢰도 {confidence:.0%}).",
            "symptoms": "뚜렷한 병반, 변색, 반점이 관찰되지 않았습니다.",
            "causes": "특별한 이상 원인이 발견되지 않았습니다.",
            "recommended_actions": [
                "현재 재배 관리(관수, 시비, 통풍)를 유지하세요.",
                "주기적으로 잎 상태를 재확인해 초기 이상 징후를 놓치지 마세요.",
            ],
            "source": "template",
        }
    return {
        "diagnosis_summary": f"{crop}에서 '{disease_name}'(으)로 분류되었습니다 (신뢰도 {confidence:.0%}).",
        "symptoms": "잎에 반점, 변색, 부패 등의 병징이 관찰될 수 있습니다. 정확한 병징은 추천 제품 및 방제 정보를 참고하세요.",
        "causes": "과습, 통풍 불량, 병원균/세균 전파 등이 주요 원인으로 알려져 있습니다.",
        "recommended_actions": [
            "감염된 잎과 잔재물을 제거해 확산을 막으세요.",
            "추천 방제 제품과 안전사용기간(PLS)을 확인한 뒤 살포하세요.",
            "방제 후 3~5일 뒤 재사진으로 개선 여부를 확인하세요.",
        ],
        "source": "template",
    }
