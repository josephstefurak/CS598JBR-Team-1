//! The command line driver, translated from cli.c.

use crate::psbt::*;
use crate::tx::{PsbtTxElem, PsbtTxIn, PsbtTxOut};
use std::any::Any;

fn hex_print(data: &[u8]) {
    for byte in data {
        print!("{byte:02x}");
    }
}

fn txid_print(data: &[u8]) {
    for byte in data.iter().rev() {
        print!("{byte:02x}");
    }
}

fn print_txin(txin: &PsbtTxIn) {
    txid_print(&txin.txid);
    print!(" ind:{}", txin.index);
    print!(" seq:{}", txin.sequence_number);
    if !txin.script.is_empty() {
        print!(" ");
        hex_print(&txin.script);
    }
    println!();
}

fn print_txout(txout: &PsbtTxOut) {
    if !txout.script.is_empty() {
        hex_print(&txout.script);
        print!(" ");
    }
    println!("amount:{}", txout.amount);
}

fn print_type(txelem_type: PsbtTxElemType) {
    print!("{}\t", psbt_txelem_type_tostr(txelem_type));
}

fn print_rec(elem: &mut PsbtElem, _user_data: &mut dyn Any) {
    match elem {
        PsbtElem::Record { index, record } => {
            let type_str = psbt_type_tostr(record.record_type, record.scope.clone());
            print!("{type_str}\t{index} ");
            if !record.key.is_empty() {
                hex_print(&record.key);
                print!(" ");
            }
            hex_print(&record.val);
            println!();
        }
        PsbtElem::TxElem { txelem, .. } => match txelem {
            PsbtTxElem::TxIn(txin) => {
                print_type(PsbtTxElemType::TxIn);
                print_txin(txin);
            }
            PsbtTxElem::TxOut(txout) => {
                print_type(PsbtTxElemType::TxOut);
                print_txout(txout);
            }
            PsbtTxElem::Tx(tx) => {
                print_type(PsbtTxElemType::Tx);
                println!("ver:{} locktime:{}", tx.version, tx.lock_time);
            }
            // the C driver prints the type of a witness item and nothing else
            PsbtTxElem::WitnessItem(_) => print_type(PsbtTxElemType::WitnessItem),
        },
    }
}

fn usage() -> i32 {
    println!("usage: psbt <psbt>");
    1
}

/// Reports a failed library call the way the CHECK macro of cli.c does.
fn check(res: PsbtResult, state: PsbtState) -> bool {
    if res == PsbtResult::Ok {
        return true;
    }

    println!(
        "error ({}): {}. last_state = {}",
        res as i32,
        psbt_geterr(),
        psbt_state_tostr(state)
    );
    false
}

pub fn main() -> i32 {
    let mut buffer = vec![0u8; 4096];
    let mut psbt = Psbt::new(4096);

    let Some(psbt_hex) = std::env::args().nth(1) else {
        return usage();
    };

    psbt_init(&mut psbt, &mut buffer, 4096);

    let mut psbt_len = 0;
    let res = psbt_decode(&psbt_hex, psbt_hex.len(), &mut buffer, 4096, &mut psbt_len);
    if !check(res, psbt.state) {
        return 1;
    }

    // the C driver passes no user data to its handler
    let res = psbt_read(&buffer, psbt_len, &mut psbt, Some(print_rec), &mut ());
    if !check(res, psbt.state) {
        return 1;
    }

    let mut out_len = 0;
    let res = psbt_encode(&psbt, PsbtEncoding::Base62, &mut buffer, 4096, &mut out_len);
    if !check(res, psbt.state) {
        return 1;
    }

    0
}
