# \backend\app\admin.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from prisma import Prisma

router = APIRouter(prefix="/api/admin", tags=["Administrative Control Panel"])
db = Prisma()

# Global state memory tracking the status of our automated distribution script
# Set to False (Off) by default per architectural instruction
AUTO_APPROVER_ACTIVE = False

async def get_db():
    if not db.is_connected():
        await db.connect()
    return db

class ToggleScriptRequest(BaseModel):
    enable: bool

@router.get("/status")
async def get_admin_script_status():
    """
    Exposes the active operational status of the background rewards distribution script.
    """
    return {
        "auto_approver_running": AUTO_APPROVER_ACTIVE,
        "default_state": "DISABLED_BY_DEFAULT"
    }

@router.post("/toggle-approver")
async def toggle_automated_script(payload: ToggleScriptRequest):
    """
    Modifies the live running state of the automated rewards approval background loop.
    """
    global AUTO_APPROVER_ACTIVE
    AUTO_APPROVER_ACTIVE = payload.enable
    
    state_string = "ACTIVATED" if AUTO_APPROVER_ACTIVE else "DEACTIVATED"
    print(f"[ADMIN ALERT] Automated distribution worker has been programmatically {state_string}.")
    
    return {
        "success": True,
        "auto_approver_running": AUTO_APPROVER_ACTIVE,
        "detail": f"Distribution automation loop successfully shifted to {state_string} state."
    }