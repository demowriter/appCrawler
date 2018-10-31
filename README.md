# appCrawler

# 使用方法：
## 1. 首先安装依赖的几个包
pip install -r requirements.txt   （注意python的版本用pip或者pip3）

## 2.修改config.yaml中的一些配置选项
其中的一些配置可能您用不到，适当删除或添加，其中init_craw是要主要注意的。
package_name：测试app的包名

activity_name：启动activity的名称

main_page_xpath：app的主页一般就是首页  用唯一的xpath标识出来

access_main_page：重启app后如何进入主页


设计main_page_xpath和access_main_page的策略原因?

我们的app启动时的页面是服务器控制的，也就是随机的。所以我有必要指引他的开始遍历点

如果你的app是固定的启动到某个页面可不必填写！

# 运行

python craw.py crtl+c或者遍历完会有相关截图和生成思维导图