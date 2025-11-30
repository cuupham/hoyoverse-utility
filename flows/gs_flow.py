from api.gs import GsAPI


class GsFlow:
    def __init__(self, cookies: dict): #, act_id: str):
        self.api = GsAPI(cookies) #, act_id)
    
    def is_signed(self):
        response = self.api.info()
        return response['data']['is_sign']

    def process_checkin(self):
        if self.is_signed():
            print('Player has already checked in.')
            return

        response = self.api.checkin()
        print(response)