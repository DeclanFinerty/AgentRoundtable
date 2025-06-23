
from DebateClass import DebateAgent, DebateTournament


# Example usage:
if __name__ == "__main__":
    # Society debate
    tournament1 = DebateTournament(
        num_agents=5,
        topic_question="Describe your ideal society in 200 words.",
        position_label="ideal society"
    )

    # Run whichever you want
    tournament1.run_tournament()