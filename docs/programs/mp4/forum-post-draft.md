# Forum post draft (O1) — hold until MP4 formally opens

*Drafted 2026-10-28. Owner deferred posting because MP3's due date has not
passed. Before posting, check the course page for an existing answer on
either topic and trim accordingly.*

---

**Subject: MP4 — defective libpsbt test, and release timing for the unsafe-metrics tool and validation script**

Hi all, two things on MP4 from Group 1 (satc and libpsbt).

**1. A libpsbt benchmark test cannot be passed by a correct parser.**
In the CRUST-Bench Rust tests for libpsbt (`src/bin/test.rs`), the `read_test_vector` test installs a callback that is meant to check the first record is type 0 and the second is type 0. However, the counter is declared as a local inside the callback:

```rust
fn checker(elem: &mut PsbtElem, _ud: &mut dyn std::any::Any) {
    let mut step = 0;
    match elem {
        PsbtElem::Record { record, .. } => match step {
            0 => assert_eq!(record.record_type, 0),
            1 => assert_eq!(record.record_type, 0),
            _ => {}
        },
        _ => {}
    }
    step += 1;
}
```

Because `step` resets to 0 on every call, the callback asserts that every record has type 0. The PSBT test vector contains records of types 1, 2, 4, 5 and 6, so any faithful translation of the C parser, which invokes the handler for every record, panics inside this test. The only way to make it pass is to hide records from the callback, which breaks the parser and would violate the no-gaming rules in the handout. Since we are not allowed to modify tests, our plan is to implement the C semantics faithfully, report this test as failing with this explanation, and accept 3 of 4.

Could you confirm how this test will be graded for libpsbt? For example, will it be excluded from the pass rate, or is the expected outcome 3 of 4?

**2. Where and when will the course-provided tools be released?**
The handout references two things we need before submission: the **unsafe-metrics tool** (Task 3.3 says the instructional team will provide it and that we should use it during development and report its output in Task 4) and the **validation script** (checks the required directories, config files, trajectories and translations). Neither appears to be posted yet. Could you let us know roughly when and where (Canvas, Piazza, a GitHub repo) they will be available, and what the expected invocation looks like? We have built our pipeline so the tool can slot in, but we need its real output format to finalize the safety table.

Thanks!
