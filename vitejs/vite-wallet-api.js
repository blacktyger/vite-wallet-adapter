import vitejs_pkg from '@vite/vitejs';
import {connect} from './provider.js'
import {log, method, withTimeout} from './tools.js'

const { utils, accountBlock, wallet } = vitejs_pkg;
const { ReceiveAccountBlockTask } = accountBlock;

export {
    createWallet, getTransactions,
    receiveTransactions, sendTransaction,
    getBalance
}

// --- CREATE WALLET ---\\
// :return: wallet instance object
function createWallet() {
    const newWallet = wallet.createWallet()
    const {address} = newWallet.deriveAddress(0)
    return {'mnemonics': newWallet.mnemonics, 'address': address}
}


// --- GET ADDRESS BALANCE --- \\
// :return: Wallet balance and unreceived blocks
async function getBalance(address, mnemonics, address_id=0, timeout=1000) {
    const provider = connect(method, timeout)
    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }

    // If address provided return its balance
    if (address) {
        // console.log(">> getting balance for " + address)
        return provider.getBalanceInfo(address)
    }

    // If mnemonics provided, get Wallet from network and use its address
    else if (mnemonics) {
        let wallet_ = wallet.getWallet(mnemonics).deriveAddress(address_id)
        // console.log(">> getting balance for " + wallet_.address)
        return provider.getBalanceInfo(wallet_.address)
    }
}


// --- GET TRANSACTION LIST --- \\
// :return: transactions array
async function getTransactions(address, pageIndex, pageSize) {
    const provider = connect(method)

    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }
    console.log(">> " + address, pageIndex, pageSize)
    return provider.getTransactionList({address: address, pageIndex: pageIndex, pageSize: pageSize})
}


// --- UPDATE BALANCE / RECEIVE TRANSACTIONS --- \\
// :return: None
async function receiveTransactions(mnemonics, address_id, callback={}, timeout) {
    let unreceivedBlocks = []
    let successBlocks = []
    let errorBlocks = []

    // Set provider (VITE node handler)
    const provider = connect(method, timeout)

    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }

    // Get wallet instance form mnemonics
    const wallet_ = wallet.getWallet(mnemonics);
    const {privateKey, address} = wallet_.deriveAddress(address_id);

    // Create new ReceiveTask
    const ReceiveTask = new ReceiveAccountBlockTask({
        address: address,
        privateKey: privateKey,
        provider: provider,
    });

    // Check for unreceived transactions for account
    callback.msg = 'checking balance..'
    log(`Checking balance for ${address}`)
    const {balance, unreceived} = await withTimeout(getBalance, [address], 2000)

    if (balance) {  // means if addressBalance call was success
        // Parse number of unreceivedTransactions to int
        callback.unreceived = parseInt(unreceived.blockCount)

        // Initialize ReceiveTransaction subscription task if needed
        if (callback.unreceived) {
            log(`Start Receiving ${callback.unreceived} Transactions`)
            callback.msg = 'start receiving task..'
            ReceiveTask.start({
                checkTime: 2545,
                transctionNumber: callback.unreceived
            });
        } else {
            callback.msg = `no pending transactions`
            callback.error = 1
            callback.status = "success"
            throw Error("No pending transactions")
        }

        // Handle success callback
        ReceiveTask.onSuccess((result) => {
            log({success: successBlocks.length, error: errorBlocks.length})

            if (result.message.includes("Don't have")) {
                // Handle last unreceived transaction and finish task
                let data = {unreceived: callback.unreceived, success: successBlocks, error: errorBlocks}
                callback.msg = callback.unreceived + " blocks received success"
                callback.data = data
                callback.status = 'success'
                ReceiveTask.stop();
                log(data)

            } else {
                // Update callback status and keep receiving
                // callback.msg = "working on transaction " + (unreceivedBlocks.length + 1)
                //     + "/" + callback.unreceived + '..'
                callback.msg = `>> ${unreceivedBlocks.length + 1} / ${callback.unreceived} ${result.message}`
                unreceivedBlocks.push(result.message)
                successBlocks.push(result.message)
            }
        });

        // Handle error responses
        ReceiveTask.onError((error) => {
            try {
                errorBlocks.push(error.error.error.message)
            } catch (e) {
                errorBlocks.push(error.error.message)
            }
        });

    } else {
        // Handle custom timeout case
        callback.msg = `connection timeout`
        callback.error = 1
        callback.status = "failed"
        throw Error("Connection timeout")
    }
}


// --- SEND TRANSACTION --- \\
// :return: error or transaction data in JSON
async function sendTransaction(mnemonics, address_id, toAddress, tokenId, amount, timeout=2000) {
    // Connect to provider (VITE node handler)
    const provider = connect(method, timeout)
    console.log(">> sending " + (parseInt(amount) / 10**8 )+ " to: " + toAddress)

    // Handle error with VITE node
    if (!provider) { throw "ERROR Connection to VITE NODE" }

    // 1. Import wallet from mnemonic/seedphrase
    const myWallet = wallet.getWallet(mnemonics);
    const { privateKey, address } = myWallet.deriveAddress(address_id);

    //2. Create accountBlock instance
    const {createAccountBlock} = accountBlock;
    const sendBlock = createAccountBlock('send', {
        address: address,
        toAddress: toAddress,
        tokenId: tokenId,
        amount: amount
    })

    // 3. Set provider and private sendBlockKey
    sendBlock.setProvider(provider).setPrivateKey(privateKey);

    // 4. Autofill height and previousHash
    await sendBlock.autoSetPreviousAccountBlock().catch(e => {throw e.message});

    // 5. Get difficulty for PoW Puzzle (when not enough quota)
    const {difficulty} = await provider.request('ledger_getPoWDifficulty', {
        address: sendBlock.address,
        previousHash: sendBlock.previousHash,
        blockType: sendBlock.blockType,
        toAddress: sendBlock.toAddress,
        data: sendBlock.data
    }).catch(e => {throw e.error.message});

    // If difficulty is null, it indicates the account has enough quota to
    // send the transaction. There is no need to do PoW.
    if (difficulty) {
        // Call GVite-RPC API to calculate nonce from difficulty
        const getNonceHashBuffer = Buffer.from(sendBlock.originalAddress + sendBlock.previousHash, 'hex');
        const getNonceHash = utils.blake2bHex(getNonceHashBuffer, null, 32);
        const nonce = await provider.request('util_getPoWNonce', difficulty, getNonceHash
        ).catch(e => {throw e.error.message})

        sendBlock.setDifficulty(difficulty);
        sendBlock.setNonce(nonce);
    }

    // 6. Sign and send the AccountBlock
    return sendBlock.sign().send()
        .then((result) => {return result})
        .catch(e => {throw e.error.message});
}
