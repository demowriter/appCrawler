# coding=utf-8
import json
import string
import os

traval_num = {"start_num": 0}
element_id_mapping_dict = {}
all_sub_data = [{"id": "root", "isroot": True, "topic": "首页"}]
alread_add = []

html_data = """
<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>jsMind</title>
    <link type="text/css" rel="stylesheet" href="jsmind.css" />
    <style type="text/css">
           html
        {
         height:100%;
         margin:0;
        }
        body
        {
            height:100%;
            margin:0;
        }
        #jsmind_container{
            margin-left: auto;
            margin-right: auto;
            width:100%;
            height:100%;
            border:solid 1px #ccc;
            /*background:#f4f4f4;*/
            background:#f4f4f4;
        }
    </style>
</head>
<body>
<div id="jsmind_container"></div>
<script type="text/javascript" src="http://10.0.20.2:8008/js/jsmind.js"></script>
<script type="text/javascript" src="http://10.0.20.2:8008/js/jsmind.draggable.js"></script>
<script type="text/javascript">
    function load_jsmind(){
        var mind = {
            "meta":{
                "name":"app遍历思维导图",
                "author":"qiang.zhou",
                "version":"0.1",
            },
            "format":"node_array",
            "data":$mind_sub_data

        };
        var options = {
            container:'jsmind_container',
            editable:true,
            theme:'primary',
            "expanded":true,
        }
        var jm = jsMind.show(options,mind);   
    }

    load_jsmind();
</script>
</body>
</html>
"""



def fliter_repeat_sub(every_sub_data):
    if every_sub_data not in alread_add:
        alread_add.append(every_sub_data)
        return True
    else:
        return False


def generate_every_sub(path_track_list):
    for num, each_sub in enumerate(path_track_list, 0):
        sub = {}
        if each_sub not in element_id_mapping_dict:
            sub["id"] = "sub" + str(traval_num["start_num"] + 1)  # 生成主题id
            element_id_mapping_dict[each_sub] = sub["id"]  # 加入到映射关系列表
            traval_num["start_num"] = traval_num["start_num"] + 1  # start_num加一防止id重复
        else:
            sub["id"] = element_id_mapping_dict[each_sub]
        if num == 0:  # 如果num为0说明是一级sub根节点是root
            sub["parentid"] = "root"
        else:  # 寻找自己的父类id
            sub["parentid"] = element_id_mapping_dict[path_track_list[num - 1]]

        _,sub_attru,sub_activity,sub_coordination=each_sub.split("&")
        if "com.cootek.smartdialer:id" in sub_attru:#如果是id去掉com.cootek.smartdialer:id
            sub_attru = sub_attru.split("/")[1]
        if sub_activity.count(".") > 2:#如果activty过长为了展示美观,截取.后的2个str
            sub_activity = "." + ".".join(sub_activity.split(".")[-2:])
        sub["topic"] =sub_attru+"&"+sub_activity # 加入自己的主题
        sub["expanded"]=False
        all_sub_data.append(sub)  # 写入到sub_data中


def generate_mind_map_data(traval_path_track):
    for each_path_track in traval_path_track:
        path_track_list = each_path_track.split("--->")
        generate_every_sub(path_track_list)
    return json.dumps(filter(fliter_repeat_sub, all_sub_data))


def cread_mind_report(traval_path_track, report_path):
    html_report_data = string.Template(html_data).safe_substitute(
        mind_sub_data=generate_mind_map_data(traval_path_track))
    if not os.path.exists(report_path):
        report_path = "."
    with open(report_path + "/mind_report.html", "wb")as f:
        f.write(html_report_data)


