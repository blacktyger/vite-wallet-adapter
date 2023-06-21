import {
    getBalance,
    createWallet,
    sendTransaction,
    getTransactions,
    receiveTransactions,
} from './vite-wallet-api.js';

import {
    logAndExit,
    DEBUG,
    sleep,
    ReceiveProcess
} from './tools.js'

import _yargs from 'yargs';
import { hideBin } from 'yargs/helpers';


/*
NODEJS FILE WITH VITE BLOCKCHAIN API CALLS

HOW TO USE:
Execute in your script/app with arguments:
node <this_file_path> <command> <arg1> <arg2> etc...

COMMANDS & ARGS:
- create             no args
- balance           -a <address> |or| -m <mnemonics> -i <address_derivation_id>
- transactions      -a <address> -i <page_index> -s <page_size>
- update            -m <mnemonics> -i <address_derivation_id>
- send              -m <mnemonics> -i <address_derivation_id>
                    -d <destination_address> -t <tokenId> -a <amount>

*/


// Extract commands and args from console stdin
const yargs = _yargs(hideBin(process.argv));
const args = yargs.argv


// Recognize command and run proper function withs args
switch (args._[0]) {
    case 'create':
        create()
        break

    case 'balance':
        balance(args.a, args.m, args.i)
        break

    case 'update':
        receive(args.m, args.i);
        break

    case 'transactions':
        transactions(args.a, args.n);
        break

    case 'send':
        send(args.m, args.i, args.d, args.t, args.a);
        break

    default:
        logAndExit(1, 'invalid command')
}


/*  #########################
    ### COMMAND FUNCTIONS ###
    #########################   */

// Create new Vite wallet
export async function create() {
    try {
        if (DEBUG) {
            return createWallet();
        } else {
            let wallet = createWallet()
            logAndExit(0, 'create success', wallet)
        }
    } catch (error) {logAndExit(1, error)}
}


// Get balance for vite_address from network
export async function balance(address, mnemonics, address_id) {
    try {
        if (DEBUG) {
            return getBalance(address, mnemonics, address_id);
        } else {
            let balance = await getBalance(address, mnemonics, address_id, 800)
            logAndExit(0, 'balance success', balance)
        }
    } catch (error) {logAndExit(1, error)}
}


// Get transactions list for vite_address from network
export async function transactions(address, pageIndex=0, pageSize=10) {
    try {
        if (DEBUG) {
            return getTransactions(address, pageIndex, pageSize);
        } else {
            await getTransactions(address, pageIndex, pageSize).
                then((transactions) => {logAndExit(0, 'txs success', transactions)}).
                catch((error) => {logAndExit(1, error.message)})
        }
    } catch (error) {logAndExit(1, error.message)}
}


// Send transaction to VITE network
export async function send(mnemonics, address_id, toAddress, tokenId, amount, timeout=5000) {
    if (DEBUG) {
        return sendTransaction(mnemonics, address_id, toAddress, tokenId, amount.toString(), timeout)
    } else {
        await sendTransaction(mnemonics, address_id,
            toAddress, tokenId, amount.toString(), timeout).then((result) => {
            console.log(">> sending " + (parseInt(amount) / 10 ** 8) + " completed")
            logAndExit(0, 'transaction success', result)
        }).catch(error => {logAndExit(1, error)})
    }
}


// Update wallet balance by receiving pending transactions
export async function receive(mnemonics, address_id) {
    // Initialize receiving manager to provide callback flags
    const manager = new ReceiveProcess()

    try {
        if (DEBUG) {
            return receiveTransactions(mnemonics, address_id)
        } else {
            await receiveTransactions(mnemonics, address_id, manager, 1000)

            // Keep process alive until receiving is finished or error appears
            while (manager.status !== 'success') {
                console.log(">> " + manager.msg)
                await sleep(1000)
            }
            logAndExit(manager.error, manager.msg, manager.data)
        }
    } catch (error) {logAndExit(1, error)}
}
