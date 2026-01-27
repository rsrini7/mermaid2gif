"""
Test dynamic filenames and automatic cleanup.
Verifies that:
1. Video files are generated with timestamps (avoiding overrides)
2. GIF files preserve the timestamp
3. Intermediate video files are deleted after successful GIF generation
"""
import asyncio
from src.core.graph import run_graph
from src.core.state import GraphState
from pathlib import Path
import re

def test_dynamic_cleanup():
    mermaid_code = """flowchart TD
    A["Start Loop"] --> B["Read PRD.json + progress.txt"]
    B --> C["Pick Next Task"]
    C --> D["Implement + Feedback Loops<br/>(tests, lint, types)"]
    D --> E{"Passes?"}
    E -->|No| F["Fix & Retry"]
    F --> D
    E -->|Yes| G["Commit Code"]
    G --> H["Update PRD + progress.txt"]
    H --> I{"All Tasks Done?"}
    I -->|No| A
    I -->|Yes| J["Complete"]"""
    
    state = GraphState(
        raw_input=mermaid_code,
        raw_input_type="mermaid",
        mermaid_code=mermaid_code,
        duration=3,  # Short duration for quick test
        artifacts={},
        errors=[]
    )
    
    print("=" * 80)
    print("TESTING DYNAMIC FILENAMES & CLEANUP")
    print("=" * 80)
    
    try:
        final_state = run_graph(state)
        
        gif_path = final_state.get('gif_path')
        video_path_str = final_state.get('artifacts', {}).get('video_path')
        
        # Check if GIF generated
        if not gif_path or not Path(gif_path).exists():
            print("[X] GIF generation failed")
            return False
            
        print(f"[OK] GIF generated: {gif_path}")
        
        # Verify timestamp pattern in filename
        # Expected: mermaid_YYYYMMDD_HHMMSS_mmm.gif
        filename = Path(gif_path).name
        timestamp_pattern = r"mermaid_\d{8}_\d{6}_\d+\.gif"
        
        if re.match(timestamp_pattern, filename):
            print("[OK] Filename contains timestamp pattern")
        else:
            print(f"[X] Filename does NOT match timestamp pattern: {filename}")
            return False
            
        # Verify video file cleanup
        # The video path in state points to the file that WAS created
        if video_path_str:
            video_path = Path(video_path_str)
            if not video_path.exists():
                print(f"[OK] Intermediate video file cleaned up: {video_path}")
            else:
                print(f"[X] Intermediate video file STILL EXISTS: {video_path}")
                return False
        else:
            print("[!] Video path not found in artifacts")
            
        return True
        
    except Exception as e:
        print(f"[X] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_dynamic_cleanup():
        print("\n" + "=" * 80)
        print("✅ DYNAMIC CLEANUP TEST PASSED")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("❌ DYNAMIC CLEANUP TEST FAILED")
        print("=" * 80)
