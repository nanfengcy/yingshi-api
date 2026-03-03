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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://yingshi.co/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'X-Forwarded-For': fake_ip,
        'Client-IP': fake_ip
    }
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        res.encoding = 'utf-8'
        return res.text
    except Exception as e:
        print(f"抓取失败: {e}")
        return ""

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    ac = request.args.get('ac', 'list')
    wd = request.args.get('wd', '')
    ids = request.args.get('ids', '')

    response_data = {
        "code": 1,
        "msg": "数据获取成功",
        "page": 1,
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
                # 修复1：如果没图，给一张默认的灰色占位图防崩溃
                pic_url = pics[i] if i < len(pics) else ""
                if not pic_url:
                    pic_url = "https://via.placeholder.com/150x200.png?text=No+Image"
                elif not pic_url.startswith('http'):
                    pic_url = base_url + pic_url

                # 修复2：强制提取纯数字 ID (例如从 /voddetail/73842.html 提取 73842)
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
        # 修复3：强制输出真实中文，拒绝 Unicode 编码
        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json; charset=utf-8')

    # === 详情与播放逻辑 ===
    elif ac == 'detail' and ids:
        id_list = [i for i in ids.split(',') if i]
        for vid in id_list:
            # 根据传进来的纯数字 ID，拼回完整的详情页链接
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
        return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json; charset=utf-8')

    return Response(json.dumps(response_data, ensure_ascii=False), mimetype='application/json; charset=utf-8')
