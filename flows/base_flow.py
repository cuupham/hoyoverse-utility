class BaseFlow:
    def __init__(self, api_class, cookies: dict):
        self.api = api_class(cookies)
            
    def process_checkin(self):
        info = self.api.info()

        retcode = info['retcode']
        match retcode:
            case 0:
                is_sign = info['data']['is_sign']
            case -10002:
                print(info['message'])
                return

        if is_sign:
            print('User has already checked in.')
            return

        response = self.api.checkin()
        print(response)


