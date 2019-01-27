import time

import ipaddress
import requests
import xml.etree.ElementTree as ET

class AVT5260Error(Exception):
    def __init__(self, message):
        super().__init__(message)

class AVT5260:

    FIRST_RELAY_ID = 1
    NUMBER_OF_RELAYS = 8
    def __init__(self, ip:str, timeout:int=1):
        self.exc_info = None
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise

        self._ip = ip
        self._timeout = timeout
        self._states=dict()
        [self._states.update({i:False})  for i in range(0,8)]
        self._erors = 0
        self._read_status()


    def _get_status_request_url(self)->str:
        return 'http://'+self._ip+'/status.xml'

    def _get_change_state_request_url(self, relay:int)->str:
        return 'http://'+self._ip+'/leds.cgi?led='+str(relay+AVT5260.FIRST_RELAY_ID)

    def _read_status(self):
        try:
            response = requests.get(self._get_status_request_url(), timeout=self._timeout)
            if (response.status_code!=200):
                return None
        except Exception:
            print('Connection timeout')
            return None

        if response.status_code == 200:
            root = ET.fromstring((response.content.decode()))
            for led in root:
                if led.tag.startswith('led'):
                    led_id = int(led.tag[-1:])
                    if led_id>0:
                        led_id-= AVT5260.FIRST_RELAY_ID
                        self._states.update({led_id: True if led.text == '1' else False})
        return True
    def get_state(self,relay:int)->bool:
        self._read_status()
        if relay >= 0 and relay < AVT5260.NUMBER_OF_RELAYS:
            return self._states[relay]
        else:
            return None

    def set_state(self,relay:int, state:bool)->bool:
        if relay >= 0 and relay < AVT5260.NUMBER_OF_RELAYS:
            try:
                current_state = self._states[relay]
                if current_state is not None and current_state != state:
                    response = requests.get(self._get_change_state_request_url(relay), timeout=self._timeout)
                    if response.status_code != 200:
                        return None
                    self._read_status()
                    return self.get_state(relay)==state
                else:
                    return True
            except Exception:
                raise
                # print('Connection timeout')
                return None

    def set_by_mask(self, bitmask:int)->bool:
        error_cnt = 0
        for i in range (0,AVT5260.NUMBER_OF_RELAYS):
            if bool((bitmask & 1<<i)>>i) != self._states[i]:
                try:
                    if requests.get(self._get_change_state_request_url(i), timeout=self._timeout).status_code != 200:
                        error_cnt+=1
                except:
                    print('Couldn\'t set state of relay {} due to connection issue'.format(i))
                    error_cnt += 1

        self._read_status()
        self._erors = error_cnt
        return error_cnt==0

    @property
    def errors(self)->int:
        return self._erors

    @errors.setter
    def errors(self,value:int):
        self._errors = 0

#example
if __name__ == '__main__':
    relays = AVT5260('169.254.1.1')
    print(relays.get_state(1))
    relays.set_by_mask(0xff)
    relays.set_by_mask(0x1)
    print(relays.errors)
    relays.set_by_mask(0x0)
    for i in range (0,10):
        relays.set_state(0,True)
        time.sleep(0.4)
        relays.set_state(0,False)
        time.sleep(0.4)