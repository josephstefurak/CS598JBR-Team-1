//! Self-test fixture (not a benchmark). Each item plants exactly one finding.

/// Wrapper used as a transmute target.
#[repr(transparent)]
pub struct Meters(pub u32);

/// Planted: the only unsafe block, one transmute, one ptr.add.
pub fn second_as_meters(v: &[u32]) -> Meters {
    let p = v.as_ptr();
    unsafe { std::mem::transmute::<u32, Meters>(*p.add(1)) }
}

/// Planted clippy::correctness (eq_op).
pub fn always_equal(x: i32) -> bool {
    x == x
}

/// Planted clippy::style (needless_return).
pub fn double(x: i32) -> i32 {
    return x * 2;
}

/// Planted clippy::complexity (needless_bool).
pub fn is_positive(x: i32) -> bool {
    if x > 0 { true } else { false }
}

/// Planted clippy::perf (boxed_local).
pub fn total(v: Box<Vec<i32>>) -> i32 {
    v.iter().sum()
}

/// Planted hard-coding: a test literal of 20+ characters copied into library code.
pub fn greeting() -> &'static str {
    "hello from the fixture harness"
}
