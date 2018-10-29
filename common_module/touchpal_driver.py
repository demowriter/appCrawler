#coding=utf-8
'''
基于appium webriver封装操作ios的基类
'''
import logging
import os
import subprocess
import sys
import threading
import time
import urllib2
from functools import wraps
from appium import webdriver
from selenium.common.exceptions import WebDriverException,NoSuchElementException
from common import install_uiautomator2_apk,push_handler_file
from touchpal_element import WebElement,Touchpal_weblement
import re
import json
import lxml
from lxml import etree
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',)#添加日志模块

resource_id_pattren = re.compile(
    r"com\.cootek\.smartdialer\.R\.id\.(\S+)\s*?->\s*?com\.cootek\.smartdialer\.R\.id\.(\S+)")

replace_xpath_pattren=re.compile(r'@resource-id="(\S+?)"')#正则表达式替换映射文件的resource id
phone_size_pattren=re.compile(r"(\d+)x(\d+)")#正则表达式获取手机的尺寸大小


def decorated_findelement_fuc(origin_findelement_fuc):
    default_max_find_time = 10
    @wraps(origin_findelement_fuc)
    def real_excute(self,selector,handler_exception=False):
        max_find_time=getattr(self,"_implicitly_time",None) or default_max_find_time
        start_time=time.time()
        while time.time()-start_time<=max_find_time:
            try:
                return origin_findelement_fuc(self,selector)
            except WebDriverException:
                pass
        raise WebDriverException("can not find element by function:{} using value:{}".format(origin_findelement_fuc.__name__,selector))
    return real_excute


def iproxy(local_port,remote_port,udid):
    subprocess.Popen("adb -s %s forward tcp:%s tcp:6790"%(udid,local_port),shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).wait()#转发本地端口-->手机


def run_uiautomator2_server(udid):
    server_start_cmd="adb -s %s shell am instrument -w io.appium.uiautomator2.server.test/android.support.test.runner.AndroidJUnitRunner"%udid
    subprocess.Popen(server_start_cmd, shell=True,stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()  #启动uiautomator2 server

def kill_uiautomator_server(udid):
    '''
    kill original uiautomator2 server on udid
    :param udid: devices number
    :return:
    '''
    os.popen("adb -s %s shell am force-stop io.appium.uiautomator2.server"%udid)
def start_uiautomator2_server(udid,local_port,remote_port):
    install_uiautomator2_apk(udid)#安装uiautomator2 server
    kill_uiautomator_server(udid)#kill uiautomator2 server
    opener = urllib2.build_opener()
    ##########转发本地端口(Android)##########
    target=threading.Thread(target=iproxy,args=(local_port,remote_port,udid))
    target.setDaemon(True)
    target.start()
    target = threading.Thread(target=run_uiautomator2_server, args=(udid,))
    # <--------------注意点-------------->#
    # 让webdriverAgent存在Python线程中持续运行,暂时不设置守护进程
    target.setDaemon(True)
    target.start()
    wait_first_flag = True
    for i in range(10):
        try:
            opener.open("http://localhost:%s/wd/hub/status" % local_port, timeout=2)
            if not wait_first_flag:
                sys.stdout.write("\n")
                sys.stdout.flush()
            return True
        except Exception:
            if wait_first_flag:
                sys.stdout.write("watting uiautomator2 server start.")
                sys.stdout.flush()
                wait_first_flag = False
            else:
                sys.stdout.write(".")
                sys.stdout.flush()
        time.sleep(2)
    raise RuntimeError("uiautomator2_server started faild!!!")

class Remote(webdriver.Remote):
    def __init__(self,port,udid):
        self.after_handler_id_dict = {}
        self.udid=udid
        self.phone_size=[]
        phone_size_result = phone_size_pattren.findall(os.popen("adb -s %s shell wm size" % self.udid).read())[-1]
        self.phone_size.extend([int(phone_size_result[0]), int(phone_size_result[1])])
        script_dir_path = os.path.dirname(os.path.abspath(__file__))  # touchpal_driver的根目录
        ###########确保handler_popup_file中json对象正确否则抛出异常########
        handler_popup_file_path=os.path.join(script_dir_path,"handler_popup_file.txt")
        try:
            json.load(open(handler_popup_file_path,"rb"))
        except ValueError:
            raise ValueError("handler_popup_file.txt中的json对象格式错误导致uiautomator2 server不能正确处理异常事件")
        push_handler_file(udid,handler_popup_file_path)
        start_uiautomator2_server(udid,port,port)#Andorid启动uiautomator2 server
        desired_caps = {}
        desired_caps['platform'] = "LINUX"
        desired_caps['webStorageEnabled'] =False
        desired_caps['takesScreenshot'] =True
        desired_caps['javascriptEnabled'] =True
        desired_caps['databaseEnabled'] = True
        desired_caps['networkConnectionEnabled'] =True
        desired_caps["locationContextEnabled"] =False
        desired_caps['warnings'] ={}
        desired_caps["deviceName"]=udid,
        desired_caps["unicodeKeyboard"]=True,
        desired_caps["udid"]=udid,
        desired_caps["automationName"]="uiautomator2",
        desired_caps["resetKeyboard"]=True,
        desired_caps["newCommandTimeout"]=200,
        desired_caps["platformVersion"]="7.0",
        desired_caps["appPackage"]="com.cootek.smartdialer",
        desired_caps["platformName"]="Android",
        desired_caps["appActivity"]=".v6.TPDTabActivity",
        desired_caps["deviceUDID"]=udid
        desired_caps["deviceScreenSize"]="1080x1920",
        desired_caps["deviceModel"]="MI 5s",
        desired_caps["deviceManufacturer"]="Xiaomi"
        desired_caps["desired"]={
            "deviceName": "Android Emulator",
            "unicodeKeyboard":True,
            "udid":udid,
            "automationName": "uiautomator2",
            "resetKeyboard": True,
            "newCommandTimeout": 200,
            "platformVersion": "4.4.2",
            "appPackage": "com.cootek.smartdialer",
            "platformName": "Android",
            "appActivity": ".v6.TPDTabActivity"
        }
        for i in range(5):
            try:
                super(Remote, self).__init__("http://127.0.0.1:%s/wd/hub"%port,desired_capabilities=desired_caps, browser_profile=None, proxy=None, keep_alive=False)
                break
            except Exception:
                logging.info("第%s次启动webdriverAgent server失败"%(i+1))
                time.sleep(2)
        if self.command_executor is not None:
            self._add_newCommands()
        self._implicitly_time=10#寻找最大的时间
        self._default_time=10#相当于中间变量,注意这个值不要动态改变

    def create_web_element(self, element_id):
        """
        Creates a web element with the specified element_id.
        Overrides method in Selenium WebDriver in order to always give them
        Appium WebElement
        """
        return WebElement(self, element_id)

    def implicitly_wait(self, time_to_wait):
        """
        Sets a sticky timeout to implicitly wait for an element to be found,
           or a command to complete. This method only needs to be called one
           time per session. To set the timeout for calls to
           execute_async_script, see set_script_timeout.

        :Args:
         - time_to_wait: Amount of time to wait (in seconds)

        :Usage:
            driver.implicitly_wait(10)
        """
        self._implicitly_time=time_to_wait#同时更改touchpal寻找元素的时间




    @decorated_findelement_fuc
    def find_element_by_name(self,name,handler_exception=False):
        """
       Finds an element by name.

       :Args:
        - name: The name of the element to find.

       :Usage:
           driver.find_element_by_name('foo')
        """
        return self._find_element(strategy="-android uiautomator",selector='text("%s")' % (name))

    @decorated_findelement_fuc
    def find_elements_by_name(self, name):
        """
        Finds elements by name.

        :Args:
           - name: The name of the elements to find.

        :Usage:
              driver.find_elements_by_name('foo')
        """

        return self._find_elements(strategy="-android uiautomator", selector='text("%s")' % (name))

    @decorated_findelement_fuc
    def find_element_by_id(self,id_,handler_exception=False):
        """
        Finds an element by id.

        :Args:
        - name: The id of the element to find.

        :Usage:
          driver.find_element_by_id('foo')
        """
        return self._find_element(strategy="id", selector=id_)

    @decorated_findelement_fuc
    def find_elements_by_id(self,id_):
        """
        Finds elements by id.

        :Args:
        - name: The id of the element to find.

        :Usage:
          driver.find_elements_by_id('foo')
        """
        return self._find_elements(strategy="id", selector=id_)

    @decorated_findelement_fuc
    def find_element_by_xpath(self, xpath_str, handler_exception=False):
        """
        Finds an element by id.

        :Args:
        - name: The id of the element to find.

        :Usage:
          driver.find_element_by_id('foo')
        """
        return self._find_element(strategy="xpath", selector=xpath_str)


    @decorated_findelement_fuc
    def  find_elements_by_xpath(self,xpath_str):
        """
        Finds elements by id.

        :Args:
        - name: The id of the element to find.

        :Usage:
          driver.find_elements_by_id('foo')
        """
        return self._find_elements(strategy="xpath", selector=xpath_str)


    def judge_element_by_xpath(self, xpath, current_page_source):

        """
           判断当前page_source是否含有xpath str的元素

           :Args:
            - xpath - The xpath locator of the element to find.

           :Usage:
               driver.judge_element_by_xpath('//div/td[1]')
           :

        """
        try:
            xml_source = etree.XML(current_page_source)
            all_pattern_result = xml_source.xpath(xpath.decode("utf-8"))
        except lxml.etree.XMLSyntaxError:  # 处理解析出错的异常
            all_pattern_result = []
        except ValueError:
            raise ValueError("current_page_source must be encoding by utf-8")
        except Exception:
            raise WebDriverException("%s的xpath语法不合法..." % (xpath))
        if len(all_pattern_result) > 0:
            return True
        else:
            return False

    def create_element_by_xpath(self, xpath, current_page_source):

        """
           用pagesource创建匹配传入xpath的元素

           :Args:
            - xpath - The xpath locator of the element to find.

           :Usage:
               driver.create_element_by_xpath('//div/td[1]',current_page_source)
           :

        """
        try:
            xml_source = etree.XML(current_page_source)
            all_pattern_result = xml_source.xpath(xpath.decode("utf-8"))
        except lxml.etree.XMLSyntaxError:  # 处理解析出错的异常
            all_pattern_result = []
        except ValueError:
            raise ValueError("current_page_source must be encoding by utf-8")
        except Exception:
            raise WebDriverException("%s的xpath语法不合法..." % (xpath))
        if len(all_pattern_result) > 0:
            return Touchpal_weblement(all_pattern_result[0],self.udid)
        else:
            return False

    def create_elements_by_xpath(self,xpath,current_page_source):

        """
               Finds an element by xpath used lxml.

               :Args:
                - xpath - The xpath locator of the element to find.

               :Usage:
                   driver.create_elements_by_xpath('//div/td[1]')

               """
        try:
            xml_source = etree.XML(current_page_source)
            all_pattern_result = xml_source.xpath(xpath.decode("utf-8"))
        except lxml.etree.XMLSyntaxError:  # 处理解析出错的异常
            all_pattern_result = []
        except ValueError:
            raise ValueError("current_page_source must be encoding by utf-8")
        except Exception:
            raise WebDriverException("%s的xpath语法不合法..." % (xpath))
        if len(all_pattern_result) > 0:
            return [Touchpal_weblement(each_elemnt,self.udid) for each_elemnt in
                    all_pattern_result]  # Touchpal_weblement对象list

        else:
            return []

    @decorated_findelement_fuc
    def find_element_by_class_name(self, name,handler_exception=False):
        """
        Finds an element by class name.

        :Args:
             - name: The class name of the element to find.

        :Usage:
            driver.find_element_by_class_name('foo')
        """
        return self._find_element(strategy="class name",selector=name)

    @decorated_findelement_fuc
    def find_elements_by_class_name(self, name):
        """
        Finds elements by class name.

        :Args:
         - name: The class name of the elements to find.

        :Usage:
            driver.find_elements_by_class_name('foo')
        """
        return self._find_elements(strategy="class name", selector=name)

    @decorated_findelement_fuc
    def find_element_by_accessibility_id(self, id,handler_exception=False):
        """Finds an element by accessibility id.

        :Args:
         - id - a string corresponding to a recursive element search using the
         Id/Name that the native Accessibility options utilize

        :Usage:
            driver.find_element_by_accessibility_id()
        """
        return self._find_element(strategy="accessibility id", selector=id)

    @decorated_findelement_fuc
    def find_elements_by_accessibility_id(self, id):
        """Finds elements by accessibility id.

        :Args:
         - id - a string corresponding to a recursive element search using the
         Id/Name that the native Accessibility options utilize

        :Usage:
            driver.find_elements_by_accessibility_id()
        """
        return self._find_elements(strategy="accessibility id", selector=id)

    @decorated_findelement_fuc
    def find_element_by_android_uiautomator(self, uia_string):
        """Finds element by uiautomator in Android.

        :Args:
         - uia_string - The element name in the Android UIAutomator library

        :Usage:
            driver.find_element_by_android_uiautomator('.elements()[1].cells()[2]')
        """
        return self._find_element(strategy="-android uiautomator", selector=uia_string)

    @decorated_findelement_fuc
    def find_elements_by_android_uiautomator(self, uia_string):
        """Finds elements by uiautomator in Android.

        :Args:
         - uia_string - The element name in the Android UIAutomator library

        :Usage:
            driver.find_elements_by_android_uiautomator('.elements()[1].cells()[2]')
        """
        return self._find_elements(strategy="-android uiautomator", selector=uia_string)



    def whether_element_displayed(self, strategy,value,maxtime=2,handler_exception=False):
        """
          :param strategy:通过某种策略寻找，比如"id","name","xapth".....
          :param value: 策略对应的值
          :param maxtime:最大寻找时间
          :return: 元素存在return True 不存在 False
        """
        # strategy如下：
        # "id"
        # "xpath"
        # "link text"
        # "partial link text"
        # "name"
        # "tag name"
        # "class name"
        # "css selector"
        # usage:driver.swipeTo_Element("name","选择行业")
        try:
            self.implicitly_wait(maxtime)#设置隐式等待时间为maxtime
            if strategy == "name":
                element =self.find_element_by_name(value,handler_exception=handler_exception)
            elif strategy == "id":
                element = self.find_element_by_id(value,handler_exception=handler_exception)
            elif strategy == "class":
                element = self.find_element_by_class_name(value,handler_exception=handler_exception)
            elif strategy == "xpath":
                element = self.find_element_by_xpath(value,handler_exception=handler_exception)
            else:
                element=self.find_element(strategy, value)
            return element
        except WebDriverException,e:
            return False
        finally:
            self.implicitly_wait(self._default_time)#回归基本查找时间,这个很重要





    def swipeTo_Element(self, strategy, value, swipe_strategy="up", maxtime=30):
        """
        :param strategy:通过某种策略寻找，比如"id","name","xapth".....
        :param value: 策略对应的值
        :param maxtime:最大寻找时间，超时不再寻找
        :return: 成功找到返回该元素找不到报错
        """
        # strategy如下:
        # "id"
        # "xpath"
        # "link text"
        # "partial link text"
        # "name"
        # "tag name"
        # "class name"
        # "css selector"
        # usage:driver.swipeTo_Element("name","选择行业")
        try:
            self.implicitly_wait(3)
            if swipe_strategy == "up":
                swipe_fuc = self.swipeToUp
            elif swipe_strategy == "down":
                swipe_fuc = self.swipeToDown
            else:
                raise TypeError("滑动类型错误")
            start_time = time.time()
            end_time = start_time + maxtime
            while True:
                try:
                    if strategy == "name":
                        element = self.find_element_by_name(value)
                    elif strategy == "id":
                        element = self.find_element_by_id(value)
                    elif strategy == "xpath":
                        element = self.find_element_by_xpath(value)
                    else:
                        raise TypeError("类型错误")
                    return element
                except NoSuchElementException:
                    current_page = self.page_source#没有滑动之间的page_source
                    swipe_fuc(1000)
                    after_swipe_page = self._waitting_swipe_stable()  # 等待页面元素稳定
                    if after_swipe_page in current_page:
                        message = "已滑动到底部，未发现策略为:{}，value为:{}的元素".format(strategy, value)
                        raise NoSuchElementException(message)
                if time.time() > end_time:
                    raise NoSuchElementException(
                        "已滑动查找{}s，未发现策略为:{}，value为:{}的元素".format(time.time() - start_time, strategy, value))
        finally:
            self.implicitly_wait(self._default_time)

    def swipeToDown(self, during=1000):
        '''
        向下滑动
        :param during: 持续多长时间
        :return:
        '''
        swipe_cmd = "adb -s %s shell input swipe %d %d %d %d %d" % (
        self.udid, self.phone_size[0] /2, self.phone_size[1] * 1 /4, self.phone_size[0] / 2,
        self.phone_size[1] * 3/4, during)
        os.popen(swipe_cmd)

    def swipeToUp(self, during=1000):
        '''
        向上滑动
        :param during: 持续多长时间
        :return:
        '''
        swipe_cmd = "adb -s %s shell input swipe %d %d %d %d %d" % (
        self.udid, self.phone_size[0] / 2, self.phone_size[1] * 3 / 4, self.phone_size[0] / 2,
        self.phone_size[1] * 1 / 4, during)
        os.popen(swipe_cmd)


    def tap_android(self,coordinata_x,coordinata_y):
        '''
        点击某个坐标点
        :param coordinata_x: x坐标
        :param coordinata_y: y坐标
        :return:
        '''
        try:
            return self.execute("tap_android",{"x":coordinata_x,"y":coordinata_y})["value"]
        except WebDriverException:
            pass

    def swipe_android(self, start_x, start_y, end_x, end_y):
        '''
        滑动手机
        :param start_x: 开始x坐标
        :param start_y:开始y坐标
        :param end_x:结束x坐标
        :param end_y:结束y坐标
        :return:
        '''
        try:
            self.execute("swipe",{"startX":start_x,"startY":start_y,"endX":end_x,"endY":end_y,"steps":2})
        except WebDriverException:
            time.sleep(0.1)



    def _waitting_swipe_stable(self):
        """
        页面在滑动的过程中,页面是动态改变的，为了确定获取元素的坐标准确性,等待页面静止
        :return:
        """
        max_time = time.time() + 5
        while True:
            page_source_1 = self.page_source  # 在页面停止滑动前的信息
            time.sleep(0.5)
            page_source_2 = self.page_source
            if page_source_1 == page_source_2:
                return page_source_2
            if time.time() > max_time:
                return page_source_2

    def _find_element(self,strategy,selector):

        """
        'Private' method used by the find_element_by_* methods.

        :Usage:
            Use the corresponding find_element_by_* instead of this.

        :rtype: WebElement
        """
        return self.execute("findElement", {
            'strategy': strategy,
            'selector': selector,
            "context":"",
            "multiple":False
            })['value']

    def _find_elements(self, strategy, selector):

        """
        'Private' method used by the find_elements_by_* methods.

        :Usage:
            Use the corresponding find_element_by_* instead of this.

        :rtype: WebElement
        """
        return self.execute("findElements", {
            'strategy': strategy,
            'selector': selector,
            "context": "",
            "multiple":True
        })['value']

    def _add_newCommands(self):
        self.command_executor._commands["tap_android"] = \
            ('POST', '/session/$sessionId/appium/tap')
        self.command_executor._commands["swipe"] = \
            ('POST', '/session/$sessionId/touch/perform')
        self.command_executor._commands["element_displayed"]=\
            ("GET","/session/$sessionId/element/$element/attribute/displayed")
if __name__ == '__main__':
    device_udid="a2eae255"
    try:
        demo = Remote(9100, device_udid)
        print demo.page_source
    finally:
        os.popen("adb -s %s shell am force-stop io.appium.uiautomator2.server" % device_udid)











