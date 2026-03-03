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
        "code": 1, "msg": "数据获取成功", "page": int(pg) if pg.isdigit() else 1,
        "pagecount": 999, "limit": 20, "total": 9999,
        "class": [{"type_id": 1, "type_name": "电影"}],
        "list": []
    }

    if not wd and not ids:
        wd = "我" 

    # ================= 搜索逻辑 =================
    if wd and not ids:
        search_url = f"{base_url}/vodsearch/{urllib.parse.quote(wd)}----------{pg}---.html"
        html = fetch_html(search_url)

        # 搜索页结构紧凑，沿用之前的成功正则
        names = re.findall(r'<a href="[^"]*?"><strong>(.*?)</strong></a>', html)
        urls = re.findall(r'<a href="(.*?)"><strong>.*?</strong></a>', html)
        pics = re.findall(r'<img class="lazy lazyload" data-original="(.*?)"', html)

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
                    "vod_id": vod_id, "vod_name": names[i], "vod_pic": pic_url,
                    "type_id": 1, "type_name": "电影", "vod_remarks": "点击查看",
                    "vod_time": "2026-03-03", "vod_play_from": "yingshi",
                    "vod_director": "未知", "vod_actor": "未知"
                })
        return create_response(response_data)

    # ================= 详情与选集逻辑 =================
    elif ids:
        id_list = [i for i in ids.split(',') if i]
        for vid in id_list:
            detail_url = f"{base_url}/voddetail/{vid}.html" if vid.isdigit() else (base_url + vid if vid.startswith('/') else f"{base_url}/{vid}")
            html = fetch_html(detail_url)

            # 抓取标题和图片
            title_match = re.search(r'<title>(.*?)</title>', html)
            vod_name = title_match.group(1).split('-')[0].strip() if title_match else "影视详情"

            pic_match = re.search(r'data-original="([^"]+)"', html)
            vod_pic = pic_match.group(1) if pic_match else ""
            vod_pic = base_url + vod_pic if vod_pic and not vod_pic.startswith('http') else vod_pic
            if not vod_pic:
                vod_pic = "https://via.placeholder.com/150x200.png?text=No+Image"

            # 【核心修复】：使用 [\s\S]*? 无视换行符，同时捕获链接和集数名称
            episodes = re.findall(r'<a[^>]*class="[^"]*module-play-list-link[^"]*"[^>]*href="([^"]+)"[^>]*>[\s\S]*?<span>([\s\S]*?)</span>', html)

            play_list_str = ""
            ep_count = 0
            if episodes:
                ep_list = []
                for ep_url, ep_name in episodes:
                    ep_name = ep_name.strip()
                    ep_url = ep_url.strip()
                    full_url = base_url + ep_url if ep_url.startswith('/') else ep_url
                    ep_list.append(f"{ep_name}${full_url}")
                play_list_str = "#".join(ep_list)
                ep_count = len(episodes)
            else:
                # 如果还是瞎了，给一个测试数据垫底，防止 Syncwe 崩溃
                play_list_str = "测试集$https://yingshi.co"

            response_data['list'].append({
                "vod_id": vid, "vod_name": vod_name, "vod_pic": vod_pic,
                "type_id": 1, "type_name": "电影", 
                "vod_remarks": f"成功抓取 {ep_count} 集", # 【探针】：显示在简介处，如果为0就是正则还是没匹配到
                "vod_time": "2026-03-03", "vod_play_from": "影视工厂",
                "vod_play_url": play_list_str, 
                "vod_content": f"系统探针反馈：后台共抓取到 {ep_count} 个播放链接。",
                "vod_director": "未知", "vod_actor": "未知"
            })
        return create_response(response_data)

    return create_response(response_data)
