//! Bitcoin transaction parsing, translated from tx.c.

use crate::compactsize::{compactsize_peek_length, compactsize_read};
use crate::psbt::{set_errmsg, PsbtResult};

/// Translates the C struct psbt_txin.
pub struct PsbtTxIn {
    pub txid: Vec<u8>,
    pub index: u32,
    pub script: Vec<u8>,
    pub sequence_number: u32,
}

/// Translates the C struct psbt_txout.
pub struct PsbtTxOut {
    pub amount: u64,
    pub script: Vec<u8>,
}

/// Translates the C struct psbt_witness_item.
pub struct PsbtWitnessItem {
    pub input_index: i32,
    pub item_index: i32,
    pub item: Vec<u8>,
}

/// Translates the C struct psbt_tx.
pub struct PsbtTx {
    pub version: u32,
    pub lock_time: u32,
}

/// Translates the C union inside psbt_txelem.
pub enum PsbtTxElem {
    TxIn(PsbtTxIn),
    TxOut(PsbtTxOut),
    Tx(PsbtTx),
    WitnessItem(PsbtWitnessItem),
}

/// The handler type for psbt_txelem.
pub type PsbtTxElemHandler = fn(elem: &mut PsbtTxElem, user_data: &mut dyn std::any::Any);

const SEGREGATED_WITNESS_FLAG: u8 = 0x1;

/// Parse a Bitcoin transaction.
pub fn psbt_btc_tx_parse(
    _tx: &[u8],
    _tx_size: usize,
    _user_data: &mut dyn std::any::Any,
    _handler: Option<PsbtTxElemHandler>,
) -> PsbtResult {
    parse_btc_tx(_tx, _tx_size, |mut elem| {
        if let Some(handler) = _handler {
            handler(&mut elem, &mut *_user_data);
        }
    })
}

/// The parser behind psbt_btc_tx_parse(), taking a closure so that callers in
/// this crate can keep state the `fn` pointer API cannot carry.
pub(crate) fn parse_btc_tx<F>(data: &[u8], data_size: usize, handler: F) -> PsbtResult
where
    F: FnMut(PsbtTxElem),
{
    parse(data, data_size, handler).err().unwrap_or(PsbtResult::Ok)
}

fn parse<F>(data: &[u8], data_size: usize, mut handler: F) -> Result<(), PsbtResult>
where
    F: FnMut(PsbtTxElem),
{
    let mut cursor = Cursor::new(data, data_size);

    let version = cursor.le32()?;

    let count = cursor.compactsize()?;
    let inputs = count;

    // parse inputs
    for _ in 0..count {
        handler(PsbtTxElem::TxIn(parse_txin(&mut cursor)?));
    }

    let count = cursor.compactsize()?;

    // parse outputs
    for _ in 0..count {
        handler(PsbtTxElem::TxOut(parse_txout(&mut cursor)?));
    }

    // The flag is never set by the C parser, so the witness branch is dead.
    let flag: u8 = 0;
    if flag & SEGREGATED_WITNESS_FLAG != 0 {
        for i in 0..inputs {
            let count = cursor.compactsize()?;
            for j in 0..count {
                let mut item = parse_witness_item(&mut cursor)?;
                item.input_index = i as i32;
                item.item_index = j as i32;
                handler(PsbtTxElem::WitnessItem(item));
            }
        }
    }

    let lock_time = cursor.le32()?;

    if cursor.pos != data_size {
        set_errmsg("psbt_btc_tx_parse: parsing fell short");
        return Err(PsbtResult::ReadError);
    }

    handler(PsbtTxElem::Tx(PsbtTx { version, lock_time }));

    Ok(())
}

fn parse_txin(cursor: &mut Cursor) -> Result<PsbtTxIn, PsbtResult> {
    let txid = cursor.take(32)?.to_vec();
    let index = cursor.le32()?;
    let script_len = cursor.compactsize()?;
    // tx.c skips the script without checking for space; an overlong script is
    // caught by the sequence number read below.
    let script = cursor.advance(script_len)?.to_vec();
    let sequence_number = cursor.le32()?;

    Ok(PsbtTxIn {
        txid,
        index,
        script,
        sequence_number,
    })
}

fn parse_txout(cursor: &mut Cursor) -> Result<PsbtTxOut, PsbtResult> {
    let amount = cursor.le64()?;
    let script_len = cursor.compactsize()?;
    let script = cursor.take(script_len)?.to_vec();

    Ok(PsbtTxOut { amount, script })
}

fn parse_witness_item(cursor: &mut Cursor) -> Result<PsbtWitnessItem, PsbtResult> {
    let item_len = cursor.compactsize()?;
    let item = cursor.advance(item_len)?.to_vec();

    // The indices are filled in by the caller, as in tx.c.
    Ok(PsbtWitnessItem {
        input_index: 0,
        item_index: 0,
        item,
    })
}

/// Translates the C byte cursor: an index into `data` bounded by the
/// transaction size, with the space checks of tx.c's ASSERT_SPACE macro.
struct Cursor<'a> {
    data: &'a [u8],
    size: usize,
    pos: usize,
}

impl<'a> Cursor<'a> {
    fn new(data: &'a [u8], size: usize) -> Self {
        Self {
            data,
            size,
            pos: 0,
        }
    }

    fn out_of_bounds() -> PsbtResult {
        set_errmsg("out of bounds tx.c");
        PsbtResult::ReadError
    }

    /// Translates ASSERT_SPACE(space).
    fn assert_space(&self, space: usize) -> Result<(), PsbtResult> {
        match self.pos.checked_add(space) {
            Some(end) if end <= self.size => Ok(()),
            _ => Err(Self::out_of_bounds()),
        }
    }

    /// Translates `p += len`, returning the bytes that were skipped.
    fn advance(&mut self, len: usize) -> Result<&'a [u8], PsbtResult> {
        let end = self.pos.checked_add(len).ok_or_else(Self::out_of_bounds)?;
        let bytes = self
            .data
            .get(self.pos..end)
            .ok_or_else(Self::out_of_bounds)?;
        self.pos = end;
        Ok(bytes)
    }

    fn take(&mut self, len: usize) -> Result<&'a [u8], PsbtResult> {
        self.assert_space(len)?;
        self.advance(len)
    }

    fn peek(&self) -> Result<u8, PsbtResult> {
        self.assert_space(1)?;
        self.data
            .get(self.pos)
            .copied()
            .ok_or_else(Self::out_of_bounds)
    }

    fn le32(&mut self) -> Result<u32, PsbtResult> {
        let bytes = self.take(4)?;
        bytes
            .try_into()
            .map(u32::from_le_bytes)
            .map_err(|_| Self::out_of_bounds())
    }

    fn le64(&mut self) -> Result<u64, PsbtResult> {
        let bytes = self.take(8)?;
        bytes
            .try_into()
            .map(u64::from_le_bytes)
            .map_err(|_| Self::out_of_bounds())
    }

    /// Translates the peek_length/ASSERT_SPACE/compactsize_read sequence every
    /// length field in tx.c goes through.
    fn compactsize(&mut self) -> Result<usize, PsbtResult> {
        let size_len = compactsize_peek_length(self.peek()?) as usize;
        self.assert_space(size_len)?;

        let (size, res) = compactsize_read(self.data.get(self.pos..).unwrap_or_default());
        if res != PsbtResult::Ok {
            return Err(res);
        }
        self.pos += size_len;

        usize::try_from(size).map_err(|_| Self::out_of_bounds())
    }
}
