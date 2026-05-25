
from scientist.discovery_engine import get_discovery_engine

def test_discovery():
    engine = get_discovery_engine()
    print("Running a quick discovery on 'The impact of neural-symbolic integration on AGI'...")
    result = engine.run_quick_discovery("The impact of neural-symbolic integration on AGI")
    print("\n--- Result ---")
    print(result.encode('utf-8').decode('utf-8', errors='ignore'))

if __name__ == "__main__":
    test_discovery()
