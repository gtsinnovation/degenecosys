from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from urllib.parse import urlsplit
from prisma import Prisma
from app.database import db
from app.auth import get_current_wallet, require_admin_wallet
from app.engine import apply_xp_delta

router = APIRouter(prefix="/api/contests", tags=["Contests & Challenges"])


def as_utc(value: datetime) -> datetime:
    """Treat legacy timezone-naive database dates as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def get_db():
    if not db.is_connected():
        await db.connect()
    return db


class CreateContestRequest(BaseModel):
    title: str
    description: str
    prize_pool_dd: float = Field(ge=0, allow_inf_nan=False)
    start_date: datetime
    end_date: datetime


class SubmitChallengeRequest(BaseModel):
    contest_id: str
    submission_link: str = Field(min_length=1, max_length=2048)

    @field_validator("submission_link")
    @classmethod
    def require_http_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Submission link must be an absolute HTTP or HTTPS URL.")
        return value


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
    start_date = as_utc(payload.start_date)
    end_date = as_utc(payload.end_date)
    if end_date <= start_date:
        raise HTTPException(status_code=400, detail="Contest end date must be after its start date.")

    try:
        contest = await client.contest.create(
            data={
                "title": payload.title,
                "description": payload.description,
                "prizePoolDd": payload.prize_pool_dd,
                "startDate": start_date,
                "endDate": end_date,
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

    now = datetime.now(timezone.utc)
    start_date = as_utc(contest.startDate)
    end_date = as_utc(contest.endDate)
    if end_date <= start_date:
        raise HTTPException(status_code=400, detail="Targeted challenge has an invalid schedule.")
    if now < start_date or now >= end_date:
        raise HTTPException(status_code=400, detail="Targeted challenge is outside its submission window.")

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
    requested_status = payload.status.upper()
    if requested_status not in {"APPROVED", "REJECTED", "WINNER"}:
        raise HTTPException(status_code=400, detail="Unsupported payout status.")

    is_winner = requested_status == "WINNER"
    try:
        async with client.tx() as transaction:
            submission = await transaction.contestsubmission.find_unique(
                where={"id": payload.submission_id}
            )
            if not submission:
                raise HTTPException(status_code=404, detail="Submission record not found.")

            current_status = submission.status.upper()
            if current_status == "WINNER" and not is_winner:
                raise HTTPException(
                    status_code=409,
                    detail="A winning submission cannot be changed to another status."
                )

            # Preserve a previously recorded signature when this winner request is retried.
            tx_signature = payload.tx_signature or submission.txSignature
            reward_paid = bool(tx_signature) if is_winner else False
            should_award_xp = False

            if is_winner and current_status == "WINNER":
                # Older winner rows predate xpAwarded; mark them handled without
                # granting the XP again.
                await transaction.contestsubmission.update(
                    where={"id": submission.id},
                    data={
                        "xpAwarded": True,
                        "rewardPaid": reward_paid,
                        "txSignature": tx_signature
                    }
                )
            elif is_winner:
                # Claim the one-time award with a conditional update. Concurrent
                # requests can only transition this row once.
                claimed = await transaction.contestsubmission.update_many(
                    where={
                        "id": submission.id,
                        "xpAwarded": False,
                        "status": {"not": "WINNER"}
                    },
                    data={
                        "status": "WINNER",
                        "xpAwarded": True,
                        "rewardPaid": reward_paid,
                        "txSignature": tx_signature
                    }
                )
                if claimed.count == 1:
                    should_award_xp = True
                else:
                    latest = await transaction.contestsubmission.find_unique(
                        where={"id": submission.id}
                    )
                    if not latest or latest.status.upper() != "WINNER":
                        raise HTTPException(
                            status_code=409,
                            detail="Submission payout changed concurrently; retry the request."
                        )
                    tx_signature = payload.tx_signature or latest.txSignature
                    reward_paid = bool(tx_signature)
                    await transaction.contestsubmission.update(
                        where={"id": submission.id},
                        data={"rewardPaid": reward_paid, "txSignature": tx_signature}
                    )
            else:
                changed = await transaction.contestsubmission.update_many(
                    where={
                        "id": submission.id,
                        "xpAwarded": False,
                        "status": {"not": "WINNER"}
                    },
                    data={
                        "status": requested_status,
                        "rewardPaid": False,
                        "txSignature": payload.tx_signature
                    }
                )
                if changed.count != 1:
                    raise HTTPException(
                        status_code=409,
                        detail="Submission payout changed concurrently; refresh before retrying."
                    )

            if should_award_xp:
                # Use the same compare-and-set path as votes so concurrent XP
                # sources cannot overwrite each other or leave the rank tier stale.
                await apply_xp_delta(transaction, submission.warriorId, 25)

            updated_sub = await transaction.contestsubmission.find_unique(
                where={"id": submission.id}
            )

        return {
            "success": True,
            "submission_id": updated_sub.id,
            "status": updated_sub.status,
            "reward_confirmed": updated_sub.rewardPaid
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to finalize submission payout."
        ) from exc
