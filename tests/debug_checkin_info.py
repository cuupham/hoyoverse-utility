"""Debug script to print raw responses from checkin info API"""
import asyncio
import aiohttp
import json
import os
import sys

# Thêm thư mục gốc vào path để import được src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.models.account import Account
from src.models.game import Game
from src.api.client import safe_api_call
from src.config import COMMON_HEADERS, ORIGINS, URLS
from src.api.checkin import check_cookie

async def get_game_roles(session: aiohttp.ClientSession, account: Account):
    """Lấy danh sách characters (roles) của account"""
    url = URLS['fetch_uid']
    headers = {
        **COMMON_HEADERS,
        "Cookie": account.cookie_str,
    }
    result = await safe_api_call(session, url, headers)
    return result

async def debug_get_checkin_info():
    """Gọi API /info và in ra JSON response gốc cho nhiều accounts"""
    
    # 1. Tìm và parse cookies.ps1
    cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.ps1")
    accounts = []
    
    if os.path.exists(cookies_path):
        with open(cookies_path, "r", encoding="utf-8") as f:
            content = f.read()
            import re
            # Tìm các dòng $env:ACC_X = "..."
            matches = re.findall(r'\$env:(ACC_\d+) = "(.*?)"', content)
            for name, cookie in matches:
                accounts.append(Account.from_env(name, cookie))
    
    # fallback nếu không có cookies.ps1 hoặc trống
    if not accounts:
        cookie_str = os.getenv("HOYOLAB_COOKIE")
        if cookie_str:
            accounts.append(Account.from_env("DEBUG_ACC", cookie_str))
        else:
            print("Error: Vui lòng set biến môi trường HOYOLAB_COOKIE hoặc điền vào cookies.ps1")
            return

    print(f"\n{'='*20} DEBUG CHECKIN INFO {'='*20}")
    print(f"Found {len(accounts)} accounts.")
    
    for account in accounts:
        print(f"\n\n{'#'*30} ACCOUNT: {account.name} {'#'*30}")
        # In ra ID và đoạn cuối cookie token để check xem có bị trùng lặp object không
        print(f"Account ID: {account.cookies.get('account_id_v2')}")
        print(f"Cookie Length: {len(account.cookie_str)}")
        print(f"Cookie (last 30 chars): ...{account.cookie_str[-30:]}")
        
        async with aiohttp.ClientSession() as session:
            # Check cookie and email mask
            cookie_check = await check_cookie(session, account)
            if cookie_check["valid"]:
                print(f"Email Mask: {cookie_check['email_mask']}")
            else:
                print(f"Cookie Error: {cookie_check['error']}")
            
            # Fetch Game Roles (Characters)
            roles_result = await get_game_roles(session, account)
            if roles_result["success"]:
                roles = roles_result["data"].get("data", {}).get("list", [])
                print(f"Discovered Roles ({len(roles)}):")
                for role in roles:
                    print(f"  - {role.get('game_biz')}: {role.get('nickname')} ({role.get('region')}) - UID: {role.get('game_uid')}")
            else:
                print(f"Roles Fetch Error: {roles_result['message']}")
            
            for game in Game:
                game_info = game.value
                print(f"\n[GAME] {game_info.name} ({game_info.code})")
                
                # Dựa theo curl thành công của user:
                # 1. Referer đơn giản: https://act.hoyolab.com/
                # 2. Origin: https://act.hoyolab.com
                # 3. CHỈ dùng x-rpc-lrsag (trống) cho Genshin, bỏ qua device_id và các x-rpc khác
                
                headers = {
                    **COMMON_HEADERS,
                    "Origin": "https://act.hoyolab.com",
                    "Referer": "https://act.hoyolab.com/",
                    "Cookie": account.cookie_str,
                }
                
                if game_info.code == 'gs':
                    headers["x-rpc-lrsag"] = ""
                elif game_info.signgame:
                    headers["x-rpc-signgame"] = game_info.signgame
                
                params = {"lang": "en-us", "act_id": game_info.act_id}
                url = URLS['checkin_info'][game_info.code]
                
                # Sử dụng safe_api_call nhưng xem 'data' bên trong
                result = await safe_api_call(
                    session, 
                    url, 
                    headers,
                    params=params
                )
                
                if result["success"]:
                    print("Response JSON:")
                    print(json.dumps(result["data"], indent=2, ensure_ascii=False))
                else:
                    print(f"Request Failed: {result['message']}")
                
                print("-" * 50)

if __name__ == "__main__":
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    try:
        asyncio.run(debug_get_checkin_info())
    except KeyboardInterrupt:
        pass
