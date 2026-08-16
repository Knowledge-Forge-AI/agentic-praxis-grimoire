"""Static source-binding integrity for declared Python owner values."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, Sequence

from apg_candidate_surface_contract import SurfaceContractError


SOURCE_BINDING_PROOF_SCOPE = (
    "exact static owner declaration and mechanically identifiable "
    "protected-name write refusal"
)
RUNTIME_VALUE_AUTHORITY = "not-used"
ARBITRARY_CALLER_MUTATION_SCOPE = "outside-static-source-proof"
REFLECTIVE_CALL_EFFECT_SCOPE = "outside-static-syntactic-proof"
FORBIDDEN_DYNAMIC_NAMES = {
    "__builtins__",
    "__import__",
    "attrgetter",
    "delattr",
    "eval",
    "exec",
    "getattr",
    "globals",
    "locals",
    "methodcaller",
    "setattr",
    "vars",
}
FORBIDDEN_INTROSPECTION_ATTRIBUTES = {
    "__delattr__",
    "__dict__",
    "__getattribute__",
    "__globals__",
    "__setattr__",
    "f_globals",
    "modules",
}
PROJECTION_EXPRESSION = ast.dump(
    ast.parse(
        """tuple(sorted(
    f".agents/skills/{PurePosixPath(path).parent.name}"
    for path in AUDITED_SKILLS
))""",
        mode="eval",
    ).body,
    include_attributes=False,
)
TYPE_PARAMETER_NODES = tuple(
    node_type
    for name in ("TypeVar", "TypeVarTuple", "ParamSpec")
    if (node_type := getattr(ast, name, None)) is not None
)


def fail(owner_id: str, message: str) -> NoReturn:
    raise SurfaceContractError(f"{owner_id}: {message}")


def _tree(
    path: Path, owner_id: str, source_text: str | None = None
) -> ast.Module:
    try:
        if source_text is None:
            if path.is_symlink() or not path.is_file():
                fail(
                    owner_id,
                    "Python owner is missing or not a direct regular file",
                )
            source_text = path.read_text(encoding="utf-8")
        return ast.parse(source_text)
    except (OSError, UnicodeError, SyntaxError) as error:
        fail(owner_id, f"Python owner is invalid or unreadable: {error}")


def _assignment(
    tree: ast.Module, variable: str, owner_id: str
) -> tuple[ast.expr, ast.Name]:
    matches: list[tuple[ast.expr, ast.Name]] = []
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            targets = [
                target
                for target in statement.targets
                if isinstance(target, ast.Name) and target.id == variable
            ]
            matches.extend((statement.value, target) for target in targets)
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == variable
            and statement.value is not None
        ):
            matches.append((statement.value, statement.target))
    if len(matches) != 1:
        fail(owner_id, f"{variable} assignment is missing or duplicated")
    return matches[0]


def _static_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Add)
    ):
        left = _static_string(node.left)
        right = _static_string(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _name_is_bound(tree: ast.Module, name: str) -> bool:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Name)
            and node.id == name
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ):
            return True
        if (
            isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            )
            and node.name == name
        ):
            return True
        if isinstance(node, ast.arg) and node.arg == name:
            return True
        if isinstance(node, ast.ExceptHandler) and node.name == name:
            return True
        if (
            isinstance(node, (ast.MatchAs, ast.MatchStar))
            and node.name == name
        ):
            return True
        if isinstance(node, ast.MatchMapping) and node.rest == name:
            return True
        if (
            TYPE_PARAMETER_NODES
            and isinstance(node, TYPE_PARAMETER_NODES)
            and node.name == name
        ):
            return True
        if isinstance(node, (ast.Global, ast.Nonlocal)) and name in node.names:
            return True
        if isinstance(node, ast.Import):
            if any(
                (alias.asname or alias.name.partition(".")[0]) == name
                for alias in node.names
            ):
                return True
        if isinstance(node, ast.ImportFrom):
            if any(
                alias.name == "*"
                or (alias.asname or alias.name) == name
                for alias in node.names
            ):
                return True
    return False


def _safe_getattr_call(node: ast.Call) -> bool:
    return (
        isinstance(node.func, ast.Name)
        and node.func.id == "getattr"
        and len(node.args) == 3
        and not node.keywords
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "os"
        and _static_string(node.args[1]) == "O_NOFOLLOW"
        and isinstance(node.args[2], ast.Constant)
        and node.args[2].value == 0
    )


def _assert_no_protected_write(
    tree: ast.Module,
    accepted_target: ast.Name,
    variable: str,
    owner_id: str,
) -> None:
    safe_getattr_nodes: set[int] = set()
    getattr_is_bound = _name_is_bound(tree, "getattr")
    for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
        if isinstance(call.func, ast.Name) and call.func.id == "getattr":
            if getattr_is_bound or not _safe_getattr_call(call):
                fail(
                    owner_id,
                    f"{variable} owner uses unsupported dynamic namespace "
                    "primitive getattr",
                )
            safe_getattr_nodes.add(id(call.func))
    for node in ast.walk(tree):
        if (
            isinstance(
                node,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
            )
            and node.name == variable
        ):
            fail(owner_id, f"{variable} has a definition binding")
        if isinstance(node, ast.arg) and node.arg == variable:
            fail(owner_id, f"{variable} has an argument binding")
        if (
            isinstance(node, ast.ExceptHandler)
            and node.name == variable
        ):
            fail(owner_id, f"{variable} has an exception binding")
        if (
            isinstance(node, (ast.MatchAs, ast.MatchStar))
            and node.name == variable
        ):
            fail(owner_id, f"{variable} has a pattern binding")
        if (
            isinstance(node, ast.MatchMapping)
            and node.rest == variable
        ):
            fail(owner_id, f"{variable} has a pattern binding")
        if (
            TYPE_PARAMETER_NODES
            and isinstance(node, TYPE_PARAMETER_NODES)
            and node.name == variable
        ):
            fail(owner_id, f"{variable} has a type-parameter binding")
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.partition(".")[0]
                if bound == variable:
                    fail(owner_id, f"{variable} has an import binding")
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    fail(
                        owner_id,
                        f"{variable} owner uses a wildcard import",
                    )
                bound = alias.asname or alias.name
                if bound == variable:
                    fail(owner_id, f"{variable} has an import binding")
                if alias.name in FORBIDDEN_DYNAMIC_NAMES:
                    fail(
                        owner_id,
                        f"{variable} owner imports unsupported dynamic "
                        f"namespace primitive {alias.name}",
                    )
        if (
            isinstance(node, ast.Name)
            and node.id == variable
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and node is not accepted_target
        ):
            fail(owner_id, f"{variable} has another source-authored write")
        if isinstance(node, (ast.Global, ast.Nonlocal)) and variable in node.names:
            fail(owner_id, f"{variable} has a global or nonlocal write path")
        if (
            isinstance(node, ast.Attribute)
            and node.attr == variable
            and isinstance(node.ctx, (ast.Store, ast.Del))
        ):
            fail(owner_id, f"{variable} has an attribute write path")
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.ctx, (ast.Store, ast.Del))
            and _static_string(node.slice) == variable
        ):
            fail(owner_id, f"{variable} has a namespace-subscript write path")
        if (
            isinstance(node, ast.Call)
            and (
                (
                    isinstance(node.func, ast.Name)
                    and node.func.id in {"setattr", "delattr"}
                    and len(node.args) >= 2
                    and _static_string(node.args[1]) == variable
                )
                or (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"__setattr__", "__delattr__"}
                    and node.args
                    and _static_string(node.args[0]) == variable
                )
            )
        ):
            fail(owner_id, f"{variable} has a dynamic attribute write path")
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id in FORBIDDEN_DYNAMIC_NAMES
            and id(node) not in safe_getattr_nodes
        ):
            fail(
                owner_id,
                f"{variable} owner uses unsupported dynamic namespace "
                f"primitive {node.id}",
            )
        if (
            isinstance(node, ast.Attribute)
            and node.attr
            in FORBIDDEN_INTROSPECTION_ATTRIBUTES | FORBIDDEN_DYNAMIC_NAMES
        ):
            fail(
                owner_id,
                f"{variable} owner uses unsupported namespace "
                f"introspection {node.attr}",
            )


def _evaluated_strings(
    node: ast.expr, variable: str, owner_id: str
) -> tuple[list[str], bool]:
    if isinstance(node, (ast.List, ast.Set, ast.Tuple)):
        if any(
            not isinstance(item, ast.Constant)
            or not isinstance(item.value, str)
            for item in node.elts
        ):
            fail(owner_id, f"{variable} contains a nonliteral string")
        return [item.value for item in node.elts], isinstance(node, ast.Tuple)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"frozenset", "sorted", "tuple"}
        and len(node.args) == 1
        and not node.keywords
    ):
        values, _ = _evaluated_strings(node.args[0], variable, owner_id)
        if node.func.id == "sorted":
            return sorted(values), False
        return values, True
    fail(owner_id, f"{variable} uses an unsupported static expression")


def _binding(
    tree: ast.Module, variable: str, owner_id: str
) -> tuple[ast.expr, list[str]]:
    expression, target = _assignment(tree, variable, owner_id)
    _assert_no_protected_write(tree, target, variable, owner_id)
    if (
        variable == "AUDITED_PROJECTIONS"
        and ast.dump(expression, include_attributes=False)
        == PROJECTION_EXPRESSION
    ):
        return expression, []
    values, immutable = _evaluated_strings(expression, variable, owner_id)
    if not immutable:
        fail(owner_id, f"{variable} must be an immutable static collection")
    return expression, values


def _candidate_counter(
    values: Sequence[str], candidate: str
) -> Counter[str]:
    return Counter(value for value in values if candidate in value)


def _assert_public_relative(
    values: Sequence[str], variable: str, owner_id: str
) -> None:
    for value in values:
        path = PurePosixPath(value)
        if (
            not value
            or path.is_absolute()
            or ".." in path.parts
            or "\\" in value
            or value.startswith(("~", "private/", "file:"))
            or ":" in value
            or "/" "Users/" in value
        ):
            fail(owner_id, f"{variable} contains a private or nonrelative path")


def read_bound_strings(
    path: Path,
    variable: str,
    owner_id: str,
    *,
    source_text: str | None = None,
) -> list[str]:
    """Extract one immutable declaration without importing its owner module."""
    tree = _tree(path, owner_id, source_text)
    expression, values = _binding(tree, variable, owner_id)
    if variable != "AUDITED_PROJECTIONS":
        return values
    if ast.dump(expression, include_attributes=False) != PROJECTION_EXPRESSION:
        fail(owner_id, f"{variable} uses an unsupported static expression")
    _, skills = _binding(tree, "AUDITED_SKILLS", owner_id)
    return sorted(
        f".agents/skills/{PurePosixPath(path).parent.name}"
        for path in skills
    )


def assert_bound_assignment(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    expected: Sequence[str],
    variable: str,
    *,
    source_text: str | None = None,
) -> None:
    """Require one exact static project-owner declaration."""
    owner_id = owner["owner_id"]
    values = read_bound_strings(
        root / owner["path"],
        variable,
        owner_id,
        source_text=source_text,
    )
    if _candidate_counter(values, candidate) != Counter(expected):
        fail(owner_id, f"{variable} candidate membership is incomplete or duplicated")


def assert_audited_assignment(
    root: Path,
    owner: dict[str, Any],
    candidate: str,
    expected: Sequence[str],
    variable: str,
    *,
    source_text: str | None = None,
) -> None:
    """Require one exact static public-relative audited declaration."""
    owner_id = owner["owner_id"]
    values = read_bound_strings(
        root / owner["path"],
        variable,
        owner_id,
        source_text=source_text,
    )
    _assert_public_relative(values, variable, owner_id)
    if _candidate_counter(values, candidate) != Counter(expected):
        fail(owner_id, f"{variable} actual value is incomplete or duplicated")
