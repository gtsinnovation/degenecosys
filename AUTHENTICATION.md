# Authentication and secret configuration

## Configure the deployment

Copy `.env.example` to `.env`, then set:

- `POSTGRES_PASSWORD`: a new, randomly generated database password.
- `DATABASE_URL`: the matching PostgreSQL connection string.
- `AUTH_JWT_SECRET`: at least 32 random bytes (64 hexadecimal characters).
- `ADMIN_WALLETS`: comma-separated Solana public keys allowed to administer contests and payouts.
- `CORS_ORIGINS`: exact browser origins for the deployed frontend.

Do not commit `.env`. The database password previously present in Git history must be rotated anywhere it was used; removing it from the current compose file does not remove old commits.

## Wallet sign-in

The frontend requests `POST /api/auth/challenge` with a wallet public key. The API returns a five-minute, one-time message bound to that wallet. The user signs that message with their wallet. The frontend sends the message nonce and base64 signature to `POST /api/auth/verify`. The API validates the Solana Ed25519 signature, atomically consumes the nonce, and issues a one-hour bearer token signed with `AUTH_JWT_SECRET`.

The frontend keeps the token in memory and sends it in the `Authorization: Bearer` header for protected actions. The API derives the acting wallet from the verified token; it does not trust a wallet address supplied in a vote or submission body.

## Access rules

- Voting, contest submissions, and profile updates require a verified wallet token.
- A wallet can update only its own profile.
- Contest creation, payout processing, and admin status/toggle routes require the caller's wallet to appear in `ADMIN_WALLETS`.
- Leaderboard, profile reads, and booster status remain public.
- API browser origins are restricted through `CORS_ORIGINS`.

Serve the frontend and API over HTTPS in production. CORS is a browser control, not a replacement for authentication.
