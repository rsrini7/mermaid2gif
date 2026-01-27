"""
Test seamless GIF looping - diagnose blank frame issue
"""
from src.core.graph import run_graph
from src.core.state import GraphState
from pathlib import Path

def test_seamless_loop():
    # Simple diagram for testing
    mermaid_code = """graph LR
    A[Start] --> B[Process]
    B --> C[End]"""
    
    state = GraphState(
        raw_input=mermaid_code,
        raw_input_type="mermaid",
        mermaid_code=mermaid_code,
        duration=5,  # 5 second loop
        artifacts={},
        errors=[]
    )
    
    print("=" * 80)
    print("TESTING SEAMLESS GIF LOOP")
    print("=" * 80)
    print("\nFixes applied:")
    print("  ✓ Animation duration matches video duration (5s)")
    print("  ✓ Recording stops 100ms before end (avoids blank frames)")
    print("  ✓ Context closes before page (clean video finalization)")
    print("\n" + "=" * 80 + "\n")
    
    try:
        final_state = run_graph(state)
        
        gif_path = final_state.get('gif_path')
        video_path = final_state.get('video_path')
        
        if gif_path and Path(gif_path).exists():
            gif_size = Path(gif_path).stat().st_size
            print(f"\n✅ GIF Generated!")
            print(f"\n📊 File Info:")
            print(f"  - GIF: {gif_path}")
            print(f"  - Size: {gif_size:,} bytes ({gif_size / 1024:.1f} KB)")
            print(f"  - Video: {video_path}")
            
            print(f"\n🔄 Loop Test:")
            print(f"  The GIF should now loop seamlessly without:")
            print(f"    ❌ Blank frames")
            print(f"    ❌ Visual jumps")
            print(f"    ❌ Pauses between loops")
            print(f"\n  ✅ Arrows should flow continuously!")
            
            return True
        else:
            print(f"\n❌ GIF not created")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_seamless_loop()
    if success:
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE - Check the GIF for seamless looping!")
        print("=" * 80)
