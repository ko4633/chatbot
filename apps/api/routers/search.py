"""Search: fast keyword lookup over already-stored intelligence. Deliberately
NOT the same endpoint as /research (docs/MASTER_SPEC.md §29) — this never
triggers new collection or multi-step analysis, it only queries what OMNIS
already knows.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from packages.db.models.product import Product, ProductVariant

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(q: str = Query(..., min_length=1), db: Session = Depends(get_db)) -> dict:
    pattern = f"%{q}%"
    variant_matches = (
        db.query(ProductVariant).filter(ProductVariant.title_raw.ilike(pattern)).limit(50).all()
    )
    product_ids = {v.product_id for v in variant_matches if v.product_id is not None}
    product_matches = (
        db.query(Product).filter(Product.canonical_title.ilike(pattern)).limit(50).all()
    )
    product_ids |= {p.id for p in product_matches}

    products = [db.get(Product, pid) for pid in product_ids]
    return {
        "query": q,
        "products": [
            {"id": str(p.id), "canonical_title": p.canonical_title, "category": p.category}
            for p in products
            if p is not None
        ],
    }
