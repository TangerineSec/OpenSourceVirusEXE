import frozen  # Pyinstaller多进程代码打包exe出现多个进程解决方案
import multiprocessing
import subprocess, time, sys, os
import win32con
import win32api

CMD = r"WinCoreManagement.exe"  # 需要执行程序的绝对路径


def run(cmd):
    # print('start OK!')
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    p = subprocess.Popen(cmd, shell=False)
    p.wait() # 类似于p.join()
    try:
        subprocess.call('start /b taskkill /F /IM %s' % CMD) # 清理残余
    except Exception as e:
        # print(e)
        pass

    # print('子进程关闭，重启')
    run(cmd)


if __name__ == '__main__':
    multiprocessing.freeze_support()  # Pyinstaller多进程代码打包exe出现多个进程解决方案

    run(CMD)
