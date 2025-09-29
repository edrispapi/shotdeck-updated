#!/usr/bin/env python3
"""
Run tests for deck_search
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from run_all_tests import run_test_script

if __name__ == "__main__":
    print("🧪 Running Deck Search Tests")
    print("=" * 40)

    success = run_test_script('test_deck_search.py', 'Deck Search')

    if success:
        print("\n✅ All Deck Search tests passed!")
    else:
        print("\n❌ Some Deck Search tests failed!")

    sys.exit(0 if success else 1)
