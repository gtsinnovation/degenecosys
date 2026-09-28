from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from prisma import Prisma
from app.auth import get_current_wallet, require_admin_wallet

router = APIRouter(prefix="/api/contests", tags=["Contests & Challenges"])
db = Prisma()


async def get_db():
    if not db.is_connected():
        await db.connect()
    return db


class CreateContestRequest(BaseModel):
    title: str
    description: str
    prize_pool_dd: float
    start_date: datetime
    end_date: datetime


class SubmitChallengeRequest(BaseModel):
    contest_id: str
    submission_link: str


class ProcessPayoutRequest(BaseModel):
    submission_id: str
    status: str
    tx_signature: str | None = None


@router.post("/create")
async def create_new_contest(
    payload: CreateContestRequest,
    client: Prisma = Depends(get_db),
    admin_wallet: str = Depends(require_admin_wallet),
):
    try:
        contest = await client.contest.create(
            data={
                "title": payload.title,
                "description": payload.description,
                "prizePoolDd": payload.prize_pool_dd,
                "startDate": payload.start_date,
                "endDate": payload.end_date,
                "isActive": True
            }
        )
        return {"success": True, "contest_id": contest.id, "title": contest.title}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to create contest.") from exc


@router.post("/submit")
async def submit_challenge_entry(
    payload: SubmitChallengeRequest,
    client: Prisma = Depends(get_db),
    warrior_wallet: str = Depends(get_current_wallet),
):
    warrior = await client.warrior.find_unique(where={"walletAddress": warrior_wallet})
    if not warrior:
        raise HTTPException(status_code=404, detail="Warrior identity profile not found.")

    contest = await client.contest.find_unique(where={"id": payload.contest_id})
    if not contest or not contest.isActive:
        raise HTTPException(status_code=400, detail="Targeted challenge is inactive or expired.")

    try:
        submission = await client.contestsubmission.create(
            data={
                "contestId": payload.contest_id,
                "warriorId": warrior.id,
                "submissionLink": payload.submission_link,
                "status": "PENDING"
            }
        )
        return {"success": True, "submission_id": submission.id, "status": "PENDING"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to record submission.") from exc


@router.post("/payout")
async def process_submission_payout(
    payload: ProcessPayoutRequest,
    client: Prisma = Depends(get_db),
    admin_wallet: str = Depends(require_admin_wallet),
):
    if payload.status.upper() not in {"APPROVED", "REJECTED", "WINNER"}:
        raise HTTPException(status_code=400, detail="Unsupported payout status.")

    submission = await client.contestsubmission.find_unique(where={"id": payload.submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission record not found.")

    is_winner = payload.status.upper() == "WINNER"
    reward_paid = bool(is_winner and payload.tx_signature)

    try:
        updated_sub = await client.contestsubmission.update(
            where={"id": payload.submission_id},
            data={
                "status": payload.status.upper(),
                "rewardPaid": reward_paid,
                "txSignature": payload.tx_signature
            }
        )

        if is_winner:
            target_xp = await client.warriorxp.find_unique(where={"warriorId": submission.warriorId})
            current_xp = target_xp.currentXp if target_xp else 0
            new_xp = max(-100, min(100, current_xp + 25))
            await client.warriorxp.upsert(
                where={"warriorId": submission.warriorId},
                data={
                    "create": {"warriorId": submission.warriorId, "currentXp": new_xp, "rankTier": 2 if new_xp > 0 else 1},
                    "update": {"currentXp": new_xp}
                }
            )

        return {
            "success": True,
            "submission_id": updated_sub.id,
            "status": updated_sub.status,
            "reward_confirmed": reward_paid
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to finalize submission payout.") from exc
