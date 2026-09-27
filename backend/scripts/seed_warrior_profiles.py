# seed_warrior_profiles.py
import asyncio
import datetime
from prisma import Prisma

VALID_WHALE_WALLET = "WhaleTrue999999999999999999999999999999999"
PAPERHANDS_WALLET  = "PaperDips111111111111111111111111111111111"

async def seed_rich_warrior_profiles():
    """
    Populates advanced biographical attributes and attaches mock earned badges
    to existing warrior entries to verify frontend data mapping operations.
    """
    db = Prisma()
    await db.connect()
    
    print(f"[{datetime.datetime.now()}] Running Rich Profile Identity Seed Routine...")

    # 1. INITIALIZE THE ECOSYSTEM BADGE INVENTORY SYSTEM
    print("Seeding badge catalog types into storage...")
    
    badge_alpha = await db.badge.upsert(
        where={"name": "Ascended Warrior"},
        data={
            "create": {
                "name": "Ascended Warrior",
                "description": "Accumulated maximum reputation parameters hitting +100 total XP metrics.",
                "iconSvg": "⚡",
                "xpRequirementThreshold": 100
            },
            "update": {}
        }
    )
    
    badge_whale = await db.badge.upsert(
        where={"name": "Degen Whale"},
        data={
            "create": {
                "name": "Degen Whale",
                "description": "Verified governor holding greater than 2% of total supply continuously for 30+ days.",
                "iconSvg": "🐋",
                "xpRequirementThreshold": 0
            },
            "update": {}
        }
    )

    badge_trophy = await db.badge.upsert(
        where={"name": "Challenge Overlord"},
        data={
            "create": {
                "name": "Challenge Overlord",
                "description": "Successfully won an official community graphic or code engineering puzzle challenge.",
                "iconSvg": "🏆",
                "xpRequirementThreshold": 0
            },
            "update": {}
        }
    )

    # 2. ENHANCE ALPHA WHALE WARRIOR PROFILE META DATA
    print("Updating Alpha Whale biographical profile variables...")
    whale = await db.warrior.find_unique(where={"walletAddress": VALID_WHALE_WALLET})
    if whale:
        await db.warrior.update(
            where={"id": whale.id},
            data={
                "bio": "Lead Smart Contract Architect. Long-term $DD Governor. Alpha Squad Commander.",
                "bannerUrl": "https://unsplash.com",
                "twitterHandle": "AlphaWhaleDD"
            }
        )
        
        # Link mock unlocked achievement relationships to the whale
        # Clear out any old records first to avoid unique key crashes
        await db.warriorearnedbadge.delete_many(where={"warriorId": whale.id})
        
        await db.warriorearnedbadge.create(data={"warriorId": whale.id, "badgeId": badge_whale.id})
        await db.warriorearnedbadge.create(data={"warriorId": whale.id, "badgeId": badge_trophy.id})

    # 3. ENHANCE PAPERHANDS SQUIRE PROFILE META DATA
    print("Updating Paperhands biographical profile variables...")
    paper = await db.warrior.find_unique(where={"walletAddress": PAPERHANDS_WALLET})
    if paper:
        await db.warrior.update(
            where={"id": paper.id},
            data={
                "bio": "Ecosystem Explorer. Swing trader. Building out frontend interface modules.",
                "bannerUrl": "https://unsplash.com",
                "twitterHandle": "PaperSquire"
            }
        )
        await db.warriorearnedbadge.delete_many(where={"warriorId": paper.id})
        await db.warriorearnedbadge.create(data={"warriorId": paper.id, "badgeId": badge_alpha.id})

    print("\n✅ PROFILE BIOGRAPHIES AND BADGES SEEDED FLUSH WITH SUCCESS.")
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(seed_rich_warrior_profiles())