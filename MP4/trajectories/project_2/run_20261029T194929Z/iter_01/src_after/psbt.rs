//! Partially signed bitcoin transactions, translated from psbt.c.

use crate::base64::{base62_encode, base64_decode, base64_encode};
use crate::compactsize::{
    compactsize_length, compactsize_peek_length, compactsize_read, compactsize_write,
};
use crate::tx::*;
use std::cell::Cell;
use std::fmt;

// Common constant from common.h
pub const MAX_SERIALIZE_SIZE: u32 = 0x02000000;

// --- Enum definitions ---

#[derive(Debug, PartialEq, Eq)]
pub enum PsbtResult {
    Ok,
    CompactReadError,
    ReadError,
    WriteError,
    InvalidState,
    NotImplemented,
    OobWrite,
}

impl fmt::Display for PsbtResult {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{self:?}")
    }
}

#[derive(Debug, PartialEq, Eq)]
pub enum PsbtGlobalType {
    UnsignedTx = 0,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PsbtEncoding {
    Hex,
    Base64,
    Base62,
    Protobuf,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PsbtInputType {
    NonWitnessUtxo = 0,
    WitnessUtxo = 1,
    PartialSig = 2,
    SighashType = 3,
    RedeemScript = 4,
    WitnessScript = 5,
    Bip32Derivation = 6,
    FinalScriptSig = 7,
    FinalScriptWitness = 8,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PsbtOutputType {
    RedeemScript = 0,
    WitnessScript = 1,
    Bip32Derivation = 2,
}

#[derive(Debug, PartialEq, Eq, Clone)]
pub enum PsbtScope {
    Global,
    Inputs,
    Outputs,
}

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum PsbtState {
    Init = 2,
    Global,
    Inputs,
    InputsNew,
    Outputs,
    OutputsNew,
    Finalized,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PsbtElemType {
    Record,
    TxElem,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PsbtTxElemType {
    TxIn,
    TxOut,
    Tx,
    WitnessItem,
}

// --- Struct definitions ---

/// Translates the C struct psbt.
/// (Here we use a Vec<u8> to hold the PSBT data and a write position index.)
pub struct Psbt {
    pub state: PsbtState,
    pub data: Vec<u8>,
    pub write_pos: usize,
    pub data_capacity: usize,
    // For simulation purposes we keep a list of records.
    pub records: Vec<PsbtRecord>,
}

impl Psbt {
    pub fn new(capacity: usize) -> Self {
        Self {
            state: PsbtState::Init,
            data: Vec::with_capacity(capacity),
            write_pos: 0,
            data_capacity: capacity,
            records: Vec::new(),
        }
    }
}

/// Translates the C struct psbt_record.
pub struct PsbtRecord {
    /// (The C field “type” is renamed to avoid conflict with the Rust keyword.)
    pub record_type: u8,
    pub key: Vec<u8>,
    pub val: Vec<u8>,
    pub scope: PsbtScope,
}

/// Translates the C union (record/txelem) in psbt_elem into an enum.
pub enum PsbtElem {
    Record { index: i32, record: PsbtRecord },
    TxElem { index: i32, txelem: PsbtTxElem },
}

/// The C typedef for a handler function.
pub type PsbtElemHandler = fn(elem: &mut PsbtElem, user_data: &mut dyn std::any::Any);

// External constants
pub const PSBT_MAGIC: [u8; 4] = [0x70, 0x73, 0x62, 0x74]; // "psbt"
pub static PSBT_ERRMSG: &str = "psbt error";

thread_local! {
    /// Translates the C global `psbt_errmsg`, which is assigned from all over
    /// the library. psbt_geterr() reports a constant, so this only mirrors the
    /// C writes.
    static ERRMSG: Cell<&'static str> = const { Cell::new(PSBT_ERRMSG) };
}

/// Records an error message the way the C assigns `psbt_errmsg`.
pub(crate) fn set_errmsg(msg: &'static str) {
    ERRMSG.set(msg);
}

/// Return the number of bytes stored in the PSBT.
pub fn psbt_size(tx: &Psbt) -> usize {
    tx.data.len()
}

/// Read a PSBT, reporting every record and every transaction element to the
/// given handler.
pub fn psbt_read(
    src: &[u8],
    _src_size: usize,
    psbt: &mut Psbt,
    elem_handler: Option<PsbtElemHandler>,
    user_data: &mut dyn std::any::Any,
) -> PsbtResult {
    let mut kvs = 0;
    let mut inputs = 0;
    let mut outputs = 0;

    if psbt.state != PsbtState::Init {
        set_errmsg("psbt_read: psbt not initialized, use psbt_init first");
        return PsbtResult::InvalidState;
    }

    if _src_size > psbt.data_capacity {
        set_errmsg("psbt_read: read buffer is larger than psbt capacity");
        return PsbtResult::OobWrite;
    }

    let Some(src) = src.get(.._src_size) else {
        set_errmsg("psbt_read: read buffer is smaller than src_size");
        return PsbtResult::ReadError;
    };
    psbt.data.clear();
    psbt.data.extend_from_slice(src);

    // parsing should try to get this to the finalized state,
    // otherwise it's an invalid psbt
    psbt.state = PsbtState::Init;
    psbt.write_pos = 0;

    // XXX: needed so that the asserts work properly. this is probably fine...
    psbt.data_capacity = _src_size;

    while psbt.state != PsbtState::Finalized && psbt.write_pos <= _src_size {
        match psbt.state {
            PsbtState::Init => {
                if let Err(res) = psbt_read_header(psbt) {
                    return res;
                }
            }

            PsbtState::Global | PsbtState::Inputs | PsbtState::Outputs => {
                if byte_at(psbt, psbt.write_pos) == 0 {
                    psbt.state = match psbt.state {
                        PsbtState::Inputs => {
                            kvs += 1;
                            if kvs >= inputs {
                                kvs = 0;
                                PsbtState::OutputsNew
                            } else {
                                PsbtState::InputsNew
                            }
                        }
                        PsbtState::Outputs => {
                            kvs += 1;
                            if kvs >= outputs {
                                PsbtState::Finalized
                            } else {
                                PsbtState::OutputsNew
                            }
                        }
                        // the global state; the C asserts nothing else arrives
                        // here at a null byte
                        _ => PsbtState::InputsNew,
                    };
                } else {
                    let rec = match psbt_read_record(psbt, _src_size) {
                        Ok(rec) => rec,
                        Err(res) => return res,
                    };

                    if psbt.state == PsbtState::Global
                        && rec.record_type == PsbtGlobalType::UnsignedTx as u8
                    {
                        // parse transaction for number of inputs/outputs
                        let res = parse_btc_tx(&rec.val, rec.val.len(), |elem| {
                            let elem_type = txelem_type(&elem);

                            // forward txelem events to user
                            if let Some(handler) = elem_handler {
                                // the C leaves the element index uninitialized
                                // for transaction elements
                                let mut elem = PsbtElem::TxElem {
                                    index: 0,
                                    txelem: elem,
                                };
                                handler(&mut elem, &mut *user_data);
                            }

                            match elem_type {
                                PsbtTxElemType::TxIn => inputs += 1,
                                PsbtTxElemType::TxOut => outputs += 1,
                                _ => {}
                            }
                        });

                        if res != PsbtResult::Ok {
                            return res;
                        }
                    }

                    // record callback
                    if let Some(handler) = elem_handler {
                        let mut elem = PsbtElem::Record {
                            index: kvs,
                            record: rec,
                        };
                        handler(&mut elem, &mut *user_data);
                    }
                }
            }

            PsbtState::OutputsNew => {
                // the C asserts that the byte consumed here is a null byte
                psbt.write_pos += 1;
                psbt.state = PsbtState::Outputs;
            }

            PsbtState::InputsNew => {
                psbt.write_pos += 1;
                psbt.state = PsbtState::Inputs;
            }

            // unreachable: the loop stops in the finalized state
            PsbtState::Finalized => break,
        }
    }

    if psbt.state != PsbtState::Finalized {
        set_errmsg("psbt_read: invalid psbt");
        return PsbtResult::InvalidState;
    } else if byte_at(psbt, psbt.write_pos) != 0 {
        set_errmsg("psbt_read: expected null byte at end of psbt");
        return PsbtResult::ReadError;
    }

    psbt.write_pos += 1;
    // psbt_size() is the distance between the data and the write position
    psbt.data.truncate(psbt.write_pos);

    PsbtResult::Ok
}

/// Decode a hex or base64 encoded PSBT into dest.
pub fn psbt_decode(
    src: &str,
    _src_size: usize,
    dest: &mut [u8],
    dest_size: usize,
    psbt_len: &mut usize,
) -> PsbtResult {
    const B64_MAGIC: &[u8] = b"cHNid";

    // the C reads src_size bytes of a bare char pointer
    let src = &src.as_bytes()[.._src_size.min(src.len())];
    let capacity = dest_size.min(dest.len());
    let dest = &mut dest[..capacity];

    // simple sanity check before we look for base64 encoding
    if src.len() < B64_MAGIC.len() {
        set_errmsg("psbt_decode: psbt too small");
        return PsbtResult::ReadError;
    }

    // base64 detection
    if src.starts_with(B64_MAGIC) {
        return match base64_decode(src, dest) {
            Some(size) => {
                *psbt_len = size;
                PsbtResult::Ok
            }
            None => PsbtResult::ReadError,
        };
    }

    *psbt_len = src.len() / 2;
    psbt_hex_decode(src, dest)
}

/// Encode the PSBT data into a destination buffer using the requested encoding.
pub fn psbt_encode(
    psbt: &Psbt,
    encoding: PsbtEncoding,
    dest: &mut [u8],
    dest_size: usize,
    out_len: &mut usize,
) -> PsbtResult {
    if psbt.state != PsbtState::Finalized {
        set_errmsg(
            "psbt_encode: psbt not in finalized state. use psbt_read to parse \
             an existing psbt, or the psbt_write functions to create one.",
        );
        return PsbtResult::WriteError;
    }

    psbt_encode_raw(
        &psbt.data,
        psbt_size(psbt),
        encoding,
        dest,
        dest_size,
        out_len,
    )
}

/// Encode raw PSBT data into dest using the requested encoding.
pub fn psbt_encode_raw(
    psbt_data: &[u8],
    _psbt_len: usize,
    encoding: PsbtEncoding,
    dest: &mut [u8],
    dest_size: usize,
    out_len: &mut usize,
) -> PsbtResult {
    let psbt_data = &psbt_data[.._psbt_len.min(psbt_data.len())];
    let capacity = dest_size.min(dest.len());
    let dest = &mut dest[..capacity];

    match encoding {
        PsbtEncoding::Hex => {
            let res = hex_encode(psbt_data, dest);
            *out_len = psbt_data.len() * 2 + 1;
            res
        }
        PsbtEncoding::Base64 => match base64_encode(psbt_data, dest) {
            Some(len) => {
                *out_len = len;
                PsbtResult::Ok
            }
            None => {
                set_errmsg("psbt_encode: base64 encode failure");
                PsbtResult::WriteError
            }
        },
        PsbtEncoding::Base62 => match base62_encode(psbt_data, dest) {
            Some(len) => {
                *out_len = len;
                PsbtResult::Ok
            }
            None => {
                set_errmsg("psbt_encode: base62 encode failure");
                PsbtResult::WriteError
            }
        },
        PsbtEncoding::Protobuf => PsbtResult::NotImplemented,
    }
}

/// Return the last error message.
pub fn psbt_geterr() -> &'static str {
    PSBT_ERRMSG
}

/// Convert a PSBT state to a human–readable string.
pub fn psbt_state_tostr(state: PsbtState) -> &'static str {
    match state {
        PsbtState::Init => "INIT",
        PsbtState::Global => "GLOBAL",
        PsbtState::Inputs => "INPUTS",
        PsbtState::InputsNew => "INPUTS_NEW",
        PsbtState::Outputs => "OUTPUTS",
        PsbtState::OutputsNew => "OUTPUTS_NEW",
        PsbtState::Finalized => "FINALIZED",
    }
}

/// Return a string for a record type and scope.
pub fn psbt_type_tostr(record_type: u8, scope: PsbtScope) -> &'static str {
    match scope {
        PsbtScope::Global => {
            global_type(record_type).map_or("UNKNOWN_GLOBAL_TYPE", psbt_global_type_tostr)
        }
        PsbtScope::Inputs => {
            input_type(record_type).map_or("UNKNOWN_INPUT_TYPE", psbt_input_type_tostr)
        }
        PsbtScope::Outputs => {
            output_type(record_type).map_or("UNKNOWN_OUTPUT_TYPE", psbt_output_type_tostr)
        }
    }
}

/// Return a string for a psbt_txelem type.
pub fn psbt_txelem_type_tostr(txelem_type: PsbtTxElemType) -> &'static str {
    match txelem_type {
        PsbtTxElemType::Tx => "TX",
        PsbtTxElemType::TxIn => "TXIN",
        PsbtTxElemType::TxOut => "TXOUT",
        PsbtTxElemType::WitnessItem => "WITNESS_ITEM",
    }
}

pub fn psbt_global_type_tostr(gt: PsbtGlobalType) -> &'static str {
    match gt {
        PsbtGlobalType::UnsignedTx => "GLOBAL_UNSIGNED_TX",
    }
}

pub fn psbt_output_type_tostr(ot: PsbtOutputType) -> &'static str {
    match ot {
        PsbtOutputType::RedeemScript => "OUT_REDEEM_SCRIPT",
        PsbtOutputType::WitnessScript => "OUT_WITNESS_SCRIPT",
        PsbtOutputType::Bip32Derivation => "OUT_BIP32_DERIVATION",
    }
}

pub fn psbt_input_type_tostr(it: PsbtInputType) -> &'static str {
    match it {
        PsbtInputType::NonWitnessUtxo => "IN_NON_WITNESS_UTXO",
        PsbtInputType::WitnessUtxo => "IN_WITNESS_UTXO",
        PsbtInputType::PartialSig => "IN_PARTIAL_SIG",
        PsbtInputType::SighashType => "IN_SIGHASH_TYPE",
        PsbtInputType::RedeemScript => "IN_REDEEM_SCRIPT",
        PsbtInputType::WitnessScript => "IN_WITNESS_SCRIPT",
        PsbtInputType::Bip32Derivation => "IN_BIP32_DERIVATION",
        PsbtInputType::FinalScriptSig => "IN_FINAL_SCRIPTSIG",
        PsbtInputType::FinalScriptWitness => "IN_FINAL_SCRIPTWITNESS",
    }
}

/// Write a global record into the PSBT.
pub fn psbt_write_global_record(psbt: &mut Psbt, rec: &PsbtRecord) -> PsbtResult {
    if psbt.state == PsbtState::Init {
        // write header if we haven't yet. the C ignores the result here: a
        // failed header write is reported by the record write below
        let _ = psbt_write_header(psbt);
        psbt.state = PsbtState::Global;
    } else if psbt.state != PsbtState::Global {
        set_errmsg(
            "psbt_write_global_record: you can only write a global record \
             after psbt_init and before psbt_write_input_record",
        );
        return PsbtResult::InvalidState;
    }

    to_result(psbt_write_record(psbt, rec))
}

/// Write an input record into the PSBT.
pub fn psbt_write_input_record(psbt: &mut Psbt, rec: &PsbtRecord) -> PsbtResult {
    if psbt.state == PsbtState::Global {
        // close global records
        if let Err(res) = psbt_close_records(psbt) {
            return res;
        }
        psbt.state = PsbtState::Inputs;
    } else if psbt.state != PsbtState::Inputs && psbt.state != PsbtState::InputsNew {
        set_errmsg(
            "psbt_write_input_record: attempting to write an input record \
             before any global records have been written. use \
             psbt_write_global_record first",
        );
        return PsbtResult::InvalidState;
    }

    to_result(psbt_write_record(psbt, rec))
}

/// Write an output record into the PSBT.
pub fn psbt_write_output_record(psbt: &mut Psbt, rec: &PsbtRecord) -> PsbtResult {
    if psbt.state == PsbtState::Inputs {
        // close input records
        if let Err(res) = psbt_close_records(psbt) {
            return res;
        }
        psbt.state = PsbtState::Outputs;
    } else if psbt.state != PsbtState::Outputs && psbt.state != PsbtState::OutputsNew {
        set_errmsg(
            "psbt_write_input_record: attempting to write an input record \
             before any global records have been written. use \
             psbt_write_global_record first",
        );
        return PsbtResult::InvalidState;
    }

    to_result(psbt_write_record(psbt, rec))
}

/// Create a new input record set.
pub fn psbt_new_input_record_set(_psbt: &mut Psbt) -> PsbtResult {
    if _psbt.state == PsbtState::Global
        || _psbt.state == PsbtState::InputsNew
        || _psbt.state == PsbtState::Inputs
    {
        if let Err(res) = psbt_close_records(_psbt) {
            return res;
        }
        _psbt.state = PsbtState::InputsNew;
        return PsbtResult::Ok;
    }

    set_errmsg(
        "psbt_new_input_record_set: this can only be called after \
         psbt_write_global_record, psbt_new_input_record_set, or \
         psbt_write_input_record",
    );
    PsbtResult::InvalidState
}

/// Create a new output record set.
pub fn psbt_new_output_record_set(psbt: &mut Psbt) -> PsbtResult {
    if psbt.state == PsbtState::Inputs
        || psbt.state == PsbtState::InputsNew
        || psbt.state == PsbtState::OutputsNew
        || psbt.state == PsbtState::Outputs
    {
        if let Err(res) = psbt_close_records(psbt) {
            return res;
        }
        psbt.state = PsbtState::OutputsNew;
        return PsbtResult::Ok;
    }

    set_errmsg("psbt_new_output_record_set: this can only be called after writing input records");
    PsbtResult::InvalidState
}

/// Initialize a PSBT using the given destination buffer.
pub fn psbt_init(psbt: &mut Psbt, _dest: &mut [u8], dest_size: usize) -> PsbtResult {
    // the C points the psbt at the caller's buffer; here the psbt owns its data
    psbt.data.clear();
    psbt.records.clear();
    psbt.write_pos = 0;
    psbt.data_capacity = dest_size;
    psbt.state = PsbtState::Init;

    PsbtResult::Ok
}

/// Print the PSBT (only succeeds after finalization).
pub fn psbt_print(psbt: &Psbt, stream: &mut dyn std::io::Write) -> PsbtResult {
    if psbt.state != PsbtState::Finalized {
        set_errmsg("psbt_print: transaction is not finished");
        return PsbtResult::InvalidState;
    }

    let size = psbt_size(psbt);
    for &byte in psbt.data.iter().take(size) {
        if write!(stream, "{byte:02x}").is_err() {
            set_errmsg("psbt_print: write failure");
            return PsbtResult::WriteError;
        }
    }
    // the C prints the trailing newline on stdout, not on the stream
    println!();

    PsbtResult::Ok
}

/// Finalize the PSBT.
pub fn psbt_finalize(psbt: &mut Psbt) -> PsbtResult {
    if psbt.state != PsbtState::OutputsNew && psbt.state != PsbtState::Outputs {
        set_errmsg("psbt_finalize: no output records found");
        return PsbtResult::InvalidState;
    }

    if let Err(res) = psbt_close_records(psbt) {
        return res;
    }

    psbt.state = PsbtState::Finalized;

    PsbtResult::Ok
}

/// Translates the sentinel-free error handling of the C: an `Ok` result is
/// PSBT_OK.
fn to_result(res: Result<(), PsbtResult>) -> PsbtResult {
    res.err().unwrap_or(PsbtResult::Ok)
}

/// Translates the ASSERT_SPACE macro of psbt.c.
fn assert_space(tx: &Psbt, size: usize) -> Result<(), PsbtResult> {
    match tx.write_pos.checked_add(size) {
        Some(end) if end <= tx.data_capacity => Ok(()),
        _ => {
            set_errmsg("write out of bounds psbt.c");
            Err(PsbtResult::OobWrite)
        }
    }
}

/// Reads the byte under the cursor. The C dereferences the cursor without a
/// space check in a few places; the destination buffers the callers hand over
/// are zero filled past the psbt, so a read past the data yields zero.
fn byte_at(tx: &Psbt, pos: usize) -> u8 {
    tx.data.get(pos).copied().unwrap_or(0)
}

/// Writes `bytes` through the cursor, as the C memcpy's to the write position.
fn write_bytes(tx: &mut Psbt, bytes: &[u8]) -> Result<(), PsbtResult> {
    assert_space(tx, bytes.len())?;

    let end = tx.write_pos + bytes.len();
    if tx.data.len() < end {
        tx.data.resize(end, 0);
    }
    tx.data[tx.write_pos..end].copy_from_slice(bytes);
    tx.write_pos = end;

    Ok(())
}

/// Writes a compact size field through the cursor. The bytes
/// compactsize_write() leaves untouched stay zero, like they do in the zero
/// filled buffers the C is given.
fn write_compactsize(tx: &mut Psbt, size: u64) -> Result<(), PsbtResult> {
    let field_len = compactsize_length(size) as usize;
    assert_space(tx, field_len)?;

    let end = tx.write_pos + field_len;
    if tx.data.len() < end {
        tx.data.resize(end, 0);
    }
    compactsize_write(&mut tx.data[tx.write_pos..end], size);
    tx.write_pos = end;

    Ok(())
}

fn psbt_write_header(tx: &mut Psbt) -> Result<(), PsbtResult> {
    write_bytes(tx, &PSBT_MAGIC)?;
    write_bytes(tx, &[0xff])?;
    tx.state = PsbtState::Global;

    Ok(())
}

fn psbt_close_records(tx: &mut Psbt) -> Result<(), PsbtResult> {
    write_bytes(tx, b"\0")
}

fn psbt_write_record(tx: &mut Psbt, rec: &PsbtRecord) -> Result<(), PsbtResult> {
    // don't forget the type byte in the key size
    let key_size_with_type = rec.key.len() as u64 + 1;

    // write key length
    write_compactsize(tx, key_size_with_type)?;

    // write type
    write_bytes(tx, &[rec.record_type])?;

    // write key
    write_bytes(tx, &rec.key)?;

    // write value length
    write_compactsize(tx, rec.val.len() as u64)?;

    // write value
    write_bytes(tx, &rec.val)
}

fn psbt_read_header(tx: &mut Psbt) -> Result<(), PsbtResult> {
    assert_space(tx, 4)?;

    if tx.data.get(tx.write_pos..tx.write_pos + PSBT_MAGIC.len()) != Some(&PSBT_MAGIC[..]) {
        set_errmsg("psbt_read: invalid magic header");
        return Err(PsbtResult::ReadError);
    }

    tx.write_pos += 4;

    let magic_end = byte_at(tx, tx.write_pos);
    tx.write_pos += 1;
    if magic_end != 0xff {
        set_errmsg("psbt_read: no 0xff found after magic");
        return Err(PsbtResult::ReadError);
    }

    tx.state = PsbtState::Global;

    Ok(())
}

fn psbt_read_record(tx: &mut Psbt, src_size: usize) -> Result<PsbtRecord, PsbtResult> {
    let size = read_size(tx, src_size, "psbt_read: record key size too large")?;

    // the key size includes the type byte, which is not part of the key
    let key_start = tx.write_pos + 1;
    let record_type = byte_at(tx, tx.write_pos);
    let key = tx
        .data
        .get(key_start..tx.write_pos + size)
        .unwrap_or_default()
        .to_vec();

    tx.write_pos += size;

    let scope = match tx.state {
        PsbtState::Global => PsbtScope::Global,
        PsbtState::Inputs => PsbtScope::Inputs,
        PsbtState::Outputs => PsbtScope::Outputs,
        _ => {
            set_errmsg("psbt_read_record: invalid record state");
            return Err(PsbtResult::InvalidState);
        }
    };

    let size = read_size(tx, src_size, "psbt_read: record value size too large")?;
    let val = tx
        .data
        .get(tx.write_pos..tx.write_pos + size)
        .unwrap_or_default()
        .to_vec();

    tx.write_pos += size;

    Ok(PsbtRecord {
        record_type,
        key,
        val,
        scope,
    })
}

/// Reads a record key or value length: the compact size under the cursor,
/// checked against the end of the psbt and against the write space.
fn read_size(
    tx: &mut Psbt,
    src_size: usize,
    too_large: &'static str,
) -> Result<usize, PsbtResult> {
    let size_len = compactsize_peek_length(byte_at(tx, tx.write_pos)) as usize;
    assert_space(tx, size_len)?;

    let (size, res) = compactsize_read(tx.data.get(tx.write_pos..).unwrap_or_default());
    if res != PsbtResult::Ok {
        return Err(res);
    }
    tx.write_pos += size_len;

    let fits = usize::try_from(size).ok().filter(|&size| {
        tx.write_pos
            .checked_add(size)
            .is_some_and(|end| end <= src_size)
    });
    let Some(size) = fits else {
        set_errmsg(too_large);
        return Err(PsbtResult::ReadError);
    };

    assert_space(tx, size)?;

    Ok(size)
}

/// Translates the psbt_hex_decode() of psbt.c.
fn psbt_hex_decode(src: &[u8], dest: &mut [u8]) -> PsbtResult {
    if src.len() % 2 != 0 {
        set_errmsg("psbt_decode: invalid hex string");
        return PsbtResult::ReadError;
    }

    if dest.len() < src.len() / 2 {
        set_errmsg("psbt_decode: dest_size must be at least half the size of src_size");
        return PsbtResult::ReadError;
    }

    for (out, pair) in dest.iter_mut().zip(src.chunks_exact(2)) {
        let [c1, c2] = [pair[0], pair[1]];
        if !c1.is_ascii_hexdigit() || !c2.is_ascii_hexdigit() {
            set_errmsg("psbt_decode: invalid hex string");
            return PsbtResult::ReadError;
        }

        *out = hexdigit(c1) << 4 | hexdigit(c2);
    }

    PsbtResult::Ok
}

/// Translates hexdigit(). Only ever called on validated hex digits; the
/// wrapping arithmetic keeps anything else well defined.
fn hexdigit(hex: u8) -> u8 {
    if hex <= b'9' {
        hex.wrapping_sub(b'0')
    } else {
        hex.to_ascii_uppercase().wrapping_sub(b'A').wrapping_add(10)
    }
}

/// Translates hexchar(). The C asserts that `val` is a nibble.
fn hexchar(val: u8) -> u8 {
    b"0123456789abcdef"[usize::from(val & 0x0f)]
}

/// Translates hex_encode(): lowercase hex with a nul terminator.
fn hex_encode(buf: &[u8], dest: &mut [u8]) -> PsbtResult {
    if dest.len() < buf.len() * 2 + 1 {
        return PsbtResult::OobWrite;
    }

    for (out, &byte) in dest.chunks_exact_mut(2).zip(buf) {
        out.copy_from_slice(&[hexchar(byte >> 4), hexchar(byte & 0xf)]);
    }
    if let Some(end) = dest.get_mut(buf.len() * 2) {
        *end = b'\0';
    }

    PsbtResult::Ok
}

fn txelem_type(elem: &PsbtTxElem) -> PsbtTxElemType {
    match elem {
        PsbtTxElem::TxIn(_) => PsbtTxElemType::TxIn,
        PsbtTxElem::TxOut(_) => PsbtTxElemType::TxOut,
        PsbtTxElem::Tx(_) => PsbtTxElemType::Tx,
        PsbtTxElem::WitnessItem(_) => PsbtTxElemType::WitnessItem,
    }
}

fn global_type(record_type: u8) -> Option<PsbtGlobalType> {
    match record_type {
        0 => Some(PsbtGlobalType::UnsignedTx),
        _ => None,
    }
}

fn input_type(record_type: u8) -> Option<PsbtInputType> {
    Some(match record_type {
        0 => PsbtInputType::NonWitnessUtxo,
        1 => PsbtInputType::WitnessUtxo,
        2 => PsbtInputType::PartialSig,
        3 => PsbtInputType::SighashType,
        4 => PsbtInputType::RedeemScript,
        5 => PsbtInputType::WitnessScript,
        6 => PsbtInputType::Bip32Derivation,
        7 => PsbtInputType::FinalScriptSig,
        8 => PsbtInputType::FinalScriptWitness,
        _ => return None,
    })
}

fn output_type(record_type: u8) -> Option<PsbtOutputType> {
    Some(match record_type {
        0 => PsbtOutputType::RedeemScript,
        1 => PsbtOutputType::WitnessScript,
        2 => PsbtOutputType::Bip32Derivation,
        _ => return None,
    })
}
