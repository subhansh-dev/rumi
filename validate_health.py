
from brain.agi_orchestrator import get_agi_orchestrator
import json

def health_check():
    orchestrator = get_agi_orchestrator()
    status = orchestrator.get_system_status()
    print(json.dumps(status, indent=2))

if __name__ == "__main__":
    health_check()
