# backend/scripts/snapshot_worker.py
import asyncio
import datetime
import os
from decimal import Decimal

import httpx
from prisma import Prisma

RPC_ENDPOINT = os.getenv("SOLANA_RPC_URL", "")
MINT_ADDRESS = os.getenv("DD_MINT_ADDRESS", "")
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOTAL_SUPPLY = Decimal("1000000000")
WHALE_THRESHOLD_PERCENT = Decimal("2")


async def rpc_call(client: httpx.AsyncClient, method: str, params: list):
    response = await client.post(
        RPC_ENDPOINT,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(f"Solana RPC {method} failed: {payload['error']}")
    if "result" not in payload:
        raise RuntimeError(f"Solana RPC {method} returned no result.")
    return payload["result"]


async def get_whale_balances(client: httpx.AsyncClient) -> dict[str, Decimal]:
    # getTokenLargestAccounts returns only 20 token accounts. Scan all classic
    # SPL token accounts for this mint so wallets outside that top 20 are included.
    accounts = await rpc_call(
        client,
        "getProgramAccounts",
        [
            TOKEN_PROGRAM_ID,
            {
                "encoding": "jsonParsed",
                "commitment": "confirmed",
                "filters": [
                    {"dataSize": 165},
                    {"memcmp": {"offset": 0, "bytes": MINT_ADDRESS}},
                ],
            },
        ],
    )

    owner_balances: dict[str, Decimal] = {}
    for account in accounts:
        try:
            info = account["account"]["data"]["parsed"]["info"]
            if info.get("mint") != MINT_ADDRESS:
                continue
            owner = info["owner"]
            amount = Decimal(info["tokenAmount"]["uiAmountString"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Could not parse an SPL token account returned by RPC.") from exc
        owner_balances[owner] = owner_balances.get(owner, Decimal("0")) + amount

    minimum_balance = TOTAL_SUPPLY * WHALE_THRESHOLD_PERCENT / Decimal("100")
    return {
        owner: balance
        for owner, balance in owner_balances.items()
        if balance >= minimum_balance
    }


async def capture_token_holders_snapshot():
    if not RPC_ENDPOINT or not MINT_ADDRESS:
        raise RuntimeError("SOLANA_RPC_URL and DD_MINT_ADDRESS must be configured.")

    db = Prisma()
    await db.connect()
    current_date = datetime.datetime.now(datetime.timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0, tzinfo=None
    )
    print(f"[{datetime.datetime.now(datetime.timezone.utc)}] Starting token holder snapshot.")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            whale_balances = await get_whale_balances(client)
            # Missing daily rows represent a balance below the 2% qualification
            # threshold, matching verify_whale_booster_status's fail-closed logic.
            if whale_balances:
                await db.walletbalancesnapshot.delete_many(
                    where={
                        "snapshotDate": current_date,
                        "walletAddress": {"notIn": list(whale_balances)},
                    }
                )
            else:
                await db.walletbalancesnapshot.delete_many(
                    where={"snapshotDate": current_date}
                )

            for owner, balance in whale_balances.items():
                percentage_held = (balance / TOTAL_SUPPLY) * Decimal("100")
                await db.walletbalancesnapshot.upsert(
                    where={
                        "walletAddress_snapshotDate": {
                            "walletAddress": owner,
                            "snapshotDate": current_date,
                        }
                    },
                    data={
                        "create": {
                            "walletAddress": owner,
                            "tokenBalance": float(balance),
                            "circulatingPercentage": float(percentage_held),
                            "snapshotDate": current_date,
                        },
                        "update": {
                            "tokenBalance": float(balance),
                            "circulatingPercentage": float(percentage_held),
                        },
                    },
                )

            print(f"Captured qualifying snapshots for {len(whale_balances)} wallet owners.")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(capture_token_holders_snapshot())
