from api.sr import SrAPI


class SrFlow:
    def __init__(self, cookies:dict): #, act_id:str):
        self.api = SrAPI(cookies) #, act_id)
    
    def is_signed(self):
        response = self.api.info()
        #return response.get('data', {}).get('is_sign', False)
        return response['data']['is_sign']
    
    def process_checkin(self):
        if self.is_signed():
            print('Player has already checked in.')
            return
        response = self.api.checkin()
        print(response)