# M8 structural inspection: satc and libpsbt translations

Scope: library code only. Paths are relative to `MP4/translations/`.
satc = `project_1/src/satc.rs` (634 lines). libpsbt = `project_2/src/{base64,cli,compactsize,psbt,tx}.rs` (1518 lines).
`src/bin` and `src/interfaces` are excluded from the counts. Nothing was built or run; this is a read of the code only.

Grep method: `/usr/bin/grep -nE '<pattern>' <files>`, run over each project's library files (the helper script was a scratch file and is not committed). Patterns used:
`\.unwrap\(\)` · `\.expect\(` · `(panic|unreachable|unimplemented|todo|assert|assert_eq|assert_ne|debug_assert[a-z_]*)!` · `\.clone\(\)` ·
` as (u8|u16|u32|u64|usize|i8|i16|i32|i64|isize|f64|f32|char)\b` · `^\s*(pub(\(crate\))? )?static |thread_local!` · `for [a-z_]+ in 0\.\.` ·
`#!?\[allow` · `\bunsafe\b` · `\.unwrap_or` · `&mut ` · `\) -> PsbtResult` · `-> Result<` · `-> Option<`.
I checked every index expression by hand. The grep can't tell whether an index can panic.

## satc

### Counts (library code only)

| Pattern | Count | Sites |
|---|---|---|
| `.unwrap()` / `.expect(` | 0 / 0 | none |
| `panic!`/`unreachable!`/`unimplemented!`/`todo!`/`assert*!` | 0 | none |
| `.clone()` | 0 | none. H-A1's risk did not happen: Copy arrays are copied with `*p` (`satc.rs:226`, `:477`, `:513`) |
| `as` casts | 0 | none |
| `static` / `thread_local` | 0 | none |
| `unsafe` | 0 | none |
| `#[allow]` | 1 | `satc.rs:411 #[allow(clippy::too_many_arguments)]`. This is the one allowance D-ALLOW permits, on the function it names |
| `.unwrap_or` | 1 | `satc.rs:334 polygon.points.first().copied().unwrap_or([0.0, 0.0])`. It gives defined behaviour where the C would read `points[0]` of an empty polygon (UB) |
| C-style index loop | 1 | `satc.rs:550 for i in 0..len {` (`len = points.len()`, `:548`). It needs `i` to reach the neighbouring `prev`/`next` elements (`:551-552`) and to index `edges[i]` (`:556`) |
| Index that can panic on input the C handles | 0 | Runtime Vec indexes are at `:172`, `:368`, `:556-557`, `:565-566`, `:578-579`. All are bounded by `calc_points.len()` with a `% len` wrap. `edges[i]` (`:556`) only goes out of range if a caller makes the pub fields inconsistent, which would also be an out-of-bounds read (UB) in the C |
| Out-parameters (`&mut` used to return values) | 6, all set by the interface | `:389 result: &mut [f64; 2]` (flatten). `response: &mut SatcResponse` at `:205`, `:420`, `:520`, `:542`, `:624` |
| Integer codes vs Option/Result | 1 code-returning fn, set by the interface | `:486 satc_voronoi_region(..) -> i32` returns the `SATC_*_VORONOI_REGION` i32 constants (`:72-76`). There are no error paths. `bool` returns follow the interface |

### Ownership: good
- `satc.rs:226 let mut p = *p;` and `:477 *axis` copy `[f64;2]` instead of cloning it.
- `satc.rs:183-186` `satc_polygon_set_points` takes the `Vec` by value and moves it into the struct (`polygon.points = points;`). No copy is made.
- `satc.rs:513 test_point.pos = *point;` takes a borrowed point and mutates an owned local.
- Awkward but set by the interface: `satc.rs:225 pub fn satc_point_copy(p: &[f64; 2], q: &[f64; 2])`. Its `p` parameter is dead (H-A3). The body (`:226-229`) still copies `p` and overwrites both fields. Returning `*q` would be equivalent.

### Types: acceptable. The weak spots are all set by the interface
- `satc.rs:554 let mut overlap_n = None;` / `:573 Some(satc_point_normalize(&point))`: the C `NULL` pointer becomes an `Option`, which is the agent's own good choice.
- `satc.rs:22 pub num_points: usize` duplicates `points.len()`, and the code honours it with `.take(polygon.num_points)` at `:157` and `:339`. This field comes from the interface.
- `satc.rs:486 -> i32` and `:563-590` match on i32 constants with a catch-all `_ =>` for the middle region. A private enum was possible, but the public return type is fixed.
- `satc.rs:143-147 impl Default for SatcResponse` was added by the agent. It resolves H-A2 `new_without_default` without an allow.

### Control flow: mostly iterator-based. One function keeps the C's loop shape
- Good: `satc.rs:154-166` `polygon_recalc` is written as a `.iter().take().map().collect()` pipeline.
- Good: `satc.rs:210 for axis in a.normals.iter().chain(b.normals.iter())` merges the C's two loops (C `satc.h:1446-1458`) into one.
- Good: `satc.rs:439-443 let shortest_way_out = || {...}` turns a duplicated C branch into a closure.
- C-shaped: `satc.rs:550-611` keeps the C's index loop, the `overlap`/`overlap_n` locals and the early `return false` (C `satc.h:1324-1403`). `:604-610 match overlap_n { Some(normal) if ... => ..., _ => {} }` is a single-arm match.

### Error handling: not applicable. UB is given defined behaviour as D-FAITHFUL requires
- `satc.rs:330-334`: the doc comment says the uninitialised C `pos` is taken to be the origin. The `unwrap_or` that covers an empty polygon is not mentioned in that comment.
- `satc.rs:394 points.iter().take(len)` stops at the slice end where the C would read past it.
- C bugs are reproduced and documented: `:269-277` (rotate sign), `:282-290` (normalize macro, NaN `y`), `:294-299` (unparenthesised project macro), `:338 let mut y_max = x_max;`.

### Organisation: flat free functions that mirror C names (set by the interface), with small private helpers
- `satc.rs:79-91` adds private `point_dot`/`point_len2`/`point_len` in place of the C macros.
- `satc.rs:150 fn polygon_recalc(polygon: &mut SatcPolygon)` is a free function where a private method would also work. This was the agent's choice and is minor.
- `satc.rs:426-429` calls the out-parameter pub API internally (`let mut range_a = [0.0, 0.0]; satc_flatten_points_on(..., &mut range_a)`) instead of a private helper that returns the value. The agent chose to reuse the public function.

## libpsbt

### Counts (library code only)

| Pattern | Count | Sites |
|---|---|---|
| `.unwrap()` / `.expect(` | 0 / 0 | none |
| panic/assert family | 0 | none |
| `.clone()` | 1 | `cli.rs:45 psbt_type_tostr(record.record_type, record.scope.clone())`. The interface takes `PsbtScope` by value and derives only `Clone` (`psbt.rs:66`). The agent added `Copy` to `PsbtState` (`psbt.rs:73`) but not to `PsbtScope`, so this clone could have been avoided |
| `as` casts | 13 | Listed below |
| `static` / `thread_local` | 2 items | `psbt.rs:143 pub static PSBT_ERRMSG` comes from the interface. `psbt.rs:145-150 thread_local! { static ERRMSG: Cell<&'static str> ... }` is the agent's (H-L6 safe option). The broad `\bstatic\b` grep matched 13 lines; the other 11 are `&'static str` lifetimes |
| `unsafe` / `#[allow]` | 0 / 0 | none |
| `.unwrap_or*` | 7 | `psbt.rs:634`, `:652`, `:749`, `:768`, `:791`; `tx.rs:66`, `:231`. All are deliberate defaults, not hidden panics |
| C-style index loops | 0 of the `0..x.len()` form | `tx.rs:81`, `:88 for _ in 0..count` repeat a count read from the input. `tx.rs:95`, `:97 for i in 0..inputs` / `for j in 0..count` use the counter as a value, inside the dead segwit branch (`:92-93`) |
| Index that can panic on input the C handles | 0 | Every slice is clamped or `.get`-based: `psbt.rs:321`, `:323`, `:381`, `:383` (`.min(len)`); `:663`, `:680` (after `resize`); `:721`, `:748`, `:767`, `:791` (`.get`); `:825` (`chunks_exact(2)`); `:849` (`& 0x0f`); `base64.rs:34` (6-bit value); `:74`, `:78`, `:94` (u8 into a 256-entry table); `:102` (`filled < 4`) |
| Scalar out-parameters | 3, all set by the interface | `psbt.rs:316 psbt_len: &mut usize`, `:352 out_len`, `:379 out_len` |
| Buffer out-parameters | 8 public (set by the interface), 4 private | Public: `base64.rs:15`, `:20`, `:69` (`_out`); `compactsize.rs:80`; `psbt.rs:314`, `:350`, `:377` (`dest`); `:584` (`_dest`, unused). Private, the agent's own: `base64.rs:26`, `compactsize.rs:102`, `psbt.rs:813`, `:853` |
| Status enum vs Result/Option | 18 `-> PsbtResult` · 20 `-> Result<_, PsbtResult>` · 10 `-> Option<_>` · 2 `-> (u64, PsbtResult)` | The 13 public `-> PsbtResult` functions (12 in `psbt.rs`, plus `tx.rs:52`) are set by the interface. The other 5 are private: the converters `psbt.rs:633 to_result` and `tx.rs:172 out_of_bounds`, and the agent-chosen status returns `psbt.rs:813 psbt_hex_decode`, `:853 hex_encode` and `tx.rs:62 parse_btc_tx`. The sentinel `compactsize.rs:8 (u64::MAX, PsbtResult::CompactReadError)` comes from the interface tuple, and every caller checks `res` first (`psbt.rs:792`, `tx.rs:232`) |

The 13 `as` casts:
- Guarded and lossless: `compactsize.rs:86 _size as u8`, `:89 as u16`, `:92 as u32` (each sits inside its range branch); `base64.rs:74 i as u8` (i < 64).
- Widening, lossless on 64-bit: `psbt.rs:673`, `:788`, `tx.rs:228` (u32 to usize); `psbt.rs:700`, `:712` (usize to u64).
- Enum discriminant: `psbt.rs:239 PsbtGlobalType::UnsignedTx as u8`; `cli.rs:86 res as i32` (the C prints the numeric code).
- Possibly truncating: `tx.rs:99-100 i as i32` / `j as i32`. The interface's i32 fields force this, and the code sits in the dead branch.

### Ownership: good. The agent resolved the C's buffer aliasing
- `psbt.rs:585 // the C points the psbt at the caller's buffer; here the psbt owns its data`. `_dest` is ignored, and `psbt.rs:189-190 data.clear(); extend_from_slice(src)` copies the input into the struct.
- `tx.rs:157-161 struct Cursor<'a> { data: &'a [u8], ... }` borrows the input, and `advance` returns subslices with the input's lifetime (`:186`).
- `psbt.rs:242-261`: the parser closure captures `inputs`, `outputs` and `&mut *user_data`. No `Any` downcasting or raw pointers are used (H-L5).
- Weak spot: `cli.rs:45 .clone()` (see the table).

### Types: good where the agent had a choice
- `psbt.rs:73 #[derive(..., Clone, Copy)] pub enum PsbtState` adds `Copy` to the interface's derives, which resolves H-L9.
- `psbt.rs:877-906` adds `global_type`/`input_type`/`output_type -> Option<..>` to turn a byte into an enum, and `:437 .map_or("UNKNOWN_GLOBAL_TYPE", psbt_global_type_tostr)` uses them.
- `compactsize.rs:11-21` reads integers with `src.get(..2)?.try_into().ok().map(u16::from_le_bytes)` (H-L15).
- Set by the interface: `src: &[u8]` is paired with a redundant size argument (`psbt.rs:166 _src_size`, `:315 dest_size`, `:375 _psbt_len`). The agent clamps rather than trusting the size: `psbt.rs:321 &src.as_bytes()[.._src_size.min(src.len())]`.
- Agent's choice: underscore-prefixed parameters are used in function bodies (`base64.rs:79 _src.iter()`, `compactsize.rs:85 if _size < 253`, `psbt.rs:180 if _src_size > ...`, `:546 _psbt.state`). The names were kept from the stubs, and a leading underscore normally means "unused" (H-L4).

### Control flow: two styles. Iterator code in the codecs, the C state machine in `psbt_read`
- Good: `base64.rs:36-62 src.chunks_exact(3)` plus `match *blocks.remainder() { [b0] => ..., [b0, b1] => ... }`.
- Good: `psbt.rs:824 for (out, pair) in dest.iter_mut().zip(src.chunks_exact(2))`.
- C-shaped: `psbt.rs:200-293` is one `while ... { match psbt.state { ... } }` over 94 lines that reproduces the C switch, including the counters `kvs`/`inputs`/`outputs` (`:171-173`).
- C-shaped: `psbt.rs:651-653 byte_at` returns 0 past the end, so the loop runs on phantom zero bytes up to `write_pos <= _src_size` (`:200`) the way the C does. This is documented at `:648-650`.

### Error handling: a clean `Result` core with a status-code shell
- Good: the private core uses `Result` and `?`: `psbt.rs:698-716 psbt_write_record` chains five `?` calls, and `tx.rs:118-133 parse_txin` and `:186-238 Cursor` do the same.
- Boundary conversion: `psbt.rs:633-635 to_result` and `tx.rs:66 .err().unwrap_or(PsbtResult::Ok)`.
- Weak spot: `psbt_read` (`:164-308`) was not split into an inner `-> Result` function the way `parse_btc_tx` was. It has 7 `return res;` sites (`:204`, `:264`, `:509`, `:529`, `:551`, `:573`, `:623`), and 6 of them come from `if let Err(res) = ...` (the other, `:264`, is a status check). The `if let Err` sites also appear in other functions.
- Weak spot, a write-only global: `ERRMSG` is written at `psbt.rs:153-155` and never read. `psbt_geterr` returns the constant (`:416-418`), as the interface's prefilled body did (`interfaces/psbt.rs:165-167`), whereas the C returns the last message (`c/psbt.c:793-795`). The agent states this at `:147-148`. As a result, `cli.rs:87` always prints "psbt error". The interface wrote the body, but the agent chose to keep it and to keep the dead state.
- `psbt.rs:491 let _ = psbt_write_header(psbt);` ignores the error explicitly, matching the C, and says so at `:489-490`.

### Organisation: good module split, with duplicated cursor logic
- Good: `tx.rs:47-67` puts the fn-pointer public API over a private generic `parse_btc_tx<F: FnMut(PsbtTxElem)>`, which is the H-L5 design.
- Duplication: the cursor logic exists twice. `psbt.rs:638 assert_space` / `:783 read_size` duplicate `tx.rs:178 Cursor::assert_space` / `:227 Cursor::compactsize`. `psbt.rs` works on the interface's `pub write_pos` field (`psbt.rs:105`) through free functions that take `tx: &mut Psbt` (`:656-810`) rather than using `Cursor` or methods.
- `cli.rs:93 pub fn main() -> i32` follows D-CLIMAIN.

## Shape question

What the weak spots share is a public surface in the C's shape. The agent kept the C's structure at that boundary, and built a Rust-shaped private layer beneath it in many but not all places.

1. **The interface sets the C-shaped API.** Every out-parameter (satc 6, libpsbt 3 scalar and 8 buffer), every status-code return (libpsbt's 13 public `-> PsbtResult` functions, `satc.rs:486 -> i32`), the redundant length parameters (`psbt.rs:166`, `satc.rs:386`, `:415`, `:417`) and the redundant `num_points` field (`satc.rs:22`) appear verbatim in `interfaces/*.rs`. They are not the agent's fault.
2. **Where it had a choice, the agent mirrored the C's control flow.** Examples: the state machine in `psbt.rs:200-293`, the index loop in `satc.rs:550-611`, the free functions over `&mut Psbt` (`psbt.rs:656-810`), the internal call through the out-parameter API (`satc.rs:426-429`), and the status-returning private helpers (`psbt.rs:813`, `:853`). The same agent wrote iterator- and `Result`-based code elsewhere: `satc.rs:154-166`, `:210`, `base64.rs:36-62` and `tx.rs:118-238`. Faithful-translation pressure (H-S5 exact values, D-FAITHFUL) explains why it stayed close to the C. The idiomatic style was clearly available to it.
3. **Prefilled interface bodies were kept even when they changed behaviour.** `psbt_geterr` stayed constant (`psbt.rs:416-418`), which leaves `ERRMSG` write-only. The underscore parameter names were kept and then used in function bodies (`base64.rs:69-116`, `compactsize.rs:80-96`).
4. **What is absent.** Neither project has `unwrap`, `expect`, a panic macro, an assert, `unsafe`, or an index that can panic on input the C handles. Every UB site was given a documented, defined behaviour (`satc.rs:330-334`, `base64.rs:7-12`, `psbt.rs:648-653`, `compactsize.rs:25-27`).

## Hard-coding read

**None found.** Neither library contains test-vector values, length special cases, `cfg(test)` or environment checks. A grep for `cfg|env::|std::process|include_|TRANSACTION|PSBT_HEX|EMPTY_INPUTS|== *(889|1024|2048|4096)` over the library files matched only `cli.rs:99 std::env::args_os()`. That is the driver's argv read, which D-CLIMAIN calls for.

Read in full: all 634 lines of `satc.rs` and all of `base64.rs`, `compactsize.rs`, `cli.rs`, `psbt.rs` and `tx.rs`. The functions that consume test-visible inputs were checked one by one:
- **satc:** `satc_point_scale_xy`; `satc_polygon_create`/`SatcPolygon::new`/`satc_polygon_set_points`/`polygon_recalc`; `satc_polygon_get_centroid`; `satc_circle_create`; `satc_response_create`/`SatcResponse::new`; `satc_test_circle_circle`; `satc_test_polygon_circle`; `satc_voronoi_region`; `satc_box_create`; `satc_box_to_polygon`; `satc_test_polygon_polygon`; `satc_is_separating_axis`; `satc_flatten_points_on`; `satc_point_in_circle`; `satc_point_in_polygon`; `satc_point_normalize`/`perp`/`sub`/`add`/`reverse`/`scale_x`.
- **libpsbt:** `psbt_init`; `psbt_write_global_record`/`input`/`output`; `psbt_new_output_record_set`; `psbt_print`; `psbt_finalize`; `psbt_decode`; `psbt_hex_decode`; `hexdigit`; `base64_decode`; `psbt_read`; `psbt_read_header`; `psbt_read_record`; `read_size`; `compactsize_read`/`peek_length`/`length`/`write`; `parse_btc_tx`/`parse`/`parse_txin`/`parse_txout`; the `Cursor` methods; `psbt_encode`/`psbt_encode_raw`; `hex_encode`/`hexchar`; `write_bytes`/`write_compactsize`/`psbt_write_header`/`psbt_close_records`/`psbt_write_record`.

The only numeric literals in satc are the C's own (`satc.rs:512 0.000001`, `:307 2.0`, `:375 3.0`, `:598 2.0`). None of the test's expected values (20, 50, 33, 5.86, 4.14) appear in the library.

The defective test was not gamed. `psbt_read` invokes the handler for every record (`psbt.rs:269-275`) and for every transaction element (`:246-254`), with no suppression. That matches the ledger's M7 entry (`where.md:62`), where `read_test_vector` fails as documented (D8), with 3 of 4 tests passing.
