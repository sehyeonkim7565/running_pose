"""FR-4: PLS(안전사용기간) 자동 체크."""
from datetime import date, datetime


def check_pls(product: dict, expected_harvest_date: str, spray_date: str | None = None):
    """
    product: pesticide_db.json의 product dict (phi_days 포함)
    expected_harvest_date: "YYYY-MM-DD" 예상 수확일
    spray_date: "YYYY-MM-DD" 방제(살포) 예정일. 미지정 시 오늘 날짜 사용.
    """
    harvest = datetime.strptime(expected_harvest_date, "%Y-%m-%d").date()
    spray = (
        datetime.strptime(spray_date, "%Y-%m-%d").date() if spray_date else date.today()
    )
    days_until_harvest = (harvest - spray).days
    phi = product["phi_days"]

    if days_until_harvest < 0:
        status = "invalid"
        message = "수확 예정일이 살포일보다 이전입니다. 날짜를 다시 확인해주세요."
    elif days_until_harvest < phi:
        status = "violation"
        message = (
            f"경고: '{product['product_name']}'의 안전사용기간은 {phi}일이지만, "
            f"살포일로부터 수확 예정일까지 {days_until_harvest}일밖에 남지 않았습니다. "
            f"잔류허용기준 초과 위험이 있어 이 제품 사용을 권장하지 않습니다."
        )
    else:
        status = "safe"
        message = (
            f"안전: 살포일로부터 수확 예정일까지 {days_until_harvest}일이 남아 "
            f"안전사용기간({phi}일)을 충족합니다."
        )

    return {
        "status": status,  # safe | violation | invalid
        "message": message,
        "phi_days": phi,
        "days_until_harvest": days_until_harvest,
    }


def check_pls_for_products(products: list[dict], expected_harvest_date: str, spray_date: str | None = None):
    results = []
    for p in products:
        pls_result = check_pls(p, expected_harvest_date, spray_date)
        results.append({**p, "pls": pls_result})
    # 안전한 제품 우선 정렬 (safe > violation > invalid)
    order = {"safe": 0, "violation": 1, "invalid": 2}
    results.sort(key=lambda r: order.get(r["pls"]["status"], 3))
    return results
