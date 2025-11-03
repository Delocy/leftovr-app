#!/usr/bin/env python3
"""
Automated Test Runner for Executive Chef Architecture
Executes all test scenarios from TEST_SCENARIOS.md
"""

import asyncio
from typing import Dict, List, Any
from datetime import datetime


class TestScenario:
    def __init__(self, name: str, inputs: List[str], expected_stages: List[str]):
        self.name = name
        self.inputs = inputs
        self.expected_stages = expected_stages
        self.results: List[Dict[str, Any]] = []
        self.passed = False
        
    def log_result(self, step: int, classification: str, stage: str, output: str):
        self.results.append({
            'step': step,
            'input': self.inputs[step] if step < len(self.inputs) else None,
            'classification': classification,
            'stage': stage,
            'output_preview': output[:200] + '...' if len(output) > 200 else output
        })


class TestRunner:
    """Orchestrates test scenario execution"""
    
    def __init__(self):
        self.scenarios = self._define_scenarios()
        self.test_results: Dict[str, Any] = {}
        
    def _define_scenarios(self) -> List[TestScenario]:
        """Define all test scenarios"""
        return [
            # Scenario 1: General Query
            TestScenario(
                name="1A: General Query",
                inputs=["What's the weather like?"],
                expected_stages=["collecting", "idle"]
            ),
            
            # Scenario 2A: Pantry Add
            TestScenario(
                name="2A: Add Pantry Items",
                inputs=["Add 3 tomatoes and 2 onions to my pantry"],
                expected_stages=["collecting", "orchestrating", "executing_pantry", "pantry_complete", "idle"]
            ),
            
            # Scenario 2B: View Pantry
            TestScenario(
                name="2B: View Pantry",
                inputs=["What's in my pantry?"],
                expected_stages=["collecting", "orchestrating", "executing_pantry", "pantry_complete", "idle"]
            ),
            
            # Scenario 3A: Recipe Request - Missing Preferences
            TestScenario(
                name="3A: Recipe Request (No Prefs)",
                inputs=["I want to cook dinner"],
                expected_stages=["collecting"]  # Should stay in collecting
            ),
            
            # Scenario 3B: Recipe Request - With Preferences
            TestScenario(
                name="3B: Recipe Request (With Prefs)",
                inputs=[
                    "I want pasta recipes",
                    "I'm vegetarian and allergic to nuts"
                ],
                expected_stages=["collecting", "orchestrating", "executing_recipe_search", 
                               "synthesizing_recommendations", "presenting_options", "awaiting_selection"]
            ),
            
            # Scenario 4A: Complex Recipe Request
            TestScenario(
                name="4A: Complex Multi-Constraint Recipe",
                inputs=[
                    "I'm vegan, allergic to soy and gluten, and I need to use up my spinach before it expires"
                ],
                expected_stages=["collecting", "orchestrating", "executing_recipe_search",
                               "synthesizing_recommendations", "presenting_options", "awaiting_selection"]
            ),
            
            # Scenario 5A: Recipe Dialogue
            TestScenario(
                name="5A: Sous Chef Q&A",
                inputs=[
                    "I'm vegetarian, show me dinner recipes",
                    "What's the difference between recipe 1 and 2?"
                ],
                expected_stages=["collecting", "orchestrating", "executing_recipe_search",
                               "synthesizing_recommendations", "presenting_options", 
                               "awaiting_selection", "sous_dialogue"]
            ),
            
            # Scenario 6A: Direct Selection
            TestScenario(
                name="6A: Direct Recipe Selection",
                inputs=[
                    "I'm vegetarian, show me recipes",
                    "1"  # Direct selection
                ],
                expected_stages=["collecting", "orchestrating", "executing_recipe_search",
                               "synthesizing_recommendations", "presenting_options",
                               "awaiting_selection", "adapting_recipe", "executing_adaptation",
                               "adaptation_complete", "final_qa", "idle"]
            ),
            
            # Scenario 6B: Invalid Selection
            TestScenario(
                name="6B: Invalid Selection",
                inputs=[
                    "Show me vegetarian recipes",
                    "5"  # Out of range
                ],
                expected_stages=["collecting", "orchestrating", "executing_recipe_search",
                               "synthesizing_recommendations", "presenting_options",
                               "awaiting_selection"]  # Should stay in awaiting_selection
            ),
            
            # Scenario 9A: Multi-Turn Preference Building
            TestScenario(
                name="9A: Gradual Preference Collection",
                inputs=[
                    "I want dinner ideas",
                    "I'm vegetarian",
                    "Allergic to shellfish"
                ],
                expected_stages=["collecting", "collecting", "orchestrating", "executing_recipe_search",
                               "synthesizing_recommendations", "presenting_options", "awaiting_selection"]
            ),
            
            # Scenario 10: Complete Flow
            TestScenario(
                name="10: Complete Multi-Stage Flow",
                inputs=[
                    "Hi there",  # General
                    "Add milk to pantry",  # Pantry
                    "Now show me breakfast recipes",  # Recipe start
                    "I'm lactose intolerant",  # Preferences
                    "Can I use almond milk instead?",  # Sous dialogue
                    "2"  # Selection
                ],
                expected_stages=["collecting", "idle",  # General
                               "collecting", "orchestrating", "executing_pantry", "pantry_complete", "idle",  # Pantry
                               "collecting", "collecting", "orchestrating", "executing_recipe_search",  # Recipe
                               "synthesizing_recommendations", "presenting_options", "awaiting_selection",
                               "sous_dialogue", "adapting_recipe", "executing_adaptation",
                               "adaptation_complete", "final_qa", "idle"]
            ),
        ]
    
    def print_header(self):
        """Print test session header"""
        print("\n" + "="*100)
        print("🧪 EXECUTIVE CHEF ARCHITECTURE - COMPREHENSIVE TEST SUITE")
        print("="*100)
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Total Scenarios: {len(self.scenarios)}")
        print("="*100 + "\n")
    
    def print_scenario_header(self, scenario: TestScenario, index: int):
        """Print individual scenario header"""
        print(f"\n{'─'*100}")
        print(f"📋 TEST SCENARIO [{index}/{len(self.scenarios)}]: {scenario.name}")
        print(f"{'─'*100}")
        print(f"📝 Inputs: {len(scenario.inputs)} message(s)")
        print(f"🎯 Expected Stages: {' → '.join(scenario.expected_stages[:5])}{'...' if len(scenario.expected_stages) > 5 else ''}")
        print(f"{'─'*100}\n")
    
    def print_scenario_result(self, scenario: TestScenario):
        """Print scenario test results"""
        print(f"\n{'┄'*100}")
        print(f"📊 SCENARIO RESULT: {scenario.name}")
        print(f"{'┄'*100}")
        
        for i, result in enumerate(scenario.results, 1):
            print(f"\n  Step {i}:")
            if result['input']:
                print(f"    💬 Input: {result['input']}")
            print(f"    🏷️  Classification: {result['classification']}")
            print(f"    📍 Stage: {result['stage']}")
            print(f"    📤 Output: {result['output_preview']}")
        
        status = "✅ PASSED" if scenario.passed else "❌ NEEDS REVIEW"
        print(f"\n  {status}")
        print(f"{'┄'*100}\n")
    
    def print_summary(self):
        """Print final test summary"""
        print("\n" + "="*100)
        print("📊 TEST SUITE SUMMARY")
        print("="*100)
        
        passed = sum(1 for s in self.scenarios if s.passed)
        total = len(self.scenarios)
        
        print(f"\n✅ Passed: {passed}/{total}")
        print(f"⚠️  Review Needed: {total - passed}/{total}")
        print(f"🎯 Success Rate: {(passed/total)*100:.1f}%")
        
        print("\n📋 Detailed Results:")
        for i, scenario in enumerate(self.scenarios, 1):
            status = "✅" if scenario.passed else "⚠️"
            print(f"  {status} [{i}] {scenario.name}")
        
        print(f"\n📅 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*100 + "\n")
        
        # Save results to file
        self._save_results()
    
    def _save_results(self):
        """Save test results to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("EXECUTIVE CHEF ARCHITECTURE - TEST RESULTS\n")
            f.write("="*100 + "\n\n")
            
            for i, scenario in enumerate(self.scenarios, 1):
                f.write(f"[{i}] {scenario.name}\n")
                f.write(f"Status: {'PASSED' if scenario.passed else 'NEEDS REVIEW'}\n")
                f.write(f"Steps: {len(scenario.results)}\n")
                
                for result in scenario.results:
                    f.write(f"\n  Input: {result.get('input', 'N/A')}\n")
                    f.write(f"  Classification: {result['classification']}\n")
                    f.write(f"  Stage: {result['stage']}\n")
                    f.write(f"  Output: {result['output_preview']}\n")
                
                f.write("\n" + "-"*100 + "\n\n")
        
        print(f"💾 Results saved to: {filename}")
    
    async def run_scenario(self, scenario: TestScenario, system, index: int) -> bool:
        """
        Run a single test scenario.
        
        Note: This is a framework - actual execution would require
        integration with the ModernCollaborativeSystem's graph execution.
        For now, this provides structure for manual testing.
        """
        self.print_scenario_header(scenario, index)
        
        print("🎬 Scenario Execution:")
        print("   (Manual testing required - follow prompts below)\n")
        
        for i, user_input in enumerate(scenario.inputs, 1):
            print(f"   Step {i}: Enter this message when prompted:")
            print(f"   >>> {user_input}")
            print()
        
        print("   After completing this scenario:")
        print("   - Verify the workflow stages match expected transitions")
        print("   - Check output quality and safety validations")
        print("   - Press Enter to mark as PASSED, or type 'fail' to mark as NEEDS REVIEW")
        
        # Placeholder for manual verification
        user_verification = input("\n   Verification (Enter/fail): ").strip().lower()
        scenario.passed = user_verification != "fail"
        
        # Mock result logging (in real integration, this would come from system state)
        for i, user_input in enumerate(scenario.inputs):
            scenario.log_result(
                step=i,
                classification="[manual]",
                stage="[manual]",
                output="[See console output]"
            )
        
        self.print_scenario_result(scenario)
        return scenario.passed


def print_manual_testing_guide():
    """Print guide for manual testing"""
    print("\n" + "="*100)
    print("📖 MANUAL TESTING GUIDE")
    print("="*100)
    print("""
This test runner provides a structured framework for testing all scenarios.

🔧 SETUP:
1. Ensure the system is seeded with sample pantry data
2. Have the recipe database ingested (python scripts/ingest_recipes_qdrant.py)
3. Start fresh for each complete test run

📋 EXECUTION:
1. The test runner will display each scenario's inputs
2. Run the main system (python main.py) in parallel
3. Enter the suggested inputs when prompted
4. Observe the system's behavior and outputs
5. Verify against expected stages and outputs
6. Mark as passed/failed after each scenario

⚠️  CRITICAL CHECKS:
- ✅ Allergen detection and filtering
- ✅ Dietary restriction compliance
- ✅ Stage transitions match expected flow
- ✅ Validator catches safety issues
- ✅ User can dialogue with Sous Chef
- ✅ Final recipes are properly formatted

📊 AFTER TESTING:
- Review the generated test_results_*.txt file
- Document any failures or unexpected behaviors
- Update code as needed and re-run
    """)
    print("="*100 + "\n")


async def main():
    """Main test execution"""
    runner = TestRunner()
    
    runner.print_header()
    print_manual_testing_guide()
    
    print("\n🚀 Ready to begin testing?")
    print("   1. Open another terminal and run: python main.py")
    print("   2. Press Enter here to start the test scenarios...")
    input()
    
    # Run all scenarios
    for i, scenario in enumerate(runner.scenarios, 1):
        try:
            await runner.run_scenario(scenario, system=None, index=i)
        except KeyboardInterrupt:
            print("\n\n⚠️  Testing interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Error in scenario {scenario.name}: {e}")
            scenario.passed = False
    
    # Print summary
    runner.print_summary()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                                                                              ║
    ║        🧪 EXECUTIVE CHEF ARCHITECTURE TEST RUNNER                           ║
    ║                                                                              ║
    ║        Comprehensive scenario testing for multi-agent orchestration         ║
    ║                                                                              ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())

