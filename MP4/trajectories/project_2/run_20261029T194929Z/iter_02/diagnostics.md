### Build: ok

### Tests: 3 of 4 passed
- `read_test_vector` FAILED (known-defective test, expected to fail)

```
thread 'read_test_vector' panicked at src/bin/test.rs:126:26:
assertion `left == right` failed
  left: 4
 right: 0
note: run with `RUST_BACKTRACE=1` environment variable to display a backtrace
```

### Clippy (your code only; warnings from the test files are excluded): correctness 0, style 0, complexity 0, perf 0

### Safety (proxy): unsafe lines 0, unsafe calls 0, unsafe casts 0, pointer arithmetic 0

### Interface: 0 missing, 0 changed
