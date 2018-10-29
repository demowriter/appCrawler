#coding=utf-8
'''
some public class or fuction
'''
import os
import logging
dir_path=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))#工程根目录

def push_handler_file(udid,handler_file_file_path):
    os.popen("adb -s %s push %s /data/local/tmp/"%(udid,handler_file_file_path))
    logging.info("导入处理弹框文件成功...")

def install_uiautomator2_apk(udid):
    '''
    安装uiautomator2的apk包
    :param udid:
    :return:
    '''
    if "uiautomator2.server" not in os.popen("adb -s %s shell pm list package -3|grep uiautomator2.server|grep -v test"%udid).read():
        logging.info("检测到没有安装uiautomator2_server尝试安装apk")
        server_apk_path = os.path.join(dir_path,"apk","appium-uiautomator2-server.apk")
        os.popen("adb -s %s install %s"%(udid,server_apk_path))

    if "uiautomator2.server.test" not in os.popen(
                    "adb -s %s shell pm list package -3|grep uiautomator2.server.test" % udid).read():
        logging.info("检测到没有安装uiautomator2_server_test尝试安装apk")
        server_test_apk_path = os.path.join(dir_path, "apk","appium-uiautomator2-server-debug-androidTest.apk")
        os.popen("adb -s %s install %s" % (udid, server_test_apk_path))

def install_unicode_apk(udid):
    if "io.appium.android.ime" not in os.popen("adb -s %s shell pm list package -3|grep io.appium.android.ime" % udid).read():
        logging.info("检测到没有安装appium输入法尝试安装apk")
        server_apk_path = os.path.join(dir_path, "apk", "UnicodeIME-debug.apk")
        os.popen("adb -s %s install %s" % (udid, server_apk_path))