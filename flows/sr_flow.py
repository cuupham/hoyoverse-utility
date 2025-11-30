from flows.base_flow import BaseFlow
from api.sr import SrAPI


class SrFlow(BaseFlow):
    def __init__(self, cookies):
        super().__init__(SrAPI, cookies)