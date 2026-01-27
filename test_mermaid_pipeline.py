"""
Test the new Mermaid.js pipeline end-to-end
"""
import asyncio
from src.core.graph import run_graph
from src.core.state import GraphState

async def test_mermaid_pipeline():
    # Simple test diagram
    mermaid_code = """graph TD
    A[Start] --> B[Process]
    B --> C[End]"""
    
    # Create initial state
    state = GraphState(
        raw_input=mermaid_code,
        raw_input_type="mermaid",
        mermaid_code=mermaid_code,
        duration=5,
        artifacts={}
    )
    
    print("Testing Mermaid.js pipeline...")
    print(f"Input: {mermaid_code}")
    
    try:
        # Run the pipeline
        final_state = run_graph(state)
        
        print("\n=== PIPELINE RESULTS ===")
        print(f"Success: {bool(final_state.get('gif_path'))}")
        print(f"GIF Path: {final_state.get('gif_path')}")
        print(f"Errors: {final_state.get('errors', [])}")
        
        if final_state.get("artifacts"):
            print("\nArtifacts created:")
            for key, value in final_state["artifacts"].items():
                if isinstance(value, str):
                    print(f"  - {key}: {len(value)} bytes" if len(value) > 100 else f"  - {key}: {value}")
        
        return final_state
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_mermaid_pipeline())
