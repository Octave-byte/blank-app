
########################################
### LIBRARY
########################################

import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st


########################################
### UTILS
########################################


lifi_key= st.secrets["auth_token"]
headers = {
    "accept": "application/json",
    "x-lifi-api-key": lifi_key
    }

def is_address_format(token: str):
    """Heuristic check to distinguish symbols from addresses based on chain-specific formats."""
    if token.startswith("0x") and len(token) == 42:
        return True  # Ethereum-style
    if token.startswith("0x") and len(token) == 66:
        return True  # Sui-style
    if token.startswith("bc") and len(token) == 14:
        return True  # Bitcoin (approx length range)
    if len(token) == 44:  # Solana addresses are fixed 44-char base58
        return True
    return False

def resolve_token(chain_id, token_input):
    #if is_address_format(token_input):
    #    return token_input, None
    # Otherwise, it's a symbol — resolve via API
    token_resp = requests.get(
        f"https://li.quest/v1/token?chain={chain_id}&token={token_input}",
        headers=headers
    )
    if token_resp.status_code != 200:
        raise ValueError(f"Failed to resolve token '{token_input}' on chain {chain_id}")
    token_data = token_resp.json()
    return token_data["address"], token_data["decimals"], token_data["priceUSD"]


def get_default_address_for_chain(chain_id):
    """
    Return default `fromAddress` based on chain ID type/format.
    """
    if chain_id == 9270000000000000:
        return "0xfd0c1c20e31915f318a219e04ba237b730d15f96a20d37835bff2041e2d1efd8"  # Sui
    if chain_id == 20000000000001:
        return "bc1qf68dp726r5dta0nwfpldtcfug9c9dx4vygtw5j"  # Bitcoin
    if chain_id == 1151111081099710:
        return "FgkkFMTgYURGN9y6NsJKbnTWXBEb5UGHovf9ZhBQhEHZ"  # Solana
    return "0xb29601eB52a052042FB6c68C69a442BD0AE90082"  # Default fallback


def get_native_token_address(chain_name):
    special_natives = {
        "Solana": "SOL",
        "Sui": "SUI",
        "Binance": "BNB",
        "Avalanche": "AVAX",
        "Gnosis": "xDAI",
        "Lens": "GHO",
        "Metis": "METIS",
        "Rootstock": "RBTC",
        "Bitcoin": "bitcoin"
    }
    return special_natives.get(chain_name, "ETH")

def get_chain_id(chain_name):
    chain_id_mapping = {
        "Abstract": 2741,
        "Apechain": 33139,
        "Arbitrum": 42161,
        "Aurora": 1313161554,
        "Avalanche": 43114,
        "Base": 8453,
        "Berachain": 80094,
        "Bitcoin": 20000000000001,
        "Blast": 81457,
        "BOB": 60808,
        "Boba": 288,
        "BSC": 56,
        "Celo": 42220,
        "Corn": 21000000,
        "Cronos": 25,
        "Ethereum": 1,
        "Etherlink": 42793,
        "Fantom": 250,
        "FUSE": 122,
        "Gnosis": 100,
        "Gravity": 1625,
        "HyperEVM": 999,
        "Immutable zkEVM": 13371,
        "Ink": 57073,
        "Kaia": 8217,
        "Lens": 232,
        "Linea": 59144,
        "Lisk": 1135,
        "Mantle": 5000,
        "Metis": 1088,
        "Mode": 34443,
        "Moonbeam": 1284,
        "Moonriver": 1285,
        "opBNB": 204,
        "Optimism": 10,
        "Polygon": 137,
        "Polygon zkEVM": 1101,
        "Rootstock": 30,
        "Scroll": 534352,
        "Sei": 1329,
        "Solana": 1151111081099710,
        "Soneium": 1868,
        "Sonic": 146,
        "Sui": 9270000000000000,
        "Superposition": 55244,
        "Swellchain": 1923,
        "Taiko": 167000,
        "Unichain": 130,
        "World Chain": 480,
        "XDC": 50,
        "zkSync": 324,
    }
    return chain_id_mapping.get(chain_name)

########################################
### FUNCTIONS
########################################


def resolve_transfer_details(src_chain_name, dst_chain_name, src_token_symbol, dst_token_symbol, sending_amount):
   # 1. Get all chain IDs -  API (commented) or via list
    #chain_resp = requests.get("https://li.quest/v1/chains?", headers=headers)
    #chains = chain_resp.json()
    #name_to_chain_id = {item["name"]: item["id"] for item in chains["chains"]}
    #src_chain_id = name_chain_id.get(src_chain_name)
    #dst_chain_id = name_chain_id.get(dst_chain_name)
    
    src_chain_id = get_chain_id(src_chain_name)
    dst_chain_id = get_chain_id(dst_chain_name)

    if src_chain_id is None or dst_chain_id is None:
        raise ValueError(f"Invalid chain name(s): {src_chain_name}, {dst_chain_name}")

    # 2. Resolve tokens
    src_token_address, src_decimals, src_price  = resolve_token(src_chain_id, src_token_symbol)
    dst_token_address, dst_decimals, dst_price = resolve_token(dst_chain_id, dst_token_symbol)

    # 3. Convert sending amount
    if src_decimals is not None:
        sending_amount_raw = int(float(sending_amount) * (10 ** src_decimals))
    else:
        sending_amount_raw = int(sending_amount)

    return {
        "src_chain_id": src_chain_id,
        "dst_chain_id": dst_chain_id,
        "src_token_address": src_token_address,
        "dst_token_address": dst_token_address,
        "sending_amount": sending_amount_raw,
        "price_from_amount": src_price,
        "price_to_amount": dst_price,
    }


def jumper_quote(originChain, destinationChain, originToken, destinationToken, amount, price_from_amount, price_to_amount, order):

    from_address = get_default_address_for_chain(originChain)
    to_address = get_default_address_for_chain(destinationChain)

    payload = {
        "fromChain": originChain,
        "toChain": destinationChain,
        "fromToken": originToken,
        "toToken": destinationToken,
        "fromAddress": from_address,
        "toAddress": to_address,
        "fromAmount": int(amount),
        "order": order
    }

    lifi_response = requests.get(
        "https://li.quest/v1/quote",
        headers=headers,
        params=payload,
        #timeout=10
    )

    if lifi_response.status_code == 200:
        lifi = lifi_response.json()
        
        tool = lifi["tool"]
        to_amount = int(lifi["estimate"]["toAmount"]) / (10 ** lifi["action"]["toToken"]["decimals"])
        to_amount_usd = to_amount * float(price_to_amount)
        from_amount_usd = float(price_from_amount) * int(lifi["estimate"]["fromAmount"]) / (10 ** lifi["action"]["fromToken"]["decimals"])
        
        jumper_link = (
                f"https://jumper.exchange/?"
                f"fromChain={originChain}&fromToken={originToken}"
                f"&toChain={destinationChain}&toToken={destinationToken}"
            )
        
        result = {
            "project": "Jumper",
            "tool":tool,
            "expectedAmount": to_amount,
            "efficiency": to_amount_usd / from_amount_usd,
            "time": lifi["estimate"]["executionDuration"],
            "link": jumper_link
        }
        return result
    else:
        return {}

def run_multistep_route(route_plan, initial_amount, order):
        steps = []
        current_amount = initial_amount
        total_time = 0
        usd_in = None
        usd_out = None

        for src_chain, dst_chain, src_token, dst_token in route_plan:
            
            try:
                details = resolve_transfer_details(src_chain, dst_chain, src_token, dst_token, current_amount)
                quote = jumper_quote(
                    originChain=details["src_chain_id"],
                    destinationChain=details["dst_chain_id"],
                    originToken=details["src_token_address"],
                    destinationToken=details["dst_token_address"],
                    amount=details["sending_amount"],
                    price_from_amount=details["price_from_amount"],
                    price_to_amount=details["price_to_amount"],
                    order = order
                )
                print(quote)
                steps.append(quote)
                current_amount = quote["expectedAmount"]
                total_time += quote["time"]

                # track efficiency
                if not usd_in:
                    usd_in = float(details["price_from_amount"]) * initial_amount
                usd_out = float(details["price_to_amount"]) * current_amount
            except Exception:
                return None

        if not steps:
            return None

        return {
            "steps": steps,
            "finalAmountUSD": usd_out,
            "totalTime": total_time,
            "cumulativeEfficiency": f"{(usd_out / usd_in) * 100:.4f}%" if usd_in and usd_out else "N/A"
        }


def find_best_routes(src_chain_name, dst_chain_name, src_token, dst_token, amount, order):
    
    base_chain = "Base"
    base_native = get_native_token_address(base_chain)
    src_native = get_native_token_address(src_chain_name)
    dst_native = get_native_token_address(dst_chain_name)

    # 1. Direct
    direct_route = run_multistep_route([
        (src_chain_name, dst_chain_name, src_token, dst_token)
    ], amount, order)

    if direct_route:
        return {
            "type": "direct",
            "description": "Direct quote found.",
            **direct_route
        }

    # 2. Native bridge (swap → bridge → swap)
    native_plan = []
    if src_token != src_native:
        native_plan.append((src_chain_name, src_chain_name, src_token, src_native))
    native_plan.append((src_chain_name, dst_chain_name, src_native, dst_native))
    if dst_token != dst_native:
        native_plan.append((dst_chain_name, dst_chain_name, dst_native, dst_token))

    native_route = run_multistep_route(native_plan, amount, order)
    if native_route and len(native_route["steps"]) >= 2:
        return {
            "type": "native_bridge",
            "description": "Swap to native, bridge, swap from native.",
            **native_route
        }

    # 3. Via Base (direct bridge)
    if src_chain_name != base_chain and dst_chain_name != base_chain:
        base_direct_route = run_multistep_route([
            (src_chain_name, base_chain, src_token, base_native),
            (base_chain, dst_chain_name, base_native, dst_token)
        ], amount, order)
        if base_direct_route:
            return {
                "type": "via_base_direct",
                "description": "Bridge to Base native, then to destination.",
                **base_direct_route
            }

    # 4. Via Base + native swaps
    if src_chain_name != base_chain and dst_chain_name != base_chain:
        base_native_plan = []
        if src_token != src_native:
            base_native_plan.append((src_chain_name, src_chain_name, src_token, src_native))
        base_native_plan.append((src_chain_name, base_chain, src_native, base_native))
        base_native_plan.append((base_chain, dst_chain_name, base_native, dst_native))
        if dst_token != dst_native:
            base_native_plan.append((dst_chain_name, dst_chain_name, dst_native, dst_token))

        base_native_route = run_multistep_route(base_native_plan, amount, order)
        if base_native_route and len(base_native_route["steps"]) >= 3:
            return {
                "type": "via_base_with_native",
                "description": "Swap to native → Base → dst native → final token",
                **base_native_route
            }


    # Nothing worked
    return {
        "type": "unavailable",
        "description": "No available route found.",
        "steps": [],
        "finalAmountUSD": 0,
        "totalTime": 0,
        "cumulativeEfficiency": "0%"}



def find_best_routes_parallel(src_chain_name, dst_chain_name, src_token, dst_token, amount, order):
    base_chain = "Base"
    base_native = get_native_token_address(base_chain)
    src_native = get_native_token_address(src_chain_name)
    dst_native = get_native_token_address(dst_chain_name)

    def get_efficiency(result):
        try:
            return float(result.get("cumulativeEfficiency", "0%").replace('%', ''))
        except:
            return 0

    def strategy_direct():
        return {
            "type": "direct",
            "description": "Direct quote found.",
            **run_multistep_route([
                (src_chain_name, dst_chain_name, src_token, dst_token)
            ], amount, order)
        }

    def strategy_native_bridge():
        plan = []
        if src_token != src_native:
            plan.append((src_chain_name, src_chain_name, src_token, src_native))
        plan.append((src_chain_name, dst_chain_name, src_native, dst_native))
        if dst_token != dst_native:
            plan.append((dst_chain_name, dst_chain_name, dst_native, dst_token))

        result = run_multistep_route(plan, amount, order)
        if result and len(result["steps"]) >= 2:
            return {
                "type": "native_bridge",
                "description": "Swap to native, bridge, swap from native.",
                **result
            }

    def strategy_base_direct():
        if src_chain_name == base_chain or dst_chain_name == base_chain:
            return None
        plan = [
            (src_chain_name, base_chain, src_token, base_native),
            (base_chain, dst_chain_name, base_native, dst_token)
        ]
        result = run_multistep_route(plan, amount, order)
        if result:
            return {
                "type": "via_base_direct",
                "description": "Bridge to Base native, then to destination.",
                **result
            }

    def strategy_base_with_native():
        if src_chain_name == base_chain or dst_chain_name == base_chain:
            return None
        plan = []
        if src_token != src_native:
            plan.append((src_chain_name, src_chain_name, src_token, src_native))
        plan.append((src_chain_name, base_chain, src_native, base_native))
        plan.append((base_chain, dst_chain_name, base_native, dst_native))
        if dst_token != dst_native:
            plan.append((dst_chain_name, dst_chain_name, dst_native, dst_token))

        result = run_multistep_route(plan, amount, order)
        if result and len(result["steps"]) >= 3:
            return {
                "type": "via_base_with_native",
                "description": "Swap to native → Base → dst native → final token",
                **result
            }


    strategies = [
        strategy_direct,
        strategy_native_bridge,
        strategy_base_direct,
        strategy_base_with_native
    ]

    results = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_strategy = {executor.submit(fn): fn.__name__ for fn in strategies}
        for future in as_completed(future_to_strategy):
            try:
                result = future.result()
                if result and result.get("steps"):
                    results.append(result)
            except Exception:
                continue

    if results:
        best = max(results, key=get_efficiency)
        return {
            "best": best,
            "alternatives": [
                {
                    "type": route["type"],
                    "description": route["description"],
                    "efficiency": f"{get_efficiency(route):.2f}%",
                    "steps": route["steps"]
                }
                for route in results if route != best
            ]
    }


    return {
        "type": "unavailable",
        "description": "No available route found.",
        "steps": [],
        "finalAmountUSD": 0,
        "totalTime": 0,
        "cumulativeEfficiency": "0%"
    }


