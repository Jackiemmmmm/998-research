"""Judge module - Evaluate agent outputs against ground truth.

Supports 3 modes: exact, json, regex.
"""

import json
import re
from typing import Any, Dict, Optional, Tuple

from jsonschema import ValidationError, validate


class Judge:
    """Judge for evaluating agent outputs."""

    @staticmethod
    def evaluate(
        output: str,
        ground_truth: Any,
        judge_config: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
        lenient: bool = False
    ) -> Tuple[bool, str]:
        """Evaluate output against ground truth.

        Args:
            output: Agent output (string)
            ground_truth: Expected answer
            judge_config: Judge configuration with 'mode' field
            schema: Optional JSON schema for validation
            lenient: If True, extract answer from output before judging

        Returns:
            Tuple of (success: bool, explanation: str)
        """
        # Apply lenient extraction if requested
        if lenient:
            output = Judge._extract_answer(output, ground_truth, judge_config)

        mode = judge_config.get("mode", "exact")

        if mode == "exact":
            return Judge._judge_exact(output, ground_truth)
        elif mode == "json":
            return Judge._judge_json(output, ground_truth, judge_config, schema)
        elif mode == "regex":
            return Judge._judge_regex(output, judge_config)
        else:
            return False, f"Unknown judge mode: {mode}"

    @staticmethod
    def _extract_answer(
        output: str,
        ground_truth: Any,
        judge_config: Dict[str, Any]
    ) -> str:
        """Intelligently extract the actual answer from verbose model output.

        Examples:
            "The cost of 12 apples is $20." -> "20"
            "Anna is the shortest." -> "Anna"
            "The date '12 October 2025' normalized to ISO 2025-10-12" -> "2025-10-12"

        Args:
            output: Raw model output
            ground_truth: Expected answer (used to infer extraction type)
            judge_config: Judge configuration

        Returns:
            Extracted answer string
        """
        mode = judge_config.get("mode", "exact")

        # Ensure output is a string
        if not isinstance(output, str):
            output = str(output)

        output = output.strip()

        # For JSON mode, don't extract here - _judge_json handles JSON extraction
        # Extraction here would return a dict, causing .strip() errors later
        if mode == "json":
            return output

        # For regex mode, don't extract (regex is already lenient)
        if mode == "regex":
            return output

        # For exact mode, infer type from ground_truth
        if ground_truth is not None:
            ground_truth_str = str(ground_truth).strip()

            # Check if ground_truth is a number
            if re.match(r'^\d+(\.\d+)?$', ground_truth_str):
                # Extract first number from output
                match = re.search(r'\b(\d+(?:\.\d+)?)\b', output)
                if match:
                    return match.group(1)

            # Check if ground_truth is a date (YYYY-MM-DD)
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', ground_truth_str):
                # Extract ISO date
                match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', output)
                if match:
                    return match.group(1)

            # Check if ground_truth is a single word
            elif ' ' not in ground_truth_str and len(ground_truth_str) < 30:
                # Extract first meaningful word
                # Remove common prefix phrases
                cleaned = output
                for prefix in ["The answer is", "It is", "The result is", "This is"]:
                    if cleaned.lower().startswith(prefix.lower()):
                        cleaned = cleaned[len(prefix):].strip()

                # Get first word, removing punctuation
                words = cleaned.split()
                if words:
                    first_word = words[0].rstrip('.,!?:;')
                    return first_word

        # If no extraction applied, return original
        return output

    @staticmethod
    def _judge_exact(output: str, ground_truth: Any) -> Tuple[bool, str]:
        """Exact match judge - output must exactly match ground truth.

        Examples:
            "408" == "408" → True
            "Paris" == "Paris" → True
            "paris" != "Paris" → False
        """
        output_cleaned = output.strip()
        ground_truth_str = str(ground_truth).strip()

        if output_cleaned == ground_truth_str:
            return True, f"Exact match: '{output_cleaned}'"
        else:
            return False, f"Mismatch: got '{output_cleaned}', expected '{ground_truth_str}'"

    @staticmethod
    def _judge_json(
        output: str,
        ground_truth: Any,
        judge_config: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """JSON judge - parse output as JSON and validate.

        Steps:
        1. Parse output as JSON
        2. Validate against schema (if provided)
        3. Compare with ground truth (if provided, ignoring specified fields)
        """
        # Step 1: Parse JSON
        try:
            parsed_output = Judge._extract_and_parse_json(output)
        except (json.JSONDecodeError, ValueError) as e:
            return False, f"JSON parse error: {str(e)}"

        # Step 2: Validate schema
        if schema:
            try:
                validate(instance=parsed_output, schema=schema)
            except ValidationError as e:
                return False, f"Schema validation failed: {e.message}"

        # Step 3: Compare with ground truth
        if ground_truth is not None:
            ignore_fields = judge_config.get("ignore_fields", [])

            # Remove ignored fields
            if isinstance(parsed_output, dict) and isinstance(ground_truth, dict):
                output_filtered = {k: v for k, v in parsed_output.items() if k not in ignore_fields}
                truth_filtered = {k: v for k, v in ground_truth.items() if k not in ignore_fields}

                if output_filtered == truth_filtered:
                    return True, f"JSON match (ignoring {ignore_fields}): {output_filtered}"
                else:
                    return False, f"JSON mismatch: got {output_filtered}, expected {truth_filtered}"
            else:
                if parsed_output == ground_truth:
                    return True, f"JSON exact match: {parsed_output}"
                else:
                    return False, f"JSON mismatch: got {parsed_output}, expected {ground_truth}"
        else:
            # No ground truth, just validate structure
            return True, f"JSON valid (no ground truth to compare): {parsed_output}"

    @staticmethod
    def _judge_regex(output: str, judge_config: Dict[str, Any]) -> Tuple[bool, str]:
        """Regex judge - check if output matches regex pattern.

        Example:
            pattern: r"(?i)^paris$"
            "Paris" → True
            "paris" → True
            "PARIS" → True
            "paris city" → False
        """
        pattern = judge_config.get("pattern")
        if not pattern:
            return False, "No regex pattern provided"

        try:
            if re.search(pattern, output):
                return True, f"Regex match: pattern '{pattern}' found in output"
            else:
                return False, f"Regex mismatch: pattern '{pattern}' not found in '{output}'"
        except re.error as e:
            return False, f"Regex error: {str(e)}"

    @staticmethod
    def _extract_and_parse_json(text: str) -> Any:
        """Extract and parse JSON from text.

        Handles:
        - Pure JSON
        - JSON in markdown code blocks
        - JSON embedded in text
        """
        text = text.strip()

        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to extract from markdown code block
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        match = re.search(code_block_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try to find JSON object or array in text
        json_pattern = r'(\{.*\}|\[.*\])'
        match = re.search(json_pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # If all fails, raise error
        raise ValueError(f"Could not extract valid JSON from: {text[:100]}...")


class LLMJudge:
    """LLM-as-Judge for qualitative evaluation.

    Uses a strong LLM to evaluate output quality.
    """

    def __init__(self, model_name: Optional[str] = None):
        """Initialize LLM judge.

        Args:
            model_name: Optional model name. If None, uses configured LLM
        """
        if model_name:
            from langchain.chat_models import init_chat_model
            self.llm = init_chat_model(model_name)
        else:
            from src.llm_config import get_llm
            self.llm = get_llm()

    def evaluate(
        self,
        query: str,
        output: str,
        ground_truth: Optional[str] = None
    ) -> Dict[str, Any]:
        """Evaluate output quality using LLM.

        Args:
            query: Original user query
            output: Agent output
            ground_truth: Optional ground truth answer

        Returns:
            Dict with scores for relevance, accuracy, completeness, conciseness
        """
        prompt = self._build_evaluation_prompt(query, output, ground_truth)

        try:
            response = self.llm.invoke([{"role": "user", "content": prompt}])
            result = self._parse_llm_response(response.content)
            return result
        except Exception as e:
            return {
                "relevance": 5,
                "accuracy": 5,
                "completeness": 5,
                "conciseness": 5,
                "overall": 5.0,
                "explanation": f"LLM evaluation failed: {str(e)}"
            }

    def _build_evaluation_prompt(
        self,
        query: str,
        output: str,
        ground_truth: Optional[str]
    ) -> str:
        """Build evaluation prompt for LLM."""
        prompt = f"""Evaluate the following agent output on a scale of 1-10 for each dimension:

Query: {query}

Agent Output: {output}
"""

        if ground_truth:
            prompt += f"\nGround Truth Answer: {ground_truth}\n"

        prompt += """
Evaluate on these dimensions (1-10):
1. Relevance: Does it address the query?
2. Accuracy: Is the information correct?
3. Completeness: Is the answer complete?
4. Conciseness: Is it concise without unnecessary details?

Return JSON:
{
  "relevance": <1-10>,
  "accuracy": <1-10>,
  "completeness": <1-10>,
  "conciseness": <1-10>,
  "explanation": "<brief explanation>"
}
"""
        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM evaluation response."""
        try:
            # Extract JSON from response
            parsed = Judge._extract_and_parse_json(response)

            # Calculate overall score
            overall = (
                parsed.get("relevance", 5) +
                parsed.get("accuracy", 5) +
                parsed.get("completeness", 5) +
                parsed.get("conciseness", 5)
            ) / 4.0

            parsed["overall"] = overall
            return parsed

        except Exception as e:
            return {
                "relevance": 5,
                "accuracy": 5,
                "completeness": 5,
                "conciseness": 5,
                "overall": 5.0,
                "explanation": f"Failed to parse LLM response: {str(e)}"
            }


if __name__ == "__main__":
    # Test exact judge
    success, msg = Judge.evaluate("408", "408", {"mode": "exact"})

    success, msg = Judge.evaluate("Paris", "paris", {"mode": "exact"})

    # Test JSON judge
    output = '{"name": "iPhone 15", "price": 999}'
    ground_truth = {"name": "iPhone 15", "price": 999}
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "price": {"type": "number"}
        },
        "required": ["name", "price"]
    }
    success, msg = Judge.evaluate(output, ground_truth, {"mode": "json"}, schema)

    # Test regex judge
    success, msg = Judge.evaluate("Paris", None, {"mode": "regex", "pattern": r"(?i)^paris$"})

    success, msg = Judge.evaluate("PARIS", None, {"mode": "regex", "pattern": r"(?i)^paris$"})
