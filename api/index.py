from flask import Flask, request, Response
import requests
import re
import urllib.parse
import urllib3
import json
import random

app = Flask(__name__)
# 禁用本地环境的 HTTPS 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
base_url = "https://yingshi.co"

def fetch_html(url):
    # 随机生成假 IP，完美伪装人类浏览器，防止被影视工厂拉黑
    fake_ip = f"{random.randint(11, 250)}.{random.randint(11, 250)}.{random.randint(11, 250)}.{random.randint(11, 250)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://yingshi.co/',
        'X-Forwarded-For': fake_ip,
        'Client-IP': fake_ip
    }
    try:
        # 设置 10 秒超时，防止 Vercel 崩溃
        res = requests.get(url, headers=headers, verify=False, timeout=10)
        res.encoding = 'utf-8'
        return res.text
    except:
        return ""

def create_response(data):
    # 生成带“跨域通行证(CORS)”的响应，防止 Syncwe 等 App 拦截数据
    res = Response(json.dumps(data, ensure_ascii=False), mimetype='application/json; charset=utf-8')
    res.headers['Access-Control-Allow-Origin'] = '*'
    res.headers['Access-Control-Allow-Methods'] = '*'
    res.headers['Access-Control-Allow-Headers'] = '*'
    return res

# 万能路由：无论 Syncwe 访问 / 还是 /api 还是 /api.php/provide/vod 都能接住
@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'OPTIONS'])
@app.route('/<path:path>', methods=['GET', 'POST', 'OPTIONS'])
def catch_all(path):
    # 放行 App 发送的预检请求
    if request.method == 'OPTIONS':
        return create_response({})

    # 兼容 GET 和 POST 两种传参方式
    ac = request.values.get('ac', 'list')
    wd = request.values.get('wd', '')
    ids = request.values.get('ids', '')
    pg = request.values.get('pg', '1')

    # 准备标准的 MacCMS 响应外壳
    response_data = {
        "code": 1, "msg": "数据获取成功", "page": int(pg) if pg.isdigit() else 1,
        "pagecount": 999, "limit": 20, "total": 9999,
        "class": [{"type_id": 1, "type_name": "电影"}],
        "list": []
    }

    # 【终极开机欺骗】：如果软件没传搜索词和ID（代表正在做开机健康检查）
    # 我们直接偷偷塞一个“我”字！让它去抓取搜索结果，避免返回空列表被软件拉黑
    if not wd and not ids:
        wd = "我" 

    # ================= 第一步：处理搜索请求 =================
    if wd and not ids:
        search_url = f"{base_url}/vodsearch/{urllib.parse.quote(wd)}----------{pg}---.html"
        html = fetch_html(search_url)

        # 搜索页的正则表达式（你之前验证过成功的版本）
        names = re.findall(r'<a href="[^"]*?"><strong>(.*?)</strong></a>', html)
        urls = re.findall(r'<a href="(.*?)"><strong>.*?</strong></a>', html)
        pics = re.findall(r'<img class="lazy lazyload" data-original="(.*?)"', html)

        if names:
            response_data['total'] = len(names)
            for i in range(len(names)):
                # 处理图片
                pic = pics[i] if i < len(pics) else ""
                pic_url = base_url + pic if pic and not pic.startswith('http') else pic
                if not pic_url:
                    pic_url = "https://via.placeholder.com/150x200.png?text=No+Image"

                # 提取纯数字 ID
                raw_url = urls[i]
                vod_id = raw_url
                id_match = re.search(r'/voddetail/(\d+)\.html', raw_url)
                if id_match:
                    vod_id = id_match.group(1)

                # 塞满标准字段，防止软件解析崩溃
                response_data['list'].append({
                    "vod_id": vod_id, "vod_name": names[i], "vod_pic": pic_url,
                    "type_id": 1, "type_name": "电影", "vod_remarks": "点击查看详情",
                    "vod_time": "2026-03-03", "vod_play_from": "yingshi",
                    "vod_director": "未知", "vod_actor": "未知"
                })
        return create_response(response_data)

    # ================= 第二步：处理详情与选集抓取请求 =================
    elif ids:
        id_list = [i for i in ids.split(',') if i]
        for vid in id_list:
            # 拼装详情页网址
            detail_url = f"{base_url}/voddetail/{vid}.html" if vid.isdigit() else (base_url + vid if vid.startswith('/') else f"{base_url}/{vid}")
            html = fetch_html(detail_url)

            # 1. 抓取真实标题
            title_match = re.search(r'<title>(.*?)</title>', html)
            vod_name = title_match.group(1).split('-')[0].strip() if title_match else "影视详情"

            # 2. 抓取真实海报图
            pic_match = re.search(r'data-original="([^"]+)"', html)
            vod_pic = pic_match.group(1) if pic_match else ""
            vod_pic = base_url + vod_pic if vod_pic and not vod_pic.startswith('http') else vod_pic
            if not vod_pic:
                vod_pic = "https://via.placeholder.com/150x200.png?text=No+Image"

            # 3. 【核心修复】：基于你提供的源码，使用兼容换行符的终极暴力正则抓取选集
            episodes = re.findall(r'<a[^>]*class="[^"]*module-play-list-link[^"]*"[^>]*href="([^"]+)"[^>]*>[\s\S]*?<span>([\s\S]*?)</span>', html)

            play_list_str = ""
            ep_count = 0
            if episodes:
                ep_list = []
                for ep_url, ep_name in episodes:
                    ep_name = ep_name.strip()
                    ep_url = ep_url.strip()
                    # 补全完整播放链接
                    full_url = base_url + ep_url if ep_url.startswith('/') else ep_url
                    # 按照 Syncwe 要求的标准格式拼装：集数$链接
                    ep_list.append(f"{ep_name}${full_url}")
                
                play_list_str = "#".join(ep_list)
                ep_count = len(episodes)
            else:
                # 极端防崩溃保底
                play_list_str = "无选集数据$#"

            # 4. 组装详情页 JSON，加入探针数据
            response_data['list'].append({
                "vod_id": vid, "vod_name": vod_name, "vod_pic": vod_pic,
                "type_id": 1, "type_name": "电影", 
                "vod_remarks": f"成功抓取 {ep_count} 集", # 探针：能在外面看到到底抓了几集
                "vod_time": "2026-03-03", "vod_play_from": "影视工厂",
                "vod_play_url": play_list_str, 
                "vod_content": f"系统探针反馈：后台共抓取到 {ep_count} 个播放链接。请在下方选集列表查看。",
                "vod_director": "未知", "vod_actor": "未知"
            })
        return create_response(response_data)

    return create_response(response_data)

# 用于本地测试启动
if __name__ == '__main__':
    app.run(debug=True, port=8080)
