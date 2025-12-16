"""
#!/usr/bin/env python3
Command-line interface for health claim checking (alternative to Streamlit).

Usage: python main.py "Does hot water cure malaria?"
"""

import sys
from config import Config
from data_loader import get_all_myths
from pubmed_search import PubMedSearcher
from vector_store import HealthKnowledgeBase
from agent import HealthCheckAgent

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py 'Your health claim here'")
        print("\nExamples:")
        print("  python main.py 'Does hot water cure malaria?'")
        print("  python main.py 'Can sugar cause diabetes?'")
        sys.exit(1)
    
    claim = " ".join(sys.argv[1:])
    
    print("🏥 Nigerian Health Claim Checker")
    print("=" * 70)
    print(f"\nChecking claim: {claim}\n")
    
    try:
        # Initialize system
        print("⏳ Initializing system...")
        config = Config()
        config.validate()
        
        pubmed = PubMedSearcher(config.PUBMED_EMAIL)
        kb = HealthKnowledgeBase(config)
        
        # Index myths if needed
        if kb.get_count() == 0:
            print("📚 Indexing health myths database...")
            myths = get_all_myths()
            kb.index_myths(myths)
        
        agent = HealthCheckAgent(config, kb, pubmed)
        print("✓ System ready!\n")
        
        # Check claim
        print("🔍 Analyzing claim...\n")
        result = agent.check_claim(claim)
        
        print("=" * 70)
        print("RESULT:")
        print("=" * 70)
        print(result['response'])
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()