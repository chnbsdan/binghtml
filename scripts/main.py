import os
import json
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
import logging
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ========== 所有文件直接输出到仓库根目录 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICTURE_DIR = os.path.join(BASE_DIR, "picture")

os.makedirs(PICTURE_DIR, exist_ok=True)

# ========== 从 bing 项目获取数据 ==========
BING_RAW_JSON = "https://raw.githubusercontent.com/chnbsdan/bing/main/json/"


def fetch_bing_index():
    """获取 bing 项目的最新数据"""
    try:
        today = datetime.now().strftime("%Y%m%d")
        url = f"{BING_RAW_JSON}{today}.json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        
        # 如果今天没有，往前找30天
        for i in range(1, 31):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
            url = f"{BING_RAW_JSON}{date}.json"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                logging.info(f"成功获取 {date}.json")
                return resp.json()
        return None
    except Exception as e:
        logging.error(f"获取 bing 数据失败: {e}")
        return None


def download_and_convert_to_webp(image_url, output_path):
    """下载图片并转换为 WebP"""
    try:
        resp = requests.get(image_url, timeout=30)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGB")
        max_width, max_height = 2560, 1600
        img.thumbnail((max_width, max_height))
        img.save(output_path, "WEBP", quality=80, method=6)
        return True
    except Exception as e:
        logging.error(f"转换失败: {e}")
        return False


def process_bing_data(bing_data):
    """处理数据并保存为 WebP"""
    if not bing_data or "images" not in bing_data:
        return []

    result = []
    for img_info in bing_data["images"]:
        startdate = img_info.get("startdate", "")
        if not startdate:
            continue
            
        date = datetime.strptime(startdate, "%Y%m%d").strftime("%Y-%m-%d")
        filename = f"{startdate}.webp"
        output_path = os.path.join(PICTURE_DIR, filename)
        
        # 如果图片不存在则下载转换
        if not os.path.exists(output_path):
            urlbase = img_info.get("urlbase", "")
            if urlbase:
                high_res_url = f"https://www.bing.com{urlbase}_UHD.jpg"
                fallback_url = f"https://www.bing.com{urlbase}_1920x1080.jpg"
                try:
                    test_resp = requests.head(high_res_url, timeout=5)
                    image_url = high_res_url if test_resp.status_code == 200 else fallback_url
                except:
                    image_url = fallback_url
            else:
                continue
            
            if not download_and_convert_to_webp(image_url, output_path):
                continue
        
        result.append({
            "filename": filename,
            "date": date,
            "path": f"/picture/{filename}",
            "copyright": img_info.get("copyright", ""),
            "startdate": startdate
        })
    
    # 按日期排序，最新的在前
    result.sort(key=lambda x: x["startdate"], reverse=True)
    
    # 只保留最近30天
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    filtered = [item for item in result if item["startdate"] >= thirty_days_ago]
    
    # 删除超过30天的旧图片
    existing_files = set(os.listdir(PICTURE_DIR))
    for item in result:
        if item not in filtered:
            filepath = os.path.join(PICTURE_DIR, item["filename"])
            if os.path.exists(filepath):
                os.remove(filepath)
    
    return filtered


def generate_index_json(images):
    """生成 index.json"""
    index_path = os.path.join(PICTURE_DIR, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(images, f, ensure_ascii=False, indent=2)
    logging.info(f"生成 index.json，共 {len(images)} 项")


def copy_index_html():
    """复制 index.html 到根目录"""
    template_path = os.path.join(BASE_DIR, "templates", "index.html")
    target_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(template_path):
        shutil.copy2(template_path, target_path)
        logging.info("复制 index.html")


def main():
    logging.info("===== 开始构建 =====")
    
    bing_data = fetch_bing_index()
    if not bing_data:
        logging.error("无法获取 bing 数据")
        return
    
    images = process_bing_data(bing_data)
    if not images:
        logging.error("没有有效的图片数据")
        return
    
    generate_index_json(images)
    copy_index_html()
    
    logging.info(f"===== 构建完成，共 {len(images)} 张图片 =====")


if __name__ == "__main__":
    main()
