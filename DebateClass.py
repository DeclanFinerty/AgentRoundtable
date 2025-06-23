#!/usr/bin/env python3
"""
Enhanced Society Debate System with memory, benchmarking, and modularity
"""

import json
import ollama
import time
from datetime import datetime
from itertools import combinations
from pathlib import Path
from typing import List, Dict, Optional
from tqdm import tqdm

class DebateAgent:
    """Flexible debating agent for any topic"""
    
    def __init__(self, agent_id: str, model: str = "llama3.2"):
        self.agent_id = agent_id
        self.model = model
        self.conversation_history = []
        self.initial_position = None  # Their main stance/answer
        self.position_label = None    # What to call it ("society", "solution", etc)
        self.performance_metrics = {
            "total_tokens": 0,
            "total_time": 0,
            "response_times": [],
            "avg_response_time": 0
        }
    
    def _add_to_history(self, role: str, content: str):
        """Add interaction to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def _get_context(self, additional_prompt: str) -> List[Dict]:
        """Build conversation context with history"""
        messages = []
        
        # Set the agent's identity and position via system prompt
        if self.initial_position and self.position_label:
            messages.append({
                "role": "system",
                "content": f"You are a member of a round table discussing {self.position_label}. Your stance is: {self.initial_position}."
            })
        
        # Add conversation history
        for entry in self.conversation_history:
            messages.append({
                "role": entry["role"], 
                "content": entry["content"]
            })
        
        # Add new prompt
        messages.append({
            "role": "user",
            "content": additional_prompt
        })
        
        return messages
    
    def generate_response(self, prompt: str, include_history: bool = True) -> str:
        """Generate response with performance tracking"""
        start_time = time.time()
        
        if include_history:
            messages = self._get_context(prompt)
        else:
            messages = [{"role": "user", "content": prompt}]
        
        response = ollama.chat(
            model=self.model,
            messages=messages
        )
        
        # Track performance
        elapsed_time = time.time() - start_time
        self.performance_metrics["response_times"].append(elapsed_time)
        self.performance_metrics["total_time"] += elapsed_time
        self.performance_metrics["avg_response_time"] = (
            sum(self.performance_metrics["response_times"]) / 
            len(self.performance_metrics["response_times"])
        )
        
        content = response["message"]["content"]
        
        # Add to history
        self._add_to_history("user", prompt)
        self._add_to_history("assistant", content)
        
        return content
    
    def set_initial_position(self, question: str, position_label: str = "position") -> str:
        """Generate and store initial position on any topic"""
        response = self.generate_response(question, include_history=False)
        self.initial_position = response
        self.position_label = position_label
        return response
    
    def get_metrics(self) -> Dict:
        """Return performance metrics for this agent"""
        return {
            "agent_id": self.agent_id,
            "model": self.model,
            "total_responses": len(self.performance_metrics["response_times"]),
            "total_time": self.performance_metrics["total_time"],
            "avg_response_time": self.performance_metrics["avg_response_time"],
            "min_response_time": min(self.performance_metrics["response_times"]) if self.performance_metrics["response_times"] else 0,
            "max_response_time": max(self.performance_metrics["response_times"]) if self.performance_metrics["response_times"] else 0,
            "total_tokens": self.performance_metrics["total_tokens"],
            "conversation_length": len(self.conversation_history)
        }


# # Example usage for different debate types:

# # Society debates
# agent = GenericDebateAgent("agent_0")
# agent.set_initial_position(
#     "Describe your ideal society in 200 words",
#     position_label="ideal society"
# )

# # Technology debates  
# agent = GenericDebateAgent("agent_1")
# agent.set_initial_position(
#     "Should AI development be regulated? Take a position and defend it.",
#     position_label="stance on AI regulation"
# )

# # Problem-solving debates
# agent = GenericDebateAgent("agent_2")
# agent.set_initial_position(
#     "How should we address climate change? Propose your top 3 solutions.",
#     position_label="climate solutions"
# )


class DebateTournament:
    """Tournament system for any debate topic"""
    
    def __init__(self, 
                 num_agents: int = 10,
                 models: Optional[List[str]] = None,
                 topic_question: str = None,
                 position_label: str = "position",
                 output_dir: str = "debate_results"):
        
        self.num_agents = num_agents
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.position_label = position_label
        
        # Flexible topic question
        self.topic_question = topic_question or "Describe your ideal society in 200 words."
        
        # Initialize agents with specified models
        if models is None:
            models = ["llama3.2"] * num_agents
        elif len(models) < num_agents:
            models = (models * (num_agents // len(models) + 1))[:num_agents]
        
        self.agents = {
            f"agent_{i}": DebateAgent(f"agent_{i}", models[i])
            for i in range(num_agents)
        }
        
        # Storage for results
        self.positions = {}  # Renamed from societies
        self.debates = []
        self.votes = {}
        self.tournament_metrics = {
            "start_time": None,
            "end_time": None,
            "total_duration": None,
            "phase_durations": {}
        }
    
    def run_phase_1_positions(self):
        """Generate all initial positions with progress bar"""
        print(f"\n=== Phase 1: Generating Initial {self.position_label.title()}s ===")
        phase_start = time.time()
        
        for agent_id, agent in tqdm(self.agents.items(), desc=f"Generating {self.position_label}s"):
            position = agent.set_initial_position(self.topic_question, self.position_label)
            self.positions[agent_id] = {
                "agent_id": agent_id,
                "position": position,
                "model": agent.model,
                "generated_at": datetime.now().isoformat()
            }
        
        self.tournament_metrics["phase_durations"]["positions"] = time.time() - phase_start
        
        # Save positions
        with open(self.output_dir / "positions.json", "w") as f:
            json.dump({
                "topic_question": self.topic_question,
                "position_label": self.position_label,
                "positions": self.positions
            }, f, indent=2)
    
    def run_debate(self, agent_a_id: str, agent_b_id: str) -> Dict:
        """Run a streamlined debate between two agents"""
        agent_a = self.agents[agent_a_id]
        agent_b = self.agents[agent_b_id]
        
        debate = {
            "participants": [agent_a_id, agent_b_id],
            "rounds": [],
            "timing": {}
        }
        
        round_start = time.time()
        
        # Round 1: First rebuttals of initial positions
        rebuttal_prompt_a = f"""Your opponent's {self.position_label} is:
{agent_b.initial_position}

Point out specific weaknesses, contradictions, or problems with their {self.position_label}.
Be analytical and precise. Keep response under 150 words."""

        rebuttal_prompt_b = f"""Your opponent's {self.position_label} is:
{agent_a.initial_position}

Point out specific weaknesses, contradictions, or problems with their {self.position_label}.
Be analytical and precise. Keep response under 150 words."""

        rebuttal_a = agent_a.generate_response(rebuttal_prompt_a)
        rebuttal_b = agent_b.generate_response(rebuttal_prompt_b)
        
        debate["rounds"].append({
            "type": "first_rebuttal",
            agent_a_id: rebuttal_a,
            agent_b_id: rebuttal_b
        })
        
        # Round 2: Counter-rebuttals (responding to the criticism)
        counter_prompt_a = f"""Your opponent criticized your {self.position_label} by saying:
{rebuttal_b}

Address their criticisms directly and explain why your {self.position_label} still holds.
Keep response under 150 words."""

        counter_prompt_b = f"""Your opponent criticized your {self.position_label} by saying:
{rebuttal_a}

Address their criticisms directly and explain why your {self.position_label} still holds.
Keep response under 150 words."""

        counter_a = agent_a.generate_response(counter_prompt_a)
        counter_b = agent_b.generate_response(counter_prompt_b)
        
        debate["rounds"].append({
            "type": "counter_rebuttal",
            agent_a_id: counter_a,
            agent_b_id: counter_b
        })
        
        debate["timing"]["duration"] = time.time() - round_start
        
        return debate
    
    def run_phase_2_debates(self):
        """Run all debates with progress tracking"""
        print("\n=== Phase 2: Running Debates ===")
        phase_start = time.time()
        
        debate_pairs = list(combinations(self.agents.keys(), 2))
        
        for agent_a_id, agent_b_id in tqdm(debate_pairs, desc="Running debates"):
            debate = self.run_debate(agent_a_id, agent_b_id)
            self.debates.append(debate)
        
        self.tournament_metrics["phase_durations"]["debates"] = time.time() - phase_start
        
        # Save debates
        with open(self.output_dir / "debates.json", "w") as f:
            json.dump(self.debates, f, indent=2)
    
    def run_phase_3_voting(self):
        """Voting phase with progress tracking"""
        print("\n=== Phase 3: Voting on Debates ===")
        phase_start = time.time()
        
        for i, debate in enumerate(tqdm(self.debates, desc="Collecting votes")):
            debate_votes = []
            participants = debate['participants']
            
            # Get votes from non-participants
            for agent_id, agent in self.agents.items():
                if agent_id not in participants:
                    debate_summary = self._format_debate_for_voting(debate, i)
                    vote_prompt = f"""{debate_summary}

Based on the strength of arguments and rebuttals, which {self.position_label} is more convincing?
Reply with only 'A' or 'B' and one sentence explaining why."""
                    
                    vote_response = agent.generate_response(vote_prompt)
                    
                    # Parse vote
                    vote = "A" if "A" in vote_response[:10] else "B"
                    winner_id = participants[0] if vote == "A" else participants[1]
                    
                    debate_votes.append({
                        "voter_id": agent_id,
                        "winner_id": winner_id,
                        "reasoning": vote_response,
                        "vote": vote
                    })
            
            self.votes[f"debate_{i}"] = {
                "participants": participants,
                "votes": debate_votes
            }
        
        self.tournament_metrics["phase_durations"]["voting"] = time.time() - phase_start
        
        # Save votes
        with open(self.output_dir / "votes.json", "w") as f:
            json.dump(self.votes, f, indent=2)
    
    def _format_debate_for_voting(self, debate: Dict, debate_index: int) -> str:
        """Format debate for viewing by voters"""
        p = debate['participants']
        r = debate['rounds']
        
        # Get initial positions from stored data
        pos_a = self.positions[p[0]]["position"]
        pos_b = self.positions[p[1]]["position"]
        
        return f"""Judge this debate about {self.position_label}s.

=== Initial Positions ===
Position A ({p[0]}): {pos_a}

Position B ({p[1]}): {pos_b}

=== Debate ===
A's criticism of B: {r[0][p[0]]}

B's criticism of A: {r[0][p[1]]}

A's defense: {r[1][p[0]]}

B's defense: {r[1][p[1]]}"""
    
    def calculate_results(self):
        """Calculate final results and performance metrics"""
        print("\n=== Calculating Results ===")
        
        # Win counts
        win_counts = {agent_id: 0 for agent_id in self.agents.keys()}
        
        for debate_id, vote_data in self.votes.items():
            votes = vote_data['votes']
            winner_count = {}
            
            for vote in votes:
                winner_id = vote['winner_id']
                winner_count[winner_id] = winner_count.get(winner_id, 0) + 1
            
            debate_winner = max(winner_count, key=winner_count.get)
            win_counts[debate_winner] += 1
        
        rankings = sorted(win_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Collect performance metrics
        agent_metrics = {
            agent_id: agent.get_metrics() 
            for agent_id, agent in self.agents.items()
        }
        
        # Save comprehensive results
        results = {
            "tournament_info": {
                "num_agents": self.num_agents,
                "topic_question": self.topic_question,
                "position_label": self.position_label,
                "timestamp": datetime.now().isoformat(),
                "duration": self.tournament_metrics
            },
            "rankings": rankings,
            "win_counts": win_counts,
            "agent_performance": agent_metrics
        }
        
        with open(self.output_dir / "tournament_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print("\n=== Final Rankings ===")
        for i, (agent_id, wins) in enumerate(rankings):
            agent = self.agents[agent_id]
            avg_time = agent.performance_metrics["avg_response_time"]
            print(f"{i+1}. {agent_id} ({agent.model}): {wins} wins, avg response: {avg_time:.2f}s")
        
        print(f"\nTotal tournament duration: {self.tournament_metrics['total_duration']:.2f} seconds")
    
    def run_tournament(self):
        """Run complete tournament"""
        print(f"=== Flexible Debate Tournament ===")
        print(f"Topic: {self.topic_question[:80]}...")
        print(f"Position Type: {self.position_label}")
        print(f"Agents: {self.num_agents}")
        
        self.tournament_metrics["start_time"] = time.time()
        
        # Run phases
        self.run_phase_1_positions()
        self.run_phase_2_debates()
        self.run_phase_3_voting()
        
        self.tournament_metrics["end_time"] = time.time()
        self.tournament_metrics["total_duration"] = (
            self.tournament_metrics["end_time"] - 
            self.tournament_metrics["start_time"]
        )
        
        self.calculate_results()
        
        print(f"\nResults saved to {self.output_dir}/")




