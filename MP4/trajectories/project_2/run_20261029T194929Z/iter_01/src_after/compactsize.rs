//! Bitcoin compact size serialisation, translated from compactsize.c.

use crate::psbt::{set_errmsg, PsbtResult, MAX_SERIALIZE_SIZE};

/// Translates the READERR macro: the C reader reports the error and returns -1.
fn read_error(msg: &'static str) -> (u64, PsbtResult) {
    set_errmsg(msg);
    (u64::MAX, PsbtResult::CompactReadError)
}

fn deserialize_u16(src: &[u8]) -> Option<u16> {
    src.get(..2)?.try_into().ok().map(u16::from_le_bytes)
}

fn deserialize_u32(src: &[u8]) -> Option<u32> {
    src.get(..4)?.try_into().ok().map(u32::from_le_bytes)
}

fn deserialize_u64(src: &[u8]) -> Option<u64> {
    src.get(..8)?.try_into().ok().map(u64::from_le_bytes)
}

pub fn compactsize_read(_data: &[u8]) -> (u64, PsbtResult) {
    const NON_CANONICAL: &str = "non-canonical compactsize_read()";
    // The C reads through a bare pointer; a truncated field is reported as a
    // read error instead.
    const TRUNCATED: &str = "truncated compactsize_read()";

    let Some((&chsize, rest)) = _data.split_first() else {
        return read_error(TRUNCATED);
    };

    let ret_size = if chsize < 253 {
        u64::from(chsize)
    } else if chsize == 253 {
        let Some(size) = deserialize_u16(rest) else {
            return read_error(TRUNCATED);
        };
        if size < 253 {
            return read_error(NON_CANONICAL);
        }
        u64::from(size)
    } else if chsize == 254 {
        let Some(size) = deserialize_u32(rest) else {
            return read_error(TRUNCATED);
        };
        if size < 0x10000 {
            return read_error(NON_CANONICAL);
        }
        u64::from(size)
    } else {
        let Some(size) = deserialize_u64(rest) else {
            return read_error(TRUNCATED);
        };
        if size < 0x1_0000_0000 {
            return read_error(NON_CANONICAL);
        }
        size
    };

    if ret_size > u64::from(MAX_SERIALIZE_SIZE) {
        return read_error(NON_CANONICAL);
    }

    (ret_size, PsbtResult::Ok)
}

pub fn compactsize_length(_data: u64) -> u32 {
    if _data < 253 {
        1
    } else if _data <= u64::from(u16::MAX) {
        1 + 2
    } else if _data <= u64::from(u32::MAX) {
        1 + 4
    } else {
        1 + 8
    }
}

pub fn compactsize_write(_dest: &mut [u8], _size: u64) {
    // The C writer serialises the 0xFD/0xFE/0xFF marker and then serialises the
    // little-endian size at the very same offset, so for sizes of 253 and above
    // the marker is overwritten and the last byte of the field is left
    // untouched. Reproduced exactly.
    if _size < 253 {
        serialize(_dest, &[_size as u8]);
    } else if _size <= u64::from(u16::MAX) {
        serialize(_dest, &[253]);
        serialize(_dest, &(_size as u16).to_le_bytes());
    } else if _size <= u64::from(u32::MAX) {
        serialize(_dest, &[254]);
        serialize(_dest, &(_size as u32).to_le_bytes());
    } else {
        serialize(_dest, &[255]);
        serialize(_dest, &_size.to_le_bytes());
    }
}

/// Translates the serialize_uN() helpers, which memcpy to the start of `dest`.
/// A destination that is too small is left alone; every caller in the C checks
/// for space first.
fn serialize(dest: &mut [u8], bytes: &[u8]) {
    if let Some(dest) = dest.get_mut(..bytes.len()) {
        dest.copy_from_slice(bytes);
    }
}

pub fn compactsize_peek_length(_chsize: u8) -> u32 {
    if _chsize < 253 {
        1
    } else if _chsize == 253 {
        1 + 2
    } else if _chsize == 254 {
        1 + 4
    } else {
        1 + 8
    }
}
