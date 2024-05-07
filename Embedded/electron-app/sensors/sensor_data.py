# DamaskRose

#  - NFC ��� �α��� ���
#    : NFC �±� �� Token ����

#  - ��ü ���� ���� ���
#    1. �α��� ����
#        1-1. 5�� �̻� �ڸ� ���
#        1-2. 2�ð� �̻� �ڸ��� �ɾ� �ִ� ���
#    2. �α׾ƿ� ����
#        2-1. ��� �ν� �� AOD ȭ�� ���

import os
from dotenv import load_dotenv
import board
import busio
import time
import json
import sys
import requests
import io
from adafruit_pn532.i2c import PN532_I2C
from gpiozero import MotionSensor

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_serial_number():
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line.startswith('Serial'):
                return line.split(':')[1].strip()
    return None

load_dotenv() # .env ���� �ε�
server_url = os.getenv('SERVER_URL')

i2c = busio.I2C(board.SCL, board.SDA) # I2C ���� ����
pn532 = PN532_I2C(i2c, debug=False) # PN532 ��� �ʱ�ȭ
pn532.SAM_configuration() # SAM ����


pir = MotionSensor(17)  # GPIO 17�� �ɿ� ����� PIR ���� HC-SR501
motion_detected_time = time.time()

logged_in = False
print("Waiting for NFC card...", file=sys.stderr)

# ������ �ð� ����
NO_MOTION_TIMEOUT = 300  # 5��
LONG_SIT_TIMEOUT = 7200  # 2�ð�
last_motion_time = time.time()

while True:
    if not  logged_in:  # �α׾ƿ� ����
        # ī���� UID �б�
        uid = pn532.read_passive_target(timeout=0.5)
        if uid is not None:
            # ī�� UID�� ��� ���ڿ��� ��ȯ
            card_serial_id = ''.join(["{0:x}".format(i).zfill(2) for i in uid])
            # print("card UID:", card_serial_id)
            
            # ��������� �ø��� �ѹ�
            device_id = get_serial_number()
            
            # POST ��û ������
            url = f'{server_url}/api/device/login'
            payload = {'deviceId': device_id, 'cardSerialId': card_serial_id}
            headers = {'Content-Type': 'application/json'}

            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                response_data = response.json()
                # print("Server response:", response_data)

                if response_data.get('message') == '�α��� ����':
                    print("NFC �α��� ����")
                    sys.stdout.write(json.dumps(response_data))
                    sys.stdout.flush()
                    logged_in = True
                    motion_detected_time = time.time()  # ������ ���� �ð� �ʱ�ȭ
                else:
                    print("Login failed:", response_data.get('message'))
                    
            except requests.exceptions.HTTPError as e:
                print(f"HTTP error occurred: {e}")  # HTTP ���� ���
            except requests.exceptions.RequestException as e:
                print(f"Request error: {e}")  # ��û ���� ���
            except Exception as e:
                print(f"An error occurred: {e}")  # ��Ÿ ���� ó��

        elif pir.motion_detected:
            # �α׾ƿ� ���¿��� ���� �� AOD ȭ�� ���
            print("AOD ����")
            sys.stdout.write(json.dumps({"type": "AOD"}))
            sys.stdout.flush()

    elif logged_in: # �α��� ����
        if pir.motion_detected: # ������ ����
            motion_detected_time = time.time()
            last_motion_time = time.time()
            print("Motion detected.")

        current_time = time.time()
        if current_time - motion_detected_time > NO_MOTION_TIMEOUT:
            # �ڸ� ��� ���� ����
            print("�ڸ� ��� ����")
            sys.stdout.write(json.dumps({"type": "AWAY"}))
            sys.stdout.flush()
            motion_detected_time = current_time  # Ÿ�̸� ����

        if current_time - last_motion_time > LONG_SIT_TIMEOUT:
            # ���� �ɾ� ���� ���� ����
            print("���� �ɾ� ���� ����")
            sys.stdout.write(json.dumps({"type": "LONG_SIT"}))
            sys.stdout.flush()
            last_motion_time = current_time  # Ÿ�̸� ����
    
    # �α׾ƿ� ��� �߰�!!!!!!
    
    time.sleep(1)  # �˻� ���� ����
       