import requests
from web3 import Web3
import os
import json
import time
from datetime import datetime
from functools import wraps
import eth_abi.packed

class Token:
    # ETH
    ETH_ADDRESS = Web3.to_checksum_address('0xae13d989dac2f0debff460ac112a837c89baa7cd')
    MAX_AMOUNT = int('0x' + 'f' * 64, 16)

    def __init__(self, address, router, wrap_addr, provider=None):
        
        print("address: " + address + ", provider: " + provider )
        self.address = Web3.to_checksum_address(address)
        self.provider = os.environ['PROVIDER'] if not provider else provider
        adapter = requests.adapters.HTTPAdapter(pool_connections=1000, pool_maxsize=1000)
        session = requests.Session()
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        self.web3 = Web3(Web3.HTTPProvider(self.provider, session=session))
        self.wallet_address = None

        # ETH
        ETH_ADDRESS = Web3.to_checksum_address(wrap_addr)

        self.router = self.web3.eth.contract(
            address=Web3.to_checksum_address(router),
            abi=json.load(open("pyuniswap/abi_files/" + "router3.abi")))
        self.erc20_abi = json.load(
            open("pyuniswap/abi_files/" + "erc20.abi"))

        self.wrap_abi = json.load(
            open("pyuniswap/abi_files/" + "wrap.abi"))

        self.gas_limit = 500000

    def get_symbol(self, address=None):
        address = self.wallet_address if not address else Web3.to_checksum_address(address)
        if not address:
            raise RuntimeError('Please provide the wallet address!')
        erc20_contract = self.web3.eth.contract(address=self.address, abi=self.erc20_abi)
        return erc20_contract.functions.symbol().call()

    def decimals(self, address=None):
        address = self.wallet_address if not address else Web3.to_checksum_address(address)
        if not address:
            raise RuntimeError('Please provide the wallet address!')
        erc20_contract = self.web3.eth.contract(address=self.address, abi=self.erc20_abi)
        return erc20_contract.functions.decimals().call()

    def set_gas_limit(self, gas_limit):
        self.gas_limit = int(gas_limit)

    def connect_wallet(self, wallet_address='', private_key=''):
        # print("connect wallet!")
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.private_key = private_key
        if not self.is_approved(self.ETH_ADDRESS):
            self.approve(self.ETH_ADDRESS, gas_price=self.web3.eth.gas_price, timeout=2100)
        # print("connect wallet end!")

    def is_connected(self):
        return False if not self.wallet_address else True

    def require_connected(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.is_connected():
                raise RuntimeError('Please connect the wallet first!')
            return func(self, *args, **kwargs)

        return wrapper

    def create_transaction_params(self, value=0, gas_price=None, gas_limit=None):
        if not self.is_connected():
            raise RuntimeError('Please connect the wallet first!')
        if not gas_price:
            gas_price = self.web3.eth.gas_price
        if not gas_limit:
            gas_limit = self.gas_limit
        return {
            "from": self.wallet_address,
            "value": value,
            'gasPrice': gas_price,
            "gas": gas_limit,
            "nonce": self.web3.eth.get_transaction_count(self.wallet_address)
        }

    def wrap_ether(self, amountIn):
        gas_price = self.web3.eth.gas_price
        weth_contract = self.web3.eth.contract(address=self.ETH_ADDRESS, abi=self.wrap_abi)
        func = weth_contract.functions.deposit()
        params = self.create_transaction_params(value=amountIn, gas_price=gas_price)
        tx = self.send_transaction(func, params)
        self.web3.eth.wait_for_transaction_receipt(tx, 900)
        weth_balance = weth_contract.functions.balanceOf(self.wallet_address).call()
        print(f"weth balance: {weth_balance / 10**18}")

    def unwrap_ether(self, amountIn):
        gas_price = self.web3.eth.gas_price
        weth_contract = self.web3.eth.contract(address=self.ETH_ADDRESS, abi=self.wrap_abi)
        weth_balance = weth_contract.functions.balanceOf(self.wallet_address).call()
        func = weth_contract.functions.withdraw(amountIn)
        params = self.create_transaction_params(gas_price=gas_price)
        tx = self.send_transaction(func, params)
        self.web3.eth.wait_for_transaction_receipt(tx, 900)
        weth_balance = weth_contract.functions.balanceOf(self.wallet_address).call()
        print(f"weth balance: {weth_balance / 10**18}")

    def send_transaction(self, func, params):
        tx = func.build_transaction(params)
        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
        # tx = tx_hash.hex()
        # self.web3.eth.wait_for_transaction_receipt(tx)
        return self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    def send_buy_transaction(self, signed_tx):
        return self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)

    @require_connected
    def is_approved(self, token_address=None, amount=MAX_AMOUNT):
        token_address = Web3.to_checksum_address(token_address) if token_address else self.address
        erc20_contract = self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
        approved_amount = erc20_contract.functions.allowance(self.wallet_address, self.router.address).call()
        # print(approved_amount)
        return approved_amount >= amount

    @require_connected
    def get_rest_allowance(self, token_address=None, amount=MAX_AMOUNT):
        token_address = Web3.to_checksum_address(token_address) if token_address else self.address
        erc20_contract = self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
        approved_amount = erc20_contract.functions.allowance(self.wallet_address, self.router.address).call()
        return amount - approved_amount

    @require_connected
    def approve(self, token_address, amount=MAX_AMOUNT, gas_price=None, timeout=900):
        if not gas_price:
            gas_price = self.web3.eth.gas_price
        token_address = Web3.to_checksum_address(token_address)
        erc20_contract = self.web3.eth.contract(address=token_address, abi=self.erc20_abi)
        func = erc20_contract.functions.approve(self.router.address, amount)
        params = self.create_transaction_params(gas_price=gas_price)
        tx = self.send_transaction(func, params)
        self.web3.eth.wait_for_transaction_receipt(tx, timeout=timeout)

    def price(self, amount=int(1e18), swap_token_address=ETH_ADDRESS):
        swap_token_address = Web3.to_checksum_address(swap_token_address)
        return self.router.functions.getAmountsOut(amount, [self.address, swap_token_address]).call()[-1]

    def received_amount_by_swap(self, input_token_amount=int(1e18), input_token_address=ETH_ADDRESS):
        input_token_address = Web3.to_checksum_address(input_token_address)
        return self.router.functions.getAmountsOut(input_token_amount, [input_token_address, self.address]).call()[-1]

    def balance(self, address=None):
        address = self.wallet_address if not address else Web3.to_checksum_address(address)
        if not address:
            raise RuntimeError('Please provide the wallet address!')
        erc20_contract = self.web3.eth.contract(address=self.address, abi=self.erc20_abi)
        return erc20_contract.functions.balanceOf(self.wallet_address).call()

    @require_connected
    def buyv3(self, consumed_token_amount, consumed_token_address=ETH_ADDRESS, pool_fee=500, gas_price=1, timeout=900, speed=1):
        if gas_price == 1:
            gas_price = int(self.web3.eth.gas_price * speed)
        else:
            gas_price = int(gas_price)
        
        min_out = 0
        if not self.is_approved(consumed_token_address, consumed_token_amount):
            self.approve(self.address, gas_price=gas_price, timeout=timeout)


        path = eth_abi.packed.encode_packed(['address','uint24','address'], [consumed_token_address, pool_fee, self.address])
        tx_params = (
            path, 
            self.wallet_address, 
            consumed_token_amount, # amount in
            0 #min amount out
        )
        func = self.router.functions.exactInput(tx_params)
        params = self.create_transaction_params(gas_price=gas_price)
        tx = func.build_transaction(params)
        return self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)
        # return self.send_transaction(signed_tx)

    @require_connected
    def buyv2(self, consumed_token_amount, consumed_token_address=ETH_ADDRESS, slippage=0.01, gas_price=1, timeout=900, speed=1):
        if gas_price == 1:
            gas_price = int(self.web3.eth.gas_price * speed)
        else:
            gas_price = int(gas_price)

        min_out = 0
        func = self.router.functions.swapExactTokensForTokens(consumed_token_amount, min_out,
                                                              [consumed_token_address, self.address],
                                                              self.wallet_address)
        params = self.create_transaction_params(gas_price=gas_price)
        tx = func.build_transaction(params)
        return self.web3.eth.account.sign_transaction(tx, private_key=self.private_key)

    @require_connected
    def sellv3(self, amount, received_token_address=ETH_ADDRESS, pool_fee=500,  gas_price=1, timeout=900, speed=1):
        if gas_price == 1:
            gas_price = int(self.web3.eth.gas_price * speed)
        else:
            gas_price = int(gas_price)
        min_out = 0
        if not self.is_approved(self.address, amount):
            self.approve(self.address, gas_price=gas_price, timeout=timeout)

        path = eth_abi.packed.encode_packed(['address','uint24','address'], [self.address, pool_fee, received_token_address])

        tx_params = (
            path, 
            self.wallet_address, 
            amount, # amount in
            0 #min amount out
        )
        func = self.router.functions.exactInput(tx_params)
        params = self.create_transaction_params(gas_price=gas_price)

        return self.send_transaction(func, params)

    @require_connected
    def sellv2(self, amount, received_token_address=ETH_ADDRESS, slippage=0.01,  gas_price=1, timeout=900, speed=1):
        if gas_price == 1:
            gas_price = int(self.web3.eth.gas_price * speed)
        else:
            gas_price = int(gas_price)
        # received_amount = self.price(amount, received_token_address)
        # min_out = int(received_amount * (1 - slippage))
        min_out = 0
        if not self.is_approved(self.address, amount):
            self.approve(self.address, gas_price=gas_price, timeout=timeout)

        func = self.router.functions.swapExactTokensForTokens(amount, min_out,
                                                                  [self.address, received_token_address],
                                                                  self.wallet_address)
        params = self.create_transaction_params(gas_price=gas_price)
        return self.send_transaction(func, params)