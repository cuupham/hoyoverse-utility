from flows.base_flow import BaseFlow
from api.zzz import ZzzAPI


class ZzzFlow(BaseFlow):
    def __init__(self, cookies):
        super().__init__(ZzzAPI, cookies)