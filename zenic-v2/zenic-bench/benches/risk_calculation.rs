//! Benchmarks for Risk Calculation — Graph algorithms for blast radius,
//! risk propagation, critical path, and reachability analysis.
//!
//! These benchmarks test the pure algorithmic components extracted from
//! zenic-pybridge/src/risk/ (which use PyO3 types). Here we benchmark
//! the core algorithms directly with Rust data structures.
//!
//! Measures:
//! - Blast radius calculation (single node, varying graph sizes)
//! - Multi-node blast radius
//! - Risk propagation (varying decay factors)
//! - Critical path identification
//! - Reachability analysis
//! - Graph construction overhead

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};
use std::collections::{HashMap, HashSet, VecDeque};

// ---------------------------------------------------------------------------
// Helpers — Pure Rust graph structures (mirrors pybridge risk module)
// ---------------------------------------------------------------------------

/// Builds a forward adjacency list from edge pairs.
fn build_forward_adj(edges: &[(String, String)]) -> HashMap<String, Vec<String>> {
    let mut adj: HashMap<String, Vec<String>> = HashMap::new();
    for (src, dst) in edges {
        adj.entry(src.clone()).or_default().push(dst.clone());
    }
    adj
}

/// Generates a linear chain graph: A → B → C → ... → N
fn linear_chain_graph(n: usize) -> Vec<(String, String)> {
    (0..n - 1)
        .map(|i| (format!("node_{}", i), format!("node_{}", i + 1)))
        .collect()
}

/// Generates a diamond graph: each node fans out to 3 children.
fn diamond_graph(depth: usize, fanout: usize) -> Vec<(String, String)> {
    let mut edges = Vec::new();
    for d in 0..depth {
        for f in 0..fanout.pow(d as u32) {
            let parent = format!("d{}_f{}", d, f);
            for c in 0..fanout {
                let child = format!("d{}_f{}", d + 1, f * fanout + c);
                edges.push((parent.clone(), child));
            }
        }
    }
    edges
}

/// Generates a random-ish DAG with N nodes and E edges.
fn random_dag(nodes: usize, edges_per_node: usize) -> Vec<(String, String)> {
    let mut edges = Vec::new();
    for i in 0..nodes {
        for j in 1..=edges_per_node {
            let target = (i + j) % nodes;
            if target != i {
                edges.push((format!("n{}", i), format!("n{}", target)));
            }
        }
    }
    edges
}

// ---------------------------------------------------------------------------
// Algorithm: BFS blast radius
// ---------------------------------------------------------------------------

fn blast_radius_bfs(
    forward: &HashMap<String, Vec<String>>,
    source: &str,
) -> HashSet<String> {
    let mut visited = HashSet::new();
    let mut queue = VecDeque::new();
    queue.push_back(source.to_string());

    while let Some(current) = queue.pop_front() {
        if visited.contains(&current) {
            continue;
        }
        visited.insert(current.clone());
        if let Some(neighbors) = forward.get(&current) {
            for neighbor in neighbors {
                if !visited.contains(neighbor) {
                    queue.push_back(neighbor.clone());
                }
            }
        }
    }

    visited.remove(source);
    visited
}

// ---------------------------------------------------------------------------
// Algorithm: Risk propagation
// ---------------------------------------------------------------------------

fn propagate_risks(
    nodes: &[String],
    edges: &[(String, String)],
    base_risks: &HashMap<String, f64>,
    decay: f64,
) -> HashMap<String, f64> {
    let mut reverse_adj: HashMap<String, Vec<String>> = HashMap::new();
    for (src, dst) in edges {
        reverse_adj.entry(dst.clone()).or_default().push(src.clone());
    }

    let mut effective: HashMap<String, f64> = HashMap::new();
    for node in nodes {
        let own_risk = *base_risks.get(node).unwrap_or(&0.0);
        let incoming = reverse_adj.get(node).cloned().unwrap_or_default();
        let max_propagated = incoming
            .iter()
            .filter_map(|src| effective.get(src).map(|r| r * decay))
            .fold(0.0_f64, f64::max);
        effective.insert(node.clone(), own_risk.max(max_propagated));
    }
    effective
}

// ---------------------------------------------------------------------------
// Algorithm: Critical path
// ---------------------------------------------------------------------------

fn find_critical_path(
    nodes: &[String],
    edges: &[(String, String)],
    durations: &HashMap<String, i64>,
) -> (Vec<String>, i64) {
    let mut predecessors: HashMap<String, Vec<String>> = HashMap::new();
    for node in nodes {
        predecessors.entry(node.clone()).or_default();
    }
    for (src, dst) in edges {
        predecessors.entry(dst.clone()).or_default().push(src.clone());
    }

    let mut earliest_finish: HashMap<String, i64> = HashMap::new();
    let mut pred_on_path: HashMap<String, Option<String>> = HashMap::new();

    for node in nodes {
        let dur = *durations.get(node).unwrap_or(&0);
        let preds = predecessors.get(node).cloned().unwrap_or_default();
        let (max_pf, best) = preds.iter().fold((0_i64, None), |(mf, bp), p| {
            let pf = *earliest_finish.get(p).unwrap_or(&0);
            if pf > mf { (pf, Some(p.clone())) } else { (mf, bp) }
        });
        earliest_finish.insert(node.clone(), max_pf + dur);
        pred_on_path.insert(node.clone(), best);
    }

    let (end_node, total_dur) = earliest_finish
        .iter()
        .max_by_key(|(_, &f)| f)
        .map(|(k, &v)| (k.clone(), v))
        .unwrap_or_default();

    let mut path = Vec::new();
    let mut current: Option<String> = Some(end_node);
    while let Some(node) = current {
        path.push(node.clone());
        current = pred_on_path.get(&node).and_then(|p| p.clone());
    }
    path.reverse();
    (path, total_dur)
}

// ---------------------------------------------------------------------------
// Algorithm: Reachability
// ---------------------------------------------------------------------------

fn compute_reachability(
    forward: &HashMap<String, Vec<String>>,
    sources: &[String],
) -> HashMap<String, Vec<String>> {
    let mut by_source = HashMap::new();
    for source in sources {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        queue.push_back(source.clone());

        while let Some(current) = queue.pop_front() {
            if visited.contains(&current) {
                continue;
            }
            visited.insert(current.clone());
            if let Some(neighbors) = forward.get(&current) {
                for n in neighbors {
                    if !visited.contains(n) {
                        queue.push_back(n.clone());
                    }
                }
            }
        }
        visited.remove(source);
        by_source.insert(source.clone(), visited.into_iter().collect());
    }
    by_source
}

// ---------------------------------------------------------------------------
// Benchmarks
// ---------------------------------------------------------------------------

fn bench_blast_radius(c: &mut Criterion) {
    let mut group = c.benchmark_group("risk_calculation/blast_radius");

    for &node_count in &[10usize, 50, 100, 500, 1000] {
        let edges = linear_chain_graph(node_count);
        let forward = build_forward_adj(&edges);

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("linear_chain", node_count),
            &forward,
            |b, forward| {
                b.iter(|| {
                    let _ = blast_radius_bfs(black_box(forward), black_box("node_0"));
                });
            },
        );
    }

    // Diamond graph (exponential fanout)
    for &depth in &[3usize, 5, 7] {
        let edges = diamond_graph(depth, 2);
        let forward = build_forward_adj(&edges);
        let _node_count = forward.len();

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("diamond_depth", depth),
            &forward,
            |b, forward| {
                b.iter(|| {
                    let _ = blast_radius_bfs(black_box(forward), black_box("d0_f0"));
                });
            },
        );
    }

    group.finish();
}

fn bench_multi_node_blast_radius(c: &mut Criterion) {
    let mut group = c.benchmark_group("risk_calculation/multi_node_blast");

    for &node_count in &[50usize, 200, 500] {
        let edges = random_dag(node_count, 3);
        let forward = build_forward_adj(&edges);
        let sources: Vec<String> = (0..5).map(|i| format!("n{}", i)).collect();

        group.throughput(Throughput::Elements(sources.len() as u64));
        group.bench_with_input(
            BenchmarkId::new("5_sources", node_count),
            &forward,
            |b, forward| {
                b.iter(|| {
                    for src in &sources {
                        let _ = blast_radius_bfs(black_box(forward), black_box(src));
                    }
                });
            },
        );
    }

    group.finish();
}

fn bench_risk_propagation(c: &mut Criterion) {
    let mut group = c.benchmark_group("risk_calculation/risk_propagation");

    for &node_count in &[10usize, 50, 100, 500] {
        let edges = linear_chain_graph(node_count);
        let nodes: Vec<String> = (0..node_count).map(|i| format!("node_{}", i)).collect();
        let base_risks: HashMap<String, f64> = nodes
            .iter()
            .enumerate()
            .map(|(i, n)| (n.clone(), (i as f64 / node_count as f64).min(1.0)))
            .collect();

        for &decay in &[0.0, 0.5, 0.9, 1.0] {
            group.throughput(Throughput::Elements(node_count as u64));
            group.bench_with_input(
                BenchmarkId::new(format!("nodes_{}", node_count), decay),
                &(nodes.clone(), edges.clone(), base_risks.clone()),
                |b, (nodes, edges, base_risks)| {
                    b.iter(|| {
                        let _ = propagate_risks(
                            black_box(nodes),
                            black_box(edges),
                            black_box(base_risks),
                            black_box(decay),
                        );
                    });
                },
            );
        }
    }

    group.finish();
}

fn bench_critical_path(c: &mut Criterion) {
    let mut group = c.benchmark_group("risk_calculation/critical_path");

    for &node_count in &[10usize, 50, 100, 500] {
        let edges = linear_chain_graph(node_count);
        let nodes: Vec<String> = (0..node_count).map(|i| format!("node_{}", i)).collect();
        let durations: HashMap<String, i64> = nodes
            .iter()
            .map(|n| (n.clone(), 10))
            .collect();

        group.throughput(Throughput::Elements(node_count as u64));
        group.bench_with_input(
            BenchmarkId::new("linear_chain", node_count),
            &(nodes, edges, durations),
            |b, (nodes, edges, durations)| {
                b.iter(|| {
                    let _ = find_critical_path(
                        black_box(nodes),
                        black_box(edges),
                        black_box(durations),
                    );
                });
            },
        );
    }

    group.finish();
}

fn bench_reachability(c: &mut Criterion) {
    let mut group = c.benchmark_group("risk_calculation/reachability");

    for &node_count in &[50usize, 200, 500] {
        let edges = random_dag(node_count, 3);
        let forward = build_forward_adj(&edges);
        let sources: Vec<String> = (0..3).map(|i| format!("n{}", i)).collect();

        group.throughput(Throughput::Elements(sources.len() as u64));
        group.bench_with_input(
            BenchmarkId::new("3_sources", node_count),
            &forward,
            |b, forward| {
                b.iter(|| {
                    let _ = compute_reachability(black_box(forward), black_box(&sources));
                });
            },
        );
    }

    group.finish();
}

fn bench_graph_construction(c: &mut Criterion) {
    let mut group = c.benchmark_group("risk_calculation/graph_construction");

    for &edge_count in &[100usize, 1000, 10000] {
        group.throughput(Throughput::Elements(edge_count as u64));
        group.bench_with_input(
            BenchmarkId::new("build_adj_list", edge_count),
            &edge_count,
            |b, &edge_count| {
                let edges: Vec<(String, String)> = (0..edge_count)
                    .map(|i| (format!("src_{}", i), format!("dst_{}", i)))
                    .collect();
                b.iter(|| {
                    let _ = build_forward_adj(black_box(&edges));
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_blast_radius,
    bench_multi_node_blast_radius,
    bench_risk_propagation,
    bench_critical_path,
    bench_reachability,
    bench_graph_construction,
);
criterion_main!(benches);
