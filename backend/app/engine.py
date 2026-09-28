# backend/app/engine.py
import datetime
from prisma import Prisma

TOTAL_SUPPLY = 1_000_000_000.0
WHALE_THRESHOLD_PERCENT = 2.0
REQUIRED_DAYS = 30


async def verify_whale_booster_status(db: Prisma, wallet_address: str) -> bool:
    """
    Requires a qualifying daily snapshot on every date spanning 30 elapsed days.
    """
    today = datetime.date.today()
    period_start = today - datetime.timedelta(days=REQUIRED_DAYS)

    snapshots = await db.walletbalancesnapshot.find_many(
        where={
            "walletAddress": wallet_address,
            "snapshotDate": {
                "gte": datetime.datetime.combine(period_start, datetime.time.min),
                "lte": datetime.datetime.combine(today, datetime.time.max)
            }
        }
    )

    valid_days = {
        snap.snapshotDate.date()
        for snap in snapshots
        if snap.circulatingPercentage >= WHALE_THRESHOLD_PERCENT
    }
    required_dates = {
        period_start + datetime.timedelta(days=offset)
        for offset in range(REQUIRED_DAYS + 1)
    }
    return required_dates.issubset(valid_days)


async def apply_xp_delta(
    db: Prisma, warrior_id: str, xp_delta: int
) -> tuple[int, int]:
    """Apply a bounded XP change with compare-and-set retries.

    The caller should use this inside the same transaction as the event that
    grants XP. The conditional update keeps concurrent XP sources from
    overwriting one another and updates the rank tier with the XP value.
    """
    xp_record = await db.warriorxp.find_unique(where={"warriorId": warrior_id})
    if xp_record is None:
        await db.warriorxp.create(
            data={"warriorId": warrior_id, "currentXp": 0, "rankTier": 1}
        )

    for _ in range(10):
        xp_record = await db.warriorxp.find_unique(where={"warriorId": warrior_id})
        if xp_record is None:
            raise RuntimeError("Warrior XP record disappeared during update.")

        current_xp = xp_record.currentXp
        new_xp = max(-100, min(100, current_xp + xp_delta))
        if new_xp >= 100:
            rank_tier = 3
        elif new_xp > 0:
            rank_tier = 2
        else:
            rank_tier = 1

        updated = await db.warriorxp.update_many(
            where={"warriorId": warrior_id, "currentXp": current_xp},
            data={"currentXp": new_xp, "rankTier": rank_tier}
        )
        if updated.count == 1:
            return new_xp, rank_tier

    raise RuntimeError("Could not update warrior XP after concurrent changes.")


async def process_vote_action(
    db: Prisma, voter_wallet: str, target_wallet: str, is_upvote: bool
) -> dict:
    """
    Records one vote per voter/target pair and applies its XP change atomically.
    The unique voter/target key prevents duplicate votes, and compare-and-set retries
    prevent concurrent votes from overwriting one another's XP changes.
    """
    voter = await db.warrior.find_unique(where={"walletAddress": voter_wallet})
    target = await db.warrior.find_unique(where={"walletAddress": target_wallet})

    if not voter or not target:
        return {"success": False, "detail": "Warrior profile records not found."}

    if voter.id == target.id:
        return {"success": False, "detail": "Self-voting actions are prohibited."}

    has_booster = await verify_whale_booster_status(db, voter_wallet)
    vote_weight = 5.0 if has_booster else 1.0
    xp_delta = int(vote_weight) if is_upvote else -int(vote_weight)
    vote_key = {
        "voterId_targetId": {
            "voterId": voter.id,
            "targetId": target.id
        }
    }

    try:
        # Inserting the unique vote and changing XP in one transaction prevents both
        # retries and concurrent duplicate requests from applying XP more than once.
        async with db.tx() as transaction:
            await transaction.communityupvote.create(
                data={
                    "voterId": voter.id,
                    "targetId": target.id,
                    "weight": vote_weight
                }
            )

            # XP writes share one conditional update path with contest awards.
            new_xp, rank_tier = await apply_xp_delta(
                transaction, target.id, xp_delta
            )
    except Exception:
        try:
            existing_vote = await db.communityupvote.find_unique(where=vote_key)
        except Exception:
            return {"success": False, "detail": "Vote could not be recorded. Please retry."}
        if existing_vote:
            return {
                "success": False,
                "detail": "This wallet has already voted for that warrior."
            }
        return {"success": False, "detail": "Vote could not be recorded. Please retry."}

    return {
        "success": True,
        "voter_has_booster": has_booster,
        "target_new_xp": new_xp,
        "target_tier": rank_tier
    }
