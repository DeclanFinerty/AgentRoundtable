#!/usr/bin/env python3
"""

Author: Declan Finerty


Society Debate Tournament - Minimal Proof of Concept
10 bots describe ideal societies and debate each other
"""

import json
import ollama
from datetime import datetime
from itertools import combinations
from pathlib import Path

class SocietyDebateTournament:
    def __init__(self, model="llama3.2", num_bots=10):
        self.model = model
        self.num_bots = num_bots
        self.results_dir = Path("debate_results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Initialize data storage
        self.societies = {}
        self.debates = []
        self.votes = {}
        
    def generate_ideal_society(self, bot_id):
        """Each bot describes their ideal society"""
        prompt = """Describe your ideal society in 200 words. Include:
- Governance structure
- Economic system  
- Core values
- How conflicts are resolved
Be specific and consistent."""

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        
        society = {
            "bot_id": bot_id,
            "description": response["message"]["content"],
            "generated_at": datetime.now().isoformat()
        }
        
        self.societies[bot_id] = society
        return society
    
    def run_debate(self, bot_a_id, bot_b_id):
        """Run a structured debate between two bots"""
        society_a = self.societies[bot_a_id]["description"]
        society_b = self.societies[bot_b_id]["description"]
        
        debate = {
            "participants": [bot_a_id, bot_b_id],
            "rounds": []
        }
        
        # Round 1: Opening statements (just their societies)
        debate["rounds"].append({
            "type": "opening",
            bot_a_id: society_a,
            bot_b_id: society_b
        })
        
        # Round 2: Rebuttals
        rebuttal_prompt_a = f"""Your opponent proposes this society:
{society_b}

Point out potential flaws or problems with their society. Be specific.
Keep response under 150 words."""

        rebuttal_prompt_b = f"""Your opponent proposes this society:
{society_a}

Point out potential flaws or problems with their society. Be specific.
Keep response under 150 words."""

        rebuttal_a = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": rebuttal_prompt_a}]
        )["message"]["content"]
        
        rebuttal_b = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": rebuttal_prompt_b}]
        )["message"]["content"]
        
        debate["rounds"].append({
            "type": "rebuttal",
            bot_a_id: rebuttal_a,
            bot_b_id: rebuttal_b
        })
        
        # Round 3: Closing arguments
        closing_prompt_a = f"""Defend why your society is better.
Your society: {society_a}
Their criticism: {rebuttal_b}
Keep response under 100 words."""

        closing_prompt_b = f"""Defend why your society is better.
Your society: {society_b}
Their criticism: {rebuttal_a}
Keep response under 100 words."""

        closing_a = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": closing_prompt_a}]
        )["message"]["content"]
        
        closing_b = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": closing_prompt_b}]
        )["message"]["content"]
        
        debate["rounds"].append({
            "type": "closing",
            bot_a_id: closing_a,
            bot_b_id: closing_b
        })
        
        self.debates.append(debate)
        return debate
    
    def vote_on_debate(self, debate, voter_id):
        """Have a bot vote on who won a debate"""
        # Format debate for viewing
        debate_text = f"""Judge this debate between two ideal societies.

Society A: {debate['rounds'][0][debate['participants'][0]]}

Society B: {debate['rounds'][0][debate['participants'][1]]}

A's criticism of B: {debate['rounds'][1][debate['participants'][0]]}

B's criticism of A: {debate['rounds'][1][debate['participants'][1]]}

A's defense: {debate['rounds'][2][debate['participants'][0]]}

B's defense: {debate['rounds'][2][debate['participants'][1]]}

Which society would you rather live in? Reply with only 'A' or 'B' and one sentence explaining why."""

        response = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": debate_text}]
        )
        
        vote_text = response["message"]["content"]
        
        # Extract vote (look for A or B)
        vote = "A" if "A" in vote_text[:10] else "B"
        winner_id = debate['participants'][0] if vote == "A" else debate['participants'][1]
        
        return {
            "voter_id": voter_id,
            "winner_id": winner_id,
            "reasoning": vote_text
        }
    
    def run_tournament(self):
        """Run the full tournament"""
        print("=== Society Debate Tournament ===\n")
        
        # Phase 1: Generate societies
        print("Phase 1: Generating ideal societies...")
        for i in range(self.num_bots):
            bot_id = f"bot_{i}"
            print(f"  Bot {i} describing their ideal society...")
            self.generate_ideal_society(bot_id)
        
        # Save societies
        with open(self.results_dir / "societies.json", "w") as f:
            json.dump(self.societies, f, indent=2)
        
        # Phase 2: Run all debates
        print("\nPhase 2: Running debates...")
        debate_pairs = list(combinations(range(self.num_bots), 2))
        
        for i, (a, b) in enumerate(debate_pairs):
            bot_a_id = f"bot_{a}"
            bot_b_id = f"bot_{b}"
            print(f"  Debate {i+1}/45: {bot_a_id} vs {bot_b_id}")
            self.run_debate(bot_a_id, bot_b_id)
        
        # Save debates
        with open(self.results_dir / "debates.json", "w") as f:
            json.dump(self.debates, f, indent=2)
        
        # Phase 3: Voting
        print("\nPhase 3: Voting on debates...")
        for i, debate in enumerate(self.debates):
            debate_votes = []
            participants = debate['participants']
            
            # Get votes from all non-participants
            for j in range(self.num_bots):
                voter_id = f"bot_{j}"
                if voter_id not in participants:
                    vote = self.vote_on_debate(debate, voter_id)
                    debate_votes.append(vote)
            
            self.votes[f"debate_{i}"] = {
                "participants": participants,
                "votes": debate_votes
            }
            
            # Quick tally
            winner_count = {}
            for vote in debate_votes:
                winner_id = vote['winner_id']
                winner_count[winner_id] = winner_count.get(winner_id, 0) + 1
            
            print(f"  Debate {i+1}: {winner_count}")
        
        # Save votes
        with open(self.results_dir / "votes.json", "w") as f:
            json.dump(self.votes, f, indent=2)
        
        # Calculate final rankings
        self.calculate_rankings()
    
    def calculate_rankings(self):
        """Calculate which societies won the most debates"""
        win_counts = {f"bot_{i}": 0 for i in range(self.num_bots)}
        
        for debate_id, vote_data in self.votes.items():
            votes = vote_data['votes']
            winner_count = {}
            
            for vote in votes:
                winner_id = vote['winner_id']
                winner_count[winner_id] = winner_count.get(winner_id, 0) + 1
            
            # Determine debate winner
            debate_winner = max(winner_count, key=winner_count.get)
            win_counts[debate_winner] += 1
        
        # Sort by wins
        rankings = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)
        
        print("\n=== Final Rankings ===")
        for i, (bot_id, wins) in enumerate(rankings):
            print(f"{i+1}. {bot_id}: {wins} debate wins")
            
        # Save summary
        summary = {
            "rankings": rankings,
            "win_counts": win_counts,
            "total_debates": len(self.debates),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(self.results_dir / "tournament_summary.json", "w") as f:
            json.dump(summary, f, indent=2)


if __name__ == "__main__":
    tournament = SocietyDebateTournament(model="llama3.2", num_bots=10)
    tournament.run_tournament()
    
    print("\nResults saved to ./debate_results/")
