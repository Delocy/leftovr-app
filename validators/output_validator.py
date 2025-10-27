"""
Output Validator - Non-Agent Safety and Quality Checker

Performs deterministic validation of outputs from Pantry and Recipe workflows.
Ensures allergen compliance, dietary restrictions, and output completeness.
"""
from typing import Dict, List, Any, Optional
import re


class ResultValidator:
    """
    Non-agent validator for pantry and recipe outputs.
    Performs safety checks, completeness validation, and output formatting.
    """

    def __init__(self):
        self.validation_history: List[Dict[str, Any]] = []

    def validate_pantry_response(
        self,
        pantry_result: Dict[str, Any],
        user_prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate pantry operation response.

        Args:
            pantry_result: Result from PantryAgent operation
            user_prefs: User preferences (for context)

        Returns:
            {passed: bool, issues: List[str], content: str}
        """
        issues = []

        # Check if result exists
        if not pantry_result:
            issues.append("Empty pantry result")
            return {
                "passed": False,
                "issues": issues,
                "content": "⚠️ Unable to process pantry operation."
            }

        # Check for errors in result
        if "error" in pantry_result:
            issues.append(f"Pantry operation error: {pantry_result['error']}")
            return {
                "passed": False,
                "issues": issues,
                "content": f"⚠️ Pantry error: {pantry_result['error']}"
            }

        # Format successful pantry response
        message = pantry_result.get("message", "Pantry operation completed successfully")

        validation_result = {
            "passed": True,
            "issues": issues,
            "content": f"✅ {message}"
        }

        self.validation_history.append({
            "type": "pantry",
            "result": validation_result
        })

        return validation_result

    def validate_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        user_prefs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate recipe recommendations for safety and compliance.

        Args:
            recommendations: List of recipe recommendations
            user_prefs: User preferences with allergies and restrictions

        Returns:
            {passed: bool, issues: List[str], filtered_recommendations: List[Dict]}
        """
        issues = []
        filtered_recs = []

        if not recommendations:
            issues.append("No recommendations available")
            return {
                "passed": False,
                "issues": issues,
                "filtered_recommendations": []
            }

        # Extract user constraints
        allergies = [a.lower().strip() for a in user_prefs.get("allergies", [])]
        restrictions = [r.lower().strip() for r in user_prefs.get("restrictions", [])]

        for rec in recommendations:
            rec_issues = []

            # Check allergen safety
            if not rec.get("allergen_safe", True):
                rec_issues.append("Contains allergens")

            # Check dietary compliance
            if not rec.get("dietary_compliant", True):
                rec_issues.append("Does not meet dietary restrictions")

            # Additional allergen check in ingredients
            ingredients = rec.get("ingredients", [])
            if isinstance(ingredients, list):
                ing_text = " ".join([str(i).lower() for i in ingredients])
                for allergen in allergies:
                    if allergen in ing_text:
                        rec_issues.append(f"CRITICAL: Contains allergen '{allergen}'")

            # Check for vegan/vegetarian compliance
            if "vegan" in restrictions or "vegetarian" in restrictions:
                meat_keywords = ["chicken", "beef", "pork", "fish", "lamb", "turkey", "meat"]
                for keyword in meat_keywords:
                    if keyword in " ".join([str(i).lower() for i in ingredients]):
                        if "vegan" in restrictions:
                            rec_issues.append(f"Not vegan: contains {keyword}")
                        elif "vegetarian" in restrictions and keyword != "fish":
                            rec_issues.append(f"Not vegetarian: contains {keyword}")

            # If critical issues found, skip this recommendation
            if any("CRITICAL" in issue for issue in rec_issues):
                issues.extend([f"Recipe '{rec.get('title')}': {issue}" for issue in rec_issues])
                continue

            # Add non-critical warnings to the recommendation
            if rec_issues:
                rec["validation_warnings"] = rec_issues
                issues.extend([f"Recipe '{rec.get('title')}': {issue}" for issue in rec_issues])

            filtered_recs.append(rec)

        validation_result = {
            "passed": len(filtered_recs) > 0,
            "issues": issues,
            "filtered_recommendations": filtered_recs
        }

        self.validation_history.append({
            "type": "recommendations",
            "result": validation_result
        })

        return validation_result

    def validate_adapted_recipe(
        self,
        formatted_recipe: str,
        user_prefs: Dict[str, Any],
        messages: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Validate adapted recipe for safety and completeness.

        Args:
            formatted_recipe: Formatted recipe text
            user_prefs: User preferences with allergies and restrictions
            messages: Conversation history for context

        Returns:
            {passed: bool, issues: List[str], content: str}
        """
        issues = []

        if not formatted_recipe or len(formatted_recipe.strip()) < 50:
            issues.append("Recipe content is incomplete or missing")
            return {
                "passed": False,
                "issues": issues,
                "content": "⚠️ Unable to generate complete recipe."
            }

        # Extract user constraints
        allergies = [a.lower().strip() for a in user_prefs.get("allergies", [])]
        restrictions = [r.lower().strip() for r in user_prefs.get("restrictions", [])]

        recipe_lower = formatted_recipe.lower()

        # CRITICAL: Check for allergens in recipe text
        for allergen in allergies:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + re.escape(allergen) + r'\b'
            if re.search(pattern, recipe_lower):
                issues.append(f"CRITICAL: Recipe contains allergen '{allergen}'")

        # Check dietary compliance
        if "vegan" in restrictions:
            non_vegan = ["egg", "eggs", "milk", "cream", "butter", "cheese", "honey",
                        "chicken", "beef", "pork", "fish", "meat", "gelatin"]
            for item in non_vegan:
                pattern = r'\b' + re.escape(item) + r'\b'
                if re.search(pattern, recipe_lower):
                    issues.append(f"Not vegan: contains {item}")

        if "vegetarian" in restrictions:
            meat_items = ["chicken", "beef", "pork", "lamb", "turkey", "meat", "bacon", "sausage"]
            for item in meat_items:
                pattern = r'\b' + re.escape(item) + r'\b'
                if re.search(pattern, recipe_lower):
                    issues.append(f"Not vegetarian: contains {item}")

        # Check for basic recipe components
        has_ingredients = "ingredient" in recipe_lower or "##" in formatted_recipe
        has_steps = "step" in recipe_lower or "instruction" in recipe_lower or re.search(r'\d+\.', formatted_recipe)

        if not has_ingredients:
            issues.append("Recipe missing ingredients section")
        if not has_steps:
            issues.append("Recipe missing cooking instructions")

        # Determine pass/fail
        critical_issues = [i for i in issues if "CRITICAL" in i]
        passed = len(critical_issues) == 0

        # Format output
        if passed and not issues:
            content = formatted_recipe
        elif passed:
            # Non-critical warnings only
            warning_text = "⚠️ Note: " + "; ".join(issues) + "\n\n"
            content = warning_text + formatted_recipe
        else:
            # Critical failures
            critical_text = "🚨 SAFETY ALERT: " + "; ".join(critical_issues) + "\n\n"
            content = critical_text + "Recipe cannot be recommended due to safety concerns."

        validation_result = {
            "passed": passed,
            "issues": issues,
            "content": content,
            "score": 100 if passed and not issues else (50 if passed else 0)
        }

        self.validation_history.append({
            "type": "adapted_recipe",
            "result": validation_result
        })

        return validation_result

    def validate_and_format(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main validation entry point - routes to appropriate validator based on workflow stage.

        Args:
            state: Current workflow state

        Returns:
            {passed: bool, issues: List[str], content: str}
        """
        stage = state.get("current_workflow_stage", "")
        user_prefs = state.get("user_preferences", {})

        # Pantry validation
        if stage in ["pantry_complete", "executing_pantry"]:
            pantry_result = state.get("agent_delegation_results", {}).get("pantry", {})
            return self.validate_pantry_response(pantry_result, user_prefs)

        # Recommendations validation
        elif stage in ["presenting_options", "synthesizing_recommendations"]:
            recommendations = state.get("sous_chef_recommendations", [])
            validation = self.validate_recommendations(recommendations, user_prefs)

            # Format recommendations for display
            if validation["passed"]:
                filtered = validation["filtered_recommendations"]
                content = self._format_recommendations_display(filtered, validation["issues"])
                return {
                    "passed": True,
                    "issues": validation["issues"],
                    "content": content
                }
            else:
                return {
                    "passed": False,
                    "issues": validation["issues"],
                    "content": "⚠️ Unable to find safe recipe recommendations matching your requirements."
                }

        # Adapted recipe validation
        elif stage in ["final_qa", "adaptation_complete"]:
            formatted_recipe = state.get("formatted_recipe", "")
            messages = state.get("messages", [])
            return self.validate_adapted_recipe(formatted_recipe, user_prefs, messages)

        # Default/unknown stage
        else:
            return {
                "passed": False,
                "issues": [f"Unknown validation stage: {stage}"],
                "content": "Unable to validate output."
            }

    def _format_recommendations_display(
        self,
        recommendations: List[Dict[str, Any]],
        issues: List[str]
    ) -> str:
        """Format validated recommendations for user display."""
        output = []

        if issues:
            output.append("⚠️ Note: Some recommendations were filtered for safety:\n")
            for issue in issues[:3]:  # Show first 3 issues
                output.append(f"  • {issue}")
            output.append("\n")

        output.append("📋 Validated Recommendations:\n")

        for i, rec in enumerate(recommendations[:3], 1):
            rank_emoji = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."

            output.append(f"\n{rank_emoji} **{rec.get('title', 'Unknown Recipe')}**")
            output.append(f"   Score: {rec.get('score', 0)} | Time: {rec.get('time_minutes', '?')} min | Difficulty: {rec.get('difficulty', 'unknown')}")

            why = rec.get('why_recommended', '')
            if why:
                output.append(f"   Why: {why}")

            # Show expiring items being used
            expiring = rec.get('expiring_items_used', [])
            if expiring:
                output.append(f"   ⚠️ Uses expiring: {', '.join(expiring)}")

            # Show validation warnings if any
            warnings = rec.get('validation_warnings', [])
            if warnings:
                output.append(f"   ⚠️ Warnings: {'; '.join(warnings)}")

        output.append("\n\nWhich recipe would you like to make? (Reply 1, 2, or 3)")

        return "\n".join(output)

    def get_validation_history(self) -> List[Dict[str, Any]]:
        """Return validation history for debugging."""
        return self.validation_history

    def clear_history(self):
        """Clear validation history."""
        self.validation_history = []

