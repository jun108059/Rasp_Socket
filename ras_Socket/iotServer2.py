import socketserver, json
import logging
import os
os.environ.setdefault('DJANGO_SETTINGS_MOUDLE', 'djsite.settings')
django.setup()
from searchs.models import Search

class IoTRequestHandler(socketserver.StreamRequestHandler):
     def handle(self):
        client = self.request.getpeername() # request의 ip address(host, port) return
        logging.info("Client connecting: {}".format(client)) # 받아온 client의 ip address를 출력

        for line in self.rfile: # client가 requset한 기록을 실시간으로 파일로 만들어서 한 줄 한 줄 읽어옴
            # get a request message in JSON and converts into dict
            # json으로부터 요청 메시지 받아서 dict로 전환
            try: # rfile의 한 줄 한 줄(line)을 UTF-8로 해독해서 불러옴
                request = json.loads(line.decode('utf-8')) # json을 통해 파일의 한줄을 request 변수에 저장
            except ValueError as e: # 값을 불러오는 데에 실패했을 경우,
                # reply ERROR response message
                # 에러 응답 메시지를 응답
                error_msg = '{}: json decoding error'.format(e)
                status = 'ERROR {}'.format(error_msg)
                response = dict(status=status, deviceid=request.get('deviceid'), msgid=request.get('msgid'))
                response = json.dumps(response)
                self.wfile.write(response.encode('utf-8') + b'\n') # error를 write file 형식으로 만들어서 기록
                self.wfile.flush()  # file을 만들기 위해 사용한 버퍼를 비워줌
                logging.error(error_msg)    # error 출력
                break
            else: # try가 문제없이 실행될 경우 이어서 실행
                status = 'OK'
                logging.debug("{}:{}".format(client, request)) # 문제없이 실행됐을 경우 client와 request를 info형식으로 출력

            # extract the sensor data from the request
            # 요청으로부터 센서 데이터를 추출함
            data = request.get('data') # data의 value값 불러오기
            if data:        # data exists
                rfidNumber = float(data.get('rfidNumber'))
                Search(name='data', state=data).save()

            # Insert sensor data into DB tables, 데이터를 DB table에 넣는다
            # and retrieve information to control the actuators, 그리고 actuator를 제어하기 위해 정보를 검색

            # apply rules to control actuators
            activate = {}
                # activate actuators if necessary to control
            if rfidNumber ==1 :
                activate['RED'] = 'ON'
                activate['GREEN'] = 'OFF'
                activate['BLUE'] = 'OFF'
                activate['BUZZER'] = 'ON'
            elif rfidNumber ==2:
                activate['RED'] = 'OFF'
                activate['GREEN'] = 'ON'
                activate['BLUE'] = 'OFF'
                activate['BUZZER'] = 'ON'
            elif rfidNumber ==3:
                activate['RED'] = 'OFF'
                activate['GREEN'] = 'OFF'
                activate['BLUE'] = 'ON'
                activate['BUZZER'] = 'ON'
            elif rfidNumber ==4:
                activate['RED'] = 'ON'
                activate['GREEN'] = 'OFF'
                activate['BLUE'] = 'ON'
                activate['BUZZER'] = 'ON'

            ##### 여기까지 반복 #####

            # reply response message
            # 응답 메시지 reply
            response = dict(status=status, deviceid=request.get('deviceid'),msgid=request.get('msgid'))
            if activate:
                response['activate'] = activate
            response = json.dumps(response)
            self.wfile.write(response.encode('utf-8') + b'\n') # 응답을 UTF-8로 암호화
            self.wfile.flush()
            logging.debug("%s" % response)

        # end of for loop
        logging.info('Client closing: {}'.format(client))

# logging.basicConfig(filename='', level=logging.INFO)
logging.basicConfig(filename='', level=logging.DEBUG,
                    format = '%(asctime)s:%(levelname)s:%(message)s')

serv_addr = ("", 10077)
with socketserver.ThreadingTCPServer(serv_addr, IoTRequestHandler) as server:
    logging.info('Server starts: {}'.format(serv_addr)) # port 번호가 10007인 서버를 연다고 말해준다
    server.serve_forever()