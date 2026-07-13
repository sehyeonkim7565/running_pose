import json
import os

_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pesticide_db.json")

with open(_DATA_PATH, encoding="utf-8") as f:
    PESTICIDE_DB = json.load(f)


def get_disease_info(class_name: str):
    return PESTICIDE_DB["diseases"].get(class_name)


def is_healthy(class_name: str) -> bool:
    return class_name in PESTICIDE_DB.get("healthy_labels", [])


def recommend_products(class_name: str, organic_only: bool = False):
    info = get_disease_info(class_name)
    if not info:
        return None
    products = info["products"]
    if organic_only:
        products = [p for p in products if p["organic_allowed"]]
    return {
        "crop": info["crop"],
        "disease_name": info["disease_name"],
        "pathogen_type": info["pathogen_type"],
        "products": products,
    }
