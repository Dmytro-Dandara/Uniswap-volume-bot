import argparse
import time
import json
import random
from web3 import Web3
from datetime import datetime
import threading
import os
import cli_ui

from pyuniswap.pyuniswap3 import Token
# print("module import end!")

f = open('config.json')
data = json.load(f)
provider_http = data["provider_http"]
router_address = data["router_address"]
new_token_address = data["new_token_address"]
pool_fee = int(data["pool_fee"])

trade_gas_price = int(data["trade_gas_price"] * pow(10, 9))
trade_gas_limit = int(data["trade_gas_limit"])


trade_wallet_address = []
for trade_wallet_addr in data["trade_wallet_address"]:
    trade_wallet_address.append(trade_wallet_addr)

trade_private_keys = []
for trade_private_key in data["trade_private_keys"]:
    trade_private_keys.append(trade_private_key)

trade_eth_amounts = []
for trade_eth_amount in data["trade_eth_amounts"]:
    trade_eth_amounts.append([int(trade_eth_amount[0]* pow(10, 18)), int(trade_eth_amount[1]* pow(10, 18))])

time_delays = []
for time_delay in data["time_delays"]:
    time_delays.append(int(time_delay))

# current_token = Token(
#                 address=new_token_address,
#                 router=router_address,
#                 provider=provider_http
#             )
# current_token.connect_wallet(trade_wallet_address[0], trade_private_keys[0])

# if not current_token.is_approved(new_token_address, liquidity_token_amount):
# current_token.approve(new_token_address, 0)
# current_token.set_gas_limit(liquidity_gas_limit)

# token_decimal = current_token.decimals()
# token_symbol = current_token.get_symbol()


# print(f"Current_token:{new_token_address}, symbol: {token_symbol}, decimals: {token_decimal}")

def start_bot(addr, pvtkey, start_amount, time_delay=10):
    print(f"Current_address:{addr}")
    current_token = Token(
                address=new_token_address,
                router=router_address,
                provider=provider_http
            )
    current_token.connect_wallet(addr, pvtkey)
    current_token.set_gas_limit(trade_gas_limit)
    current_token.wrap_ether(start_amount)

    sign_buy_tx = current_token.buyv3(start_amount, pool_fee=pool_fee, gas_price=trade_gas_price, timeout=2100)
    buy_result = current_token.send_buy_transaction(sign_buy_tx)
    current_token.web3.eth.wait_for_transaction_receipt(buy_result)
    print(f'buy transaction hash: {buy_result.hex()}')
    
    print(f'Start Sell')
    received_amount = current_token.balance()
    sign_sell_tx = current_token.sellv3(received_amount, pool_fee=pool_fee, gas_price=trade_gas_price, timeout=2100)
    current_token.web3.eth.wait_for_transaction_receipt(sign_sell_tx)
    print(f'sell transaction hash: {sign_sell_tx.hex()}')
    current_token.unwrap_ether(start_amount)
    time.sleep(time_delay);


for index in range(len(trade_private_keys)):
    try:
        threading.Thread(target=start_bot, args=(trade_wallet_address[index], trade_private_keys[index], random.randint(trade_eth_amounts[index][0],trade_eth_amounts[index][1]), time_delays[index])).start()
        # time.sleep(1);
    except Exception as e:
        print(f'Buy error: {e}')

