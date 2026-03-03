from flask import Flask, request, Response
import requests
import re
import urllib.parse
import urllib3
import json
import random

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

def create_response(data):
    res = Response(json.dumps(data, ensure_ascii=False), mimetype='application/json; charset=utf-8')
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Methods'] = '*'
    res.headers['Access-Control-Allow-Headers'] = '*'
    return res

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def catch_all(path):
    if request.method == 'OPTIONS':
        return create_response({})

    ac = request.values.get('ac', 'list')
    wd = request.values.get('wd', '')
    ids = request.values.get('ids', '')
    pg = request.values.get('pg', '1')

    response_data = {
        "code": 1,
        "msg": "数据获取成功",
        "page": int(pg) if pg.isdigit() else 1,
        "pagecount": 999,
        "limit": 20,
        "total": 9999,
        "class": [
            {"type_id": 1, "type_name": "电影"},
            {"type_id": 2, "type_name": "电视剧"},
            {"type_id": 3, "type_name": "综艺"},
            {"type_id": 4, "type_name": "动漫"}
        ],
        "list": []
    }

    # ================= 核心修复：健康检查的“无敌正则”提取法 =================
    if ac == 'list' and not wd and not ids:
        # 直接抓取电影分类第一页，保证结构绝对标准
        target_url = f"{base_url}/vodshow/1--------1---.html"
        html = fetch_html(target_url)
        
        # 先切出每一个视频的大块代码
        blocks = re.findall(r'<a class="module-item"([\s\S]*?)</a>', html)
        
        for block in blocks:
            # 在每个大块里单独提取各个属性，无视它们在 HTML 里的前后顺序
            url_match = re.search(r'href="([^"]+)"', block)
            name_match = re.search(r'title="([^"]+)"', block)
            pic_match = re.search(r'data-original="([^"]+)"', block)
            
            if url_match and name_match:
                url = url_match.group(1)
                name = name_match.group(1)
                pic = pic_match.group(1) if pic_match else ""
                
                pic_url = pic if pic.startswith('http') else base_url + pic
                if not pic_url:
                    pic_url = "https://via.placeholder.com/150x200.png?text=No+Image"
                
                vod_id = url
                id_match = re.search(r'/voddetail/(\d+)\.html', url)
                if id_match:
                    vod_id = id_match.group(1)
                
                response_data['list'].append({
                    "vod_id": vod_id,
                    "vod_name": name,
                    "vod_pic": pic_url,
                    "type_id": 1,
                    "type_name": "电影",
                    "vod_remarks": "高清",
                    "vod_time": "2026-03-03",
                    "vod_play_from": "yingshi",
                    "vod_director": "未知",
                    "vod_actor": "未知"
                })
        return create_response(response_data)

    # ================= 第二步：搜索列表（沿用你验证过的成功正则） =================
    elif (ac == 'list' or ac == 'videolist') and wd:
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
                pic = pics[i] if i < len(pics) else ""
                pic_url = base_url + pic if pic and not pic.startswith('http') else pic
                if not pic_url:
                    pic_url = "https://via.placeholder.com/150x200.png?text=No+Image"

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
                    "type_name": "电影",
                    "vod_remarks": "点击播放",
                    "vod_time": "2026-03-03",
                    "vod_play_from": "yingshi",
                    "vod_director": "未知",
                    "vod_actor": "未知"
                })
        return create_response(response_data)

    # ================= 第三步：详情与播放 =================
    elif ac == 'detail' and ids:
        id_list = [i for i in ids.split(',') if i]
        for vid in id_list:
            detail_url = f"{base_url}/voddetail/{vid}.html" if vid.isdigit() else (base_url + vid if vid.startswith('/') else f"{base_url}/{vid}")
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

            response_data['list'].append({
                "vod_id": vid,
                "vod_name": "影视资源",
                "vod_pic": "https://via.placeholder.com/150x200.png?text=No+Image",
                "type_id": 1,
                "type_name": "电影",
                "vod_remarks": "高清",
                "vod_time": "2026-03-03",
                "vod_play_from": "yingshi",
                "vod_play_url": play_list_str,
                "vod_content": "暂无简介",
                "vod_director": "未知",
                "vod_actor": "未知"
            })
        return create_response(response_data)

    return create_response(response_data)
