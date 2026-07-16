# Vertex AI AutoML 이미지 분류용 데이터 가져오기 CSV 생성 스크립트 (로컬 PC PowerShell에서 실행)
#
# 사용법:
#   1) gcloud auth login / gcloud config set project disease-plant 가 이미 되어 있어야 함
#   2) PowerShell에서:  .\build_automl_import_csv.ps1
#   3) 생성된 automl_import.csv 를 버킷에 업로드:
#        gsutil cp automl_import.csv gs://disease_plant_full/automl_import.csv
#   4) Vertex AI 콘솔 > Datasets > Create > Image > Single-label classification
#      > Import files from Cloud Storage > gs://disease_plant_full/automl_import.csv 지정
#
# ML_USE(TRAIN/VALIDATION/TEST) 컬럼은 일부러 비워둠 -> Vertex AI가 자동으로
# train/validation/test를 8:1:1로 나눠줌 (기존 train/valid 폴더 구성을 그대로 신뢰하기보다
# AutoML 표준 자동 분할을 쓰는 게 안전함).

$Bucket = "gs://disease_plant_full"
$TrainPrefix = "archive/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)/train"
$ValidPrefix = "archive/New Plant Diseases Dataset(Augmented)/New Plant Diseases Dataset(Augmented)/valid"
$OutFile = "automl_import.csv"

function Get-Rows {
    param([string]$Prefix)

    $lines = gsutil ls -r "$Bucket/$Prefix/**"
    foreach ($line in $lines) {
        $line = $line.Trim()
        if (-not $line -or $line.EndsWith('/') -or $line.StartsWith('CommandException')) { continue }
        $parts = $line -split '/'
        $label = $parts[$parts.Length - 2]
        "$line,$label"
    }
}

Write-Host "train 목록 수집 중..."
$trainRows = Get-Rows -Prefix $TrainPrefix
Write-Host "valid 목록 수집 중..."
$validRows = Get-Rows -Prefix $ValidPrefix

$all = $trainRows + $validRows
$all | Out-File -FilePath $OutFile -Encoding utf8

Write-Host "완료: $OutFile ($($all.Count) rows)"
