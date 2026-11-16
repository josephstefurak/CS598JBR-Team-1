use fixture::fixture::*;

const GREETING: &str = "hello from the fixture harness";

/// Planted harness clippy::style (needless_return) in the immutable test file.
fn helper() -> i32 {
    return 3;
}

fn main() {
    let _ = helper();
}

#[test]
fn passes() {
    assert_eq!(double(helper()), 6);
    assert_eq!(greeting(), GREETING);
    assert!(always_equal(1));
    assert!(is_positive(2));
    assert_eq!(total(Box::new(vec![1, 2])), 3);
    assert_eq!(second_as_meters(&[7, 9]).0, 9);
}

#[test]
fn fails() {
    assert_eq!(double(2), 5, "planted failure");
}
