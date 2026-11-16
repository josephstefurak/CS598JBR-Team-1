//! Self-test fixture, partial variant (loop drills): builds, one clippy style warning, one interface item missing.

/// Wrapper around a distance.
#[repr(transparent)]
pub struct Meters(pub u32);

pub fn second_as_meters(v: &[u32]) -> Meters {
    Meters(v[1])
}

pub fn always_equal(_x: i32) -> bool {
    true
}

pub fn double(x: i32) -> i32 {
    return x * 2;
}

pub fn is_positive(x: i32) -> bool {
    x > 0
}

// The fixture interface fixes a Box<Vec<i32>> parameter; the drill project allows this one lint.
#[allow(clippy::boxed_local)]
pub fn total(v: Box<Vec<i32>>) -> i32 {
    v.iter().sum()
}

pub fn greeting() -> &'static str {
    concat!("hello from the ", "fixture harness")
}
