"""
We define IoT Protocol messages as Python dicts for example.
They are serialized as JSON format string, then encoded in utf-8.
Caution: because every messages are delimited by new line character (b'\n') in a TCP session,
avoid using LF character inside Python strings.

The POST request messages may be sent periodically for server
to inform the client to activate the actuators if needed.

<request message> ::= <request object in JSON format with UTF-8 encoding> <LF>

<request object> ::=
    {   'method': 'POST',
        'deviceid': <device id>,
        'msgid': <messge id>,
        'data': {'distance': 28.5 }
    }

<response message> ::= <response object in JSON format with UTF-8 encoding> <LF>

<response object> ::=
    {   'status': 'OK' | 'ERROR <error msg>',
        'deviceid': <device id>
        'msgid': <messge id>
      [ 'activate': {'red': 'ON', 'green': 'OFF',
                        'blue': 'OFF', 'buzzer': 'ON' } ]  # optional
    }

<LF> ::= b'\n'
"""

from socket import *
import json, time, sys
import selectors, uuid
import random, math
import logging
import RPi.GPIO as GPIO

ECHO = 21
TRIG = 20
RED = 16
GREEN = 17
BLUE = 18
BUZZER = 14

GPIO.setmode(GPIO.BCM)
GPIO.setup(ECHO, GPIO.IN)
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)
GPIO.setup(BUZZER, GPIO.OUT)

def sen_data():
    ultradis = 0
    while True:
        GPIO.out(TRIG,False)
        time.sleep(0.02)
        GPIO.out(TRIG,True)
        time.sleep(0.2)
        GPIO.out(TRIG,False)

        start = time.time()

        while(GPIO.input(ECHO) == 1):
            pass

        travel = time.time() - start

        ultradis = travel / 58

        print("%d", ultradis, 'cm\n')

        if(ultradis < 10 and ultradis > 0):
            GPIO.out(BUZZER, GPIO.HIGH)
            GPIO.out(RED, GPIO.HIGH)
            GPIO.out(GREEN, GPIO.LOW)
            GPIO.out(BLUE, GPIO.LOW)
            yield ultradis

        elif(ultradis < 50):
            GPIO.out(BUZZER, GPIO.LOW)
            GPIO.out(RED, GPIO.LOW)
            GPIO.out(GREEN, GPIO.HIGH)
            GPIO.out(BLUE, GPIO.LOW)
            yield ultradis

        else:
            GPIO.out(BUZZER, GPIO.LOW)
            GPIO.out(RED, GPIO.LOW)
            GPIO.out(GREEN, GPIO.LOW)
            GPIO.out(BLUE, GPIO.HIGH)
            yield ultradis

        time.sleep(0.1)

class IoTClient:
    def __init__(self, server_addr, deviceid):
        """IoT client with persistent connection
        Each message separated by b'\n'

        :param server_addr: (host, port)
        :param deviceid: id of this IoT
        """

        sock = socket(AF_INET, SOCK_STREAM)
        sock.connect(server_addr)  # connect to server process
        rfile = sock.makefile('rb')  # file-like obj
        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)

        self.sock = sock
        self.rfile = rfile
        self.deviceid = deviceid
        self.sel = sel
        self.requests = {}      # messages sent but not yet received their responses
        self.time_to_expire = None

    def select_periodic(self, interval):
        """Wait for ready events or time interval. (ready event 또는 time interval을 기다림, sensor값이
                                                    들어오지 않아서 timeout 될 때까지의 간격을 time interval이라 함)
        Timeout event([]) occurs every interval, periodically. (timeout event는 모든 구간에서, 정기적으로 일어남)
        """
        now = time.time()
        if self.time_to_expire is None:
            self.time_to_expire = now + interval
        timeout_left = self.time_to_expire - now
        if timeout_left > 0:
            events = self.sel.select(timeout=timeout_left)
            if events:
                return events
        # time to expire elapsed or timeout event occurs
        self.time_to_expire += interval # set next time to expire
        return []

    def run(self):
        # Report sensors' data forever
        sensor = sen_data()
        msgid = 0

        while True:
            try:
                events = self.select_periodic(interval=5)
                if not events:      # timeout occurs
                    try:
                        distance = next(sensor)
                    except StopIteration: # 더 이상 보낼 데이터가 없으면 종료
                        logging.info('No more sensor data to send')
                        break
                    data = dict(distance=distance) # 만든 dict를 data값으로 입력
                    # msgid = str(uuid.uuid1())
                    msgid += 1
                    request = dict(method='POST', deviceid=self.deviceid, msgid=msgid, data=data)
                    logging.debug(request)
                    request_bytes = json.dumps(request).encode('utf-8') + b'\n'
                    self.sock.sendall(request_bytes)
                    self.requests[msgid] = request_bytes
                else:               # EVENT_READ
                    response_bytes = self.rfile.readline()     # receive response, rfile 문서의 한 줄을 읽어옴
                    if not response_bytes: # 서버가 비정상 종료
                        self.sock.close()
                        raise OSError('Server abnormally terminated')
                    response = json.loads(response_bytes.decode('ASCII')) # json을 통해 전달받은 데이터를 UTF-8로 해독
                    logging.debug(response)

                    # msgid in response allows to identify the specific request message
                    # It enables asynchronous transmission of request messages in pipelining
                    # response에서 msgid는 구체적인 요청 msg의  identify하도록 허락한다
                    # pipelining에서 요청 msg의 비동기적 전송을 가능하게 한다
                    msgid = response.get('msgid')
                    if msgid and msgid in self.requests:
                        del self.requests[msgid]
                    else:
                        logging.warning('{}: illegal msgid received. Ignored'.format(msgid))
            except Exception as e:
                logging.error(e)
                break
        # end of while loop

        logging.info('client terminated')
        self.sock.close()


if __name__ == '__main__':
    if len(sys.argv) == 3: # iotclient.py, host:port, deviceId, 3가지의 값이 모두 입력될 경우
        host, port = sys.argv[1].split(':') # host:port를 host와 port로 분리
        port = int(port)
        deviceid = sys.argv[2]
    else: # 3가지 값의 입력이 제대로 이루어지지 않았을 경우
        print('Usage: {} host:port deviceid'.format(sys.argv[0]))
        sys.exit(1)

    logging.basicConfig(level=logging.DEBUG,
                        format = '%(asctime)s:%(levelname)s:%(message)s')
    client = IoTClient((host, port), deviceid)
    client.run()
GPIO.cleanup()