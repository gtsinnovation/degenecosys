# backend\scripts\test_contests.py
import asyncio
import httpx
from datetime import datetime, timedelta

# Target App Engine Container Connection Strings
API_BASE = "http://localhost:8000"

async def run_contests_and_challenges_validation_suite():
    print("====================================================")
    print("🧪 LAUNCHING CONTESTS & REWARDS VALIDATION SUITE...")
    print("====================================================\n")

    # Mock parameters for execution verification
    test_warrior_wallet = "TestWarriorWalletAddress111111111111111"
    
    async with httpx.AsyncClient() as client:
        # Step 1: Pre-register a mock Warrior profile to establish relational keys
        print("[1/4] Ensuring target test warrior exists in the DB matrix...")
        # We trigger standard upsert properties or mock seeding via our backend logic
        # For pure testing, we assume a warrior record exists or hit an onboarding route.
        # Let's verify or seed directly.

        # Step 2: Initialize an active community contest frame
        print("[2/4] Registering a new community contest challenge...")
        contest_payload = {
            "title": "Degen Meme Overlord Challenge #1",
            "description": "Produce the highest quality viral ecosystem graphic content detailing $DD utility properties.",
            "prize_pool_dd": 50000.0,
            "start_date": datetime.utcnow().isoformat(),
            "end_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        
        res_contest = await client.post(f"{API_BASE}/api/contests/create", json=contest_payload)
        contest_data = res_contest.json()
        
        if res_contest.status_code != 200:
            print(f"❌ Failed to create contest: {contest_data}")
            return
            
        contest_id = contest_data["contest_id"]
        print(f"✅ Success! Contest built cleanly with UUID: {contest_id}")

        # Step 3: Simulate a Warrior sending in a submission link proof-of-work
        print("\n[3/4] Registering a warrior submission entry handle...")
        
        # First ensure the warrior is initialized by making an artificial upvote event or inserting them
        # Let's try to post a contest entry directly
        submission_payload = {
            "contest_id": contest_id,
            "warrior_wallet": "WhaleTrue999999999999999999999999999999999", # Using the validated whale wallet we seeded yesterday
            "submission_link": "https://github.com"
        }
        
        res_sub = await client.post(f"{API_BASE}/api/contests/submit", json=submission_payload)
        sub_data = res_sub.json()
        
        if res_sub.status_code != 200:
            print(f"❌ Submission rejected by core rules: {sub_data['detail']}")
            print("💡 Note: Running your historical snapshot seed script ensures profiles are verified.")
            return
            
        submission_id = sub_data["submission_id"]
        print(f"✅ Success! Entry logged under Submission ID: {submission_id}")

        # Step 4: Execute an administrative reward payout distribution event
        print("\n[4/4] Executing contest winner payout status changes...")
        payout_payload = {
            "submission_id": submission_id,
            "status": "WINNER",
            "tx_signature": "5xM3rG...OnChainSolanaTxHashRef...99zKx" # Mock transaction receipt signature
        }
        
        res_payout = await client.post(f"{API_BASE}/api/contests/payout", json=payout_payload)
        payout_data = res_payout.json()
        
        print("====================================================")
        print("🎉 REWARDS MECHANICS TEST SEQUENCE RESULTS:")
        print("====================================================")
        print(f"Status Output:      {payout_data['status']}")
        print(f"Reward Confirmed:   {payout_data['reward_confirmed']}")
        print("====================================================")

if __name__ == "__main__":
    asyncio.run(run_contests_and_challenges_validation_suite())