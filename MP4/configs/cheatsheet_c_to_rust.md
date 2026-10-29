Pattern-level guidance only. It does not describe any specific function.

| C construct | Safe Rust |
|---|---|
| `*(uint32_t *)cursor` and similar reinterpreting reads | `u32::from_le_bytes(buf[i..i + 4].try_into()?)` with checked slicing |
| byte cursor (`unsigned char *p` advanced through a buffer) | a `usize` index into a slice; `get(i..j)` returns `None` instead of reading out of bounds |
| `memcpy(dst, src, n)` | `dst[..n].copy_from_slice(&src[..n])` after checking both lengths |
| `void *user_data` passed to a callback | `&mut dyn Any` and `downcast_mut::<T>()`, or a generic closure inside a private helper |
| union with a tag field | an `enum` with data, as the interface already declares |
| global mutable state (`static char *errmsg`) | `thread_local!` with `Cell`/`RefCell`, or a `Mutex`; never `static mut` |
| `FILE *` output | `&mut dyn std::io::Write`, with `write!` errors mapped to the interface's error type |
| output parameter (`double *out`) | return the value, or `&mut` exactly as the interface declares |
| sentinel return codes | the interface's result enum, `Option` or `Result` |
| fixed-size array of points (`double p[2]`) | `[f64; 2]`, which is `Copy`, so pass by value or reference without `.clone()` |
| `for (i = 0; i < n; i++) a[i]` | `for x in &a` / `.iter().enumerate()` / `.zip()`, unless the index itself is needed |
| `x = x + y` | `x += y` |
| early `return v;` as the last statement | the tail expression `v` |
| declare-then-assign (`T x; ... x = ...;`) | `let x = ...;` at the point of assignment |
| `if (a) {...} else { if (b) {...} }` | `else if b {...}` |
| `v = vec![]; v.push(..); v.push(..)` | `vec![.., ..]` |
| redundant casts (`x as f64` on an `f64`) | drop the cast |
| `format!("{}", x)` | `format!("{x}")` (clippy's `uninlined_format_args` is in the style group) |
| `std::f64::MAX`, `std::u32::MAX` | `f64::MAX`, `u32::MAX` |
| `&Vec<T>` parameters you add yourself | `&[T]` |
| a `new()` with no arguments | also implement `Default` (clippy's `new_without_default`) |
