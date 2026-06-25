import json
from web3 import Web3

RPC_URL = "https://liteforge.rpc.caldera.xyz/http"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

FACTORY = Web3.to_checksum_address("0x7D0FFa854edaE7659A1989Be42Df4CCe218F4c8C")
MORPHO  = Web3.to_checksum_address("0x80cb97194e9C885e313B76Bc108C5F7307f534F2")
MARKET_ID = "0x2dffbf1298d075cead09e1f8cc312c43582dd4b44e00fa216d16014f2023036c"

FACTORY_ABI = [
    {"inputs":[],"name":"allPairsLength","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
    {"inputs":[{"type":"uint256"}],"name":"allPairs","outputs":[{"type":"address"}],"stateMutability":"view","type":"function"},
]
PAIR_ABI = [
    {"inputs":[{"name":"owner","type":"address"}],"name":"balanceOf","outputs":[{"type":"uint256"}],"stateMutability":"view","type":"function"},
]
MORPHO_ABI = [
    {"inputs":[{"name":"marketId","type":"bytes32"},{"name":"user","type":"address"}],"name":"position","outputs":[
        {"name":"supplyShares","type":"uint256"},{"name":"borrowShares","type":"uint128"},{"name":"collateral","type":"uint128"},
    ],"stateMutability":"view","type":"function"},
]

def get_all_pairs():
    factory = w3.eth.contract(address=FACTORY, abi=FACTORY_ABI)
    length = factory.functions.allPairsLength().call()
    return [factory.functions.allPairs(i).call() for i in range(length)]

def check_swaps(wallet, min_swaps):
    pairs = get_all_pairs()
    if not pairs:
        return False
    topic_swap = w3.keccak(text="Swap(address,address,uint256,uint256)").hex()
    user = wallet[2:].lower()
    count = 0
    try:
        logs = w3.eth.get_logs({
            "address": pairs,
            "topics": [topic_swap, None, "0x" + user.zfill(64)],
            "fromBlock": 0, "toBlock": "latest"
        })
        count += len(logs)
    except:
        pass
    try:
        logs = w3.eth.get_logs({
            "address": pairs,
            "topics": [topic_swap, "0x" + user.zfill(64)],
            "fromBlock": 0, "toBlock": "latest"
        })
        count += len(logs)
    except:
        pass
    return count >= min_swaps

def check_borrow(wallet):
    morpho = w3.eth.contract(address=MORPHO, abi=MORPHO_ABI)
    pos = morpho.functions.position(MARKET_ID, Web3.to_checksum_address(wallet)).call()
    return pos[1] > 0

def check_liquidity(wallet, pair_addr):
    pair = Web3.to_checksum_address(pair_addr)
    pair_contract = w3.eth.contract(address=pair, abi=PAIR_ABI)
    balance = pair_contract.functions.balanceOf(Web3.to_checksum_address(wallet)).call()
    return balance > 0

def handler(request):
    if request.method != "POST":
        return {"statusCode": 405, "body": "Method Not Allowed"}

    try:
        data = request.get_json()
    except:
        return {"statusCode": 400, "body": json.dumps({"error": "invalid JSON"})}

    wallet = data.get("wallet") or data.get("account")
    task = data.get("task") or data.get("metadata", {}).get("task")
    if not wallet or not task:
        return {"statusCode": 400, "body": json.dumps({"error": "wallet and task required"})}

    try:
        if task == "swaps":
            min_swaps = int(data.get("min", 10))
            ok = check_swaps(wallet, min_swaps)
        elif task == "borrow":
            ok = check_borrow(wallet)
        elif task == "liquidity":
            pair = data.get("pair")
            if not pair:
                return {"statusCode": 400, "body": json.dumps({"error": "pair address required"})}
            ok = check_liquidity(wallet, pair)
        else:
            return {"statusCode": 400, "body": json.dumps({"error": f"unknown task '{task}'"})}
        return {"statusCode": 200, "body": json.dumps({"completed": ok})}
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}