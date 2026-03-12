"""
API route handlers.
"""

from fastapi import APIRouter, HTTPException
from ..services import analyze_service, organize_service
from ..models import AnalyzeRequest, OrganizeRequest, AnalyzeResult, OrganizeResult

router = APIRouter(prefix="/api/v1", tags=["api"])


@router.post("/analyze", response_model=AnalyzeResult)
async def analyze_endpoint(request: AnalyzeRequest):
    """
    Analyze a music library and return genre distribution statistics.
    """
    try:
        result = analyze_service(
            source=request.source,
            level=request.level,
            limit=request.limit,
            exclude_dir=request.exclude_dir,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/organize", response_model=OrganizeResult)
async def organize_endpoint(request: OrganizeRequest):
    """
    Organize files into genre-based folder structure.
    """
    try:
        result = organize_service(
            source=request.source,
            destination=request.destination,
            mode=request.mode,
            level=request.level,
            profile=request.profile,
            dry_run=request.dry_run,
            skip_existing=request.skip_existing,
            skip_unknown_only=request.skip_unknown_only,
            on_collision=request.on_collision,
            limit=request.limit,
            exclude_dir=request.exclude_dir,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Organization failed: {str(e)}")
