from fastapi import APIRouter, Depends, HTTPException
from app.auth import require_admin_wallet

router = APIRouter(prefix="/api/admin", tags=["Administrative Control Panel"])


@router.get("/status")
async def get_admin_script_status(
    admin_wallet: str = Depends(require_admin_wallet),
):
    return {
        "auto_approver_running": False,
        "default_state": "NOT_IMPLEMENTED"
    }


@router.post("/toggle-approver")
async def toggle_automated_script(
    admin_wallet: str = Depends(require_admin_wallet),
):
    raise HTTPException(
        status_code=501,
        detail="The automated approval worker is not implemented."
    )
