import http_pkg from "@vite/vitejs-http";
import vitejs_pkg from '@vite/vitejs';
import ws from "@vite/vitejs-ws";

const { WS_RPC } = ws;
const { HTTP_RPC } = http_pkg;
const { ViteAPI } = vitejs_pkg;


export function connect(method, timeout=5000) {
    let service

    if (method === 'http') {
        service = new HTTP_RPC("https://node.vite.net/gvite/", timeout);
    } else {
        service = new WS_RPC("wss://node-vite.thomiz.dev/ws", timeout);
    }

    let provider = new ViteAPI(service, () => {
        if (method !== 'http') {
            if (!provider.isConnected) {
                log(`Connected to VITE NODE: ${provider.isConnected}`)
            }
        }
    });

    if (method === 'http') {
        if (!provider.isConnected) {
            log(`Connected to VITE NODE: ${provider.isConnected}`)
        }
    }
    return provider
}
