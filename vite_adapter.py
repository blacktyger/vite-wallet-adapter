import argparse

from src import ViteJsAdapter


# Manage script via CLI
if __name__ == '__main__':
    provider = ViteJsAdapter(debug=False)

    parser = argparse.ArgumentParser(
        description="Python wrapper for the @vite.js nodeJS library.",
        usage="%(prog)s [command] [args]"
        )

    command = parser.add_subparsers(dest='command')

    # Create command line arguments
    create = command.add_parser('create', help='Create new Vite wallet')

    # Get balance command line arguments
    balance = command.add_parser('balance', help='Get wallet balance')
    balance.add_argument("--address", "-a", help="wallet address", required=False)
    balance.add_argument("--mnemonics", "-m", help="wallet mnemonic seed phrase", required=False)
    balance.add_argument("--address_id", "-i", help="wallet address derivation path", required=False, default=0)

    # Get transactions command line arguments
    transactions = command.add_parser('transactions', help='Get wallet transactions')
    transactions.add_argument("--address", "-a", help="wallet address", required=True)
    transactions.add_argument("--page_index", "-i", help="page index, default is 0", required=False, default=0)
    transactions.add_argument("--page_size", "-s", help="page size, default is 20", required=False, default=20)

    # Send transaction command line arguments
    send = command.add_parser('send', help='Send transaction')
    send.add_argument("--to_address", "-a", help="receiver wallet address", required=True)
    send.add_argument("--address_id", "-i", help="wallet address derivation path", required=False, default=0)
    send.add_argument("--mnemonics", "-m", help="sender's wallet mnemonic seed phrase", required=True)
    send.add_argument("--amount", help="amount to send", required=True)
    send.add_argument("--token_id", "-t", help="vite token id", required=True)

    # Update wallet pending transactions command line arguments
    update = command.add_parser('update', help='Update wallet by receiving pending transactions')
    update.add_argument("--mnemonics", "-m", help="sender's wallet mnemonic seed phrase", required=True)
    update.add_argument("--address_id", "-i", help="wallet address derivation path", required=False, default=0)

    args = parser.parse_args()

    match args.command:
        case "create":
            wallet = provider.create_wallet()
            print(f"New wallet created successfully!\n {wallet['data']}")
        case "balance":
            if args.address:
                print(provider.get_balance(address=args.address))
            elif args.mnemonics:
                print(provider.get_balance(mnemonics=args.mnemonics, address_id=args.address_id if args.address_id else 0))
            else:
                print(f"'--address' or '--mnemonics' is required")
        case "transactions":
            print(provider.get_transactions(address=args.address, page_index=args.page_index, page_size=args.page_size))
        case "send":
            print(provider.send_transaction(
                to_address=args.to_address, mnemonics=args.mnemonics, address_id=args.address_id, token_id=args.token_id, amount=args.amount))
        case "update":
            print(provider.get_updates(mnemonics=args.mnemonics, address_id=args.address_id))
