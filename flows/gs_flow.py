from api.gs_api import GsAPI


class GsFlow:

    def __init__(self, cookies):
        self.api = GsAPI(cookies)
    
    # --- Main Process ---
    def process_checkin(self) -> str | dict:
        data = self.api.info()
        retcode = data['retcode']

        if retcode != 0:
            return data

        if is_sign := data.get('data', {}).get('is_sign'):
            return f'"is_sign": {is_sign}. Already checked-in'

        return self.api.checkin()