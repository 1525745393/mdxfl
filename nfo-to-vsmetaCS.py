#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
SynoMeta Converter v2025.5 
专为群晖DS920+ DSM7.2+设计 
功能：自动监控指定目录的NFO文件并生成VSMETA 
"""
 
import os 
import sys 
import time 
import hashlib 
import struct 
import xml.etree.ElementTree as ET 
from watchdog.observers import Observer 
from watchdog.events import FileSystemEventHandler 
 
# 配置区（用户可自定义）=======================================
WATCH_FOLDER = "/volume1/media"          # 监控的媒体库根目录 
CUSTOM_POSTER_NAMES = [                  # 自定义封面文件名（优先级降序）
    "custom-poster.jpg",
    "cover.jpg", 
    "folder.jpg"
]
EXCLUDE_FOLDERS = [                      # 排除目录 
    "@eaDir",
    ".tmp"
]
# ========================================================= 
 
class SynoMetaGenerator:
    VSMETA_HEADER = b'\x56\x53\x4D\x01\x00\x00\x00'
    
    def __init__(self):
        self.cache = set()
        
    def find_custom_art(self, nfo_path):
        """查找自定义封面和背景图"""
        folder = os.path.dirname(nfo_path)
        for pattern in CUSTOM_POSTER_NAMES:
            poster = os.path.join(folder, pattern)
            if os.path.exists(poster):
                return poster 
        return None 
 
    def generate_vsmeta(self, nfo_path):
        """生成VSMETA文件"""
        try:
            # 计算文件哈希用于缓存 
            file_hash = hashlib.md5(open(nfo_path,'rb').read()).hexdigest()
            if file_hash in self.cache:
                return 
            
            # 解析NFO文件 
            tree = ET.parse(nfo_path)
            root = tree.getroot()
            
            # 构建元数据字典 
            meta = {
                'title': root.findtext('title', '').strip(),
                'originaltitle': root.findtext('originaltitle', '').strip(),
                'plot': root.findtext('plot', '').strip(),
                'year': int(root.findtext('year', '0')),
                'rating': min(float(root.findtext('rating', '0')) * 2, 10)  # 10分制 
            }
            
            # 查找自定义封面 
            custom_art = self.find_custom_art(nfo_path)
            if custom_art:
                meta['poster'] = custom_art 
            
            # 生成VSMETA二进制（此处简化为示例）
            vsmeta_path = os.path.splitext(nfo_path)[0] + ".vsmeta"
            with open(vsmeta_path, 'wb') as f:
                f.write(self.VSMETA_HEADER)
                # 实际应添加完整的元数据字段 
                
            self.cache.add(file_hash)
            print(f"Generated: {vsmeta_path}")
            
        except Exception as e:
            print(f"Error processing {nfo_path}: {str(e)}")
 
class NfoHandler(FileSystemEventHandler):
    def __init__(self, generator):
        self.generator = generator 
        
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.nfo'):
            self.generator.generate_vsmeta(event.src_path)
 
def setup_synology_task():
    """配置群晖计划任务"""
    generator = SynoMetaGenerator()
    observer = Observer()
    
    # 添加监控路径（排除系统目录）
    for root, dirs, _ in os.walk(WATCH_FOLDER):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_FOLDERS]
        observer.schedule(NfoHandler(generator), root, recursive=True)
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
 
if __name__ == '__main__':
    print("""
    ███████╗███╗   ██╗ ██████╗ ███╗   ███╗███████╗ 
    ██╔════╝████╗  ██║██╔═══██╗████╗ ████║██╔════╝ 
    ███████╗██╔██╗ ██║██║   ██║██╔████╔██║█████╗  
    ╚════██║██║╚██╗██║██║   ██║██║╚██╔╝██║██╔══╝  
    ███████║██║ ╚████║╚██████╔╝██║ ╚═╝ ██║███████╗ 
    ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝ 
    DSM7.2+ Automatic Meta Converter 
    """)
    setup_synology_task()
