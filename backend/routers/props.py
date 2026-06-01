import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))

from fastapi import APIRouter
from typing import Optional
from props_model import analyze_hit_prop

router = APIRouter()


@router.get("/mlb/hit/{batter_id}")
async def mlb_hit_prop(batter_id: int, pitcher_id: int, book_line: Optional[int] = None):
    return await analyze_hit_prop(batter_id, pitcher_id, book_line)
