
from brain.agi_orchestrator import get_agi_orchestrator

def test_orchestrator():
    orchestrator = get_agi_orchestrator()
    print("Processing goal: 'Explain the core of Rumi'...")
    result = orchestrator.process_goal("Explain the core of Rumi")
    print(f"Success: {result['success']}")
    print(f"Elapsed: {result['elapsed_seconds']}s")
    print(f"Stages completed: {list(result['stages'].keys())}")

if __name__ == "__main__":
    test_orchestrator()
