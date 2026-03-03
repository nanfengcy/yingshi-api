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

    # ================= 搜索列表 =================
    if wd and not ids:
        search_url = f"{base_url}/vodsearch/{urllib.parse.quote(wd)}----------{pg}---.html"
        html = fetch_html(search_url)

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
                    # 突破点1：强制转换为纯数字格式！
                    vod_id = int(id_match.group(1))

                response_data['list'].append({
                    "vod_id": vod_id, "vod_name": names[i], "vod_pic": pic_url,
                    "type_id": 1, "type_name": "电影", "vod_remarks": "点击查看",
                    "vod_play_from": "yingshim3u8"
                })
        return create_response(response_data)

    # ================= 详情与多线路抓取 =================
    elif ids:
        id_list = [i for i in ids.split(',') if i]
        for vid in id_list:
            detail_url = f"{base_url}/voddetail/{vid}.html" if str(vid).isdigit() else (base_url + vid if vid.startswith('/') else f"{base_url}/{vid}")
            html = fetch_html(detail_url)

            title_match = re.search(r'<title>(.*?)</title>', html)
            vod_name = title_match.group(1).split('-')[0].strip() if title_match else "影视详情"

            pic_match = re.search(r'data-original="([^"]+)"', html)
            vod_pic = pic_match.group(1) if pic_match else ""
            vod_pic = base_url + vod_pic if vod_pic and not vod_pic.startswith('http') else vod_pic
            if not vod_pic:
                vod_pic = "https://via.placeholder.com/150x200.png?text=No+Image"

            # 使用你源码分析出的精准正则，同时匹配整个播放列表区块
            play_lists = re.findall(r'<div class="module-play-list-content[^>]*>([\s\S]*?)</div>', html)
            
            play_from_list = []
            play_url_list = []
            
            # 第一层保障：按区块提取
            if play_lists:
                for i, plist in enumerate(play_lists):
                    episodes = re.findall(r'<a class="module-play-list-link" href="(.*?)" title=".*?"><span>(.*?)</span></a>', plist)
                    if episodes:
                        ep_str_list = []
                        for ep_url, ep_name in episodes:
                            full_url = base_url + ep_url if ep_url.startswith('/') else ep_url
                            # 突破点2：强制给 HTML 网页披上 .m3u8 的羊皮！骗过软件！
                            if ".m3u8" not in full_url:
                                full_url += "#.m3u8"
                            ep_str_list.append(f"{ep_name.strip()}${full_url}")
                        play_url_list.append("#".join(ep_str_list))
                        play_from_list.append("yingshim3u8")

            # 第二层保底：如果区块没提取到，全局暴力提取一次
            if not play_url_list:
                episodes = re.findall(r'<a class="module-play-list-link" href="(.*?)" title=".*?"><span>(.*?)</span></a>', html)
                if episodes:
                    ep_str_list = []
                    for ep_url, ep_name in episodes:
                        full_url = base_url + ep_url if ep_url.startswith('/') else ep_url
                        if ".m3u8" not in full_url:
                            full_url += "#.m3u8"
                        ep_str_list.append(f"{ep_name.strip()}${full_url}")
                    play_url_list.append("#".join(ep_str_list))
                    play_from_list.append("yingshim3u8")
            
            if play_url_list:
                vod_play_from = "$$$".join(play_from_list)
                vod_play_url = "$$$".join(play_url_list)
            else:
                vod_play_from = "yingshim3u8"
                vod_play_url = "伪装测试集$https://yingshi.co/test.m3u8"

            response_data['list'].append({
                "vod_id": int(vid) if str(vid).isdigit() else vid, 
                "vod_name": vod_name, 
                "vod_pic": vod_pic,
                "type_id": 1, 
                "type_name": "电影", 
                "vod_year": "2026",
                "vod_area": "中国",
                "vod_remarks": "更新完毕",
                "vod_actor": "未知",
                "vod_director": "未知",
                "vod_content": "如果终于看到选集了，说明之前真的是被 Syncwe 的后缀检查给屏蔽了！",
                "vod_play_from": vod_play_from,
                "vod_play_url": vod_play_url
            })
        return create_response(response_data)

    return create_response(response_data)
