//! Base64/base62 encoding and decoding, translated from base64.c
//! (originally RFC1341 base64 code by Jouni Malinen).

const BASE64_TABLE: [u8; 64] =
    *b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

/// The C base62 table is a 62 character string indexed with 6 bit values:
/// index 62 reads its terminating NUL, which is reproduced here, and index 63
/// reads past the array, which is undefined in C. That read is defined here as
/// a NUL byte as well.
const BASE62_TABLE: [u8; 64] =
    *b"0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz\0\0";

/// Encode the given source bytes into base62. Returns the number of written bytes on success.
pub fn base62_encode(_src: &[u8], _out: &mut [u8]) -> Option<usize> {
    base_encode(_src, _out, &BASE62_TABLE)
}

/// Encode the given source bytes into base64. Returns the number of written bytes on success.
pub fn base64_encode(_src: &[u8], _out: &mut [u8]) -> Option<usize> {
    base_encode(_src, _out, &BASE64_TABLE)
}

/// Translates base_encode(): the shared encoder of base64.c. The output is NUL
/// terminated and the terminator is not counted in the returned length.
fn base_encode(src: &[u8], out: &mut [u8], base_table: &[u8; 64]) -> Option<usize> {
    // 3-byte blocks to 4-byte, plus one byte for the nul termination. The
    // checked arithmetic takes the place of the C's integer overflow guard.
    let olen = src.len().checked_mul(4)? / 3 + 5;
    if olen > out.len() {
        return None; // buffer overflow
    }

    let encode = |val: u8| base_table[usize::from(val)];
    let mut pos = 0;
    let mut blocks = src.chunks_exact(3);
    for block in &mut blocks {
        let (b0, b1, b2) = (block[0], block[1], block[2]);
        let quad = [
            encode(b0 >> 2),
            encode(((b0 & 0x03) << 4) | (b1 >> 4)),
            encode(((b1 & 0x0f) << 2) | (b2 >> 6)),
            encode(b2 & 0x3f),
        ];
        out.get_mut(pos..pos + quad.len())?.copy_from_slice(&quad);
        pos += quad.len();
    }

    let tail = match *blocks.remainder() {
        [b0] => Some([encode(b0 >> 2), encode((b0 & 0x03) << 4), b'=', b'=']),
        [b0, b1] => Some([
            encode(b0 >> 2),
            encode(((b0 & 0x03) << 4) | (b1 >> 4)),
            encode((b1 & 0x0f) << 2),
            b'=',
        ]),
        _ => None, // the remainder of chunks_exact(3) is empty here
    };
    if let Some(tail) = tail {
        out.get_mut(pos..pos + tail.len())?.copy_from_slice(&tail);
        pos += tail.len();
    }

    *out.get_mut(pos)? = b'\0';
    Some(pos)
}

/// Decode the given base64-encoded source bytes. Returns the number of decoded bytes on success.
pub fn base64_decode(_src: &[u8], _out: &mut [u8]) -> Option<usize> {
    const INVALID: u8 = 0x80;

    let mut dtable = [INVALID; 256];
    for (i, &c) in BASE64_TABLE.iter().enumerate() {
        dtable[usize::from(c)] = i as u8;
    }
    dtable[usize::from(b'=')] = 0;

    let valid = |c: u8| dtable[usize::from(c)] != INVALID;
    let count = _src.iter().filter(|&&c| valid(c)).count();
    if count == 0 || count % 4 != 0 {
        return None;
    }

    let olen = count / 4 * 3;
    if _out.len() < olen {
        return None;
    }

    let mut block = [0u8; 4];
    let mut filled = 0;
    let mut pos = 0;
    let mut pad = 0;
    for &c in _src {
        let tmp = dtable[usize::from(c)];
        if tmp == INVALID {
            continue;
        }

        if c == b'=' {
            pad += 1;
        }
        block[filled] = tmp;
        filled += 1;
        if filled < block.len() {
            continue;
        }

        // The C asserts that every write stays strictly below out_capacity,
        // which aborts when the output exactly fills the buffer. The capacity
        // check above already guarantees the three bytes fit.
        let decoded = [
            (block[0] << 2) | (block[1] >> 4),
            (block[1] << 4) | (block[2] >> 2),
            (block[2] << 6) | block[3],
        ];
        _out.get_mut(pos..pos + decoded.len())?.copy_from_slice(&decoded);
        pos += decoded.len();
        filled = 0;

        match pad {
            0 => continue,
            1 => pos -= 1,
            2 => pos -= 2,
            _ => return None, // invalid padding
        }
        break;
    }

    Some(pos)
}
