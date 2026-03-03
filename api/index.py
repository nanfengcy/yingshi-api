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

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
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
        "class": [{"type_id": 1, "type_name": "影视"}],
        "list": []
    }

    # ================= 第一步：搜索列表 =================
    if (ac == 'list' or ac == 'videolist') and wd:
        # 完全遵循你的 searchUrl 模板
        search_url = f"{base_url}/vodsearch/{urllib.parse.quote(wd)}-------------.html"
        html = fetch_html(search_url)

        # 完美照搬你的正则（仅在 * 后面加了 ? 防止 Python 贪婪匹配吃掉整个网页）
        name_regex = r'<a href="[^"]*?"><strong>(.*?)</strong></a>'
        url_regex = r'<a href="(.*?)"><strong>.*?</strong></a>'
        pic_regex = r'<img class="lazy lazyload" data-original="(.*?)" alt=".*?" referrerpolicy="no-referrer" src=".*?">'

        names = re.findall(name_regex, html)
        urls = re.findall(url_regex, html)
        pics = re.findall(pic_regex, html)

        if names:
            response_data['total'] = len(names)
            for i in range(len(names)):
                # 原汁原味提取，不做任何多余的修改
                pic = pics[i] if i < len(pics) else ""
                vod_id = urls[i] # 保持 /voddetail/xxxxx.html 原样，不提取数字

                response_data['list'].append({
                    "vod_id": vod_id, 
                    "vod_name": names[i],
                    "vod_pic": base_url + pic if pic and not pic.startswith('http') else pic,
                    "type_id": 1,
                    "vod_remarks": "点击播放"
                })
        return create_response(response_data)

    # ================= 第二步：详情播放 =================
    elif ac == 'detail' and ids:
        # 此时的 ids 就是上面保持原样的 /voddetail/xxxxx.html
        id_list = [i for i in ids.split(',') if i]
        
        for vid in id_list:
            # 拼出真正的详情页地址
            detail_url = base_url + vid if vid.startswith('/') else f"{base_url}/{vid}"
            html = fetch_html(detail_url)

            # 完美照搬你的 itemNameRegex 和 itemUrlRegex
            item_name_regex = r'<a class="module-play-list-link" href=".*?" title=".*?"><span>(.*?)</span></a>'
            item_url_regex = r'<a class="module-play-list-link" href="(.*?)" title=".*?"><span>.*?</span></a>'

            ep_names = re.findall(item_name_regex, html)
            ep_urls = re.findall(item_url_regex, html)

            play_list_str = ""
            if ep_names and ep_urls:
                ep_list = []
                for i in range(len(ep_names)):
                    ep_name = ep_names[i]
                    # 补全播放页链接
                    ep_url = base_url + ep_urls[i] if ep_urls[i].startswith('/') else ep_urls[i]
                    # 拼接为 Syncwe 需要的格式：集数$链接
                    ep_list.append(f"{ep_name}${ep_url}")
                play_list_str = "#".join(ep_list)

            response_data['list'].append({
                "vod_id": vid,
                "vod_name": "视频详情",
                "vod_play_from": "默认线路",
                "vod_play_url": play_list_str
            })
        return create_response(response_data)

    return create_response(response_data)
