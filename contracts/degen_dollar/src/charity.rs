use anchor_lang::prelude::*;

#[account]
pub struct CharityVaultState {
    pub total_charity_minted: u64, // Tracks initial 1% allocation total tokens
    pub total_distributed: u64,    // Running total of claimed charity streams
    pub distribution_count: u32,   // Count of approved payouts executed
    pub bump: u8,                  // PDA bump tracker for program verification
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Default)]
pub struct CharityDistributionInfo {
    pub recipient: Pubkey,         // Whitelisted organization wallet destination
    pub amount: u64,               // Requested token payout count
    pub description_hash: [u8; 32],// IPFS hash recording community voting approval records
}