#!/usr/bin/env python3
# 群晖专用版 VSmeta 生成工具 v1.1 优化版

import os
import re
import json
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# 默认配置项
default_config = {
    "scan_root": "./JAV_output",
    "output_vsmeta_dir": "",
    "skip_existing": True,
    "rename_video": False,
    "rename_keep_original": True,
    "rename_skip_well_named": True,
    "rename_template": "{id}_{title}",
    "thread_count": 4,
    "log_dir": "./logs",
    "log_format": "txt",
    "dry_run": False,
    "python_path": "",
    "video_extensions": [".mp4", ".mkv", ".avi", ".mov", ".wmv"],
    "nfo_dir": ""
}


# 自动补全配置字段
def load_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    for k, v in default_config.items():
        if k not in config:
            config[k] = v
            print(f"[警告] 缺失配置项 '{k}'，已自动补全默认值: {v}")
    return config


# 自动判断 Python 路径
def find_python_path(user_path):
    if user_path and Path(user_path).exists():
        return user_path
    for p in ["/usr/local/bin/python3", "/usr/bin/python3", "/bin/python3"]:
        if Path(p).exists():
            return p
    return "python3"


# 简易 vsmeta 数据生成（模拟）
def generate_vsmeta(video_path):
    name = video_path.stem
    fake_id = re.search(r"[A-Z]{2,5}-?\d{3,5}", name.upper())
    vid = fake_id.group() if fake_id else "UNKNOWN"
    return {
        "id": vid,
        "title": f"示例标题_{vid}",
        "title_ja": f"サンプルタイトル_{vid}",
        "plot": "暂无剧情信息",
        "plot_ja": "ストーリー情報なし",
        "actor": ["演员A", "演员B"],
        "tag": ["剧情", "制服"],
        "studio": "示例片商",
        "date": "2024-01-01",
        "series": "系列作"
    }


# 保存 .vsmeta 文件
def save_vsmeta(meta, output_path, dry_run):
    if dry_run:
        print(f"[Dry-run] 将保存 vsmeta 至: {output_path}")
        return
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


# 根据模板生成新文件名
def generate_new_filename(template, meta, suffix=".mp4"):
    try:
        newname = template.format(**meta)
    except KeyError:
        newname = meta["id"]
    return re.sub(r"[\\/:*?\"<>|]", "_", newname) + suffix


# 日志记录器
class Logger:
    def __init__(self, path, json_mode=False):
        self.json_mode = json_mode
        self.log = []
        self.path = path
        Path(path.parent).mkdir(parents=True, exist_ok=True)

    def add(self, status, path, reason="", level="INFO"):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        entry = {
            "timestamp": timestamp,
            "level": level,
            "status": status,
            "path": str(path),
            "reason": reason
        }
        self.log.append(entry)
        print(f"[{timestamp}] [{level}] [{status}] {path}" + (f"，原因：{reason}" if reason else ""))

    def save(self):
        if self.json_mode:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.log, f, indent=2, ensure_ascii=False)
        else:
            with open(self.path, 'w', encoding='utf-8') as f:
                for entry in self.log:
                    f.write(f"[{entry['timestamp']}] [{entry['level']}] [{entry['status']}] {entry['path']}" +
                            (f"，原因：{entry['reason']}" if entry['reason'] else "") + "\n")


# 文件处理逻辑（支持重命名）
def process_file(full_path, config, logger, dry_run, output_dir):
    try:
        meta = generate_vsmeta(full_path)
        vsmeta_path = (output_dir or full_path.parent) / (full_path.stem + ".vsmeta")
        if config["skip_existing"] and vsmeta_path.exists():
            logger.add("跳过", full_path, "vsmeta 已存在")
            return
        save_vsmeta(meta, vsmeta_path, dry_run)

        if config["rename_video"]:
            new_name = generate_new_filename(config["rename_template"], meta, suffix=full_path.suffix)
            new_path = full_path.parent / new_name

            if config["rename_skip_well_named"] and full_path.stem in new_name:
                logger.add("跳过", full_path, "已符合命名规范")
                return

            if not dry_run:
                if config["rename_keep_original"]:
                    full_path.rename(new_path)
                else:
                    os.replace(full_path, new_path)
            logger.add("重命名", new_path)
        else:
            logger.add("成功", full_path)
    except FileNotFoundError:
        logger.add("失败", full_path, "文件未找到", level="ERROR")
    except PermissionError:
        logger.add("失败", full_path, "权限不足", level="ERROR")
    except Exception as e:
        logger.add("失败", full_path, str(e), level="ERROR")


# 主处理逻辑（多线程支持）
def process_all(config):
    scan_root = Path(config["scan_root"])
    output_dir = Path(config["output_vsmeta_dir"]) if config["output_vsmeta_dir"] else None
    extensions = tuple(config["video_extensions"])
    dry_run = config["dry_run"]
    log_format = config["log_format"].lower()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = Path(config["log_dir"]) / f"log_{ts}.{log_format}"
    logger = Logger(log_path, json_mode=(log_format == "json"))

    with ThreadPoolExecutor(max_workers=config["thread_count"]) as executor:
        for root, _, files in os.walk(scan_root):
            for file in files:
                if file.lower().endswith(extensions):
                    full_path = Path(root) / file
                    executor.submit(process_file, full_path, config, logger, dry_run, output_dir)
    logger.save()


# CLI 入口
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VSmeta 群晖专用整理工具 v1.1")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径（默认 config.json）")
    args = parser.parse_args()

    config = load_config(args.config)
    config["python_path"] = find_python_path(config.get("python_path", ""))
    process_all(config)
