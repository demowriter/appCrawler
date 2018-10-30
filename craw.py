#coding=utf-8
import os
import sys
dir_path=os.path.dirname(os.path.abspath(__file__))#工程根目录
sys.path.append(dir_path)
os.chdir(dir_path)
import re
import time
from common_module import touchpal_driver as  webdriver
from common_module.genarate_mind_report import cread_mind_report
from common_module.common import *
from selenium.common.exceptions import WebDriverException
import copy
import subprocess
import tempfile
import logging
import threading
import lxml
from lxml import etree
from common_module.touchpal_element import Touchpal_weblement
from  initialize_parameter import *
from collections import OrderedDict
activity_pattern=re.compile("(\S+/\S+)")
digit_pattern=re.compile(r"\d*[\+,\d]$")
class Graph(object):
    def __init__(self,driver,udid):
        self.udid=udid
        self.node_neighbors =OrderedDict()
        self.driver=driver
        self.wsize=self.driver.phone_size#记录Android phone的size方便后续截图
        self.find_new_node=True
        self.visited =[]
        self.root_list=[]
        self.gray_activity_record = {}  # 记录遍历过程中灰activity的次数
        self.gray_activity_traverse_iteself_time = {}  #记录灰activity在自身activity遍历的次数
        self.caputure_onlyone_record={}#白名单acitivity中只抓取一次的记录
        self.need_scrolled_xpath_record={}#避免在需要滚动的页面点击一个button后，多次滚动查找,判断只滚动一次
        self.traverse_route={}#node与click_path隐射
        self.already_find_node=[]
        self.access_root_error_record={}#记录没有找到某个node对应的次数
        self.traverse_track_record=set()#遍历路径记录
        self.new_nodes=True
        self.first_root_node=None
        self.last_page_source=None
    def adb_minicap(self,pic_save_path):
        '''
         capture screen with minicap
         如果提供了截图保存路径则把截图保存到相应路径中
        https://github.com/openstf/minicap
        :param pic_save_path:截图保存路径
        :param scale: 缩放标准
        :return:
        '''
        remote_file = tempfile.mktemp(dir='/data/local/tmp/', prefix='minicap-', suffix='.jpg')
        w, h, r =self.wsize[0],self.wsize[1], 0

        params = '{x}x{y}@{rx}x{ry}/{r}'.format(x=w, y=h, rx=int(w * 1), ry=int(h * 1), r=r * 90)
        try:
            screenshot_shell_list = ['adb', '-s',self.udid, 'shell', 'LD_LIBRARY_PATH=/data/local/tmp',
                                     '/data/local/tmp/minicap', '-s', '-P', params, '>', remote_file]

            subprocess.Popen(screenshot_shell_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE).wait()
            pull_shell_cmd = "adb -s {} pull {} {}".format(self.udid, remote_file, pic_save_path)
            os.popen(pull_shell_cmd)
        finally:
            remove_shell_cmd = "adb -s {} shell rm -rf {}".format(self.udid, remote_file)
            os.popen(remove_shell_cmd)

    def init_Graph(self):
        if not xpath_listView_element:
            raise  TypeError("xpath_listView_element must have values！！！")
        if not xpath_unRecyclerView_element:
            raise  TypeError("xpath_unRecyclerView_element must have values！！！")
        if package_name not in os.popen("adb -s %s shell pm list package -3|grep '%s'"%(self.udid,package_name)).read():
            raise RuntimeError("手机里并没有装有package_name：%s的包！！！"%package_name)
        for each_gray_xpath_str in caputure_onlyone_on_whitePage:#初始化在白名单只抓取一次的状态
            self.caputure_onlyone_record[each_gray_xpath_str]=False
        for each_need_scrolled_xpath in need_scrolled_page_xpath:#初始化符合滚动xpath页面只抓取一次的状态
            self.need_scrolled_xpath_record[each_need_scrolled_xpath]=False
        logging.info("启动app，并初始化页面")
        os.popen("adb -s %s shell am start -S  -W  %s/%s"%(self.udid,package_name,activity_name))#启动activiy
        if main_page_xpath and not self.driver.whether_element_displayed("xpath",main_page_xpath):#如果提供了初始页面则确保处于callog页面
            self.driver.find_element_by_xpath(access_main_page).click()#点击回到初始页面
            time.sleep(3)  # 等待可能出现的弹框
        main_page_node=self.find_all_clickables("")
        self.root_list=main_page_node#遍历的根list
        self.add_nodes(main_page_node)#加入root node
        for each_node in main_page_node:
            self.traverse_route[each_node]=each_node#加入路径
            self.already_find_node.append(each_node)#加入已遍历完的list

    def add_nodes(self, nodelist):
        for node in nodelist:
            if node not in self.nodes():
                self.node_neighbors[node]=[]

    def add_edge(self,edge):
        u, v = edge
        if (u!=v):
            if v not in self.node_neighbors[u]:
                self.node_neighbors[u].append(v)

    def nodes(self):
        return self.node_neighbors.keys()


    def add_trace(self,new_nodes,node):
        for each_node in new_nodes:
            self.traverse_route[each_node]=self.traverse_route[node]+"--->"+str(each_node)

    def find_all_clickables(self,activity_before_click):
        '''
        取得一个页面所有合法的节点
        :return:
        '''
        node_on_activity =[]
        current_package_name,activity_identification=self.get_current_activity().split("/")
        if package_name not in current_package_name:#检测app包名
            logging.warn("package:%s为非遍历的app，跳过寻找新的node..."%activity_identification)
            self._reback_to_app()
            return []
        elif self._judge_black_activity(activity_identification):#检测黑名单activity
            logging.warn("当前activity:%s为黑名单activity，跳过寻找新的node..."%activity_identification)
            return []
        elif (activity_identification not in white_activity_name):#检测灰名单activity
            if self._judge_gray_activity(activity_before_click,activity_identification):
                return []
        current_page_source = self.get_page_source()#获取当前page_source
        if not current_page_source:
            logging.warn("获取当前页面page_source失败")
            return []
        if self.last_page_source==current_page_source:#如果当前页面和上一个页面相同即ui不发送变化
            logging.warn("ui没有发送变化放弃新的node")
            return []
        node_on_activity.extend(self._get_legal_element_url(current_page_source,activity_identification))#加入node list
        if self._judge_need_scroll(current_page_source):#如果需要滚动查找，滚动元素(为了逻辑简单目前只滚动一次)
            logging.info("当前页面需要滚动查找元素遍历...")
            self.driver.swipeToUp()#上滑
            time.sleep(0.5)#等待0.5S
            current_page_source = self.get_page_source()  #滚动后重新获取当前page_source
            node_after_scroll=self._get_legal_element_url(current_page_source,activity_identification)
            node_on_activity.extend(node_after_scroll)#加入滚动后的元素集合
            node_on_activity=["scrolled&"+each_node for each_node in node_on_activity]#加入需要滚动查找的标识
        else:
            node_on_activity=["noscrolled&"+each_node for each_node in node_on_activity]#加入不需要滚动查找的标识
        self.last_page_source=current_page_source#赋值给last_page_source
        return node_on_activity



    def click_element(self,node_name):
        scroll_flag,attribute_identification, activity_identification, coordination_message=node_name.split("&")
        if "com." in attribute_identification and ":id" in attribute_identification:#说明匹配了id
            strategy="id"
        else:
            strategy="name"
        element = self.driver.whether_element_displayed(strategy, attribute_identification, 2)
        if element:  # 如果存在改元素点击
            x,y=coordination_message.split("_")
            self.driver.tap_android(x,y)#点击相应的坐标
        else:
            raise WebDriverException("can not find %s using %s"%(attribute_identification,strategy))

    def find_click_path(self,original_setp):
        '''
        找到点击的最佳路径
        :param original_setp:
        :return:
        '''
        before_reverse=copy.deepcopy(original_setp)
        max_loop_time=len(before_reverse)
        def reback_path(step_name):
            for num,each_step_name in enumerate(before_reverse):
                if each_step_name==step_name:
                    return before_reverse[num:]
        original_setp.reverse()#反转original_setp
        loop_start_num=0
        while True:
            current_acitivity=self.get_current_activity().split("/")[1]
            for each_step_click in original_setp:#检测当前step中每个node，找到则返回路径
                if self._judge_node_name_on_current(each_step_click,current_acitivity):
                    return (True,reback_path(each_step_click))
            if ".hometown.FancyBrowserVideoActivity" in current_acitivity:
                self._press_back_on_hometown()#老乡圈的播放界面需要双击
            else:
                self._press_back_button()#按返回键继续寻找
            loop_start_num=loop_start_num+1
            if loop_start_num>=max_loop_time:
                logging.warn("寻找最佳路径失败...")
                break
        return (False,before_reverse)


    def depth_first_search(self):
        order = []
        try:
            def dfs(node):
                each_node_name = ""
                try:
                    click_path = self.traverse_route[node]
                    logging.info("the element path will click is :" + click_path)
                    clcik_step = click_path.split("--->")
                    if time.time()-self.traverse_start_time>traverse_max_time:
                        logging.info("超时...")
                        return 0
                    if len(clcik_step)>traverse_depth:#点击的路径deeply大于4层，不再寻找新的node
                        logging.warn("已经深入到%s层了,不产生新的"%traverse_depth)
                        self.find_new_node=False
                    else:
                        self.find_new_node=True
                    find_reasonable_result,reasonable_path=self.find_click_path(clcik_step)
                    if not find_reasonable_result:#如果没有找到合适的快捷路径
                        self._check_main_page()#检测是否为主页面
                    else:
                        logging.info("最佳路径寻找成功,路径为:"+"--->".join(reasonable_path))
                    activity_before_click=self.get_current_activity().split("/")[1]#获取点击前的activity
                    for each_node_name in reasonable_path:
                        self.click_element(each_node_name)
                    self.traverse_track_record.add(click_path)
                    if self.find_new_node:
                        new_nodes = self.find_all_clickables(activity_before_click)
                        if len(new_nodes) > 0:
                            self.add_nodes(new_nodes)
                            self.add_trace(new_nodes, node)
                            for each_node in new_nodes:
                                self.add_edge((node, each_node))
                        time.sleep(0.5)#如果找寻了新的node,为截图停留较短的时间
                    else:
                        time.sleep(1)#如果没有找新的node,为截图停留较长的时间
                    if screen_shot_flag:
                        self.adb_minicap(screen_shot_path + self._handler_click_path(click_path))#minicap快速截图
                except WebDriverException,e:
                    ####对不能正常点击的node做一个记录方便后续出错处理#######
                    if each_node_name not in self.access_root_error_record:
                        self.access_root_error_record[each_node_name]=1
                    else:
                        self.access_root_error_record[each_node_name] =self.access_root_error_record[each_node_name]+1
                    logging.error(e.msg)
                    if self.access_root_error_record[each_node_name]>node_max_error_time:#如果寻找某个node的错误过多说明该node可能是个动态的控件(toast或者某些特别操作才能出来)我们修改下面的所有的控件为已访问节省遍历时间
                        logging.warn("node:%s已经超过%s次无法找到控件，判断为动态控件放弃遍历其生产的节点...."%(each_node_name,node_max_error_time))
                        for child_node_on_each_node_name in self.node_neighbors[each_node_name]:
                            self.visited.append(child_node_on_each_node_name)
                except Exception,e:
                    logging.error(e.message)
                finally:
                    self.visited.append(node)
                    order.append(node)
                for n in self.node_neighbors[node]:
                    if not n in self.visited:
                        dfs(n)
            self.traverse_start_time=time.time()#开始时间
            if self.first_root_node:
                dfs(self.first_root_node)
            else:
                dfs(self.root_list[0])
            for node in self.nodes():
                if not node in self.visited:
                    dfs(node)
        except Exception,e:
            logging.error(e.message)
            raise RuntimeError(e.message)
        except KeyboardInterrupt:
            logging.info("停止遍历....")
        finally:
            cread_mind_report(self.traverse_track_record,"")
            return order



    def get_current_activity(self):
        '''
        返回一个稳定的当前activity
        :param udid:
        :return:
        '''
        return activity_pattern.search(os.popen("adb -s %s shell dumpsys window windows |grep 'mFocusedApp='" % self.udid).read()).group(1)



    def get_page_source(self):
        '''
        获取当前页面稳定的page_source
        :return:
        '''
        max_time = time.time()+5
        page_source_2 = None
        while time.time() < max_time:
            page_source_1 = page_source_2 or self._get_illegal_source()  # 在页面停止滑动前的信息
            time.sleep(0.5)
            page_source_2 = self._get_illegal_source()
            if page_source_2 and (page_source_1 == page_source_2):
                return page_source_2
        return page_source_2

    def _get_illegal_source(self):
        '''
        获取当前页面合理的page_source
        :return:
        '''
        max_time = time.time()+10  # 最大获取page_source时间
        while True:
            page_source = self.driver.page_source.encode("utf-8")
            if "正在加载" not in page_source:
                if self._check_page_souce(page_source):
                    return page_source
            if time.time() > max_time:
                return None

    def _check_page_souce(self, page_source):
        '''
        检测当前page_source是否合法
        :param page_source:
        :return:
        '''
        while True:
            for each_xpath in illegal_xpath_handle_by_monitor:  # 遍历列出来的不合法page_source xpath
                element=self.driver.create_element_by_xpath(each_xpath, page_source)
                if element:
                    logging.info("含有非法的illegal_xpath")
                    element.click()
                    return False
            for each_xpath, handler_function_str in illegal_xpath_handle_yourself.items():
                if self.driver.judge_element_by_xpath(each_xpath.encode("utf-8"), page_source):  # 如果配置该xpath
                    handler_function = eval(handler_function_str)  # 拿到真正的函数体
                    handler_function(self)  # 传递参数
                    return False
            return True



    def _get_legal_element_url(self,current_page_source,activity_identification):
        '''
        根据当前page_source发现所有合法的遍历node
        :param current_page_source:
        :param activity_identification:
        :return:
        '''
        black_pattern_xpath_str, judge_black_xpath_result = self._judge_black_xpath_str_onPage(current_page_source)  # 检测当前页面是否含有黑名单xpath str
        if judge_black_xpath_result:
            logging.warn("当前的activity：%s,含有black_xpath_str:%s，放弃寻找新的node" % (activity_identification, black_pattern_xpath_str))
            return []
        if activity_identification in white_activity_name:  # 如果是白名单activity判断caputure_onlyone_on_whitePage中只寻找一次控件的逻辑
            match_caputure_onlyone_xpath, judge_caputure_onlyone_result = self._judge_caputure_onlyone_logic(current_page_source)
            if judge_caputure_onlyone_result:
                logging.warn("白名单activity：%s,含有caputure_onlyone_xpath:%s，放弃再一次寻找新的node" %(activity_identification, match_caputure_onlyone_xpath))
                return []
        black_attribute_collect = self.collect_black_attribute_by_xpath(current_page_source)  # 利用balck xpath str动态取得的id与text包含坐标信息的黑名单集合
        element_url_on_activity = []
        ################进入到真正获取元素的主题#############
        all_legal_element=[]
        for each_white_xpath in white_xpath:
            all_legal_element.append(self.driver.create_elements_by_xpath(each_white_xpath,current_page_source))#遍历白名单中的xpath
        all_legal_element = self.driver.create_elements_by_xpath(xpath_listView_element, current_page_source)
        all_legal_element.extend(self.driver.create_elements_by_xpath(xpath_unRecyclerView_element, current_page_source))
        #############遍历所有element对象##########
        for each_element in all_legal_element:
            try:
                element_height_width=each_element.element_height_width()
                if element_height_width["width"]<element_min_width and element_height_width["height"]<element_min_height:
                    logging.info("元素的宽度和高度太小，忽略遍历")
                    continue
                attribute_identification = each_element.get_attribute("text").encode("utf-8")  # 拿到text属性标识
                if attribute_identification:
                    if attribute_identification in black_text:  # 过滤黑名单text
                        logging.info("过滤黑名单text:%s" % attribute_identification)
                        continue
                    coordinate_identification = each_element.element_centre_coodination_str()#element中心坐标标识
                    black_text_attribute_dict = dict(black_attribute_collect["text"])
                    if attribute_identification+"&"+coordinate_identification in black_text_attribute_dict:  # 过滤由黑名单xpath生成的黑名单text
                        logging.info("过滤黑名单xpath:%s" % black_text_attribute_dict[attribute_identification+"&"+coordinate_identification])
                        continue
                    if digit_pattern.match(attribute_identification):
                        logging.info("过滤掉以数字开头的text:%s" % attribute_identification)
                        continue
                else:
                    attribute_identification = each_element.get_attribute("resourceId").encode("utf-8")  # 拿到id属性标识
                    if attribute_identification in black_id:  # 过滤黑名单id
                        logging.info("过滤黑名单id:%s" % attribute_identification)
                        continue
                    coordinate_identification = each_element.element_centre_coodination_str()#element中心坐标标识
                    black_id_attribute_dict = dict(black_attribute_collect["id"])  # 过滤由黑名单xpath生成的黑名单id
                    if attribute_identification+"&"+coordinate_identification in black_id_attribute_dict:
                        logging.info("过滤黑名单xpath:%s" % black_id_attribute_dict[attribute_identification+"&"+coordinate_identification])
                        continue
                each_element_url = attribute_identification + "&" + activity_identification + "&" + coordinate_identification
                if each_element_url not in self.already_find_node:
                    element_url_on_activity.append(each_element_url)
                    self.already_find_node.append(each_element_url)  # 加入已经发现element_url
            except WebDriverException, e:
                logging.error("find_all_clickables中出现错误:" + e.msg)

        return element_url_on_activity



    def _handler_click_path(self,orignal_click_path):
        orignal_click_path=str(orignal_click_path).replace("%s:id/"%package_name,"")#替换有id/标识
        orignal_click_path=orignal_click_path.split("--->")
        return "click-"+"-".join([each_item.split("&")[1] for each_item in orignal_click_path])+".jpg"



    def _judge_node_name_on_current(self,node_name,current_acitivity):
        '''
        校验当前页面是否完全匹配node_name
        :param node_name:
        :param current_acitivity:
        :return:
        '''
        scroll_flag,attribute_identification,activity_identification,coordination_message = node_name.split("&")# 拿到属性名称和activity
        scroll_flag=True if scroll_flag=="scrolled" else False
        if current_acitivity==activity_identification:#如果当前activiy与activity_identification相同,判断attribute_identification
            if "com." in attribute_identification and ":id" in attribute_identification:#说明匹配了id
                result=self.check_element_quickly("id",attribute_identification,coordination_message,scroll_flag)
            else:
                result =self.check_element_quickly("name",attribute_identification,coordination_message,scroll_flag)
            if result:
                return True

    def _check_main_page(self):
        if main_page_xpath:#如果提供了主界面的校验xpath
            os.popen("adb -s %s shell am start %s/%s" %(self.udid,package_name,activity_name))  # 防止多次back误回退到桌面重新再次启动
            if self.driver.whether_element_displayed("xpath",main_page_xpath):
                return True
            else:
                phone_tab = self.driver.whether_element_displayed("xpath",access_main_page,2)
                if phone_tab and self.get_current_activity() == "%s/%s"%(package_name,activity_name):  # 如果电话tab可见点击电话tab
                    phone_tab.click()
                else:
                    logging.error("app回到主界面失败,尝试kill app重新启动...")
                    os.popen("adb -s %s shell am start -S  -W  %s/%s" %(self.udid,package_name,activity_name))
                    if self.driver.whether_element_displayed("xpath",main_page_xpath):# 如果提供了初始页面则确保处于callog页面
                        self.driver.find_element_by_xpath(access_main_page).click()  # 点击回到初始页面
        else:#直接重启进入app主界面
            os.popen("adb -s %s shell am start -S  -W  %s/%s" %(self.udid,package_name,activity_name))

    def _press_back_button(self):
        '''
        按返回键
        :return:
        '''
        os.popen("adb -s %s shell input keyevent 4" % self.udid)  # back


    def _press_back_on_hometown(self):
        '''
        老乡圈界面快速点击2次返回
        :return:
        '''
        def click_back_twice(i):
            time.sleep(i/2)
            os.popen("adb -s %s shell input keyevent 4" % self.udid)  # back
        targets=[threading.Thread(target=click_back_twice,args=(i,))for i in range(2)]
        for each_target in targets:
            each_target.start()

    def _reback_to_app(self):
        ''''
        返回到当前app
        '''
        for i in range(3):
            self._press_back_button()
            if self.get_current_activity().split("/")[0]==package_name:
                return True
        self._check_main_page()#校验主界面




    def _judge_need_scroll(self,current_page_source):
        for each_need_scrolled_xpath in need_scrolled_page_xpath:
            if self.driver.judge_element_by_xpath(each_need_scrolled_xpath,current_page_source):#如果发现匹配
                if self.need_scrolled_xpath_record[each_need_scrolled_xpath]:
                    logging.info("滚动页面已滚动查找过,放弃再次滚动查找....")
                    return False
                self.need_scrolled_xpath_record[each_need_scrolled_xpath]=True#重置标志位
                return True
        return False


    def _judge_black_activity(self,activity_identification):
        '''
        当前activity包含黑名单中给定的activity返回True
        :param activity_identification:
        :return:
        '''
        for each_black_activity in black_activity_name:
            if each_black_activity.lower() in activity_identification.lower():
                return True
        return False


    def _judge_gray_activity(self,activity_before_click,activity_identification):
        '''
        校验灰名单activity
        :param activity_identification:
        :return:
        '''
        if activity_before_click != activity_identification:  # 如果灰名单activity在点击之前与点击之后相同,应该是在同一页面点击的结果
            if activity_identification not in self.gray_activity_record:
                self.gray_activity_record[activity_identification] = 1
            else:
                self.gray_activity_record[activity_identification] = self.gray_activity_record[activity_identification] + 1
            if self.gray_activity_record[activity_identification] > gray_activity_max_traverse:
                logging.warn("当前灰名单activity:%s为已经寻找过%s次跳过寻找新的node..." % (activity_identification, gray_activity_max_traverse))
                return True
        else:
            if activity_identification not in self.gray_activity_traverse_iteself_time:
                self.gray_activity_traverse_iteself_time[activity_identification] = 1
            else:
                self.gray_activity_traverse_iteself_time[activity_identification] =self.gray_activity_traverse_iteself_time[activity_identification] + 1
            if self.gray_activity_traverse_iteself_time[activity_identification] > gray_activity_max_traverse_itself:
                logging.warn("当前灰名单activity:%s在自身activity已经寻找过%s次跳过寻找新的node..."%(activity_identification, gray_activity_max_traverse_itself))
                return True
        return False

    def _judge_black_xpath_str_onPage(self, current_page_source):
        '''
        当前page_source含有某black_xpath_str,含有则返回true
        :param activity_identification:
        :return:
        '''
        for each_black_xpath_str in judge_black_page_by_xpath:
            if self.driver.judge_element_by_xpath(each_black_xpath_str,current_page_source):
                return (each_black_xpath_str,True)
        return ("",False)

    def _judge_caputure_onlyone_logic(self, current_page_source):
        '''
        当前白名单的activity中是是否已经寻找过一次caputure_onlyone_on_whitePage，如果没有寻找返回flase,已经找过一次了返回true(表示当前页面放弃寻找新的控件)
        :param activity_identification:
        :return:
        '''
        for each_caputure_onlyone_xpath in self.caputure_onlyone_record.keys():
            if self.driver.judge_element_by_xpath(each_caputure_onlyone_xpath,current_page_source):#如果当前页面含有此xpath_str
                if self.caputure_onlyone_record[each_caputure_onlyone_xpath]==False:#说明是第一次匹配到 xpath_str
                    self.caputure_onlyone_record[each_caputure_onlyone_xpath]=True#改变标志位为True
                    return ("",False)
                else:
                    return (each_caputure_onlyone_xpath, True)
        return ("",False)

    def collect_black_attribute_by_xpath(self,current_page_source):
        '''
        利用backlist_element中给定的黑名单xpath_str转换成id与text包含坐标信息的集合
        为什么要包含坐标？当我们用id或者text标识一个element时，如果页面上存在多个相同的id和text那么就得用坐标来区分，对每一个合法的元素
        过滤
        :param current_page_source:
        :return:{"text":[],"id":[]}
        '''
        black_attribute_collect={"text":[],"id":[]}#利用black xpath str手机相关的text与id黑名单集合
        for each_black_xpath_str in black_xpath:#遍历黑名单的xpath
            match_element=self.driver.create_element_by_xpath(each_black_xpath_str,current_page_source)#寻找touchpal_element
            if match_element:
                each_black_text_attribute=match_element.get_attribute("text").encode("utf-8")#利用touchpal_element取得text属性
                each_black_id_attribute = match_element.get_attribute("resourceId").encode("utf-8")#利用touchpal_element取得id属性
                coodination_str=match_element.element_centre_coodination_str()#获取坐标信息
                if each_black_text_attribute:
                    black_attribute_collect["text"].append((each_black_text_attribute+"&"+coodination_str,each_black_xpath_str))#加入text黑名单集合
                if each_black_id_attribute:
                    black_attribute_collect["id"].append((each_black_id_attribute+"&"+coodination_str,each_black_xpath_str))#加入id黑名单集合
        return black_attribute_collect

    def check_element_quickly(self,strategy,value,coordination_message,scroll_flag):
        '''
        暂时没有用到  备用
        :param strategy:
        :param value:
        :param scroll_flag:
        :return:
        '''
        if strategy == "name":
            xpath_str = ".//*[@text='%s']" % value
        elif strategy == "id":
            xpath_str = ".//*[@resource-id='%s']" % value
        else:
            raise TypeError("strategy不合法")
        after_swipe_page = None
        max_find_time = time.time()+10
        find_time=0
        cannot_swipe_num = 0
        while time.time() < max_find_time:
            before_swipe_page = after_swipe_page or self.get_page_source()  # 开始滑动的page_source
            try:
                xml_source = etree.XML(before_swipe_page)
                all_pattern_result = xml_source.xpath(xpath_str.decode("utf-8"))  # 一定要转换成unicode编码,免得中文不识别
            except lxml.etree.XMLSyntaxError:  # 处理解析出错的异常
                all_pattern_result = []
            except Exception, e:
                raise WebDriverException(e.message)
            if len(all_pattern_result) > 0:  # 如果发现了元素
                if scroll_flag==False:#校验坐标信息
                    for each_pattern in all_pattern_result:
                        if Touchpal_weblement(each_pattern,self.udid).element_centre_coodination_str()==coordination_message:
                            return True
                return True#滚动考虑偏差不校验坐标
            if scroll_flag:  # 如果滑动
                if cannot_swipe_num == 0:  # 没有触发不能滑动时,开始时上滑
                    logging.info("上滑")
                    self.driver.swipeToUp()  # 上滑
                elif cannot_swipe_num == 1:  # 触发不能滑动时,说明第一次已经滑动到底部没找到,下滑再找一次
                    logging.info("下滑")
                    self.driver.swipeToDown()  # 下滑
                after_swipe_page = self.get_page_source()
                if after_swipe_page in before_swipe_page:  # 说明已经不能再滑动了
                    cannot_swipe_num = cannot_swipe_num + 1
                if cannot_swipe_num > 1:
                    return False
            else:  # 非滑动查找元素
                find_time += 1
                if find_time > 1:
                    return False
            time.sleep(0.2)
        return False



if __name__ == '__main__':
    device_udid = "a2eae255"
    if device_udid not in os.popen("adb devices").read():
        raise RuntimeError("udid:%s不存在"%device_udid)
    else:
        install_uiautomator2_apk(device_udid)
        install_unicode_apk(device_udid)
        os.popen("adb -s %s shell ime enable io.appium.android.ime/.UnicodeIME"%device_udid)
        os.popen("adb -s %s shell ime set io.appium.android.ime/.UnicodeIME" % device_udid)#启用appium输入法
    try:
        driver = webdriver.Remote(8300,device_udid)
        g = Graph(driver,device_udid)
        g.init_Graph()#初始化Graph对象
        order = g.depth_first_search()
    finally:
        os.popen("adb -s %s shell am force-stop io.appium.uiautomator2.server" %device_udid)
        os.popen("adb -s %s shell am force-stop io.appium.android.ime" % device_udid)