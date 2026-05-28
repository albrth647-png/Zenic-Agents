"""
Risk Prediction (F3) — Blast radius, propagation, critical path, reachability.

Provides: calculate_blast_radius, propagate_risks, find_critical_path,
          compute_reachability, multi_node_blast_radius
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from ._loader import HAS_NATIVE


def calculate_blast_radius(
    node_id: str, edges: list[tuple[str, str]],
) -> dict[str, Any]:
    """Calculate the blast radius of a node failure."""
    if HAS_NATIVE:
        from ._loader import _rust_calculate_blast_radius
        return _rust_calculate_blast_radius(node_id, edges)
    # Pure Python fallback
    forward: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        forward[src].append(dst)

    direct = set(forward.get(node_id, []))
    visited: set[str] = set()
    queue = deque([node_id])

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for neighbor in forward.get(current, []):
            if neighbor not in visited:
                queue.append(neighbor)

    visited.discard(node_id)
    transitive = visited - direct
    blast_size = len(visited)
    risk_level = "low" if blast_size == 0 else "medium" if blast_size <= 3 else "high" if blast_size <= 10 else "critical"

    return {"source_node": node_id, "blast_radius": list(visited),
            "direct_dependents": list(direct),
            "transitive_dependents": list(transitive),
            "blast_radius_size": blast_size, "risk_level": risk_level}


def propagate_risks(
    nodes: list[str],
    edges: list[tuple[str, str]],
    base_risks: dict[str, float],
    decay: float,
) -> dict[str, Any]:
    """Propagate risk scores through the DAG."""
    if HAS_NATIVE:
        from ._loader import _rust_propagate_risks
        return _rust_propagate_risks(nodes, edges, base_risks, decay)
    # Pure Python fallback
    if not (0.0 <= decay <= 1.0):
        raise ValueError("decay must be between 0.0 and 1.0")

    reverse_adj: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        reverse_adj[dst].append(src)

    effective: dict[str, float] = {}
    risk_paths: dict[str, list[str]] = {}

    for node in nodes:
        own_risk = base_risks.get(node, 0.0)
        incoming = reverse_adj.get(node, [])
        max_propagated = 0.0
        max_source = ""
        for src in incoming:
            src_eff = effective.get(src, 0.0)
            propagated = src_eff * decay
            if propagated > max_propagated:
                max_propagated = propagated
                max_source = src

        effective_risk = max(own_risk, max_propagated)
        effective[node] = effective_risk

        if max_source and max_propagated > own_risk:
            path = risk_paths.get(max_source, [])[:]
            path.append(node)
            risk_paths[node] = path
        else:
            risk_paths[node] = [node]

    max_effective = max(effective.values()) if effective else 0.0
    high_risk = [n for n, r in effective.items() if r >= 0.7]

    return {"effective_risks": effective, "max_effective_risk": max_effective,
            "high_risk_nodes": high_risk, "risk_paths": risk_paths}


def find_critical_path(
    nodes: list[str],
    edges: list[tuple[str, str]],
    durations: dict[str, int],
) -> dict[str, Any]:
    """Identify the critical path in the DAG."""
    if HAS_NATIVE:
        from ._loader import _rust_find_critical_path
        return _rust_find_critical_path(nodes, edges, durations)
    # Pure Python fallback
    predecessors: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        predecessors[node] = []
    for src, dst in edges:
        predecessors[dst].append(src)

    earliest_finish: dict[str, int] = {}
    pred_on_path: dict[str, str | None] = {}

    for node in nodes:
        node_dur = durations.get(node, 0)
        max_pred = 0
        best_pred = None
        for pred in predecessors[node]:
            pf = earliest_finish.get(pred, 0)
            if pf > max_pred:
                max_pred = pf
                best_pred = pred
        earliest_finish[node] = max_pred + node_dur
        pred_on_path[node] = best_pred

    end_node = max(earliest_finish, key=earliest_finish.get) if earliest_finish else ""
    total_duration = earliest_finish.get(end_node, 0)

    critical_path: list[str] = []
    current: str | None = end_node
    while current:
        critical_path.append(current)
        current = pred_on_path.get(current)
    critical_path.reverse()

    critical_set = set(critical_path)
    is_on_critical = {n: n in critical_set for n in nodes}

    return {"critical_path": critical_path,
            "total_duration_ms": total_duration,
            "is_on_critical_path": is_on_critical}


def compute_reachability(
    source_nodes: list[str], edges: list[tuple[str, str]],
) -> dict[str, Any]:
    """Compute reachability from source nodes."""
    if HAS_NATIVE:
        from ._loader import _rust_compute_reachability
        return _rust_compute_reachability(source_nodes, edges)
    # Pure Python fallback
    forward: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        forward[src].append(dst)

    all_reachable: set[str] = set()
    by_source: dict[str, list[str]] = {}

    for source in source_nodes:
        visited: set[str] = set()
        queue = deque([source])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            for neighbor in forward.get(current, []):
                if neighbor not in visited:
                    queue.append(neighbor)
        visited.discard(source)
        all_reachable.update(visited)
        by_source[source] = list(visited)

    return {"reachable": list(all_reachable),
            "reachable_count": sum(len(v) for v in by_source.values()),
            "by_source": by_source}


def multi_node_blast_radius(
    failed_nodes: list[str], edges: list[tuple[str, str]],
) -> dict[str, Any]:
    """Calculate combined blast radius for multiple node failures."""
    if HAS_NATIVE:
        from ._loader import _rust_multi_node_blast_radius
        return _rust_multi_node_blast_radius(failed_nodes, edges)
    # Pure Python fallback
    forward: dict[str, list[str]] = defaultdict(list)
    for src, dst in edges:
        forward[src].append(dst)

    failed_set = set(failed_nodes)
    visited: set[str] = set()
    queue = deque(failed_nodes)

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        for neighbor in forward.get(current, []):
            if neighbor not in visited:
                queue.append(neighbor)

    blast_radius = [n for n in visited if n not in failed_set]
    blast_size = len(blast_radius)
    risk_level = "low" if blast_size == 0 else "medium" if blast_size <= 5 else "high" if blast_size <= 15 else "critical"

    per_node: dict[str, dict[str, Any]] = {}
    for node in failed_nodes:
        node_result = calculate_blast_radius(node, edges)
        per_node[node] = node_result

    return {"combined_blast_radius": blast_radius,
            "blast_radius_size": blast_size,
            "risk_level": risk_level,
            "per_node": per_node}
