"""
Mock-based smoke test for Mermaid2GIF system.

This test validates the complete LangGraph workflow WITHOUT real API calls
or browser launches. All external dependencies are mocked.
"""

import unittest
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import json

from src.core.state import create_initial_state
from src.core.graph import run_graph


class TestMermaidGIFSmoke(unittest.TestCase):
    """
    Smoke test for end-to-end Mermaid2GIF workflow.
    
    Tests the complete graph execution with mocked dependencies:
    - LiteLLM API calls
    - Playwright browser automation
    - FFmpeg processing
    """
    
    @patch('src.core.graph.capture_controller')
    @patch('src.core.graph.animation_applicator')
    @patch('src.core.graph.render_diagram_node')
    @patch('src.agents.intent.get_config')
    @patch('src.agents.fixer.get_config')
    @patch('src.engine.mermaid_renderer.get_config')
    @patch('src.engine.ffmpeg_processor.get_config')
    @patch('src.engine.mermaid_validator.get_config')
    @patch('src.engine.animation_applicator.get_config')
    @patch('src.engine.capture_controller.get_config')
    @patch('src.engine.ffmpeg_processor.ffmpeg')
    @patch('src.engine.mermaid_renderer.async_playwright')
    @patch('src.agents.intent.litellm.completion')
    @patch('src.agents.fixer.litellm.completion')
    def test_end_to_end_success(
        self,
        mock_fixer_llm,
        mock_intent_llm,
        mock_playwright,
        mock_ffmpeg,
        mock_capture_config,
        mock_animation_config,
        mock_validator_config,
        mock_ffmpeg_config,
        mock_mermaid_config,
        mock_fixer_config,
        mock_intent_config,
        mock_render_diagram,
        mock_animation_applicator,
        mock_capture_controller,
    ):
        """
        Test successful end-to-end execution with mocked dependencies.
        
        Flow:
        1. Input: "Create a flowchart of A -> B"
        2. Intent agent generates Mermaid code
        3. Validator passes (placeholder always passes)
        4. Mermaid renderer generates SVG
        5. Animation applied
        6. Video captured
        7. FFmpeg converts to GIF
        8. Success state reached
        """
        # ============================================
        # Mock Configuration
        # ============================================
        mock_config = Mock()
        mock_config.openrouter_api_key = "sk-or-test-key-12345"
        mock_config.litellm_model = "openrouter/anthropic/claude-3.5-sonnet"
        mock_config.browser_timeout_ms = 30000
        mock_config.chromium_executable_path = None
        mock_config.viewport_width = 1920
        mock_config.viewport_height = 1080
        mock_config.default_fps = 30
        mock_config.default_animation_duration = 5.0
        mock_config.log_level = "INFO"
        mock_config.structured_logging = True
        
        # Apply mock config to all get_config calls
        mock_intent_config.return_value = mock_config
        mock_fixer_config.return_value = mock_config
        mock_mermaid_config.return_value = mock_config
        mock_ffmpeg_config.return_value = mock_config
        mock_validator_config.return_value = mock_config
        mock_animation_config.return_value = mock_config
        mock_capture_config.return_value = mock_config
        
        # Mock render_diagram_node to avoid async/sync issues
        def render_side_effect(state):
            state["diagram_rendered"] = True
            return state
        mock_render_diagram.side_effect = render_side_effect
        
        # Mock animation_applicator to avoid Playwright browser launch
        def animation_side_effect(state):
            state["animation_applied"] = True
            return state
        mock_animation_applicator.side_effect = animation_side_effect
        
        # Mock capture_controller to set video_path
        def capture_side_effect(state):
            # Create a temporary video file
            import tempfile
            temp_dir = Path(tempfile.mkdtemp(prefix="mermaid_gif_"))
            video_path = temp_dir / "output.webm"
            video_path.write_bytes(b"fake video content")
            state["video_path"] = str(video_path)
            return state
        mock_capture_controller.side_effect = capture_side_effect
        
        # ============================================
        # Mock LiteLLM Intent Agent Response
        # ============================================
        mock_intent_response = Mock()
        mock_intent_response.choices = [Mock()]
        mock_intent_response.choices[0].message.content = json.dumps({
            "mermaid": "graph LR\n    A[Start] --> B[End]",
            "animation": {
                "duration": 5.0,
                "preset": "default"
            }
        })
        mock_intent_llm.return_value = mock_intent_response
        
        # ============================================
        # Mock LiteLLM Fix Agent Response (not used in success path)
        # ============================================
        mock_fixer_response = Mock()
        mock_fixer_response.choices = [Mock()]
        mock_fixer_response.choices[0].message.content = json.dumps({
            "mermaid": "graph LR\n    A[Start] --> B[End]"
        })
        mock_fixer_llm.return_value = mock_fixer_response
        
        # ============================================
        # Mock Playwright Browser
        # ============================================
        # Create mock page with async methods
        mock_page = AsyncMock()
        
        # Mock page.goto()
        mock_page.goto = AsyncMock()
        
        # Mock page.wait_for_load_state()
        mock_page.wait_for_load_state = AsyncMock()
        
        # Mock page.evaluate() - simulates successful import
        async def mock_evaluate(script, *args):
            if "importData" in script:
                return {"success": True}
            elif "geDiagramContainer" in script:
                # Return valid diagram bounds (> 10px)
                return {"width": 800, "height": 600}
            return {}
        
        mock_page.evaluate = AsyncMock(side_effect=mock_evaluate)
        
        # Mock page.wait_for_selector()
        mock_page.wait_for_selector = AsyncMock()
        
        # Mock page.locator().screenshot()
        mock_locator = Mock()
        mock_locator.screenshot = AsyncMock()
        mock_page.locator = Mock(return_value=mock_locator)
        
        # Mock page.close()
        mock_page.close = AsyncMock()
        
        # Mock page.set_default_timeout()
        mock_page.set_default_timeout = Mock()
        
        # Create mock browser
        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()
        
        # Create mock playwright instance
        mock_pw_instance = AsyncMock()
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        
        # Mock async_playwright context manager
        mock_pw_context = AsyncMock()
        mock_pw_context.__aenter__ = AsyncMock(return_value=mock_pw_instance)
        mock_pw_context.__aexit__ = AsyncMock()
        mock_pw_context.start = AsyncMock(return_value=mock_pw_instance)
        
        mock_playwright.return_value = mock_pw_context
        
        # ============================================
        # Mock FFmpeg
        # ============================================
        # Mock ffmpeg.input()
        mock_input_stream = Mock()
        mock_input_stream.video = Mock()
        
        # Mock split filter
        mock_split = [Mock(), Mock()]
        mock_input_stream.video.filter = Mock(return_value=mock_split)
        
        # Mock palette generation
        mock_split[0].filter = Mock(return_value=Mock())
        
        # Mock scaling
        mock_scaled = Mock()
        mock_split[1].filter = Mock(return_value=mock_scaled)
        
        # Mock filter (paletteuse)
        mock_output_stream = Mock()
        mock_output_stream.filter = Mock(return_value=mock_output_stream)
        
        # Mock ffmpeg.filter()
        mock_ffmpeg.filter = Mock(return_value=mock_output_stream)
        
        # Mock ffmpeg.output()
        mock_output = Mock()
        mock_output.overwrite_output = Mock(return_value=mock_output)
        mock_output.run = Mock()
        mock_ffmpeg.output = Mock(return_value=mock_output)
        
        # Mock ffmpeg.input()
        mock_ffmpeg.input = Mock(return_value=mock_input_stream)
        
        # Mock ffmpeg.probe() for video info
        mock_ffmpeg.probe = Mock(return_value={
            "format": {"duration": "5.0"},
            "streams": [{
                "codec_type": "video",
                "width": 1200,
                "height": 800,
                "r_frame_rate": "30/1"
            }]
        })
        
        # ============================================
        # Create temporary output files
        # ============================================
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create dummy video file
            video_path = tmpdir_path / "output.webm"
            video_path.write_bytes(b"fake video content")
            
            # Create dummy GIF file (FFmpeg mock will "create" this)
            gif_path = tmpdir_path / "output.gif"
            
            # Mock FFmpeg run to create the GIF file
            def mock_run_side_effect(*args, **kwargs):
                # Create the GIF file when FFmpeg runs
                gif_path.write_bytes(b"GIF89a" + b"\x00" * 100)  # Minimal GIF header + data
                return None
            
            mock_output.run.side_effect = mock_run_side_effect
            
            # Also patch the video_path in capture_controller placeholder
            with patch('src.core.graph.capture_controller') as mock_capture:
                def capture_side_effect(state):
                    state["video_path"] = str(video_path)
                    return state
                
                mock_capture.side_effect = capture_side_effect
                
                # ============================================
                # Execute Graph
                # ============================================
                initial_state = create_initial_state(
                    raw_input="Create a flowchart of A -> B",
                    input_type="text"
                )
                
                final_state = run_graph(initial_state)
                
                # ============================================
                # Assertions
                # ============================================
                # Verify successful completion
                self.assertIsNotNone(final_state.get("gif_path"), "GIF path should be populated")
                self.assertEqual(len(final_state.get("errors", [])), 0, "No errors should occur")
                
                # Verify Mermaid code was generated
                self.assertIsNotNone(final_state.get("mermaid_code"), "Mermaid code should be generated")
                self.assertIn("A", final_state["mermaid_code"], "Mermaid should contain node A")
                self.assertIn("B", final_state["mermaid_code"], "Mermaid should contain node B")
                
                # Verify animation manifest
                self.assertIsNotNone(final_state.get("animation_manifest"), "Animation manifest should exist")
                
                # Verify diagram was rendered
                self.assertTrue(final_state.get("diagram_rendered", False), "Diagram should be rendered")
                
                # Verify animation was applied
                self.assertTrue(final_state.get("animation_applied", False), "Animation should be applied")
                
                # Verify video path was set
                self.assertIsNotNone(final_state.get("video_path"), "Video path should be set")
                
                # Verify LiteLLM was called
                mock_intent_llm.assert_called_once()
                
                print("PASS: Smoke test - End-to-end workflow successful")


if __name__ == "__main__":
    unittest.main()
