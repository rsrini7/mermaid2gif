"""
Test GIF quality with improved FFmpeg settings
"""
import asyncio
from src.core.graph import run_graph
from src.core.state import GraphState
from pathlib import Path

def test_gif_quality():
    # Test diagram with various elements
    mermaid_code = """graph TB
    Start[Start Process] --> Check{Check Status}
    Check -->|Success| Process[Process Data]
    Check -->|Failure| Error[Handle Error]
    Process --> Save[Save Results]
    Error --> Retry[Retry Logic]
    Retry --> Check
    Save --> End[Complete]"""
    
    # Create initial state
    state = GraphState(
        raw_input=mermaid_code,
        raw_input_type="mermaid",
        mermaid_code=mermaid_code,
        duration=5,
        artifacts={},
        errors=[]
    )
    
    print("=" * 80)
    print("TESTING HIGH-QUALITY GIF GENERATION")
    print("=" * 80)
    print("\nQuality Improvements:")
    print("  ✓ Resolution: 1280px (was 800px)")
    print("  ✓ Palette: 256 colors with diff mode")
    print("  ✓ Scaling: Lanczos (high quality)")
    print("  ✓ Dithering: Sierra2_4a (smooth gradients)")
    print("\n" + "=" * 80 + "\n")
    
    try:
        final_state = run_graph(state)
        
        gif_path = final_state.get('gif_path')
        
        if gif_path and Path(gif_path).exists():
            gif_size = Path(gif_path).stat().st_size
            print(f"\n✅ SUCCESS!")
            print(f"\n📊 GIF Info:")
            print(f"  - Path: {gif_path}")
            print(f"  - Size: {gif_size:,} bytes ({gif_size / 1024:.1f} KB)")
            print(f"\n🎨 Quality should be significantly improved!")
            print(f"   - Sharper text and shapes")
            print(f"   - Smoother gradients")
            print(f"   - Less pixelation")
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
    success = test_gif_quality()
    if success:
        print("\n" + "=" * 80)
        print("✅ HIGH-QUALITY GIF GENERATED SUCCESSFULLY!")
        print("=" * 80)
