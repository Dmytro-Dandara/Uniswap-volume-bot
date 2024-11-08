import argparse
import time
import json
import random
from web3 import Web3
from datetime import datetime
import threading
import os
import cli_ui

from pyuniswap.pyuniswap import Token

print("You are runing Bot v2!")

f = open('config.json')
data = json.load(f)
provider_http = data["provider_http"]
router_address = data["router_address"]
wrap_ether_address = data["wrap_ether_address"]
consume_token_address = data["consume_token"]
buying_token_address = data["buying_token"]
pool_fee = int(data["pool_fee"])

trade_gas_price = float(data["trade_gas_price"])
trade_gas_limit = int(data["trade_gas_limit"])


trade_wallet_address = []
for trade_wallet_addr in data["trade_wallet_address"]:
    trade_wallet_address.append(trade_wallet_addr)

trade_private_keys = []
for trade_private_key in data["trade_private_keys"]:
    trade_private_keys.append(trade_private_key)

trade_eth_amounts = []
for trade_eth_amount in data["trade_eth_amounts"]:
    trade_eth_amounts.append([float(trade_eth_amount[0]), float(trade_eth_amount[1])])

time_delays = []
for time_delay in data["time_delays"]:
    time_delays.append(int(time_delay))

web3 = Web3(Web3.HTTPProvider(provider_http))
# Get suggested gas price
suggest_gas_price = web3.eth.gas_price

if suggest_gas_price/pow(10,9) > trade_gas_price:
    raise ValueError(f"Your Gas Price has to be higher than {suggest_gas_price/pow(10,9)}")

if buying_token_address == wrap_ether_address:
    raise ValueError(f"Please input correct token address")

token_decimal = 18
current_token = None
if consume_token_address != wrap_ether_address:
    current_token = Token(
                    address=consume_token_address,
                    router=router_address,
                    wrap_addr=wrap_ether_address,
                    provider=provider_http
                )
    current_token.connect_wallet(trade_wallet_address[0], trade_private_keys[0])
    token_decimal = current_token.decimals()
    print(f"Current_token:{current_token.wallet_address}")

# print(f"Current_token:{consume_token_address},decimals: {token_decimal}")


def start_bot(consuming_token, buying_token, from_addr, pvtkey, start_amount, time_delay=10):

    current_token = Token(
                address=buying_token,
                router=router_address,
                wrap_addr=wrap_ether_address,
                provider=provider_http
            )
    current_token.connect_wallet(from_addr, pvtkey)
    current_token.set_gas_limit(trade_gas_limit)

    if consuming_token == wrap_ether_address:    
        try:
            sign_buy_raw_tx = current_token.buy(start_amount, consuming_token, gas_price=trade_gas_price * pow(10, 9), timeout=2100)
            sign_buy_tx = current_token.send_buy_transaction(sign_buy_raw_tx)
            tx_receipt = current_token.web3.eth.wait_for_transaction_receipt(sign_buy_tx)

            # Check if the transaction was successful
            if tx_receipt.status == 1:
                print(f"Buy Transaction was successful: {sign_buy_tx.hex()}")
            else:
                print(f"Buy Transaction failed: {sign_buy_tx.hex()}")
        except Exception as e:
            print(f"Buy Transaction Failed:{e}")

        try:
            received_amount = current_token.balance()
            
            sign_sell_tx = current_token.sell(received_amount, consuming_token, gas_price=trade_gas_price * pow(10, 9), timeout=2100)
            tx_receipt = current_token.web3.eth.wait_for_transaction_receipt(sign_sell_tx)
            
            # Check if the transaction was successful
            if tx_receipt.status == 1:
                print(f"Sell Transaction was successful: {sign_sell_tx.hex()}")
            else:
                print(f"Sell Transaction failed: {sign_sell_tx.hex()}")
        except Exception as e:
            print(f"Sell Transaction Failed:{e}")
    else:

        try:
            sign_buy_raw_tx = current_token.buybywbnb(start_amount, consuming_token, gas_price=trade_gas_price * pow(10, 9), timeout=2100)
            sign_buy_tx = current_token.send_buy_transaction(sign_buy_raw_tx)
            tx_receipt = current_token.web3.eth.wait_for_transaction_receipt(sign_buy_tx)

            # Check if the transaction was successful
            if tx_receipt.status == 1:
                print(f"Buy Transaction was successful: {sign_buy_tx.hex()}")
            else:
                print(f"Buy Transaction failed: {sign_buy_tx.hex()}")
        except Exception as e:
            print(f"Buy Transaction Failed:{e}")

        try:
            received_amount = current_token.balance()
            
            sign_sell_tx = current_token.sellbywbnb(received_amount, consuming_token, gas_price=trade_gas_price * pow(10, 9), timeout=2100)
            tx_receipt = current_token.web3.eth.wait_for_transaction_receipt(sign_sell_tx)
            
            # Check if the transaction was successful
            if tx_receipt.status == 1:
                print(f"Sell Transaction was successful: {sign_sell_tx.hex()}")
            else:
                print(f"Sell Transaction failed: {sign_sell_tx.hex()}")
        except Exception as e:
            print(f"Sell Transaction Failed:{e}")
    
    # waiting while delay time
    time.sleep(time_delay);

def main():
    for index in range(len(trade_private_keys)):
        try:
            threading.Thread(target=start_bot, args=(consume_token_address, buying_token_address, trade_wallet_address[index], trade_private_keys[index], random.randint(trade_eth_amounts[index][0]* pow(10, token_decimal),trade_eth_amounts[index][1]* pow(10, token_decimal)), time_delays[index])).start()
            # time.sleep(1);
        except Exception as e:
            print(f'Buy error: {e}')



first_choices = ["Run", "Edit"]
first_choice = cli_ui.ask_choice("Configuration", choices=first_choices)

if first_choice == "Run" :
    print("Running Bot")
    main()
else :
    first_choices = ["Basic Setting", "Wallet"]
    first_choice = cli_ui.ask_choice("Edit Configuration", choices=first_choices)
    f1 = open('config.json', "w")
    if first_choice == "Basic Setting" :
        name = cli_ui.ask_string("Enter HTTP Provider Url String:")
        data["provider_http"] = name

        name = cli_ui.ask_string("Enter Router Address String:")
        data["router_address"] = name

        name = cli_ui.ask_string("Enter Wrap Ether Address String:")
        data["wrap_ether_address"] = name

        name = cli_ui.ask_string("Enter Consuming Token Address String:")
        data["consume_token"] = name

        name = cli_ui.ask_string("Enter Buying Token Address String:")
        data["buying_token"] = name

        name = cli_ui.ask_string("Enter Pool Fee Number:")
        data["pool_fee"] = int(name)

        name = cli_ui.ask_string("Enter Trade Gas Price(GWei) Number:")
        data["trade_gas_price"] = int(name)

        name = cli_ui.ask_string("Enter Trade Gas Limit Number:")
        data["trade_gas_limit"] = int(name)
        print(f"Recorded String:{name}")
    else :
        name = cli_ui.ask_string("How many wallets do you want to add:")
        for index in range(int(name)):
            wallet_addr = cli_ui.ask_string("Enter Wallet Address String:")
            wallet_pvtky = cli_ui.ask_string("Enter Wallet Private Key String:")
            wallet_min = cli_ui.ask_string("Enter Buy Min Amount(Eth) Number:")
            wallet_max = cli_ui.ask_string("Enter Buy Max Amount(Eth) Number:")
            wallet_delay = cli_ui.ask_string("Enter Trade Frequency(second) Number:")
            trade_wallet_address.append(wallet_addr)
            trade_private_keys.append(wallet_pvtky)
            trade_eth_amounts.append([float(wallet_min), float(wallet_max)])
            time_delays.append(int(wallet_delay))
        data["trade_wallet_address"] = trade_wallet_address
        data["trade_private_keys"] = trade_private_keys
        data["trade_eth_amounts"] = trade_eth_amounts
        data["time_delays"] = time_delays
        
    json.dump(data, f1, indent=4)
    print(f"All Data saved")