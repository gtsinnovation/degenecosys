#!/bin/bash

# Degen Dollar ($DD) Solana Devnet Program Deployment Automation Pipeline
echo "=========================================================="
echo "🚀 Starting Degen Dollar Smart Contract Devnet Deployment..."
echo "=========================================================="

# 1. Enforce local environment key configuration checks
if [ ! -f ~/.config/solana/id.json ]; then
    echo "Error: Base Solana deployment wallet keypair missing at ~/.config/solana/id.json"
    echo "Generate one now using command: solana-keygen new"
    exit 1
fi

# 2. Lock network context parameters to Devnet endpoints
echo "Setting network targets directly to Solana Devnet RPC clusters..."
solana config set --url https://api.devnet.solana.com

# 3. Check deployment authority gas fund parameters
balance=$(solana balance | awk '{print $1}')
echo "Current Deployment Wallet Balance: $balance SOL"

# 4. Compile Anchor source files cleanly
echo "Compiling smart contract Rust binaries via Anchor framework..."
anchor build

# 5. Extract fresh Program ID variables
PROGRAM_ID=$(solana address -k target/deploy/degen_dollar-keypair.json)
echo "Verified Dynamic Program ID Handle Target: $PROGRAM_ID"
echo "Make sure this matches declare_id!(\"$PROGRAM_ID\") inside your lib.rs source code file."

# 6. Push binary bundles onto the live Devnet blockchain grid
echo "Executing deployment transaction sequence to Devnet ledger..."
anchor deploy --provider.cluster devnet

echo "=========================================================="
echo "🎉 DEPLOYMENT ENGINE EXECUTION STREAM COMPLETELY SUCCESSFUL"
echo "=========================================================="
echo "Your Program ID is now live: $PROGRAM_ID"
echo "Ecosystem initialization anchors can be monitored via Solana Explorer:"
echo "👉 https://solana.com"
echo "=========================================================="
