from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth import require_admin_wallet

router = APIRouter(prefix="/api/admin", tags=["Administrative Control Panel"])
AUTO_APPROVER_ACTIVE = False


class ToggleScriptRequest(BaseModel):
    enable: bool


@router.get("/status")
async def get_admin_script_status(
    admin_wallet: str = Depends(require_admin_wallet),
):
    return {
        "auto_approver_running": AUTO_APPROVER_ACTIVE,
        "default_state": "DISABLED_BY_DEFAULT"
    }


@router.post("/toggle-approver")
async def toggle_automated_script(
    payload: ToggleScriptRequest,
    admin_wallet: str = Depends(require_admin_wallet),
):
    global AUTO_APPROVER_ACTIVE
    AUTO_APPROVER_ACTIVE = payload.enable
    state_string = "ACTIVATED" if AUTO_APPROVER_ACTIVE else "DEACTIVATED"
    print(f"[ADMIN ALERT] Automated distribution worker has been {state_string}.")
    return {
        "success": True,
        "auto_approver_running": AUTO_APPROVER_ACTIVE,
        "detail": f"Distribution automation loop shifted to {state_string} state."
    }
