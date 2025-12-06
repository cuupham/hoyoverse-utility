from api.sr_api import SrAPI
import time


class SrFlow:

    def __init__(self, cookies:dict):
        self.api = SrAPI(cookies)

    # --- Helper ---
    def fetch_game_roles(self) -> list[dict] | dict:
        data = self.api.get_user_game_role()
        retcode = data['retcode']

        if retcode != 0:
            return data 

        uids_list = data.get("data", {}).get("list", [])
        return [
            {
                "game_uid": item.get("game_uid"),
                "game_biz": item.get("game_biz"),
                "region": item.get("region")
            }
            for item in uids_list
            if item.get("game_uid")
        ]
    
    def fetch_exchange_codes(self):
        data = self.api.get_material()
        retcode = data['retcode']

        if retcode != 0:
            return data

        codes = []

        for module in data.get('data', {}).get('modules', []):
            exchange_group = module.get('exchange_group')
            if not exchange_group:
                continue

            for bonus_info in exchange_group.get('bonuses', []):
                code = bonus_info.get('exchange_code')
                if code:
                    codes.append(code)
        return codes

    # --- Main Process ---
    def process_checkin(self) -> str | dict:
        data = self.api.info()
        retcode = data['retcode']

        if retcode != 0:
            return data

        if is_sign := data.get('data', {}).get('is_sign'):
            return f'"is_sign": {is_sign}. Already checked-in'

        return self.api.checkin()

    def claim_redeem_code(self):
        if not (uids_info := self.fetch_game_roles()):
            return 'UID not found.'
        
        if not (cd_keys := self.fetch_exchange_codes()):
            return 'CD_KEY does not exist.'

        txt = ''
        for uid_info in uids_info:
            for cd_key in cd_keys:
                _res = self.api.redeem_code(uid_info, cd_key)
                txt += f'"{cd_key}": {_res}\n'

                if cd_key != cd_keys[-1]:
                    time.sleep(5)
        return txt