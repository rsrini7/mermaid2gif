"""
Test script to debug ER diagram generation
"""
import asyncio
import json
from src.agents.intent import intent_agent
from src.core.state import create_initial_state

async def test_er_diagram():
    # Create initial state
    state = create_initial_state(
        raw_input="Create a simple ER diagram for teacher, department, student relationship",
        input_type="text"
    )
    
    # Call intent agent
    try:
        result_state = intent_agent(state)
        
        print("=" * 80)
        print("GENERATED MERMAID CODE:")
        print("=" * 80)
        print(result_state.get("mermaid_code", "NO CODE GENERATED"))
        print("=" * 80)
        
        if result_state.get("errors"):
            print("\nERRORS:")
            for error in result_state["errors"]:
                print(f"  - {error}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_er_diagram())
