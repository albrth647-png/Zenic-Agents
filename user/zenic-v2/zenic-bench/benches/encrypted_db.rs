//! Benchmarks for EncryptedDb — SQLCipher query performance.
//!
//! Measures:
//! - Open connection with key derivation (256K KDF iterations)
//! - CREATE TABLE + INSERT performance
//! - SELECT by primary key
//! - SELECT with index
//! - UPDATE performance
//! - Concurrent read performance (multiple connections)
//! - KDF iteration overhead

use criterion::{
    black_box, criterion_group, criterion_main, BenchmarkId, Criterion, Throughput,
};
use rusqlite::Connection;
use std::sync::Arc;
use std::thread;

// ---------------------------------------------------------------------------
// Benchmark: Open encrypted database
// ---------------------------------------------------------------------------

/// Measures the cost of opening an SQLCipher database.
/// The 256K KDF iterations make this expensive.
fn bench_open_encrypted(c: &mut Criterion) {
    let mut group = c.benchmark_group("encrypted_db/open");

    let tmp_dir = tempfile::tempdir().unwrap();
    let db_path = tmp_dir.path().join("bench_encrypted.db");
    let db_path_str = db_path.to_str().unwrap().to_string();

    // Pre-create the database
    {
        let conn = Connection::open(&db_path_str).unwrap();
        conn.pragma_update(None, "key", "test_passphrase").unwrap();
        conn.execute_batch("SELECT count(*) FROM sqlite_master").unwrap();
    }

    group.throughput(Throughput::Elements(1));
    group.bench_function("with_key_derivation", |b| {
        b.iter(|| {
            let conn = Connection::open(black_box(&db_path_str)).unwrap();
            conn.pragma_update(None, "key", "test_passphrase").unwrap();
            conn.execute_batch("SELECT count(*) FROM sqlite_master").unwrap();
            drop(conn);
        });
    });

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: INSERT performance
// ---------------------------------------------------------------------------

/// Measures INSERT performance on encrypted database.
fn bench_insert(c: &mut Criterion) {
    let mut group = c.benchmark_group("encrypted_db/insert");

    for &batch_size in &[1usize, 10, 100] {
        group.throughput(Throughput::Elements(batch_size as u64));
        group.bench_with_input(
            BenchmarkId::new("batch", batch_size),
            &batch_size,
            |b, &batch_size| {
                b.iter(|| {
                    let conn = Connection::open(":memory:").unwrap();
                    conn.pragma_update(None, "key", "bench_key").unwrap();
                    conn.execute_batch(
                        "CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT, value REAL, data BLOB)"
                    ).unwrap();

                    for i in 0..batch_size {
                        conn.execute(
                            "INSERT INTO t (id, name, value, data) VALUES (?1, ?2, ?3, ?4)",
                            rusqlite::params![i as i64, format!("name-{}", i), i as f64 * 1.5, vec![0u8; 64]],
                        ).unwrap();
                    }
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: SELECT performance
// ---------------------------------------------------------------------------

/// Measures SELECT performance on encrypted database.
fn bench_select(c: &mut Criterion) {
    let mut group = c.benchmark_group("encrypted_db/select");

    for &row_count in &[100usize, 1000, 10000] {
        let conn = Connection::open(":memory:").unwrap();
        conn.pragma_update(None, "key", "bench_key").unwrap();
        conn.execute_batch(
            "CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT, value REAL)"
        ).unwrap();

        for i in 0..row_count {
            conn.execute(
                "INSERT INTO t (id, name, value) VALUES (?1, ?2, ?3)",
                rusqlite::params![i as i64, format!("name-{}", i), i as f64],
            ).unwrap();
        }

        group.throughput(Throughput::Elements(1));
        group.bench_with_input(
            BenchmarkId::new("by_pk_rows", row_count),
            &conn,
            |b, conn| {
                let mut idx = 0;
                b.iter(|| {
                    let result: (i64, String, f64) = conn
                        .query_row(
                            "SELECT id, name, value FROM t WHERE id = ?1",
                            rusqlite::params![idx as i64 % row_count as i64],
                            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
                        )
                        .unwrap();
                    let _ = black_box(result);
                    idx += 1;
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Full-text scan (no index)
// ---------------------------------------------------------------------------

/// Measures full table scan performance.
fn bench_full_scan(c: &mut Criterion) {
    let mut group = c.benchmark_group("encrypted_db/full_scan");

    for &row_count in &[100usize, 1000, 10000] {
        let conn = Connection::open(":memory:").unwrap();
        conn.pragma_update(None, "key", "bench_key").unwrap();
        conn.execute_batch("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)").unwrap();

        for i in 0..row_count {
            conn.execute(
                "INSERT INTO t (id, name) VALUES (?1, ?2)",
                rusqlite::params![i as i64, format!("name-{}", i)],
            ).unwrap();
        }

        group.throughput(Throughput::Elements(row_count as u64));
        group.bench_with_input(
            BenchmarkId::new("rows", row_count),
            &conn,
            |b, conn| {
                b.iter(|| {
                    let mut stmt = conn.prepare("SELECT * FROM t WHERE name LIKE '%name-5%'").unwrap();
                    let rows: Vec<(i64, String)> = stmt
                        .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))
                        .unwrap()
                        .filter_map(|r| r.ok())
                        .collect();
                    let _ = black_box(rows);
                });
            },
        );
    }

    group.finish();
}

// ---------------------------------------------------------------------------
// Benchmark: Concurrent reads (multiple connections to same encrypted DB)
// ---------------------------------------------------------------------------

/// Measures concurrent read throughput on a file-backed encrypted database.
fn bench_concurrent_reads(c: &mut Criterion) {
    let mut group = c.benchmark_group("encrypted_db/concurrent_reads");

    let tmp_dir = tempfile::tempdir().unwrap();
    let db_path = tmp_dir.path().join("bench_concurrent.db");
    let db_path_str = db_path.to_str().unwrap().to_string();

    // Pre-populate
    {
        let conn = Connection::open(&db_path_str).unwrap();
        conn.pragma_update(None, "key", "bench_key").unwrap();
        conn.execute_batch("SELECT count(*) FROM sqlite_master").unwrap();
        conn.execute_batch("PRAGMA journal_mode=WAL;").unwrap();
        conn.execute_batch("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT, value REAL)").unwrap();
        for i in 0..1000 {
            conn.execute(
                "INSERT INTO t (id, name, value) VALUES (?1, ?2, ?3)",
                rusqlite::params![i as i64, format!("name-{}", i), i as f64],
            ).unwrap();
        }
    }

    for &num_threads in &[1usize, 2, 4] {
        group.throughput(Throughput::Elements(num_threads as u64 * 500));
        group.bench_with_input(
            BenchmarkId::new("threads", num_threads),
            &num_threads,
            |b, &num_threads| {
                b.iter(|| {
                    let handles: Vec<_> = (0..num_threads)
                        .map(|thread_id| {
                            let db_path = db_path_str.clone();
                            thread::spawn(move || {
                                let conn = Connection::open(&db_path).unwrap();
                                conn.pragma_update(None, "key", "bench_key").unwrap();
                                conn.execute_batch("SELECT count(*) FROM sqlite_master").unwrap();
                                for i in 0..500 {
                                    let _ = conn.query_row(
                                        "SELECT name FROM t WHERE id = ?1",
                                        rusqlite::params![((thread_id * 500 + i) % 1000) as i64],
                                        |row| row.get::<_, String>(0),
                                    );
                                }
                            })
                        })
                        .collect();

                    for h in handles {
                        h.join().unwrap();
                    }
                });
            },
        );
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_open_encrypted,
    bench_insert,
    bench_select,
    bench_full_scan,
    bench_concurrent_reads,
);
criterion_main!(benches);
