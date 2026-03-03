from flask import Flask, request, Response
import requests
import re
import urllib.parse
import random
import urllib3
import json

app = Flask(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

base_url = "https://yingshi.co"

def fetch_html(url):
    fake_ip = f"{random.randint(11, 250)}.{random.randint(11, 250)}.{random.randint(11, 250)}.{random.randint(11, 250)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://yingshi.co/',
        'X-Forwarded-For': fake_ip,
        'Client-IP': fake_ip
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        res.encoding = 'utf-8'
        return res.text
    except:
        return ""

# 生成带“跨域通行证”的 JSON 响应，防止 App 拦截
def create_response(data):
    res = Response(json.dumps(data, ensure_ascii=False), mimetype='application/json; charset=utf-8')
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Methods'] = '*'
    res.headers['Access-Control-Allow-Headers'] = '*'
    return res

# 兼容 GET、POST 以及 OPTIONS 等所有 App 可能发出的请求方法
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def catch_all(path):
    # App 发送的预检请求，直接放行
    if request.method == 'OPTIONS':
        return create_response({})

    # request.values 能同时兼容 URL 参数(GET)和表单数据(POST)
    ac = request.values.get('ac', 'list')
    wd = request.values.get('wd', '')
    ids = request.values.get('ids', '')
    pg = request.values.get('pg', '1') # 增加页码兼容

    response_data = {
        "code": 1,
        "msg": "数据获取成功",
        "page": int(pg) if pg.isdigit() else 1,
        "pagecount": 1,
        "limit": 20,
        "total": 0,
        "class": [
            {"type_id": 1, "type_name": "电影"},
            {"type_id": 2, "type_name": "电视剧"},
            {"type_id": 3, "type_name": "综艺"},
            {"type_id": 4, "type_name": "动漫"}
        ],
        "list": []
    }

    # === 搜索逻辑 ===
    if (ac == 'list' or ac == 'videolist') and wd:
        # 支持软件的翻页请求
        search_url = f"{base_url}/vodsearch/{urllib.parse.quote(wd)}----------{pg}---.html"
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
                pic_url = pics[i] if i < len(pics) else ""
                if not pic_url:
                    pic_url = "https://via.placeholder.com/150x200.png?text=No+Image"
                elif not pic_url.startswith('http'):
                    pic_url = base_url + pic_url

                raw_url = urls[i]
                vod_id = raw_url
                id_match = re.search(r'/voddetail/(\d+)\.html', raw_url)
                if id_match:
                    vod_id = id_match.group(1)

                response_data['list'].append({
                    "vod_id": vod_id, 
                    "vod_name": names[i],
                    "vod_pic": pic_url,
                    "type_id": 1,
                    "vod_remarks": "点击播放"
                })
        return create_response(response_data)

    # === 详情与播放逻辑 ===
    elif ac == 'detail' and ids:
        id_list = [i for i in ids.split(',') if i]
        for vid in id_list:
            detail_url = f"{base_url}/voddetail/{vid}.html" if vid.isdigit() else (base_url + vid)
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
                    ep_url = base_url + ep_urls[i]
                    ep_list.append(f"{ep_name}${ep_url}")
                play_list_str = "#".join(ep_list)

            response_data['list'].append({
                "vod_id": vid,
                "vod_name": "影视工厂资源",
                "vod_play_from": "默认线路",
                "vod_play_url": play_list_str
            })
        return create_response(response_data)

    return create_response(response_data)
