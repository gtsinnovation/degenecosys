# backend/scripts/snapshot_worker.py
import asyncio
import datetime
import os
from decimal import Decimal

import httpx
from prisma import Prisma

RPC_ENDPOINT = os.getenv("SOLANA_RPC_URL", "")
MINT_ADDRESS = os.getenv("DD_MINT_ADDRESS", "")
TOTAL_SUPPLY = Decimal("1000000000")


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


async def owner_for_token_account(client: httpx.AsyncClient, address: str) -> str:
    account = await rpc_call(
        client,
        "getAccountInfo",
        [address, {"encoding": "jsonParsed", "commitment": "confirmed"}],
    )
    value = account.get("value")
    try:
        parsed = value["data"]["parsed"]
        if parsed.get("type") != "account":
            raise ValueError("unexpected account type")
        return parsed["info"]["owner"]
    except (TypeError, KeyError, ValueError) as exc:
        raise RuntimeError(f"Could not resolve token account owner for {address}.") from exc


async def token_balance_for_owner(client: httpx.AsyncClient, owner: str) -> Decimal:
    result = await rpc_call(
        client,
        "getTokenAccountsByOwner",
        [
            owner,
            {"mint": MINT_ADDRESS},
            {"encoding": "jsonParsed", "commitment": "confirmed"},
        ],
    )
    total = Decimal("0")
    for account in result.get("value", []):
        try:
            amount = account["account"]["data"]["parsed"]["info"]["tokenAmount"]
            total += Decimal(amount["uiAmountString"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Could not parse $DD balance for wallet {owner}.") from exc
    return total


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
            largest = await rpc_call(
                client,
                "getTokenLargestAccounts",
                [MINT_ADDRESS, {"commitment": "confirmed"}],
            )
            # Largest-account results identify candidate holders, but their addresses
            # are SPL token accounts. Resolve owners, then sum every $DD token account
            # for each owner so database keys match authenticated wallet addresses.
            owners = {
                await owner_for_token_account(client, entry["address"])
                for entry in largest.get("value", [])
            }

            for owner in owners:
                balance = await token_balance_for_owner(client, owner)
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

            print(f"Captured snapshots for {len(owners)} wallet owners.")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(capture_token_holders_snapshot())
