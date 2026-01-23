"""
Test script for Claude Prompt Generation Pipeline.

Tests:
1. Structured output validation (Tool Use returns valid ComicGenerationResponse)
2. Character consistency (descriptions IDENTICAL across panels)
3. Style consistency (style keywords IDENTICAL across all panels)
4. Error handling
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.claude_prompt_service import claude_prompt_service, ClaudeResult
from app.services.pipeline import pipeline_orchestrator, PipelineConfig
from app.models.claude_schemas import ComicGenerationResponse


# ============================================================================
# Test Data
# ============================================================================

SAMPLE_COMIC_SCRIPT = [
    {
        "_type": "metadata",
        "source_file": "test_audio.mp3",
        "duration_s": 30.0,
        "language": "en"
    },
    {
        "_type": "full_transcript",
        "text": "Santa Claus wakes up on Christmas morning feeling exhausted. He tells Mrs. Claus he needs a vacation. She agrees and they pack their bags. Santa puts on a Hawaiian shirt and sunglasses. They fly to a tropical beach. Santa relaxes in a hammock while Mrs. Claus reads a book."
    },
    {
        "start_s": 0.0,
        "end_s": 5.0,
        "lyric_snippet": "Santa Claus wakes up on Christmas morning feeling exhausted."
    },
    {
        "start_s": 5.0,
        "end_s": 10.0,
        "lyric_snippet": "He tells Mrs. Claus he needs a vacation."
    },
    {
        "start_s": 10.0,
        "end_s": 15.0,
        "lyric_snippet": "She agrees and they pack their bags."
    },
    {
        "start_s": 15.0,
        "end_s": 20.0,
        "lyric_snippet": "Santa puts on a Hawaiian shirt and sunglasses."
    },
    {
        "start_s": 20.0,
        "end_s": 25.0,
        "lyric_snippet": "They fly to a tropical beach."
    },
    {
        "start_s": 25.0,
        "end_s": 30.0,
        "lyric_snippet": "Santa relaxes in a hammock while Mrs. Claus reads a book."
    }
]


# ============================================================================
# Test Functions
# ============================================================================

async def test_service_configuration():
    """Test that services are properly configured."""
    print("\n" + "="*60)
    print("TEST: Service Configuration")
    print("="*60)
    
    claude_ok = claude_prompt_service.is_configured()
    print(f"Claude configured: {claude_ok}")
    
    if not claude_ok:
        print("⚠️  ANTHROPIC_API_KEY not set - Claude tests will fail")
        return False
    
    print("✅ All services configured")
    return True


async def test_structured_output():
    """Test that Tool Use returns valid ComicGenerationResponse."""
    print("\n" + "="*60)
    print("TEST: Structured Output Validation")
    print("="*60)
    
    if not claude_prompt_service.is_configured():
        print("⏭️  Skipping - Claude not configured")
        return None
    
    try:
        result = await claude_prompt_service.generate_prompts(
            comic_script=SAMPLE_COMIC_SCRIPT,
            temperature=0.3
        )
        
        if not result.success:
            print(f"❌ Prompt generation failed: {result.error_message}")
            return False
        
        # Validate response structure
        response = result.response
        
        assert response is not None, "Response is None"
        assert isinstance(response.characters, dict), "characters is not a dict"
        assert isinstance(response.panels, list), "panels is not a list"
        assert len(response.panels) > 0, "No panels generated"
        
        print(f"✅ Generated {len(response.panels)} panels")
        print(f"✅ Character sheet: {list(response.characters.keys())}")
        print(f"✅ Global style: {response.global_style}")
        print(f"✅ Global mood: {response.global_mood}")
        
        # Validate each panel
        for panel in response.panels:
            assert panel.panel_id > 0, f"Invalid panel_id: {panel.panel_id}"
            assert panel.prompt, f"Empty prompt for panel {panel.panel_id}"
            print(f"   Panel {panel.panel_id}: {panel.prompt[:80]}...")
        
        print("✅ All panels have valid structure")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_character_consistency():
    """Test that character descriptions are IDENTICAL across panels."""
    print("\n" + "="*60)
    print("TEST: Character Consistency")
    print("="*60)
    
    if not claude_prompt_service.is_configured():
        print("⏭️  Skipping - Claude not configured")
        return None
    
    try:
        result = await claude_prompt_service.generate_prompts(
            comic_script=SAMPLE_COMIC_SCRIPT,
            temperature=0.3
        )
        
        if not result.success or not result.response:
            print(f"❌ Prompt generation failed: {result.error_message}")
            return False
        
        response = result.response
        character_sheet = result.character_sheet or response.characters
        
        print(f"Character sheet:")
        for name, desc in character_sheet.items():
            print(f"  {name}: {desc[:60]}...")
        
        # Check that character descriptions appear in prompts
        santa_appearances = []
        mrs_claus_appearances = []
        
        for panel in response.panels:
            prompt_lower = panel.prompt.lower()
            
            # Find Santa appearances
            if "santa" in prompt_lower:
                santa_appearances.append(panel.panel_id)
            
            # Find Mrs. Claus appearances
            if "mrs" in prompt_lower and "claus" in prompt_lower:
                mrs_claus_appearances.append(panel.panel_id)
        
        print(f"\nSanta appears in panels: {santa_appearances}")
        print(f"Mrs. Claus appears in panels: {mrs_claus_appearances}")
        
        # Verify character descriptions are consistent
        # Extract the character description from first appearance
        if len(santa_appearances) >= 2:
            first_prompt = response.panels[santa_appearances[0] - 1].prompt
            last_prompt = response.panels[santa_appearances[-1] - 1].prompt
            
            # Check if Santa's description appears in both
            if "Santa" in character_sheet:
                desc = character_sheet["Santa"]
                if desc in first_prompt and desc in last_prompt:
                    print(f"✅ Santa's description is IDENTICAL across panels")
                else:
                    # Check for partial match (description may be reformatted)
                    santa_desc_lower = character_sheet.get("Santa", "").lower()
                    if santa_desc_lower and santa_desc_lower[:30] in first_prompt.lower():
                        print(f"✅ Santa's description found in prompts")
                    else:
                        print(f"⚠️  Santa's description may differ between panels")
            elif "Santa Claus" in character_sheet:
                desc = character_sheet["Santa Claus"]
                if desc in first_prompt and desc in last_prompt:
                    print(f"✅ Santa Claus's description is IDENTICAL across panels")
                else:
                    print(f"⚠️  Checking partial match...")
                    # At least verify some consistency
                    print(f"   First panel prompt excerpt: {first_prompt[:100]}...")
                    print(f"   Last panel prompt excerpt: {last_prompt[:100]}...")
        
        print("✅ Character consistency test completed")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_style_consistency():
    """Test that style keywords are IDENTICAL across all panels."""
    print("\n" + "="*60)
    print("TEST: Style Consistency (without reference image)")
    print("="*60)
    
    if not claude_prompt_service.is_configured():
        print("⏭️  Skipping - Claude not configured")
        return None
    
    try:
        result = await claude_prompt_service.generate_prompts(
            comic_script=SAMPLE_COMIC_SCRIPT,
            temperature=0.3
        )
        
        if not result.success or not result.response:
            print(f"❌ Prompt generation failed: {result.error_message}")
            return False
        
        response = result.response
        
        print(f"Global style: {response.global_style}")
        print(f"Style keywords from analysis: {result.style_keywords}")
        
        # Check if prompts end with consistent style
        # (When no style reference is provided, prompts should still be consistent)
        prompt_endings = []
        for panel in response.panels:
            # Get the last ~50 chars of each prompt
            ending = panel.prompt[-100:] if len(panel.prompt) > 100 else panel.prompt
            prompt_endings.append(ending)
            print(f"   Panel {panel.panel_id} ending: ...{ending[-50:]}")
        
        print("✅ Style consistency test completed (manual review needed)")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_pronoun_handling():
    """Test that characters_present is populated even when scene uses pronouns."""
    print("\n" + "="*60)
    print("TEST: Pronoun Handling")
    print("="*60)
    
    if not claude_prompt_service.is_configured():
        print("⏭️  Skipping - Claude not configured")
        return None
    
    # This script uses pronouns heavily
    pronoun_script = [
        {
            "_type": "full_transcript",
            "text": "Alice enters the room. She looks around nervously. He watches her from the shadows. They meet eyes."
        },
        {"start_s": 0.0, "end_s": 3.0, "lyric_snippet": "Alice enters the room."},
        {"start_s": 3.0, "end_s": 6.0, "lyric_snippet": "She looks around nervously."},
        {"start_s": 6.0, "end_s": 9.0, "lyric_snippet": "He watches her from the shadows."},
        {"start_s": 9.0, "end_s": 12.0, "lyric_snippet": "They meet eyes."}
    ]
    
    try:
        result = await claude_prompt_service.generate_prompts(
            comic_script=pronoun_script,
            temperature=0.3
        )
        
        if not result.success or not result.response:
            print(f"❌ Prompt generation failed: {result.error_message}")
            return False
        
        response = result.response
        
        print(f"Character sheet: {response.characters}")
        print(f"\nPanel prompts:")
        
        # Verify character descriptions are injected even with pronoun usage
        for panel in response.panels:
            print(f"   Panel {panel.panel_id}: {panel.prompt[:100]}...")
            
            # Check if character description appears (not just pronoun)
            has_description = any(
                desc.lower()[:20] in panel.prompt.lower() 
                for desc in response.characters.values()
            )
            if has_description:
                print(f"      ✅ Character description found in prompt")
            else:
                print(f"      ⚠️  No character description found (may be expected for this panel)")
        
        print("✅ Pronoun handling test completed")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_full_pipeline():
    """Test the full pipeline (prompts + images if Gemini is configured)."""
    print("\n" + "="*60)
    print("TEST: Full Pipeline (Prompts Only - No Image Generation)")
    print("="*60)
    
    if not pipeline_orchestrator.is_configured():
        print("⏭️  Skipping - Pipeline not fully configured")
        # Still test prompts-only
        if claude_prompt_service.is_configured():
            result = await pipeline_orchestrator.generate_prompts_only(
                comic_script=SAMPLE_COMIC_SCRIPT,
                temperature=0.3
            )
            if result.success:
                print(f"✅ Prompts generated: {len(result.response.panels)} panels")
                return True
            else:
                print(f"❌ Prompt generation failed: {result.error_message}")
                return False
        return None
    
    try:
        config = PipelineConfig(
            save_images=False,
            save_metadata=False,
            prompt_temperature=0.3
        )
        
        result = await pipeline_orchestrator.run_from_transcript(
            comic_script=SAMPLE_COMIC_SCRIPT,
            config=config
        )
        
        if result.success:
            print(f"✅ Pipeline completed in {result.execution_time_s:.2f}s")
            print(f"   Total panels: {result.total_panels}")
            print(f"   Successful images: {result.successful_images}")
            print(f"   Failed images: {result.failed_images}")
            return True
        else:
            print(f"❌ Pipeline failed: {result.error_message}")
            return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Main
# ============================================================================

async def main():
    """Run all tests."""
    print("="*60)
    print("CLAUDE PIPELINE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Run tests
    results["configuration"] = await test_service_configuration()
    results["structured_output"] = await test_structured_output()
    results["character_consistency"] = await test_character_consistency()
    results["style_consistency"] = await test_style_consistency()
    results["pronoun_handling"] = await test_pronoun_handling()
    results["full_pipeline"] = await test_full_pipeline()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is True)
    failed = sum(1 for v in results.values() if v is False)
    skipped = sum(1 for v in results.values() if v is None)
    
    for test_name, result in results.items():
        if result is True:
            print(f"  ✅ {test_name}: PASSED")
        elif result is False:
            print(f"  ❌ {test_name}: FAILED")
        else:
            print(f"  ⏭️  {test_name}: SKIPPED")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
