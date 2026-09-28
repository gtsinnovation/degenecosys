import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { DegenDollar } from "../target/types/degen_dollar";
import { 
  TOKEN_PROGRAM_ID, 
  createMint, 
  createAccount, 
  getAccount 
} from "@solana/spl-token";
import { assert } from "chai";

describe("degen_dollar_ecosystem_tests", () => {
  // Configure the client to use the local validator context link
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.DegenDollar as Program<DegenDollar>;
  const authority = provider.wallet.payer;

  // Keypairs for Ecosystem Vaults
  const tokenMint = anchor.web3.Keypair.generate();
  let liquidityVault: anchor.web3.Pubkey;
  let communityVault: anchor.web3.Pubkey;
  let marketingVault: anchor.web3.Pubkey;
  let devVault: anchor.web3.Pubkey;
  let charityVault: anchor.web3.Pubkey;

  // Keypairs for Vesting Allocations Testing
  const warriorBeneficiary = anchor.web3.Keypair.generate();
  let warriorTokenAccount: anchor.web3.Pubkey;
  let vestingSchedulePda: anchor.web3.Pubkey;
  let vestingScheduleBump: number;
  let charityStatePda: anchor.web3.Pubkey;

  before(async () => {
    // 1. Derive required program-derived account handles (PDAs)
    [charityStatePda] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("charity_state")],
      program.programId
    );

    const [vestingPda, bump] = anchor.web3.PublicKey.findProgramAddressSync(
      [Buffer.from("vesting"), warriorBeneficiary.publicKey.toBuffer()],
      program.programId
    );
    vestingSchedulePda = vestingPda;
    vestingScheduleBump = bump;

    // 2. Pre-create associated SPL token vault accounts to hold allotments
    liquidityVault = await createAccount(provider.connection, authority, tokenMint.publicKey, authority.publicKey);
    communityVault = await createAccount(provider.connection, authority, tokenMint.publicKey, authority.publicKey);
    marketingVault = await createAccount(provider.connection, authority, tokenMint.publicKey, authority.publicKey);
    devVault = await createAccount(provider.connection, authority, tokenMint.publicKey, authority.publicKey);
    charityVault = await createAccount(provider.connection, authority, tokenMint.publicKey, authority.publicKey);
    
    // Target user account to collect distributed rewards
    warriorTokenAccount = await createAccount(provider.connection, authority, tokenMint.publicKey, warriorBeneficiary.publicKey);
  });

  it("Initializes the $DD Ecosystem and enforces hardcoded Tokenomics distributions", async () => {
    // Execute initialization instruction
    await program.methods
      .initializeEcosystem()
      .accounts({
        tokenMint: tokenMint.publicKey,
        liquidityVault: liquidityVault,
        communityVault: communityVault,
        marketingVault: marketingVault,
        devVault: devVault,
        charityVault: charityVault,
        authority: authority.publicKey,
        tokenProgram: TOKEN_PROGRAM_ID,
        systemProgram: anchor.web3.SystemProgram.programId,
        rent: anchor.web3.SYSVAR_RENT_PUBKEY,
      })
      .signers([tokenMint])
      .rpc();

    // Verify tokenomics supply values inside the vaults
    const communityInfo = await getAccount(provider.connection, communityVault);
    const expectedCommunityTokens = new anchor.BN(1000000000).mul(new anchor.BN(1000000000)).mul(new anchor.BN(30)).div(new anchor.BN(100)); // 30%
    
    assert.equal(communityInfo.amount.toString(), expectedCommunityTokens.toString(), "Community lockup pool should strictly hold 30% of total supply");
  });

  it("Configures a linear vesting schedule with an active cliff constraint", async () => {
    const totalVestingAmount = new anchor.BN(10_000_000).mul(new anchor.BN(1_000_000_000)); // 10M tokens
    const cliffDuration = new anchor.BN(10); // Short 10-second cliff window for local test stability
    const totalDuration = new anchor.BN(100); // 100-second full linear vesting lifecycle

    await program.methods
      .setupVesting(totalVestingAmount, cliffDuration, totalDuration)
      .accounts({
        charityState: charityStatePda,
        vestingSchedule: vestingSchedulePda,
        beneficiary: warriorBeneficiary.publicKey,
        authority: authority.publicKey,
        systemProgram: anchor.web3.SystemProgram.programId,
      })
      .rpc();

    // Pull ledger record out of the chain state matrix
    const vestingState = await program.account.vestingSchedule.fetch(vestingSchedulePda);
    assert.ok(vestingState.beneficiary.equals(warriorBeneficiary.publicKey));
    assert.equal(vestingState.amountWithdrawn.toString(), "0", "Initial drawn history must equal zero");
  });

  it("Rejects drawdown release attempts triggered before the cliff window expires", async () => {
    try {
      await program.methods
        .releaseVestedTokens()
        .accounts({
          vestingSchedule: vestingSchedulePda,
          vaultAccount: communityVault,
          vaultAuthority: authority.publicKey,
          beneficiaryTokenAccount: warriorTokenAccount,
          beneficiary: warriorBeneficiary.publicKey,
          tokenProgram: TOKEN_PROGRAM_ID,
        })
        .signers([warriorBeneficiary])
        .rpc();
        
      assert.fail("Vesting lockup guard should have blocked this early withdrawal attempt.");
    } catch (err: any) {
      // Expect custom programmatic cliff validation failure codes
      assert.include(err.toString(), "CliffNotReached", "Transaction should fail stating cliff has not been reached.");
    }
  });
});