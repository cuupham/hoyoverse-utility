class BaseFlow:
    def __init__(self, api_class, cookies: dict):
        self.api = api_class(cookies)

    def is_signed(self):
        response = self.api.info()
        if response.get('retcode') != 0:
            raise RuntimeError(f"An error occurred in request => {response}")
        return response['data']['is_sign']

    def process_checkin(self):
        if self.is_signed():
            print('Player has already checked in.')
            return
        response = self.api.checkin()
        print(response)


