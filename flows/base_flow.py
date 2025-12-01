class BaseFlow:
    def __init__(self, api_class, cookies: dict):
        self.api = api_class(cookies)
            
    def process_checkin(self) -> str:
        info = self.api.info()

        retcode = info['retcode']
        match retcode:
            case 0:
                is_sign = info['data']['is_sign']
            case -10002:
                return info['message']

        if is_sign:
            return 'User has already checked in.'

        return self.api.checkin()

