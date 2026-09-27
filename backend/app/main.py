from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prisma import Prisma
from app.engine import process_vote_action, verify_whale_booster_status
from app.contests import router as contests_router
from app.admin import router as admin_router
from app.profiles import router as profiles_router # 👈 ADD THIS IMPORT STATEMENT

app = FastAPI(title="Degen Ecosystem Application Core Engine", version="1.0.0")
db = Prisma()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(contests_router)
app.include_router(admin_router)
app.include_router(profiles_router) # 👈 ADD THIS ROUTER REGISTER LINE

@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

class VoteRequest(BaseModel):
    voter_wallet: str
    target_wallet: str
    is_upvote: bool

@app.post("/api/interact/vote")
async def register_warrior_vote(payload: VoteRequest):
    result = await process_vote_action(
        db, payload.voter_wallet, payload.target_wallet, payload.is_upvote
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["detail"])
    return result

@app.get("/api/leaderboard")
async def get_warrior_leaderboard(limit: int = 50):
    leaderboard = await db.warriorxp.find_many(
        order={"currentXp": "desc"},
        take=limit,
        include={"warrior": True}
    )
    return [
        {
            "username": item.warrior.username,
            "wallet_address": item.warrior.walletAddress,
            "current_xp": item.currentXp,
            "rank_tier": item.rankTier
        }
        for item in leaderboard
    ]

@app.get("/api/warrior/{wallet_address}/booster-status")
async def check_booster_eligibility(wallet_address: str):
    is_whale = await verify_whale_booster_status(db, wallet_address)
    return {"wallet_address": wallet_address, "has_veto_booster": is_whale}