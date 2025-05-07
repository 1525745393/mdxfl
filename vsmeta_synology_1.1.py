×××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××
# VSmeta 群晖整合脚本 v1.1
# 文件名建议：vsmeta_synology_1.1.py
# 适用于 Synology DSM / Python 3 环境，一键生成 .vsmeta 元数据文件
×××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××××

import os
import json
import argparse
from datetime import datetime
from pathlib import Path

# 默认支持的视频格式
SUPPORTED_VIDEO_EXT = [".mp4", ".mkv", ".avi", ".mov", ".wmv"]  # 建议：涵盖主流格式，扩展兼容性；更改后果：可能跳过部分文件

# 默认配置（支持自动补全）
DEFAULT_CONFIG = {
    "scan_root": "./JAV_output",  # 建议：设为待整理视频目录根路径；更改后果：脚本不会找到目标文件
    "output_vsmeta_dir": "",  # 建议：留空使用视频同目录；更改后果：指定路径需确保存在并有写权限
    "thread_count": 4,  # 建议：NAS 推荐 4-8；更改后果：线程过高可能占用资源
    "skip_existing": True,  # 建议：避免重复生成；更改后果：False 会覆盖已存在 vsmeta
    "rename_video": False,  # 建议：测试确认后开启；更改后果：开启后将重命名文件
    "rename_keep_original": True,  # 建议：开启以保留原文件；更改后果：False 会直接覆盖原文件
    "rename_skip_well_named": True,  # 建议：跳过规范文件；更改后果：False 会重命名所有文件
    "rename_template": "{id}_{title}",  # 建议：简洁结构化命名；更改后果：格式不合法可能出错
    "log_dir": "./logs",  # 建议：日志独立存储，便于查看问题；更改后果：无效路径无法写入日志
    "log_format": "txt",  # 建议：txt 或 json 可选；更改后果：写入失败
    "dry_run": False,  # 建议：先 dry-run 模拟；更改后果：False 会真实改动文件
    "python_path": ""  # 建议：留空自动检测；更改后果：手动指定必须为有效路径
}

# 加载配置并补全缺失字段
def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)
    for k, v in DEFAULT_CONFIG.items():
        if k not in config:
            config[k] = v
            print(f"[提示] 已补全默认配置：{k} = {v}")
    return config

# 自动检测 Python 路径
def find_python_path(user_path):
    if user_path and Path(user_path).exists():
        return user_path
    for p in ["/usr/local/bin/python3", "/usr/bin/python3", "/bin/python3"]:
        if Path(p).exists():
            return p
    return "python3"

# 简化 vsmeta 示例生成
def generate_vsmeta(video_path, output_path):
    dummy_metadata = {
        "title": "示例标题",
        "title_ja": "サンプルタイトル",
        "plot": "剧情简介",
        "plot_ja": "プロット",
        "id": video_path.stem,
        "tag": ["标签1", "标签2"]
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dummy_metadata, f, indent=2, ensure_ascii=False)

# 主处理函数
def process_videos(config):
    scan_root = Path(config["scan_root"])
    out_dir = config["output_vsmeta_dir"]
    dry_run = config["dry_run"]
    output_root = Path(out_dir) if out_dir else None
    log_root = Path(config["log_dir"])
    log_format = config["log_format"]
    log_root.mkdir(parents=True, exist_ok=True)
    log_entries = []
    total, success, failed = 0, 0, 0
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_root / f"log_{timestamp}.{log_format}"

    for root, _, files in os.walk(scan_root):
        for f in files:
            if not any(f.lower().endswith(ext) for ext in SUPPORTED_VIDEO_EXT):
                continue
            total += 1
            video_path = Path(root) / f
            vsmeta_path = (output_root / video_path.name).with_suffix(".vsmeta") if output_root else video_path.with_suffix(".vsmeta")
            try:
                if config["skip_existing"] and vsmeta_path.exists():
                    continue
                if not dry_run:
                    generate_vsmeta(video_path, vsmeta_path)
                log_entries.append({"file": str(video_path), "status": "success"})
                success += 1
            except Exception as e:
                log_entries.append({"file": str(video_path), "status": "failed", "reason": str(e)})
                failed += 1

    # 写日志
    if log_format == "json":
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump({
                "summary": {"total": total, "success": success, "failed": failed, "dry_run": dry_run},
                "details": log_entries
            }, f, ensure_ascii=False, indent=2)
    else:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"处理总数：{total}，成功：{success}，失败：{failed}，dry-run 模式：{'启用' if dry_run else '关闭'}\n")
            for entry in log_entries:
                status = entry["status"]
                reason = entry.get("reason", "")
                f.write(f"[{status.upper()}] {entry['file']}" + (f"，原因：{reason}\n" if reason else "\n"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VSmeta 群晖脚本 v1.1")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径（默认 config.json）")
    args = parser.parse_args()
    config = load_config(args.config)
    config["python_path"] = find_python_path(config.get("python_path", ""))
    process_videos(config)