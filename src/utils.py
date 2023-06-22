class Token:
    """Token object"""
    def __init__(self, token_id: str, symbol: str):
        self.token_id = token_id
        self.symbol = symbol

    def __str__(self) -> str:
        return f"Token({self.symbol})"


class Wallet:
    """Wallet object"""
    def __init__(self, mnemonics: str, address: str):
        self.mnemonics = mnemonics
        self.address = address
        self.balance: list[Token] = list()

    def __str__(self) -> str:
        return f"Wallet({self.address}"
