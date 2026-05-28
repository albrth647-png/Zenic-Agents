//! Cryptographic primitives — HMAC-SHA256, constant-time comparison, hex encode/decode.

use hmac::Hmac;
use sha2::Sha256;

/// Constant-time comparison of two byte slices.
///
/// WARNING: This hand-rolled implementation is logically correct but
/// NOT guaranteed to compile to constant-time assembly. The Rust compiler
/// could optimize away the loop or introduce early exits.
/// For production-grade security, consider replacing with the `subtle` crate's
/// `ConstantTimeEq` which uses compiler barriers.
/// TODO(security): Migrate to `subtle::ConstantTimeEq` in next iteration.
pub fn constant_time_compare(a: &[u8], b: &[u8]) -> bool {
    if a.len() != b.len() {
        return false;
    }
    let mut result: u8 = 0;
    for (x, y) in a.iter().zip(b.iter()) {
        result |= x ^ y;
    }
    result == 0
}

/// Compute HMAC-SHA256 of data with the given secret key.
///
/// HMAC can accept any key size, so this never fails.
/// Using `expect()` is safe here because `new_from_slice` is
/// documented as infallible for HMAC-SHA256.
pub fn hmac_sha256(secret: &[u8], data: &[u8]) -> [u8; 32] {
    use hmac::Mac;
    let mut mac = Hmac::<Sha256>::new_from_slice(secret)
        .expect("HMAC-SHA256 accepts any key length — this is documented as infallible");
    mac.update(data);
    mac.finalize().into_bytes().into()
}

/// Encode bytes as a hex string (lowercase).
pub fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

/// Decode a hex string to bytes.
pub fn hex_decode(hex: &str) -> Result<Vec<u8>, String> {
    let hex = hex.trim();
    if hex.len() % 2 != 0 {
        return Err("Hex string has odd length".to_string());
    }
    (0..hex.len())
        .step_by(2)
        .map(|i| {
            u8::from_str_radix(&hex[i..i + 2], 16)
                .map_err(|e| format!("Invalid hex at position {}: {}", i, e))
        })
        .collect()
}
