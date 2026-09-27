import asyncio
import datetime
from prisma import Prisma

# Mock wallet addresses for testing
VALID_WHALE_WALLET = "WhaleTrue999999999999999999999999999999999"
PAPERHANDS_WALLET  = "PaperDips111111111111111111111111111111111"
TOTAL_SUPPLY = 1_000_000_000.0

async def seed_mock_snapshot_history():
    """
    Populates core profile tables and 30 days of consecutive historical 
    snapshot data directly into the database to satisfy relational foreign keys.
    """
    db = Prisma()
    await db.connect()
    
    print(f"[{datetime.datetime.now()}] Initializing local profile and history generator...")
    
    # 1. UPSERT CORE WARRIOR PROFILES SO OTHER SUB-SYSTEMS CAN BIND DATA
    print("Seeding core Warrior profiles into the database matrix...")
    whale_profile = await db.warrior.upsert(
        where={"walletAddress": VALID_WHALE_WALLET},
        data={
            "create": {"walletAddress": VALID_WHALE_WALLET, "username": "Alpha_Whale_Warrior"},
            "update": {"username": "Alpha_Whale_Warrior"}
        }
    )
    
    await db.warriorxp.upsert(
        where={"warriorId": whale_profile.id},
        data={"create": {"warriorId": whale_profile.id, "currentXp": 50, "rankTier": 2}, "update": {}}
    )

    paper_profile = await db.warrior.upsert(
        where={"walletAddress": PAPERHANDS_WALLET},
        data={
            "create": {"walletAddress": PAPERHANDS_WALLET, "username": "Paperhands_Squire"},
            "update": {"username": "Paperhands_Squire"}
        }
    )
    
    await db.warriorxp.upsert(
        where={"warriorId": paper_profile.id},
        data={"create": {"warriorId": paper_profile.id, "currentXp": 0, "rankTier": 1}, "update": {}}
    )

    # Clean out any old mock data snapshots to guarantee test purity
    await db.walletbalancesnapshot.delete_many(
        where={"walletAddress": {"in": [VALID_WHALE_WALLET, PAPERHANDS_WALLET]}}
    )

    print("Generating 30 days of programmatic snapshot data...")
    today = datetime.date.today()
    
    for day_offset in range(32):
        target_date = today - datetime.timedelta(days=day_offset)
        target_timestamp = datetime.datetime.combine(target_date, datetime.time.min)

        # Scenario A: Valid Whale Wallet stays at 2.5% continuously
        whale_balance = TOTAL_SUPPLY * 0.025
        whale_percentage = 2.50
        
        await db.walletbalancesnapshot.create(
            data={
                "walletAddress": VALID_WHALE_WALLET,
                "tokenBalance": whale_balance,
                "circulatingPercentage": whale_percentage,
                "snapshotDate": target_timestamp
            }
        )

        # Scenario B: Paperhands Wallet dips below 2% at day 15
        if day_offset <= 15:
            paper_balance = TOTAL_SUPPLY * 0.03
            paper_percentage = 3.00
        else:
            paper_balance = TOTAL_SUPPLY * 0.005
            paper_percentage = 0.50

        await db.walletbalancesnapshot.create(
            data={
                "walletAddress": PAPERHANDS_WALLET,
                "tokenBalance": paper_balance,
                "circulatingPercentage": paper_percentage,
                "snapshotDate": target_timestamp
            }
        )

    print("\n✅ PROFILE AND SNAPSHOT SEED COMPLETE!")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_mock_snapshot_history())