import os
import json
import requests
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
import logging
import shutil

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ========== 路径配置 ==========
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE_DIR = os.path.join(BASE_DIR, "page")
PICTURE_DIR = os.path.join(PAGE_DIR, "picture")

# 确保目录存在
os.makedirs(PICTURE_DIR, exist_ok=True)

# ========== 从 bing 项目获取数据 ==========
BING_RAW_JSON = "https://raw.githubusercontent.com/chnbsdan/bing/main/json/"
BING_RAW_IMAGES = "https://raw.githubusercontent.com/chnbsdan/bing/main/images/"


def fetch_bing_index():
    """获取 bing 项目的最新 index.json 列表"""
    try:
        # bing 项目使用 startdate 作为文件名，如 20260722.json
        today = datetime.now().strftime("%Y%m%d")
        url = f"{BING_RAW_JSON}{today}.json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            # 如果今天的没有，尝试获取最近一天的
            logging.warning(f"无法获取今天的 JSON: {today}，尝试获取最近30天")
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
        
        # 限制最大尺寸
        max_width, max_height = 2560, 1600
        img.thumbnail((max_width, max_height))
        
        img.save(output_path, "WEBP", quality=80, method=6)
        logging.info(f"保存 WebP: {output_path}")
        return True
    except Exception as e:
        logging.error(f"下载/转换失败 {image_url}: {e}")
        return False


def process_bing_data(bing_data):
    """处理 bing 数据，生成 WebP 图片和 index.json"""
    if not bing_data or "images" not in bing_data or not bing_data["images"]:
        logging.error("无效的 bing 数据")
        return []

    images = bing_data["images"]
    result = []
    
    for img_info in images:
        # 提取信息
        startdate = img_info.get("startdate", "")
        if not startdate:
            continue
            
        # 格式化日期
        date = datetime.strptime(startdate, "%Y%m%d").strftime("%Y-%m-%d")
        filename = f"{startdate}.webp"
        output_path = os.path.join(PICTURE_DIR, filename)
        
        # 如果文件已存在，跳过
        if os.path.exists(output_path):
            logging.info(f"图片已存在，跳过: {filename}")
        else:
            # 构造图片 URL
            urlbase = img_info.get("urlbase", "")
            if urlbase:
                high_res_url = f"https://www.bing.com{urlbase}_UHD.jpg"
                fallback_url = f"https://www.bing.com{urlbase}_1920x1080.jpg"
                
                # 测试高清是否可用
                try:
                    test_resp = requests.head(high_res_url, timeout=5)
                    image_url = high_res_url if test_resp.status_code == 200 else fallback_url
                except:
                    image_url = fallback_url
            else:
                # 备用：从 bing 项目的 raw 链接获取
                image_url = f"{BING_RAW_IMAGES}{startdate}.png"
            
            if not download_and_convert_to_webp(image_url, output_path):
                continue
        
        # 收集元数据
        result.append({
            "filename": filename,
            "date": date,
            "path": f"/picture/{filename}",
            "copyright": img_info.get("copyright", ""),
            "url": img_info.get("url", ""),
            "title": img_info.get("title", ""),
            "startdate": startdate
        })
    
    # 按日期排序（最新的在前）
    result.sort(key=lambda x: x["startdate"], reverse=True)
    
    # 只保留最近 30 天
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")
    filtered = [item for item in result if item["startdate"] >= thirty_days_ago]
    
    # 删除超过 30 天的图片文件
    existing_files = set(os.listdir(PICTURE_DIR))
    for item in result:
        if item not in filtered:
            filepath = os.path.join(PICTURE_DIR, item["filename"])
            if os.path.exists(filepath):
                os.remove(filepath)
                logging.info(f"删除旧图片: {item['filename']}")
    
    return filtered


def generate_index_json(images):
    """生成 index.json"""
    index_path = os.path.join(PICTURE_DIR, "index.json")
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(images, f, ensure_ascii=False, indent=2)
        logging.info(f"生成 index.json，共 {len(images)} 项")
    except Exception as e:
        logging.error(f"生成 index.json 失败: {e}")


def copy_template():
    """复制模板文件到 page 目录"""
    template_dir = os.path.join(BASE_DIR, "templates")
    if not os.path.exists(template_dir):
        logging.warning("templates 目录不存在，跳过")
        return
    
    # 复制 index.html
    src = os.path.join(template_dir, "index.html")
    dst = os.path.join(PAGE_DIR, "index.html")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        logging.info("复制 index.html")
    
    # 复制 favicon.ico（如果存在）
    src = os.path.join(template_dir, "favicon.ico")
    dst = os.path.join(PAGE_DIR, "favicon.ico")
    if os.path.exists(src):
        shutil.copy2(src, dst)
        logging.info("复制 favicon.ico")


def main():
    logging.info("===== 开始构建 =====")
    
    # 1. 获取 bing 数据
    bing_data = fetch_bing_index()
    if not bing_data:
        logging.error("无法获取 bing 数据，退出")
        return
    
    # 2. 处理数据，生成 WebP
    images = process_bing_data(bing_data)
    if not images:
        logging.error("没有有效的图片数据")
        return
    
    # 3. 生成 index.json
    generate_index_json(images)
    
    # 4. 复制模板
    copy_template()
    
    logging.info(f"===== 构建完成，共 {len(images)} 张图片 =====")


if __name__ == "__main__":
    main()
