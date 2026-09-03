"""Reserved routes for gain-importance and SHAP artifacts."""

from fastapi import APIRouter


router = APIRouter(prefix="/interpretation", tags=["interpretation"])
