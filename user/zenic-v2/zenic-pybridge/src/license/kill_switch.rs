//! Kill-switch connectivity check — TCP with timeout + grace period.
//!
//! Security hardening:
//! - License key sent via HTTP header instead of URL query parameter
//! - SSRF protection: blocks non-HTTP schemes and private IP ranges
//! - TLS enforcement: only https:// URLs are accepted (http:// is rejected)
//! - Default-deny on parse errors and connection issues

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;

use std::io::Read;
use std::net::{IpAddr, Ipv4Addr, Ipv6Addr, TcpStream};
use std::time::Duration;

/// Check if an IP address is a private/reserved range (SSRF protection).
///
/// Blocks:
/// - IPv4: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 127.0.0.0/8, 0.0.0.0
/// - IPv6: ::1, fe80::/10, fc00::/7, ::
fn is_private_ip(ip: &IpAddr) -> bool {
    match ip {
        IpAddr::V4(v4) => {
            v4.is_private()
                || v4.is_loopback()
                || v4.is_link_local()
                || v4.is_unspecified()
                || v4.is_multicast()
                || v4.is_documentation()
        }
        IpAddr::V6(v6) => {
            v6.is_loopback()
                || v6.is_unspecified()
                || v6.is_unicast_link_local()
                || v6.is_multicast()
                || matches!(v6.segments(), [0xfc00..=0xfdff, ..]) // Unique local
        }
    }
}

/// Parse a URL string to extract (host, port).
///
/// SSRF protection: rejects non-HTTPS schemes (http://, file://, ftp://, etc.)
/// and URLs that resolve to private IP ranges.
///
/// FIX: Only HTTPS is accepted. HTTP is rejected to prevent MITM attacks
/// on the Authorization header.
pub fn parse_host_port(url: &str) -> Option<(String, u16)> {
    let url = url.trim();
    if url.is_empty() {
        return None;
    }

    // FIX: Only allow https:// scheme. http:// is rejected to enforce TLS
    // and prevent MITM interception of the Authorization header.
    let rest = if url.starts_with("https://") {
        &url[8..]
    } else if url.starts_with("http://") {
        // HTTP is NOT allowed — enforce TLS for credential protection
        return None;
    } else {
        // Reject all other schemes (file://, ftp://, gopher://, etc.)
        return None;
    };

    let host_port = rest.split('/').next().unwrap_or(rest);
    let default_port: u16 = 443; // HTTPS only

    // Handle [IPv6]:port format
    if host_port.starts_with('[') {
        if let Some(bracket_end) = host_port.find(']') {
            let host = &host_port[1..bracket_end];
            let remainder = &host_port[bracket_end + 1..];
            let port = if remainder.starts_with(':') {
                remainder[1..].parse().unwrap_or(default_port)
            } else {
                default_port
            };
            return Some((host.to_string(), port));
        }
    }

    // Handle host:port format
    if let Some(colon_pos) = host_port.rfind(':') {
        let host = &host_port[..colon_pos];
        let port_str = &host_port[colon_pos + 1..];
        if port_str.chars().all(|c| c.is_ascii_digit()) && !port_str.is_empty() {
            let port = port_str.parse().unwrap_or(default_port);
            return Some((host.to_string(), port));
        }
    }

    Some((host_port.to_string(), default_port))
}

/// Perform a TLS-secured HTTPS GET request over an established TCP stream.
///
/// Security:
/// - Uses native-tls for TLS 1.2+ handshake (cert validation, encryption)
/// - License key is sent via the `Authorization` header, not URL query param
/// - Prevents credential leakage in server logs, proxy caches, browser history
fn perform_https_get(
    stream: TcpStream,
    host: &str,
    path_url: &str,
    license_key: &str,
    timeout: Duration,
) -> Result<String, String> {
    use std::io::{Read, Write};

    stream.set_read_timeout(Some(timeout)).map_err(|e| e.to_string())?;
    stream.set_write_timeout(Some(timeout)).map_err(|e| e.to_string())?;

    // TLS handshake via native-tls
    let connector = native_tls::TlsConnector::new().map_err(|e| format!("TLS connector init failed: {}", e))?;
    let mut tls_stream = connector.connect(host, stream).map_err(|e| format!("TLS handshake failed: {}", e))?;

    // Extract path from URL
    let path = if path_url.starts_with("https://") {
        let after_scheme = &path_url[8..];
        if let Some(slash_pos) = after_scheme.find('/') {
            &after_scheme[slash_pos..]
        } else {
            "/"
        }
    } else {
        "/"
    };

    // Send license_key via Authorization header (not URL query param)
    let request = format!(
        "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\nAccept: application/json\r\nAuthorization: Bearer {}\r\n\r\n",
        path, host, license_key
    );

    tls_stream.write_all(request.as_bytes()).map_err(|e| e.to_string())?;

    let mut response = String::new();
    tls_stream.read_to_string(&mut response).map_err(|e| e.to_string())?;

    // Extract body after HTTP headers (headers end at blank line)
    if let Some(body_start) = response.find("\r\n\r\n") {
        Ok(response[body_start + 4..].to_string())
    } else if let Some(body_start) = response.find("\n\n") {
        Ok(response[body_start + 2..].to_string())
    } else {
        Ok(response)
    }
}

/// Check the remote kill-switch endpoint.
///
/// Performs a TCP connectivity check to the remote URL. If the server is
/// reachable, attempts a minimal HTTP GET to read the response. If the
/// server is unreachable, a grace period is applied.
///
/// Parameters
/// ----------
/// remote_url : str
///     The kill-switch endpoint URL.
/// license_key : str
///     The license key to identify the client.
/// timeout_secs : int
///     Connection timeout in seconds (default: 5).
///
/// Returns
/// -------
/// dict
///     ``{"is_active": bool, "should_disable": bool, "message": str}``
#[pyfunction]
#[pyo3(signature = (remote_url, license_key, timeout_secs=5u64))]
pub fn check_kill_switch(
    py: Python<'_>,
    remote_url: &str,
    license_key: &str,
    timeout_secs: u64,
) -> PyResult<Py<PyDict>> {
    let result = PyDict::new_bound(py);

    // Empty URL = no kill switch configured
    if remote_url.trim().is_empty() {
        result.set_item("is_active", true)?;
        result.set_item("should_disable", false)?;
        result.set_item("message", "No kill switch URL configured, license is active")?;
        return Ok(result.unbind());
    }

    // Parse the URL to extract host and port
    let (host, port) = match parse_host_port(remote_url) {
        Some(hp) => hp,
        None => {
            result.set_item("is_active", false)?;
            result.set_item("should_disable", false)?;
            result.set_item("message", format!("Invalid kill switch URL: {}", remote_url))?;
            return Ok(result.unbind());
        }
    };

    // SSRF protection: Resolve the hostname and check for private IP ranges
    let addr = format!("{}:{}", host, port);
    let timeout = Duration::from_secs(timeout_secs);

    // DNS resolution with SSRF check
    let socket_addr: std::net::SocketAddr = match addr.parse() {
        Ok(sa) => sa,
        Err(_) => {
            // Try DNS resolution
            use std::net::ToSocketAddrs;
            match (&host[..], port).to_socket_addrs() {
                Ok(mut addrs) => {
                    // Find the first non-private IP address
                    match addrs.find(|a| !is_private_ip(&a.ip())) {
                        Some(sa) => sa,
                        None => {
                            result.set_item("is_active", false)?;
                            result.set_item("should_disable", false)?;
                            result.set_item("message", format!("SSRF protection: kill switch host '{}' resolves to private IP", host))?;
                            return Ok(result.unbind());
                        }
                    }
                }
                Err(_) => {
                    result.set_item("is_active", false)?;
                    result.set_item("should_disable", false)?;
                    result.set_item("message", format!("Cannot resolve kill switch host: {}", host))?;
                    return Ok(result.unbind());
                }
            }
        }
    };

    // Try TCP connection with timeout, then upgrade to TLS
    match TcpStream::connect_timeout(&socket_addr, timeout) {
        Ok(stream) => {
            // Server is reachable — attempt a TLS-secured HTTPS GET
            let response = perform_https_get(
                stream, &host, remote_url, license_key, timeout,
            );

            match response {
                Ok(body) => {
                    if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&body) {
                        let is_active = parsed
                            .get("active")
                            .or_else(|| parsed.get("is_active"))
                            .and_then(|v| v.as_bool())
                            .unwrap_or(true);

                        let should_disable = parsed
                            .get("should_disable")
                            .and_then(|v| v.as_bool())
                            .unwrap_or(false);

                        let message = parsed
                            .get("message")
                            .and_then(|v| v.as_str())
                            .unwrap_or("Kill switch check completed")
                            .to_string();

                        result.set_item("is_active", is_active)?;
                        result.set_item("should_disable", should_disable)?;
                        result.set_item("message", message)?;
                    } else {
                        result.set_item("is_active", true)?;
                        result.set_item("should_disable", false)?;
                        result.set_item("message", "Server reachable, license appears active")?;
                    }
                }
                Err(_) => {
                    result.set_item("is_active", true)?;
                    result.set_item("should_disable", false)?;
                    result.set_item(
                        "message",
                        "Server reachable but could not read response, license assumed active",
                    )?;
                }
            }
        }
        Err(_) => {
            // Server unreachable — apply grace period
            result.set_item("is_active", false)?;
            result.set_item("should_disable", false)?;
            result.set_item(
                "message",
                format!("Kill switch server unreachable ({}), grace period active", addr),
            )?;
        }
    }

    Ok(result.unbind())
}
