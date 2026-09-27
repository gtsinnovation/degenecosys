# backend/app/engine.py
import datetime
from prisma import Prisma

TOTAL_SUPPLY = 1_000_000_000.0
WHALE_THRESHOLD_PERCENT = 2.0
REQUIRED_DAYS = 30

async def verify_whale_booster_status(db: Prisma, wallet_address: str) -> bool:
    """
    Checks if a wallet has held more than 2% of total supply continuously for 30+ days.
    """
    today = datetime.date.today()
    thirty_days_ago = today - datetime.timedelta(days=REQUIRED_DAYS)
    
    # Fetch snapshots across our 30-day window
    snapshots = await db.walletbalancesnapshot.find_many(
        where={
            "walletAddress": wallet_address,
            "snapshotDate": {
                "gte": datetime.datetime.combine(thirty_days_ago, datetime.time.min),
                "lte": datetime.datetime.combine(today, datetime.time.max)
            }
        }
    )
    
    # Filter snapshot history for daily continuous compliance
    valid_days = set()
    for snap in snapshots:
        if snap.circulatingPercentage >= WHALE_THRESHOLD_PERCENT:
            valid_days.add(snap.snapshotDate.date())
            
    return len(valid_days) >= REQUIRED_DAYS

async def process_vote_action(db: Prisma, voter_wallet: str, target_wallet: str, is_upvote: bool) -> dict:
    """
    Executes a community upvote or downvote event. Calculates whale booster multipliers,
    updates relative database tables, and enforces hard limits on warrior XP state tracking.
    """
    voter = await db.warrior.find_unique(where={"walletAddress": voter_wallet})
    target = await db.warrior.find_unique(where={"walletAddress": target_wallet})
    
    if not voter or not target:
        return {"success": False, "detail": "Warrior profile records not found."}
    
    if voter.id == target.id:
        return {"success": False, "detail": "Self-voting actions are prohibited."}

    # Verify if voter holds active Veto-Booster capabilities
    has_booster = await verify_whale_booster_status(db, voter_wallet)
    vote_weight = 5.0 if has_booster else 1.0
    xp_delta = int(1 * vote_weight) if is_upvote else int(-1 * vote_weight)

    # Upsert the vote record to prevent duplicate manipulation
    try:
        await db.communityupvote.upsert(
            where={
                "voterId_targetId": {
                    "voterId": voter.id,
                    "targetId": target.id
                }
            },
            data={
                "create": {"voterId": voter.id, "targetId": target.id, "weight": vote_weight},
                "update": {"weight": vote_weight}
            }
        )
    except Exception:
        return {"success": False, "detail": "Database unique validation constraint blocked voting action."}

    # Fetch and process targets live XP data
    target_xp_record = await db.warriorxp.find_unique(where={"warriorId": target.id})
    current_xp = target_xp_record.currentXp if target_xp_record else 0
    
    # Calculate new XP and clamp between the programmatic roadmap limits (-100 to +100)
    new_xp = max(-100, min(100, current_xp + xp_delta))
    
    # Assign tier based on dynamic XP milestones
    rank_tier = 1
    if new_xp >= 100:
        rank_tier = 3  # Maximum ascended status
    elif new_xp > 0:
        rank_tier = 2

    await db.warriorxp.upsert(
        where={"warriorId": target.id},
        data={
            "create": {"warriorId": target.id, "currentXp": new_xp, "rankTier": rank_tier},
            "update": {"currentXp": new_xp, "rankTier": rank_tier}
        }
    )

    return {
        "success": True,
        "voter_has_booster": has_booster,
        "target_new_xp": new_xp,
        "target_tier": rank_tier
    }