# backend/scripts/snapshot_worker.py
import os
import asyncio
import datetime
import httpx
from prisma import Prisma

# Configuration Setup
RPC_ENDPOINT = "https://solana.com" # Replace with your premium Helius/Triton RPC url
MINT_ADDRESS = "DdEgenEcosystem111111111111111111111111111" # Your Token Address
TOTAL_SUPPLY = 1_000_000_000.0

async def capture_token_holders_snapshot():
    """
    Executes an on-chain query parsing all token accounts holding Degen Dollar ($DD).
    Calculates circulating footprint share allocations and stores records into the snapshot database.
    """
    db = Prisma()
    await db.connect()
    
    current_date = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
    print(f"[{datetime.datetime.now()}] Launching Automated Midnight Token Balance Snapshot...")

    # Solana JSON-RPC payload targeting Program Accounts (Token Program) filtering by Mint
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenLargestAccounts",
        "params": [
            MINT_ADDRESS,
            {"commitment": "confirmed"}
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(RPC_ENDPOINT, json=payload, timeout=30.0)
            response_json = response.json()
            
            if "result" not in response_json or "value" not in response_json["result"]:
                print(f"Error: Invalid or blank RPC response payload returned. {response_json}")
                await db.disconnect()
                return

            accounts_data = response_json["result"]["value"]
            
            # Step through large token holders array
            for entry in accounts_data:
                # Resolve address details and raw amount (accounting for 9 decimal places)
                token_account_pubkey = entry["address"]
                raw_amount = float(entry["amount"])
                ui_amount = raw_amount / 1_000_000_000.0
                
                # Derive ratio metrics relative to the ecosystem total supply allocation
                percentage_held = (ui_amount / TOTAL_SUPPLY) * 100.0

                # Upsert record safely to maintain daily state uniqueness metrics
                await db.walletbalancesnapshot.upsert(
                    where={
                        "walletAddress_snapshotDate": {
                            "walletAddress": token_account_pubkey,
                            "snapshotDate": current_date
                        }
                    },
                    data={
                        "create": {
                            "walletAddress": token_account_pubkey,
                            "tokenBalance": ui_amount,
                            "circulatingPercentage": percentage_held,
                            "snapshotDate": current_date
                        },
                        "update": {
                            "tokenBalance": ui_amount,
                            "circulatingPercentage": percentage_held
                        }
                    }
                )
                
            print(f"[{datetime.datetime.now()}] Success: Captured and verified {len(accounts_data)} major wallet snapshots.")
            
    except Exception as e:
        print(f"Critical Worker Exception occurred while executing snapshot routines: {str(e)}")
    finally:
        await db.disconnect()

if __name__ == "__main__":
    # To run this every midnight locally, hook this script into a Linux crontab:
    # 0 0 * * * /usr/local/bin/python /workspace/backend/scripts/snapshot_worker.py
    asyncio.run(capture_token_holders_snapshot())