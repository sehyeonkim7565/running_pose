#!/usr/bin/env bash
# 로컬 PC에서 실행: 8.7만 장 원본 이미지를 GCS 버킷(disease_plant_full)에 업로드
#
# 사용법:
#   1) 아래 LOCAL_DATASET_DIR을 실제 이미지가 있는 로컬 폴더 경로로 수정
#      (클래스별 하위 폴더 구조 예: LOCAL_DATASET_DIR/Tomato___healthy/*.jpg)
#   2) gcloud CLI 설치 및 인증
#        gcloud auth login
#        gcloud config set project disease-plant
#      (서비스 계정 키를 쓰는 경우)
#        gcloud auth activate-service-account --key-file=/path/to/key.json
#        gcloud config set project disease-plant
#   3) 실행: bash upload_to_gcs.sh

set -euo pipefail

LOCAL_DATASET_DIR="${1:-$HOME/plantvillage_full}"
BUCKET="gs://disease_plant_full"

if [ ! -d "$LOCAL_DATASET_DIR" ]; then
  echo "폴더를 찾을 수 없습니다: $LOCAL_DATASET_DIR"
  echo "사용법: bash upload_to_gcs.sh /path/to/local/dataset"
  exit 1
fi

echo "업로드 대상: $LOCAL_DATASET_DIR -> $BUCKET"
echo "이미지 수(참고): $(find "$LOCAL_DATASET_DIR" -type f | wc -l)"

# -m: 병렬 업로드, rsync: 중단 후 재실행 시 이미 올라간 파일은 건너뜀(재개 가능)
gsutil -m rsync -r "$LOCAL_DATASET_DIR" "$BUCKET"

echo "업로드 완료."
