from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from prisma import Prisma
from app.auth import get_current_wallet

router = APIRouter(prefix="/api/warrior", tags=["Warrior Identity & Profiles"])
db = Prisma()


async def get_db():
    if not db.is_connected():
        await db.connect()
    return db


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(None, max_length=50)
    bio: Optional[str] = Field(None, max_length=160)
    banner_url: Optional[str] = None
    avatar_url: Optional[str] = None
    twitter_handle: Optional[str] = Field(None, max_length=15)


@router.get("/{wallet_address}/profile")
async def get_complete_warrior_profile(
    wallet_address: str, client: Prisma = Depends(get_db)
):
    warrior = await client.warrior.find_unique(
        where={"walletAddress": wallet_address},
        include={"xp": True, "earnedBadges": {"include": {"badge": True}}}
    )
    if not warrior:
        raise HTTPException(status_code=404, detail="Warrior profile not found.")

    return {
        "wallet_address": warrior.walletAddress,
        "username": warrior.username,
        "bio": warrior.bio,
        "avatar_url": warrior.avatarUrl,
        "banner_url": warrior.bannerUrl,
        "twitter_handle": warrior.twitterHandle,
        "current_xp": warrior.xp.currentXp if warrior.xp else 0,
        "rank_tier": warrior.xp.rankTier if warrior.xp else 1,
        "unlocked_badges": [
            {
                "name": eb.badge.name,
                "description": eb.badge.description,
                "icon_svg": eb.badge.iconSvg,
                "unlocked_at": eb.unlockedAt
            } for eb in warrior.earnedBadges
        ]
    }


@router.post("/{wallet_address}/update")
async def update_warrior_profile(
    wallet_address: str,
    payload: UpdateProfileRequest,
    client: Prisma = Depends(get_db),
    authenticated_wallet: str = Depends(get_current_wallet),
):
    if wallet_address != authenticated_wallet:
        raise HTTPException(status_code=403, detail="A wallet may only update its own profile.")

    warrior = await client.warrior.find_unique(where={"walletAddress": authenticated_wallet})
    if not warrior:
        raise HTTPException(status_code=404, detail="Warrior profile not found.")

    update_data = payload.model_dump(exclude_unset=True)
    try:
        updated_warrior = await client.warrior.update(
            where={"walletAddress": authenticated_wallet},
            data=update_data
        )
        return {
            "success": True,
            "wallet_address": updated_warrior.walletAddress,
            "updated_fields": list(update_data.keys())
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Profile update failed.") from exc
