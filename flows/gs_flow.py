from flows.base_flow import BaseFlow
from api.gs import GsAPI


class GsFlow(BaseFlow):
    def __init__(self, cookies):
        super().__init__(GsAPI, cookies)