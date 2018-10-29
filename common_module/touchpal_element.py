#coding=utf-8
from appium.webdriver import webelement
import os
import re
location_pattren=re.compile("\[(\d+),(\d+)\].*?\[(\d+),(\d+)\]")#正则表达式匹配元素坐标信息
class WebElement(webelement.WebElement):
    """

    重写appium的WebElment对象

    """

    def click(self):
        params = {}
        params['element'] = self._id
        params['id'] = self._id
        return self._parent.execute("clickElement", params)

    def is_displayed(self):
        params = {}
        params['element'] = self._id
        result=self._parent.execute("element_displayed",params)["value"].encode("utf-8")
        if result=="true":
            return True
        else:
            return False
    def element_centre_coodination_str(self):
        """
        返回element中心坐标字符串标识
        :return:
        """
        centre_x, centre_y=self.centre_location()
        return str(centre_x)+"_"+str(centre_y)

    def centre_location(self):
        """The centre_location of the element ."""
        location_message = self.element_location()
        x_0, y_0, x_1, y_1 = location_message[0][0], location_message[0][1], location_message[1][0], \
                             location_message[1][1]
        centre_x = (x_0 + x_1) / 2
        centre_y = (y_0 + y_1) / 2
        return (int(centre_x),int(centre_y))


    def element_location(self):
        """
        :return: 返回一个元素的左上角坐标与右下角坐标 eg:((0,0),(100,100))
        """

        element_start_location = (self.location["x"], self.location["y"])
        element_size = self.size
        element_end_location = ((element_start_location[0] + element_size["width"]),(element_start_location[1] + element_size["height"]))
        return (element_start_location, element_end_location)


class Touchpal_weblement(object):
    def __init__(self, lxml_etree_Element,udid):
        self.xml_element = lxml_etree_Element  # lxml_etree_Element对象
        self.udid = udid

    def long_click(self,during_time=2):
        centre_x, centre_y = self.centre_location()
        cmd="adb -s %s shell input swipe %s %s %s %s %s"%(self.udid,centre_x,centre_y,centre_x,centre_y,during_time*1000)
        os.popen(cmd)
    def click(self):
        centre_x, centre_y = self.centre_location()
        cmd = "adb -s %s shell input tap %s %s" % (self.udid, centre_x, centre_y)
        os.popen(cmd)

    def send_keys(self,value):
        """
        输入框输入value,目前用系统的输入法只支持英文字符
        :param value:
        :return:
        """
        self.click()#点击该输入框
        cmd = "adb -s %s shell input text %s" % (self.udid,value)
        os.popen(cmd)

    @property
    def text(self):
        """The text of the element."""
        return self.xml_element.get("text")

    def get_attribute(self,attribute_name):
        if attribute_name=="resourceId":
            attribute_name="resource-id"
        return self.xml_element.get(attribute_name)


    def element_height_width(self):
        '''
        获取元素的高度和宽度
        :return:
        '''
        element_locaton = self.xml_element.get("bounds")  # 拿到坐标值格式类似:[0,398][1080,590]
        location_result = location_pattren.search(element_locaton)
        x_0 = int(location_result.group(1))  # 左上角X坐标
        y_0 = int(location_result.group(2))  # 左上角Y坐标
        x_1 = int(location_result.group(3))  # 右下角X坐标
        y_1 = int(location_result.group(4))  # 右下角Y坐标
        return {"width":(x_1-x_0),"height":(y_1-y_0)}

    def element_centre_coodination_str(self):
        """
        返回element中心坐标字符串标识
        :return:
        """
        centre_x, centre_y=self.centre_location()
        return str(centre_x)+"_"+str(centre_y)


    # def element_location_str(self):
    #     '''
    #     返回element左上角与右下角坐标标识字符串x_0_y_0_x_1_y_1
    #     :return: x_0_y_0_x_1_y_1
    #     '''
    #
    #     left_top_corn,right_buttom_corn=self.element_location()
    #     return str(left_top_corn[0])+"_"+str(left_top_corn[1])+str(right_buttom_corn[0])+"_"+str(right_buttom_corn[1])



    def element_location(self):
        '''
        :return:返回一个元素的左上角坐标与右下角坐标 eg:((0,0),(100,100))

        '''
        element_locaton = self.xml_element.get("bounds")  # 拿到坐标值格式类似:[0,398][1080,590]
        location_result = location_pattren.search(element_locaton)
        x_0 = int(location_result.group(1))  # 左上角X坐标
        y_0 = int(location_result.group(2))  # 左上角Y坐标
        x_1 = int(location_result.group(3))  # 右下角X坐标
        y_1 = int(location_result.group(4))  # 右下角Y坐标
        return ((x_0, y_0), (x_1, y_1))

    def centre_location(self):
        """The centre_location of the element ."""
        location_message = self.element_location()
        x_0, y_0, x_1, y_1 = location_message[0][0], location_message[0][1], location_message[1][0], \
                             location_message[1][1]
        centre_x = (x_0 + x_1) / 2
        centre_y = (y_0 + y_1) / 2
        return (int(centre_x),int(centre_y))