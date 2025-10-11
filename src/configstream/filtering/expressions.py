"""Expression-based filtering engine.

Supports complex filter expressions like:
- ping < 100 AND country == "US"
- protocol IN ["vmess", "shadowsocks"] AND NOT is_blocked
- quality_score > 80 OR uptime > 95
"""
from __future__ import annotations

import operator
import re
from dataclasses import dataclass
from typing import Any, Callable, List


@dataclass
class FilterExpression:
    """Represents a filter expression."""
    field: str
    op: str
    value: Any

    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        "<=": operator.le,
        ">": operator.gt,
        ">=": operator.ge,
        "IN": lambda a, b: a in b,
        "NOT IN": lambda a, b: a not in b,
        "CONTAINS": lambda a, b: b in str(a),
        "MATCHES": lambda a, b: re.match(b, str(a)) is not None
    }

    def evaluate(self, node: dict) -> bool:
        """Evaluate expression against a node.

        Args:
            node: Node dictionary

        Returns:
            True if node matches expression
        """
        field_value = node.get(self.field)

        if field_value is None:
            return False

        op_func = self.OPERATORS.get(self.op)
        if not op_func:
            raise ValueError(f"Unknown operator: {self.op}")

        try:
            return op_func(field_value, self.value)
        except Exception:
            return False


class FilterParser:
    """Parses filter expression strings.

    Example expressions:
        "ping_ms < 100"
        "country == 'US' AND protocol == 'vmess'"
        "quality_score > 80 OR (ping_ms < 50 AND NOT is_blocked)"
    """

    @staticmethod
    def parse(expression: str) -> Callable[[dict], bool]:
        """Parse expression string into evaluator function.

        Args:
            expression: Filter expression string

        Returns:
            Function that takes node dict and returns bool
        """
        # Remove extra whitespace
        expression = " ".join(expression.split())

        # Handle parentheses
        if expression.startswith("(") and expression.endswith(")"):
            return FilterParser.parse(expression[1:-1])

        # Handle compound expressions with AND/OR
        if " AND " in expression:
            parts = expression.split(" AND ", 1)
            evaluators = [FilterParser.parse(part) for part in parts]
            return lambda node: all(e(node) for e in evaluators)

        if " OR " in expression:
            parts = expression.split(" OR ", 1)
            evaluators = [FilterParser.parse(part) for part in parts]
            return lambda node: any(e(node) for e in evaluators)

        # Handle NOT
        if expression.startswith("NOT "):
            inner = FilterParser.parse(expression[4:])
            return lambda node: not inner(node)

        # Parse simple expression
        return FilterParser._parse_simple(expression)

    @staticmethod
    def _parse_simple(expression: str) -> Callable[[dict], bool]:
        """Parse simple comparison expression.

        Args:
            expression: Simple expression like "ping_ms < 100"

        Returns:
            Evaluator function
        """
        # Try two-character operators first
        for op in ["==", "!=", "<=", ">=", "IN", "NOT IN", "CONTAINS", "MATCHES"]:
            if op in expression:
                field, value = expression.split(op, 1)
                field = field.strip()
                value = value.strip().strip("'\"")

                # Convert value to appropriate type
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.startswith("[") and value.endswith("]"):
                    # Parse list
                    value = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                else:
                    try:
                        value = float(value)
                        if value.is_integer():
                            value = int(value)
                    except ValueError:
                        pass  # Keep as string

                expr = FilterExpression(field, op, value)
                return lambda node: expr.evaluate(node)

        # Try single-character operators
        for op in ["<", ">", "="]:
            if op in expression:
                field, value = expression.split(op, 1)
                field = field.strip()
                value = value.strip().strip("'\"")

                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except ValueError:
                    pass

                op = "==" if op == "=" else op
                expr = FilterExpression(field, op, value)
                return lambda node: expr.evaluate(node)

        # Handle boolean fields
        if re.fullmatch(r"[\w_]+", expression):
            expr = FilterExpression(expression, "==", True)
            return lambda node: expr.evaluate(node)

        raise ValueError(f"Cannot parse expression: {expression}")


def filter_nodes(nodes: List[dict], expression: str) -> List[dict]:
    """Filter nodes using expression.

    Args:
        nodes: List of node dictionaries
        expression: Filter expression string

    Returns:
        Filtered list of nodes

    Example:
        >>> nodes = [{"ping_ms": 50, "country": "US"}, ...]
        >>> filtered = filter_nodes(nodes, "ping_ms < 100 AND country == 'US'")
    """
    evaluator = FilterParser.parse(expression)
    return [node for node in nodes if evaluator(node)]