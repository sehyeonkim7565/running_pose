"""Vertex AI 이미지 분류 엔드포인트 호출.

로컬 classify_image()와 동일한 반환 형식(top_k개의 {"class_name", "confidence"})을
유지해서 app/main.py에서 그대로 교체해 쓸 수 있게 한다.
"""
import base64
import os

from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict

VERTEX_PROJECT = os.environ.get("VERTEX_PROJECT", "1059859863302")
VERTEX_ENDPOINT_ID = os.environ.get("VERTEX_ENDPOINT_ID", "4405356614161268736")
VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
VERTEX_API_ENDPOINT = os.environ.get(
    "VERTEX_API_ENDPOINT", f"{VERTEX_LOCATION}-aiplatform.googleapis.com"
)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = aiplatform.gapic.PredictionServiceClient(
            client_options={"api_endpoint": VERTEX_API_ENDPOINT}
        )
    return _client


def classify_image_vertex(image_bytes: bytes, top_k: int = 3):
    """이미지 바이트를 Vertex AI 엔드포인트로 보내고 top_k 예측을 반환한다.

    반환 형식은 app/classifier.py의 classify_image()와 동일하다:
    [{"class_name": str, "confidence": float}, ...] (confidence 내림차순)
    """
    client = _get_client()

    encoded_content = base64.b64encode(image_bytes).decode("utf-8")
    instance = predict.instance.ImageClassificationPredictionInstance(
        content=encoded_content,
    ).to_value()
    parameters = predict.params.ImageClassificationPredictionParams(
        confidence_threshold=0.0,
        max_predictions=top_k,
    ).to_value()

    endpoint = client.endpoint_path(
        project=VERTEX_PROJECT, location=VERTEX_LOCATION, endpoint=VERTEX_ENDPOINT_ID
    )
    response = client.predict(
        endpoint=endpoint, instances=[instance], parameters=parameters
    )

    # 각 prediction은 {"ids": [...], "displayNames": [...], "confidences": [...]}
    # 형태이며 이미 confidence 내림차순으로 정렬되어 온다.
    results = []
    for prediction in response.predictions:
        pred = dict(prediction)
        display_names = pred.get("displayNames", [])
        confidences = pred.get("confidences", [])
        for name, confidence in zip(display_names, confidences):
            results.append({"class_name": name, "confidence": round(float(confidence), 4)})

    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results[:top_k]
