from flask import Flask, request, Response
import requests
import re
import urllib.parse
import urllib3
import json

app = Flask(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
base_url = "https://yingshi.co"

def fetch_html(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://yingshi.co/'
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        res.encoding = 'utf-8'
        return res.text
    except:
        return ""

def create_response(data):
    res = Response(json.dumps(data, ensure_ascii=False), mimetype='application/json; charset=utf-8')
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Methods'] = '*'
    res.headers['Access-Control-Allow-Headers'] = '*'
    return res

# 万能路由，兼容 Syncwe 发来的 /api.php/provide/vod
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def catch_all(path):
    if request.method == 'OPTIONS':
        return create_response({})

    # 兼容各类软件的参数传递方式
    ac = request.values.get('ac', 'list')
    wd = request.values.get('wd', '')
    ids = request.values.get('ids', '')

    response_data = {
        "code": 1,
        "msg": "数据获取成功",
        "page": 1,
        "pagecount": 1,
        "limit": 20,
        "total": 0,
        "class": [{"type_id": 1, "type_name": "电影"}],
        "list": []
    }

    # ================= 第一步：搜索列表 =================
    if (ac == 'list' or ac == 'videolist') and wd:
        search_url = f"{base_url}/vodsearch/{urllib.parse.quote(wd)}-------------.html"
        html = fetch_html(search_url)

        name_regex = r'<a href="[^"]*?"><strong>(.*?)</strong></a>'
        url_regex = r'<a href="(.*?)"><strong>.*?</strong></a>'
        pic_regex = r'<img class="lazy lazyload" data-original="(.*?)" alt=".*?" referrerpolicy="no-referrer" src=".*?">'

        names = re.findall(name_regex, html)
        urls = re.findall(url_regex, html)
        pics = re.findall(pic_regex, html)

        if names:
            response_data['total'] = len(names)
            for i in range(len(names)):
                pic = pics[i] if i < len(pics) else ""
                
                # 塞满所有 MacCMS 标准字段，防止 Syncwe 解析崩溃
                response_data['list'].append({
                    "vod_id": urls[i], 
                    "vod_name": names[i],
                    "vod_pic": base_url + pic if pic and not pic.startswith('http') else pic,
                    "type_id": 1,
                    "type_name": "电影", # Syncwe 严格要求必须有分类名
                    "vod_remarks": "点击播放",
                    "vod_time": "2024-01-01", # 凑数时间
                    "vod_play_from": "影视工厂", # 凑数线路
                    "vod_director": "未知",
                    "vod_actor": "未知"
                })
        return create_response(response_data)

    # ================= 第二步：详情播放 =================
    elif ac == 'detail' and ids:
        id_list = [i for i in ids.split(',') if i]
        for vid in id_list:
            detail_url = base_url + vid if vid.startswith('/') else f"{base_url}/{vid}"
            html = fetch_html(detail_url)

            item_name_regex = r'<a class="module-play-list-link" href=".*?" title=".*?"><span>(.*?)</span></a>'
            item_url_regex = r'<a class="module-play-list-link" href="(.*?)" title=".*?"><span>.*?</span></a>'

            ep_names = re.findall(item_name_regex, html)
            ep_urls = re.findall(item_url_regex, html)

            play_list_str = ""
            if ep_names and ep_urls:
                ep_list = []
                for i in range(len(ep_names)):
                    ep_name = ep_names[i]
                    ep_url = base_url + ep_urls[i] if ep_urls[i].startswith('/') else ep_urls[i]
                    ep_list.append(f"{ep_name}${ep_url}")
                play_list_str = "#".join(ep_list)

            # 详情页同样塞满标准字段
            response_data['list'].append({
                "vod_id": vid,
                "vod_name": "视频详情",
                "vod_pic": "",
                "type_id": 1,
                "type_name": "电影",
                "vod_remarks": "高清",
                "vod_time": "2024-01-01",
                "vod_play_from": "yingshi", # 必须有线路名称
                "vod_play_url": play_list_str,
                "vod_content": "暂无简介",
                "vod_director": "未知",
                "vod_actor": "未知"
            })
        return create_response(response_data)

    return create_response(response_data)
