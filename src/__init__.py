"""
This package is essentially a python wrapper for the @vite.js NODE.JS library
In current implementation only basic functionality is available.
https://github.com/blacktyger/vite-wallet-adapter

Requirements:
- Node.js and npm
- Python 3.11

@vite.js GitHub and documentation:
- https://github.com/vitelabs/vite.js
- https://docs.vite.org/vite-docs/vite.js/

Author: blacktyg3r.com | BTLabs.tech
"""
import subprocess
import threading
import time
import os

from .logger_ import get_logger


DEFAULT_LOGGER = get_logger()
SCRIPT_PATH = os.path.join(os.getcwd(), "vitejs/api_handler.js")


class ViteJsAdapter:
    """
    Execute @vitejs functions via python class. Possible operations:
    - Create new VITE wallet | create_wallet()
    - Get wallet transactions | transactions()
    - Receive pending transactions | update()
    - Get wallet balance | get_balance()

    Possible statuses: running, finished, failed
    """

    def __init__(self, logger: object = None, nodejs_logs: bool = True, debug: bool = True, try_counter: int = 3, script_path: str = None):
        """
        :param nodejs_logs: bool, forward logs from nodejs script
        :param debug: bool,  display debug logs
        :param try_counter: int, how many try before failing
        """
        self.listener_is_running: bool = False
        self.listener_thread: threading.Thread | None = None
        self.nodejs_logs = nodejs_logs
        self.try_counter = try_counter
        self.response: dict = dict()
        self.last_log: str = ''
        self.logger = logger if logger else DEFAULT_LOGGER
        self.status = 'running'
        self.script = script_path if script_path else SCRIPT_PATH
        self.debug = debug

    def _run_command(self, command: list) -> dict:
        """
        Run NodeJS scripts with subprocess.Popen(), parse stdout
        and return dictionary with script payload.
        :param command: Full NodeJS command as list
        :return: dict
        """
        logs_list = list()

        # Run the command as subprocess and read output
        process = subprocess.Popen(command, stdout=subprocess.PIPE, text=True)

        # While process is running collect and filter logs
        while True:
            output = process.stdout.readline()

            if output == '' and process.poll() is not None:
                # Process finished
                break

            if output.strip().startswith('>>'):
                # Filter logs from NodeJS to self.logger
                line = output.strip().replace('>>', 'node.js >>')

                if self.nodejs_logs and self.last_log != line:
                    self.logger.info(line)

                self.last_log = line

            elif output and not output.startswith((' >>', '>>')):
                # Append parts of dictionary for return
                logs_list.append(output)

        # If process finished
        if not process.poll():
            try:
                # Serialize stdout output and return dict
                logs_list = [line.replace('null', 'None') for line in logs_list]
                logs_list = [line.replace('true', 'True') for line in logs_list]
                logs_list = [line.replace('false', 'False') for line in logs_list]
                logs_json = ''.join([line.replace('\n', '') for line in logs_list])
                logs_dict = eval(logs_json)
                return logs_dict

            except Exception as e:
                return {'error': 1, 'msg': e, 'data': None}

    def _balance(self, address: str = None, mnemonics: str = None, address_id: int | str = None, **kwargs) -> dict:
        if address_id is None:
            address_id = 0

        if address:
            command = ['node', self.script, 'balance', '-a', address]
            return self._run_command(command)

        if mnemonics:
            address_id = str(address_id)
            command = ['node', self.script, 'balance', '-a', '0', '-m', mnemonics, '-i', address_id]
            return self._run_command(command)

    def _get_last_tx_id(self, address: str = None, mnemonics: str = None, **kwargs) -> int:
        balance = self._balance(address, mnemonics)

        if not balance['error']:
            try:
                return balance['data']['balance']['blockCount']
            except Exception as e:
                self.logger.warning(f"_get_last_tx_id() error: {e}")
        return 0

    def _update_status(self) -> None:
        fail_msg = "too many fail attempts"

        if self.try_counter < 1:
            self.response = {'error': 1, 'msg': fail_msg, 'data': None}
            self.status = 'failed'
        elif self.response['error']:
            self.status = 'failed'
            if self.debug:
                self.logger.error(f"{self.status} |  {self.response['msg']}")
        else:
            self.status = 'finished'

    def create_wallet(self):
        """
        Create new VITE wallet
        :return: dict with raw mnemonic string and wallet address
        """
        command = ['node', self.script, 'create']
        self.response = self._run_command(command)

        return self.response

    def get_balance(self, address: str = None, mnemonics: str = None, address_id: int | str = None, **kwargs) -> dict:
        """
        Get wallet balance from the VITE network, to get the balance mnemonics AND/OR address is required.
        :param address: str, wallet address
        :param mnemonics:, str, wallet mnemonic seed phrase
        :param address_id: int | str, wallet address derivation path, default 0
        """
        self.response = self._balance(address, mnemonics, address_id)

        while self.response['error'] and self.try_counter:
            self.try_counter -= 1

            if 'timeout' in self.response['msg'].lower():
                self.logger.warning(f"{self.response['msg']} re-try balance ({self.try_counter} left)")
                self._balance(address, mnemonics, address_id)
            else:
                return self.response

        self._update_status()

        return self.response

    def get_transactions(self, address: str, page_index: int | str = 0, page_size: int | str = 20, **kwargs) -> dict:
        """
        Get wallet transactions from the VITE network
        :param address: str, wallet address
        :param page_index: str | int, default 0
        :param page_size: str | int, default 20
        """
        page_index = str(page_index)
        page_size = str(page_size)

        command = ['node', self.script, 'transactions', '-a', address, '-i', page_index, '-s', page_size]

        self.response = self._run_command(command)

        while self.response['error'] and self.try_counter:
            self.try_counter -= 1

            if 'timeout' in self.response['msg'].lower():
                self.logger.warning(f"{self.response['msg']} re-try {command[2]} ({self.try_counter} left)")
                self._run_command(command)
            else:
                return self.response

        self._update_status()

        return self.response

    def send_transaction(self, to_address: str, mnemonics: str, token_id: str, amount: str | float, address_id: int | str = 0, **kwargs) -> dict:
        """
        Send transaction on the VITE blockchain
        :param to_address: str, wallet address
        :param address_id; int, wallet address derivation path, default 0
        :param mnemonics:, str, wallet mnemonic seed phrase
        :param token_id: str, unique token id to send
        :param amount: int | str, amount of the token to send
        """
        # Get sender's last transaction ID, later will be used to confirm that transaction was sent successfully.
        last_tx_id = self._get_last_tx_id(mnemonics)

        address_id = str(address_id)
        amount = str(amount)
        command = ['node', self.script, 'send', '-m', mnemonics, '-i', address_id, '-d', to_address, '-t', token_id, '-a', amount]

        self.response = self._run_command(command)

        while self.response['error'] and self.try_counter:
            if 'timeout' in self.response['msg'].lower():
                self.try_counter -= 1
                time.sleep(1)
                current_tx_id = self._get_last_tx_id(mnemonics)

                while not current_tx_id:
                    self.logger.warning(f"problem with getting balance, re-try...")
                    current_tx_id = self._get_last_tx_id(mnemonics)

                if current_tx_id == last_tx_id:
                    self.logger.warning(f"{self.response['msg']}, re-try send ({self.try_counter} left)..")
                    time.sleep(1)
                    self.response = self._run_command(command)
                else:
                    if self.debug:
                        self.logger.info(f"New TX last ID [{current_tx_id}], finishing process..")
                    break
            else:
                break

        self._update_status()

        return self.response

    def get_updates(self, mnemonics: str, address_id: str | int = 0, **kwargs) -> dict:
        """
        Update wallet balance by receiving pending transactions
        :param mnemonics:, str, wallet mnemonic seed phrase
        :param address_id; int, wallet address derivation path, default 0
        """
        address_id = str(address_id)
        command = ['node', self.script, 'update', '-m', mnemonics, '-i', address_id]

        self.response = self._run_command(command)

        while self.response['error'] and self.try_counter:
            self.try_counter -= 1

            if 'timeout' in self.response['msg'].lower():
                self.logger.info(f"{self.response['msg']}, re-try {command[2]} ({self.try_counter} left)")
                self._run_command(command)
            elif 'no pending' in self.response['msg'].lower():
                self.response = {'error': 0, 'msg': "No pending transactions", 'data': None}
                break
            else:
                break

        self._update_status()

        return self.response

    def _transaction_listener(self, *args) -> None:
        wallets, tokens, interval, callback = args
        first_run = True

        while self.listener_is_running:
            if not first_run:
                time.sleep(interval)

            first_run = False

            for i, wallet in enumerate(wallets):
                if self.debug:
                    wallet_ = wallet.get('address', i)
                    self.logger.debug(f"Processing wallet({wallet_})..")

                balance_ = self.get_balance(**wallet)

                if balance_['error']:
                    if self.debug:
                        self.logger.warning(f'error: {balance_["msg"]}')
                    continue

                pending = int(balance_['data']['unreceived']['blockCount'])
                self.logger.info(f"tx_listener: {pending} new transactions")

                if not pending:
                    continue

                update_ = self.get_updates(**wallet)

                if update_['error']:
                    if self.debug:
                        self.logger.warning(f'error: {update_["msg"]}')
                    continue

                transactions_ = self.get_transactions(address=wallet['address'], page_size=pending + 1)

                if transactions_['error']:
                    if self.debug:
                        self.logger.warning(f'error: {transactions_["msg"]}')
                    continue

                transactions = list()

                for transaction in transactions_['data']:
                    # Get only 'received' transactions (blockType == 4)
                    if transaction['blockType'] != 4:
                        continue

                    # Filter transactions by token symbols
                    if '__all__' in tokens:
                        transactions.append(transaction)
                    else:
                        for token in tokens:
                            if token.lower() in transaction['tokenInfo']['tokenSymbol'].lower():
                                transactions.append(transaction)
                if callback:
                    callback(transactions)

    def run_transaction_listener(self, tokens: list[str], wallets: list[dict[str, str, str | int]] = None,
                                 interval: int = 10, callback=None):
        """
        Run background thread that will monitor given Vite wallets, update (receive)
        the new transactions and return them to the callback functions.
        :param tokens: list of str, if tokens = ['__all__'] it will check for all of them
        :param wallets: list of dictionaries {address: str, mnemonics: str, address_id(optional): str | int}
        :param interval: int, refresh time interval in seconds
        :param callback: callback function to return list of new received transactions
        """
        args = (wallets, tokens, interval, callback)
        self.listener_thread = threading.Thread(target=self._transaction_listener, args=args)
        self.listener_is_running = True
        self.listener_thread.daemon = True
        self.listener_thread.start()
        if self.debug:
            self.logger.debug(f"Transaction listener started")

    def stop_transaction_listener(self):
        """Stop the running transaction listener thread"""
        if self.listener_is_running:
            if self.debug:
                self.logger.debug(f"Stopping transaction listener..")
            self.listener_is_running = False
            self.listener_thread = None
