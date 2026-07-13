from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import db, followup
from app.classifier import classify_image
from app.explain import generate_explanation
from app.pls import check_pls_for_products

app = FastAPI(title="AgriSage API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


CROP_KO = {"Apple": "사과", "Potato": "감자", "Tomato": "토마토"}


def _crop_disease_name(class_name: str) -> tuple[str, str]:
    info = db.get_disease_info(class_name)
    if info:
        return info["crop"], info["disease_name"]
    # healthy label: "Crop___healthy"
    crop_en = class_name.split("___")[0]
    return CROP_KO.get(crop_en, crop_en), "건강 (병징 없음)"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/diagnose")
async def diagnose(image: UploadFile = File(...)):
    """FR-1: 이미지 진단. 상위 top-3 클래스와 confidence를 반환한다."""
    image_bytes = await image.read()
    try:
        predictions = classify_image(image_bytes, top_k=3)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="모델이 아직 학습되지 않았습니다. backend/model/train.py를 먼저 실행하세요.",
        )
    top = predictions[0]
    crop, disease_name = _crop_disease_name(top["class_name"])
    return {
        "predictions": predictions,
        "top": {
            "class_name": top["class_name"],
            "crop": crop,
            "disease_name": disease_name,
            "confidence": top["confidence"],
            "is_healthy": db.is_healthy(top["class_name"]),
        },
    }


@app.post("/api/pipeline")
async def full_pipeline(
    image: UploadFile = File(...),
    expected_harvest_date: str | None = Form(None),
    organic_only: bool = Form(False),
):
    """FR-1~FR-4를 한 번에 수행하는 통합 파이프라인 (User Flow 재현)."""
    image_bytes = await image.read()
    try:
        predictions = classify_image(image_bytes, top_k=3)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="모델이 아직 학습되지 않았습니다. backend/model/train.py를 먼저 실행하세요.",
        )

    top = predictions[0]
    class_name = top["class_name"]
    confidence = top["confidence"]
    crop, disease_name = _crop_disease_name(class_name)
    healthy = db.is_healthy(class_name)

    explanation = generate_explanation(crop, disease_name, confidence, healthy)

    recommendation = None
    pls_results = None
    if not healthy:
        recommendation = db.recommend_products(class_name, organic_only=organic_only)
        if recommendation and expected_harvest_date:
            pls_results = check_pls_for_products(
                recommendation["products"], expected_harvest_date
            )

    low_confidence = confidence < 0.6

    case = None
    if not healthy:
        case = followup.create_case(crop, class_name)

    return {
        "predictions": predictions,
        "diagnosis": {
            "class_name": class_name,
            "crop": crop,
            "disease_name": disease_name,
            "confidence": confidence,
            "is_healthy": healthy,
            "low_confidence_warning": low_confidence,
        },
        "explanation": explanation,
        "recommendation": recommendation,
        "pls_results": pls_results,
        "followup_case": case,
    }


@app.post("/api/recommend")
def recommend(class_name: str = Form(...), organic_only: bool = Form(False)):
    """FR-3: 맞춤형 방제 추천."""
    rec = db.recommend_products(class_name, organic_only=organic_only)
    if rec is None:
        raise HTTPException(status_code=404, detail="해당 클래스에 대한 추천 데이터가 없습니다.")
    return rec


@app.post("/api/pls-check")
def pls_check(
    class_name: str = Form(...),
    expected_harvest_date: str = Form(...),
    organic_only: bool = Form(False),
):
    """FR-4: 안전기준(PLS) 자동 체크."""
    rec = db.recommend_products(class_name, organic_only=organic_only)
    if rec is None:
        raise HTTPException(status_code=404, detail="해당 클래스에 대한 추천 데이터가 없습니다.")
    results = check_pls_for_products(rec["products"], expected_harvest_date)
    return {"crop": rec["crop"], "disease_name": rec["disease_name"], "products": results}


@app.post("/api/followup/{case_id}")
async def followup_check(case_id: str, image: UploadFile = File(...)):
    """FR-5: 사후 확인 - 재사진 업로드 시 개선 여부 판단."""
    image_bytes = await image.read()
    case = followup.submit_followup_photo(case_id, image_bytes)
    if case is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 case_id입니다.")
    return case


@app.get("/api/followup/{case_id}")
def followup_get(case_id: str):
    case = followup.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="존재하지 않는 case_id입니다.")
    return case


app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
