"""Reserved routes for persisted evaluation artifacts."""

from fastapi import APIRouter


router = APIRouter(prefix="/evaluation", tags=["evaluation"])
