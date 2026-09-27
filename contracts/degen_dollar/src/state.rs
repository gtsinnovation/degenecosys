#contracts/degen_dollar/src/state.rs

use anchor_lang::prelude::*;

#[account]
pub struct VestingSchedule {
    pub beneficiary: Pubkey,    // Wallet authorized to withdraw unlocked tokens
    pub total_amount: u64,     // Total allocated tokens at inception
    pub amount_withdrawn: u64, // Tracking drawn funds to prevent double-claiming
    pub start_time: i64,       // Unix timestamp marking initialization
    pub cliff_time: i64,       // Unix timestamp before which 0 tokens are unlockable
    pub duration: i64,         // Total vesting span in seconds (e.g., 31,536,000 for 12 months)
    pub bump: u8,              // PDA derivation bump key for security verification
}
