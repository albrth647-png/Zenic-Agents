//! Shared tests for the bus module.

#[cfg(test)]
mod tests {
    use crate::bus::RingBuffer;

    #[test]
    fn test_ring_buffer_basic() {
        // Use the #[new] constructor (does not require Python)
        let cap = 4;
        let rb = RingBuffer::new(cap);
        assert_eq!(rb.capacity, cap);
        // Note: is_empty(), is_full(), etc. are #[pymethods] only —
        // not accessible from pure Rust tests.
    }

    #[test]
    fn test_ring_buffer_new_zero_capacity() {
        // When capacity is 0, defaults to 1024
        let rb = RingBuffer::new(0);
        assert_eq!(rb.capacity, 1024);
    }
}
