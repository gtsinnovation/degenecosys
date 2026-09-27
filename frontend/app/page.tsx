'use client';

import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui';
import { Shield, ArrowUp, ArrowDown, Award, Zap, Flame, Globe, Trophy, Code, Link, Send, Twitter, User } from 'lucide-react';

interface LeaderboardUser {
  username: string;
  wallet_address: string;
  current_xp: number;
  rank_tier: number;
}

interface ActiveContest {
  id: string;
  title: string;
  description: string;
  prizePoolDd: number;
  isActive: boolean;
}

interface UnlockedBadge {
  name: string;
  description: string;
  icon_svg: string;
  unlocked_at: string;
}

interface WarriorCompleteProfile {
  wallet_address: string;
  username: string | null;
  bio: string | null;
  avatar_url: string | null;
  banner_url: string | null;
  twitter_handle: string | null;
  current_xp: number;
  rank_tier: number;
  unlocked_badges: UnlockedBadge[];
}

export default function DegenWarriorPortal() {
  const { publicKey } = useWallet();
  const [warriors, setWarriors] = useState<LeaderboardUser[]>([]);
  const [contests, setContests] = useState<ActiveContest[]>([]);
  const [selectedWallet, setSelectedWallet] = useState<string>("WhaleTrue999999999999999999999999999999999");
  const [activeProfile, setActiveProfile] = useState<WarriorCompleteProfile | null>(null);
  const [boosterStatus, setBoosterStatus] = useState<boolean>(false);
  const [submissionUrl, setSubmissionUrl] = useState<string>( "");
  const [selectedContestId, setSelectedContestId] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);

  const API_BASE = "http://localhost:8000"; // Directed container local mapping handle

  const refreshDashboardData = async () => {
    try {
      const resLeaderboard = await fetch(`${API_BASE}/api/leaderboard`);
      if (resLeaderboard.ok) setWarriors(await resLeaderboard.json());

      setContests([
        {
          id: "fc8a2dc6-02de-40af-b8d5-aa6158d16c23",
          title: "Degen Meme Overlord Challenge",
          description: "Produce high quality viral graphic content highlighting $DD lockup utilities.",
          prizePoolDd: 50000.0,
          isActive: true
        }
      ]);
    } catch (err) {
      console.error("Dashboard synchronization error:", err);
    }
  };

  // Pull expanded identity parameters every time selected target shift values toggle
  useEffect(() => {
    if (selectedWallet) {
      fetch(`${API_BASE}/api/warrior/${selectedWallet}/profile`)
        .then(res => res.ok ? res.json() : null)
        .then(data => { if (data) setActiveProfile(data); })
        .catch(err => console.error("Error drawing expanded profile dataset:", err));
    }
  }, [selectedWallet]);

  useEffect(() => {
    refreshDashboardData();
    if (publicKey) {
      fetch(`${API_BASE}/api/warrior/${publicKey.toBase58()}/booster-status`)
        .then(res => res.json())
        .then(data => setBoosterStatus(data.has_veto_booster))
        .catch(err => console.error("Booster lookup error:", err));
    } else {
      setBoosterStatus(false);
    }
  }, [publicKey]);

  const handleVote = async (targetWallet: string, isUpvote: boolean) => {
    if (!publicKey) return alert("Initialize your Solana wallet framework first!");
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/interact/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voter_wallet: publicKey.toBase58(),
          target_wallet: targetWallet,
          is_upvote: isUpvote
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Transaction blocked");
      alert(`Interaction Complete! Target New XP: ${data.target_new_xp}`);
      await refreshDashboardData();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleChallengeSubmission = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!publicKey) return alert("Connect your wallet context matrix to submit proof!");
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/contests/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contest_id: selectedContestId,
          warrior_wallet: publicKey.toBase58(),
          submission_link: submissionUrl
        })
      });
      if (!response.ok) throw new Error("Submission entry rejected.");
      alert("Proof-of-work entry successfully logged!");
      setSubmissionUrl("");
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#08090C] text-gray-100 font-sans p-6 selection:bg-[#10B981] selection:text-black">
      {/* HEADER SECTION */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center border-b border-gray-800 pb-6 mb-8 gap-4">
        <div>
          <h1 className="text-3xl font-black tracking-tighter text-transparent bg-clip-text bg-gradient-to-r from-gray-100 via-[#F59E0B] to-[#10B981] flex items-center gap-2">
            <Flame className="text-[#F59E0B] animate-pulse" /> DEGEN WARRIOR ECOSYSTEM
          </h1>
          <p className="text-sm text-gray-400 mt-1">Official Interface powered by the \$DD Utility Token</p>
        </div>
        <div className="flex gap-4 items-center">
          <div className="bg-[#111318] border border-gray-800 px-4 py-2 rounded flex items-center gap-2 h-[48px]">
            <span className="h-2 w-2 rounded-full bg-[#10B981] animate-ping"></span>
            <span className="text-xs font-mono text-gray-400">Solana Devnet</span>
          </div>
          <WalletMultiButton className="!bg-[#10B981] hover:!bg-emerald-600 !text-[#08090C] !font-bold !rounded !text-sm !h-[48px] !transition-all" />
        </div>
      </header>

      {/* DASHBOARD STATISTICS OVERVIEW */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* COLUMN 1 & 2: DYNAMIC LEADERBOARD & ACTIVE CONTESTS */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* LEADERBOARD STANDINGS */}
          <section className="bg-[#111318] border border-gray-800 rounded-lg p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 text-[#10B981]">
                <Award size={20} /> LEADERBOARD STANDINGS
              </h2>
              <button onClick={refreshDashboardData} className="text-xs text-[#F59E0B] font-mono border border-[#F59E0B]/30 px-2 py-1 rounded bg-[#F59E0B]/5 hover:bg-[#F59E0B]/20 transition-all">
                ↻ Sync List
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-gray-800 text-gray-400 text-xs font-mono uppercase tracking-wider">
                    <th className="pb-3 pl-2">Warrior</th>
                    <th className="pb-3">Wallet Address</th>
                    <th className="pb-3 text-center">XP Progress</th>
                    <th className="pb-3 text-right pr-2">Interaction</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-900 font-mono text-sm">
                  {warriors.map((warrior, idx) => (
                    <tr 
                      key={idx} 
                      className={`hover:bg-[#08090C]/50 transition-colors mercantile-row cursor-pointer ${selectedWallet === warrior.wallet_address ? 'bg-[#08090C] border-l-2 border-[#F59E0B]' : ''}`}
                      onClick={() => setSelectedWallet(warrior.wallet_address)}
                    >
                      <td className="py-4 pl-2 font-bold text-gray-200 flex items-center gap-2">
                        <span className="text-xs text-gray-600">#{idx + 1}</span>
                        {warrior.username || `Warrior_${warrior.wallet_address.substring(0,4)}`}
                      </td>
                      <td className="py-4 text-gray-400">{warrior.wallet_address.substring(0, 12)}...</td>
                      <td className="py-4 text-center">
                        <span className={`px-3 py-1 rounded font-bold text-xs ${warrior.current_xp >= 0 ? 'bg-[#10B981]/10 text-[#10B981]' : 'bg-[#EF4444]/10 text-[#EF4444]'}`}>
                          {warrior.current_xp} XP
                        </span>
                      </td>
                      <td className="py-4 text-right pr-2">
                        <div className="flex justify-end gap-2" onClick={(e) => e.stopPropagation()}>
                          <button 
                            disabled={loading || !publicKey}
                            onClick={() => handleVote(warrior.wallet_address, true)}
                            className="p-2 bg-[#111318] border border-gray-800 hover:border-[#10B981] hover:text-[#10B981] text-gray-400 rounded transition-all"
                          >
                            <ArrowUp size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* ACTIVE CHALLENGES BOX */}
          <section className="bg-[#111318] border border-gray-800 rounded-lg p-6 shadow-2xl">
            <h2 className="text-xl font-bold tracking-tight flex items-center gap-2 text-[#F59E0B] mb-6">
              <Trophy size={20} /> ACTIVE ECOSYSTEM CHALLENGES
            </h2>
            <div className="grid grid-cols-1 gap-4">
              {contests.map((contest) => (
                <div
                  key={contest.id}
                  onClick={() => setSelectedContestId(contest.id)}
                  className={`p-4 rounded border transition-all cursor-pointer bg-[#08090C] ${selectedContestId === contest.id ? 'border-[#F59E0B] shadow-lg shadow-[#F59E0B]/5' : 'border-gray-800 hover:border-gray-700'}`}
                >
                  <div className="flex justify-between items-start gap-4">
                    <h3 className="font-bold text-gray-100">{contest.title}</h3>
                    <span className="shrink-0 text-xs font-mono text-[#F59E0B]">
                      {contest.prizePoolDd.toLocaleString()} $DD POOL
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-400">{contest.description}</p>
                </div>
              ))}
            </div>

            {/* CONTEST ENTRY PROOF FORM SUBMISSION */}
            {selectedContestId && (
              <form onSubmit={handleChallengeSubmission} className="mt-6 space-y-4">
                <label htmlFor="submission-url" className="block text-sm font-bold text-gray-200">
                  Submit Proof of Contribution
                </label>
                <input
                  id="submission-url"
                  type="url"
                  required
                  placeholder="Paste artifact link (GitHub, Tweet link, IPFS content hash)..."
                  value={submissionUrl}
                  onChange={(e) => setSubmissionUrl(e.target.value)}
                  className="w-full bg-[#08090C] border border-gray-800 focus:border-[#F59E0B] text-sm text-gray-100 font-mono rounded px-4 py-2.5 outline-none transition-colors"
                />
                <button
                  type="submit"
                  disabled={loading || !publicKey}
                  className="bg-[#F59E0B] hover:bg-amber-600 disabled:opacity-40 text-[#08090C] font-black py-2.5 px-4 rounded font-mono text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-colors"
                >
                  Submit Entry
                </button>
              </form>
            )}
          </section>
        </div>

        {/* COLUMN 3: TOKENOMICS VAULTS & GUARDRAILS */}
        <aside className="space-y-8">
          <section className="bg-[#111318] border border-gray-800 rounded-lg p-6 shadow-2xl">
            <h2 className="text-xl font-bold tracking-tight text-[#10B981] mb-6">
              Tokenomics Vault Allocation
            </h2>
            <dl className="space-y-4 text-sm">
              <div className="flex justify-between gap-4 border-b border-gray-800 pb-3">
                <dt className="text-gray-400">Locked Rewards (30%)</dt>
                <dd className="font-mono text-gray-100">300,000,000 $DD</dd>
              </div>
              <div className="flex justify-between gap-4 border-b border-gray-800 pb-3">
                <dt className="text-gray-400">Charity Stream (1%)</dt>
                <dd className="font-mono text-gray-100">10,000,000 $DD</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-gray-400">Liquidity Pool (50%)</dt>
                <dd className="font-mono text-gray-100">Permanently Burned</dd>
              </div>
            </dl>
          </section>

          <section className="bg-[#111318] border border-gray-800 rounded-lg p-6 shadow-2xl">
            <h2 className="text-xl font-bold tracking-tight text-[#F59E0B] mb-4">
              Governance Guardrails
            </h2>
            <p className="text-sm leading-relaxed text-gray-400">
              Leaders ascend the matrix via community verification loops. Wallets maintaining &gt;2% of circulating supply continuously for ≥30 days automatically inject a weighted multiplier (5x) into any upvote or demotion action.
            </p>
          </section>

          <section className="bg-[#111318] border border-gray-800 rounded-lg p-6 shadow-2xl">
            <h2 className="text-xl font-bold tracking-tight text-gray-200 mb-4">
              Your Wallet Status
            </h2>
            <p className={`text-sm font-bold ${boosterStatus ? 'text-[#10B981]' : 'text-gray-400'}`}>
              {boosterStatus ? '🚀 Veto-Booster Active (5x Weight)' : 'No Active Veto-Booster'}
            </p>
          </section>

          <p className="text-right text-xs font-mono text-gray-600">App Engine v1.0</p>
        </aside>
      </main>
    </div>
  );
}
