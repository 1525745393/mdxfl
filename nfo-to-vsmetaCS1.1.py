#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
【群晖专用】NFO自动转VSMETA工具 (DSM 7.2+)
功能：监控指定目录自动转换，完美适配计划任务 
"""
 
import os 
import sys 
import time 
import hashlib 
import xml.etree.ElementTree as ET 
from pathlib import Path 
 
# 配置区（用户需修改这部分）
CONFIG = {
    'WATCH_DIR': '/volume1/MDC1/AV待整理/JAV_output',      # 监控的主目录 
    'CACHE_DB':  '/volume1/MDC1/vsmeta_cache.json',  # 缓存数据库路径 
    'LOG_FILE':  '/volume1/MDC1/nfo_converter.log', # 日志文件路径 
    'FILE_PATTERNS': {                  # 自定义文件匹配规则 
        'nfo': ['*.nfo'],               # NFO文件格式 
        'poster': ['poster.jpg', 'folder.jpg', '*.jpg'], # 封面图规则 
        'backdrop': ['fanart.jpg', 'background.jpg'] # 背景图规则 
    }
}
 
class SynologyConverter:
    def __init__(self):
        self.cache = self.load_cache()
        
    def convert_all(self):
        """主转换流程"""
        for root, _, files in os.walk(CONFIG['WATCH_DIR']):
            for pattern in CONFIG['FILE_PATTERNS']['nfo']:
                for nfo_file in Path(rootglob(pattern):
                    self.process_nfo(nfo_file)
        self.save_cache()
 
    def process_nfo(self, nfo_path):
        """处理单个NFO文件"""
        try:
            # 校验是否需要处理（缓存机制）
            file_hash = self.get_file_hash(nfo_path)
            if file_hash in self.cache:
                return 
 
            # 解析NFO并生成VSMETA 
            vsmeta_data = self.generate_vsmeta(nfo_path)
            output_path = nfo_path.with_suffix('.vsmeta')
            
            # 保存结果 
            with open(output_path, 'wb') as f:
                f.write(vsmeta_data)
            
            # 更新缓存 
            self.cache[file_hash] = str(time.time())
            
        except Exception as e:
            self.log_error(f"处理失败 {nfo_path}: {str(e)}")
 
    # 其他工具方法...
    # (包含之前讨论的generate_vsmeta、图片处理等方法)
 
if __name__ == '__main__':
    converter = SynologyConverter()
    converter.convert_all()
