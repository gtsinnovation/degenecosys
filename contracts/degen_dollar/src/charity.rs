use anchor_lang::prelude::*;

#[account]
pub struct CharityVaultState {
    pub total_charity_minted: u64, // Tracks initial charity allocation
    pub total_distributed: u64,    // Running total of executed distributions
    pub distribution_count: u32,   // Count of executed distributions
    pub bump: u8,                  // PDA bump tracker
    pub distribution_authority: Pubkey, // Signer authorized to distribute charity tokens
    pub token_mint: Pubkey,        // Mint required for charity vault transfers
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Default)]
pub struct CharityDistributionInfo {
    pub recipient: Pubkey,         // Recipient wallet owning the destination token account
    pub amount: u64,               // Requested token payout amount
    pub description_hash: [u8; 32],// Optional metadata; not verified as vote approval on-chain
}