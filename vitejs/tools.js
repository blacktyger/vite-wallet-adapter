export const DEBUG = false
export const method = 'wss'

// --- Wrap function with timer and return either
// --- success function response before timout or null
export async function withTimeout(func, args = [], timeout = 2000) {
    const func_promise = new Promise((resolve, reject) => {
        resolve(func(args[0], args[1], args[2], args[3], args[4], args[5]))
    });

    const timeout_promise = new Promise((resolve, reject) => {
        setTimeout(resolve, timeout, "timeout");
    });

    const response = await Promise.any([func_promise, timeout_promise])

    if ('timeout' === response) {throw `TIMEOUT ERROR`}
    else {log("from wrapper: " + {response})}

    return response
}


// Manager for receiving VITE account blocks
export const ReceiveProcess = class {
    constructor() {
        this.status = 'working';
        this.error = 0
        this.msg = null;
        this.data = null;
        this.unreceived = 0
    }
}


// Print nested objects to stdout and exit process
export function  logAndExit(error, msg, data=null) {
    if (!DEBUG) {
        console.log(JSON.stringify(
            {error: error, msg: `${msg}`, data: data}, null, 2));
        process.exit(0);
    } else {
        console.log(msg)
    }
}

// ASYNC sleep function
export function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}


// console.log() only if DEBUG true
export function log(str) {if (DEBUG) {console.log(str);}}