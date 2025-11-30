from api.zzz import ZzzAPI


class ZzzFlow:
    def __init__(self, cookies:dict): #, act_id:str):
        self.api= ZzzAPI(cookies) #, act_id)
    
    def is_signed(self):
        return self.api.info()['data']['is_sign']

    def process_checkin(self):
        if self.is_signed():
            print('Player has already checked in.')
            return
        response = self.api.checkin()
        print(response)