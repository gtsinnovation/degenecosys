use anchor_lang::prelude::*;
use anchor_spl::token::{self, Mint, Token, TokenAccount, MintTo, Transfer};

pub mod state;
pub mod errors;
pub mod charity;

use state::*;
use charity::*;
use errors::DegenError;

declare_id!("hPo88udXwqH85rZttR4mDrdqDA9F8FS1rZTbKU5xNhi");

#[program]
pub mod degen_dollar {
    use super::*;

    /// Initializes token distribution vaults with corrected tokenomics ratios.
    pub fn initialize_ecosystem(ctx: Context<InitializeEcosystem>) -> Result<()> {
        let total_supply: u64 = 1_000_000_000 * 1_000_000_000; // 1 Billion tokens with 9 decimals

        // Updated 2026 Core Tokenomics Allotments
        let liquidity_amount = total_supply * 50 / 100;       // 50%
        let community_amount = total_supply * 30 / 100;       // 30%
        let marketing_amount = total_supply * 10 / 100;       // 10%
        let dev_amount       = total_supply * 9 / 100;        // 9%  (Adjusted for balance)
        let charity_amount   = total_supply * 1 / 100;        // 1%  (Refined from user constraints)

        token::mint_to(ctx.accounts.into_mint_to_context(ctx.accounts.liquidity_vault.to_account_info()), liquidity_amount)?;
        token::mint_to(ctx.accounts.into_mint_to_context(ctx.accounts.community_vault.to_account_info()), community_amount)?;
        token::mint_to(ctx.accounts.into_mint_to_context(ctx.accounts.marketing_vault.to_account_info()), marketing_amount)?;
        token::mint_to(ctx.accounts.into_mint_to_context(ctx.accounts.dev_vault.to_account_info()), dev_amount)?;
        token::mint_to(ctx.accounts.into_mint_to_context(ctx.accounts.charity_vault.to_account_info()), charity_amount)?;

        // Populate Charity Tracking State
        let charity_state = &mut ctx.accounts.charity_state;
        charity_state.total_charity_minted = charity_amount;
        charity_state.total_distributed = 0;
        charity_state.distribution_count = 0;
        charity_state.bump = ctx.bumps.charity_state;
        charity_state.distribution_authority = ctx.accounts.authority.key();
        charity_state.token_mint = ctx.accounts.token_mint.key();

        Ok(())
    }

    /// Creates a time-locked vesting schedule for the Community or Dev vaults
    pub fn setup_vesting(ctx: Context<SetupVesting>, total_amount: u64, cliff_duration: i64, total_duration: i64) -> Result<()> {
        let vesting_account = &mut ctx.accounts.vesting_schedule;
        let clock = Clock::get()?;

        require!(
            total_duration > 0 && cliff_duration >= 0 && cliff_duration <= total_duration,
            DegenError::InvalidVestingDuration
        );

        vesting_account.beneficiary = ctx.accounts.beneficiary.key();
        vesting_account.total_amount = total_amount;
        vesting_account.amount_withdrawn = 0;
        vesting_account.start_time = clock.unix_timestamp;
        vesting_account.cliff_time = clock.unix_timestamp.checked_add(cliff_duration).ok_or(DegenError::MathOverflow)?;
        vesting_account.duration = total_duration;
        vesting_account.bump = ctx.bumps.vesting_schedule;

        Ok(())
    }

    /// Releases unlocked tokens linearly based on the exact current timestamp
    pub fn release_vested_tokens(ctx: Context<ReleaseVestedTokens>) -> Result<()> {
        let vesting_account = &mut ctx.accounts.vesting_schedule;
        let clock = Clock::get()?;

        require_keys_eq!(ctx.accounts.beneficiary.key(), vesting_account.beneficiary, DegenError::UnauthorizedBeneficiary);
        require!(clock.unix_timestamp >= vesting_account.cliff_time, DegenError::CliffNotReached);

        let elapsed_time = clock.unix_timestamp.checked_sub(vesting_account.start_time).ok_or(DegenError::MathOverflow)?;
        
        let total_vested = if elapsed_time >= vesting_account.duration {
            vesting_account.total_amount
        } else {
            vesting_account.total_amount
                .checked_mul(elapsed_time as u64).ok_or(DegenError::MathOverflow)?
                .checked_div(vesting_account.duration as u64).ok_or(DegenError::MathOverflow)?
        };

        let claimable_amount = total_vested.checked_sub(vesting_account.amount_withdrawn).ok_or(DegenError::MathOverflow)?;
        require!(claimable_amount > 0, DegenError::NoVestedTokensAvailable);

        vesting_account.amount_withdrawn = vesting_account.amount_withdrawn.checked_add(claimable_amount).ok_or(DegenError::MathOverflow)?;

        let transfer_accounts = Transfer {
            from: ctx.accounts.vault_account.to_account_info(),
            to: ctx.accounts.beneficiary_token_account.to_account_info(),
            authority: ctx.accounts.vault_authority.to_account_info(),
        };
        
        let cpi_ctx = CpiContext::new(ctx.accounts.token_program.to_account_info(), transfer_accounts);
        token::transfer(cpi_ctx, claimable_amount)?;

        Ok(())
    }

    /// Executes a charity release authorized by the configured distribution signer.
    /// The description hash is recorded metadata; community-vote proofs are not verified on-chain.
    pub fn execute_charity_distribution(
        ctx: Context<ExecuteCharityDistribution>,
        distribution: CharityDistributionInfo
    ) -> Result<()> {
        let charity_state = &mut ctx.accounts.charity_state;

        require_keys_eq!(
            ctx.accounts.distribution_authority.key(),
            charity_state.distribution_authority,
            DegenError::Unauthorized
        );
        require_keys_eq!(
            ctx.accounts.recipient_token_account.owner,
            distribution.recipient,
            DegenError::Unauthorized
        );
        require_keys_eq!(
            ctx.accounts.recipient_token_account.mint,
            charity_state.token_mint,
            DegenError::Unauthorized
        );
        require!(distribution.amount > 0, DegenError::NoVestedTokensAvailable);

        let remaining_charity_pool = charity_state.total_charity_minted
            .checked_sub(charity_state.total_distributed)
            .ok_or(DegenError::MathOverflow)?;
        require!(distribution.amount <= remaining_charity_pool, DegenError::NoVestedTokensAvailable);

        let next_total_distributed = charity_state.total_distributed
            .checked_add(distribution.amount)
            .ok_or(DegenError::MathOverflow)?;
        let next_distribution_count = charity_state.distribution_count
            .checked_add(1)
            .ok_or(DegenError::MathOverflow)?;

        let transfer_accounts = Transfer {
            from: ctx.accounts.charity_vault.to_account_info(),
            to: ctx.accounts.recipient_token_account.to_account_info(),
            authority: ctx.accounts.distribution_authority.to_account_info(),
        };
        let cpi_ctx = CpiContext::new(
            ctx.accounts.token_program.to_account_info(),
            transfer_accounts,
        );
        token::transfer(cpi_ctx, distribution.amount)?;

        charity_state.total_distributed = next_total_distributed;
        charity_state.distribution_count = next_distribution_count;

        msg!("Charity allocation of {} tokens executed.", distribution.amount);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct InitializeEcosystem<'info> {
    #[account(init, payer = authority, mint::decimals = 9, mint::authority = authority)]
    pub token_mint: Account<'info, Mint>,
    #[account(mut)]
    pub liquidity_vault: Account<'info, TokenAccount>,
    #[account(mut)]
    pub community_vault: Account<'info, TokenAccount>,
    #[account(mut)]
    pub marketing_vault: Account<'info, TokenAccount>,
    #[account(mut)]
    pub dev_vault: Account<'info, TokenAccount>,
    #[account(mut, constraint = charity_vault.mint == token_mint.key(), constraint = charity_vault.owner == authority.key())]
    pub charity_vault: Account<'info, TokenAccount>,
    
    #[account(
        init,
        payer = authority,
        space = 8 + 8 + 8 + 4 + 1 + 32 + 32,
        seeds = [b"charity_state"],
        bump
    )]
    pub charity_state: Account<'info, CharityVaultState>,

    #[account(mut)]
    pub authority: Signer<'info>,
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

impl<'info> InitializeEcosystem<'info> {
    fn into_mint_to_context(&self, to: AccountInfo<'info>) -> CpiContext<'_, '_, '_, 'info, MintTo<'info>> {
        let cpi_accounts = MintTo { mint: self.token_mint.to_account_info(), to, authority: self.authority.to_account_info() };
        CpiContext::new(self.token_program.to_account_info(), cpi_accounts)
    }
}

#[derive(Accounts)]
pub struct SetupVesting<'info> {
    #[account(init, payer = authority, space = 8 + 32 + 8 + 8 + 8 + 8 + 8 + 1, seeds = [b"vesting", beneficiary.key().as_ref()], bump)]
    pub vesting_schedule: Account<'info, VestingSchedule>,
    /// CHECK: Target beneficiary wallet tracked as key parameters
    pub beneficiary: AccountInfo<'info>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct ReleaseVestedTokens<'info> {
    #[account(mut, seeds = [b"vesting", beneficiary.key().as_ref()], bump = vesting_schedule.bump)]
    pub vesting_schedule: Account<'info, VestingSchedule>,
    #[account(mut)]
    pub vault_account: Account<'info, TokenAccount>,
    /// CHECK: Seed validation handling authority for token account distribution mechanics
    pub vault_authority: AccountInfo<'info>,
    #[account(mut)]
    pub beneficiary_token_account: Account<'info, TokenAccount>,
    pub beneficiary: Signer<'info>,
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct ExecuteCharityDistribution<'info> {
    #[account(mut, seeds = [b"charity_state"], bump = charity_state.bump)]
    pub charity_state: Account<'info, CharityVaultState>,
    #[account(
        mut,
        constraint = charity_vault.mint == charity_state.token_mint,
        constraint = charity_vault.owner == charity_state.distribution_authority
    )]
    pub charity_vault: Account<'info, TokenAccount>,
    #[account(mut)]
    pub recipient_token_account: Account<'info, TokenAccount>,
    pub distribution_authority: Signer<'info>,
    pub token_program: Program<'info, Token>,
}