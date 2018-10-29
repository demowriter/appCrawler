#coding=utf-8
import yaml
import os
craw_config=yaml.load(open("config.yaml"))
screen_shot_flag=craw_config["traverse_shot_page"]
screen_shot_path="pic/"#截图路径
node_max_error_time=int(craw_config["node_max_error_time"]) # node节点无法寻找的最大次数超过该次数其产生的节点将放弃遍历
traverse_depth =int(craw_config["traverse_depth"])  #遍历深度
xpath_unRecyclerView_element=craw_config["xpath_unRecyclerView_element"]#非listview的元素
xpath_listView_element=craw_config["xpath_listView_element"]#listview的元素
traverse_max_time = int(craw_config["traverse_max_time"])  # 遍历的最大时长
package_name=craw_config["init_craw"]["package_name"]#app的名称
activity_name=craw_config["init_craw"]["activity_name"]#app的启动activity_name
gray_activity_max_traverse=int(craw_config["gray_activity_max_traverse"])#灰名单进入的最大次数
gray_activity_max_traverse_itself=int(craw_config["gray_activity_max_traverse_itself"])#灰名单进入的最大次数
element_min_height=int(craw_config["element_min_height"])
element_min_width=int(craw_config["element_min_width"])

if craw_config["init_craw"]["main_page_xpath"]:
    main_page_xpath=craw_config["init_craw"]["main_page_xpath"].encode("utf-8")#启动app遍历的一个初始页面
else:
    main_page_xpath=None
if craw_config["init_craw"]["access_main_page"]:
    access_main_page=craw_config["init_craw"]["access_main_page"].encode("utf-8")#如果不在初始页面,点击该按钮能到达初始页面
else:
    access_main_page=None
white_xpath=[]#存放白名单的xpath，当遍历时改列表中的xpath是一定需要去遍历的
white_activity_name=[]#存放白名单activity name（每次进入均寻找相关node)
black_activity_name=[]#存放黑名单activity name（包含的关系,不会去找相关node）
judge_black_page_by_xpath=[]#当前页面含有自定义的xpath_str不会去寻找当前页面node
black_text=[]#黑名单text
black_id=[]#黑名单id
black_xpath=[]#黑名单xpath
need_scrolled_page_xpath=[]#需要滚动当前页面遍历的xpath
caputure_onlyone_on_whitePage=[]#对于白名单的activity也有个限定当白名单activity匹配这些xpath时只遍历一次该白名单acitivity
illegal_xpath_handle_by_monitor=[]#如果当前页面资源匹配到这些资源时uiautomator2 会自动处理掉这些弹框(就是点击)
illegal_xpath_handle_yourself={}#还有一些xpath 不是监听器简单的点击就能处理的或者可能手写其他的逻辑就需要自己手动处理
if craw_config["function"]:
    for each_function_str in craw_config["function"]:
        exec(each_function_str)#初始化功能函数
if craw_config["white_activity"]:
    white_activity_name=[each.encode("utf-8") for each in craw_config["white_activity"]]

if craw_config["black_activity"]:
    black_activity_name=[each.encode("utf-8") for each in craw_config["black_activity"]]

if craw_config["white_xpath"]:
    white_xpath=[each.encode("utf-8") for each in craw_config["white_xpath"]]

if craw_config["judge_black_page_by_xpath"]:
    judge_black_page_by_xpath=[each.encode("utf-8") for each in craw_config["judge_black_page_by_xpath"]]

if craw_config["black_text"]:
    black_text=[each.encode("utf-8") for each in craw_config["black_text"]]

if craw_config["black_id"]:
    black_id=[each.encode("utf-8") for each in craw_config["black_id"]]

if craw_config["black_xpath"]:
    black_xpath=[each.encode("utf-8") for each in craw_config["black_xpath"]]

if craw_config["need_scrolled_page_xpath"]:
    need_scrolled_page_xpath=[each.encode("utf-8") for each in craw_config["need_scrolled_page_xpath"]]

if craw_config["caputure_onlyone_on_whitePage"]:
    caputure_onlyone_on_whitePage=[each.encode("utf-8") for each in craw_config["caputure_onlyone_on_whitePage"]]

if craw_config["illegal_xpath_handle_by_monitor"]:
    illegal_xpath_handle_by_monitor=[each.encode("utf-8") for each in craw_config["illegal_xpath_handle_by_monitor"]]

if craw_config["illegal_xpath_handle_yourself"]:
    illegal_xpath_handle_yourself=craw_config["illegal_xpath_handle_yourself"]
