#contracts/degen_dollar/src/errors.rs
use anchor_lang::prelude::*;

#[error_code]
pub mod DegenError {
    #[msg("The cliff period for this allocation has not expired yet.")]
    CliffNotReached,
    #[msg("There are no clear unlocked tokens available to claim at this timestamp.")]
    NoVestedTokensAvailable,
    #[msg("Unauthorized signer attempt to withdraw from this programmatic vault.")]
    UnauthorizedBeneficiary,
    #[msg("The signer or token account is not authorized for this operation.")]
    Unauthorized,
    #[msg("Math calculation error or overflow occurred during vesting evaluation.")]
    MathOverflow,
    #[msg("The vesting token accounts or authority do not match the schedule.")]
    InvalidVestingAccounts,
    #[msg("The vesting duration must be positive and the cliff must be within the duration.")]
    InvalidVestingDuration,
}
