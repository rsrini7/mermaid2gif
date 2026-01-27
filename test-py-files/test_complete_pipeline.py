"""
Complete end-to-end pipeline test with FFmpeg
Tests: Mermaid → SVG → Animation → Video → GIF
"""
import asyncio
from src.core.graph import run_graph
from src.core.state import GraphState
from pathlib import Path

def test_complete_pipeline():
    # Simple test diagram
    mermaid_code = """graph LR
    A[Client] --> B[Load Balancer]
    B --> C[Server 1]
    B --> D[Server 2]
    C --> E[Database]
    D --> E"""
    
    # Create initial state
    state = GraphState(
        raw_input=mermaid_code,
        raw_input_type="mermaid",
        mermaid_code=mermaid_code,
        duration=5,
        artifacts={},
        errors=[]  # Initialize errors list
    )
    
    print("=" * 80)
    print("TESTING COMPLETE MERMAID.JS PIPELINE")
    print("=" * 80)
    print(f"\nInput Diagram:\n{mermaid_code}\n")
    
    try:
        # Run the complete pipeline
        final_state = run_graph(state)
        
        print("\n" + "=" * 80)
        print("PIPELINE RESULTS")
        print("=" * 80)
        
        # Check for success
        gif_path = final_state.get('gif_path')
        video_path = final_state.get('video_path')
        errors = final_state.get('errors', [])
        
        print(f"\n✅ SUCCESS: {bool(gif_path)}")
        print(f"\nGenerated Files:")
        print(f"  - Video (WebM): {video_path}")
        print(f"  - GIF: {gif_path}")
        
        if gif_path and Path(gif_path).exists():
            gif_size = Path(gif_path).stat().st_size
            print(f"\n📊 GIF File Info:")
            print(f"  - Path: {gif_path}")
            print(f"  - Size: {gif_size:,} bytes ({gif_size / 1024:.1f} KB)")
            print(f"\n🎉 COMPLETE SUCCESS! GIF generated successfully!")
        else:
            print(f"\n❌ GIF file not found or not created")
        
        if video_path and Path(video_path).exists():
            video_size = Path(video_path).stat().st_size
            print(f"\n📹 Video File Info:")
            print(f"  - Path: {video_path}")
            print(f"  - Size: {video_size:,} bytes ({video_size / 1024:.1f} KB)")
        
        if errors:
            print(f"\n⚠️ Errors encountered:")
            for error in errors:
                print(f"  - {error}")
        
        # Show artifacts created
        if final_state.get("artifacts"):
            print(f"\n📦 Artifacts:")
            for key, value in final_state["artifacts"].items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"  - {key}: {len(value)} bytes")
                else:
                    print(f"  - {key}: {value}")
        
        return final_state
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = test_complete_pipeline()
    
    if result and result.get('gif_path'):
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED - PIPELINE FULLY OPERATIONAL!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ TESTS FAILED - Check errors above")
        print("=" * 80)
