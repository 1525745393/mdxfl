#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
NFO2VSMETA DSM7.2专版 (2025.05)
群晖DS920+优化版 | 支持自定义路径 | 计划任务集成 
"""
 
import os 
import sys 
import hashlib 
import struct 
import xml.etree.ElementTree as ET 
from pathlib import Path 
 
# DSM 7.2专用配置 
VSMETA_HEADER = b'\x56\x53\x4D\x01\x00\x00\x00'
CACHE_DIR = "/var/services/homes/admin/.nfo_cache"
SUPPORTED_MEDIA = ['.mp4', '.mkv', '.avi', '.mov']
 
class DSM7Converter:
    def __init__(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        
    def convert(self, input_path, output_dir=None):
        """主转换函数"""
        try:
            input_path = Path(input_path)
            
            # 自动识别输入类型 
            if input_path.is_dir():
                return self.batch_convert(input_path, output_dir)
                
            if input_path.suffix.lower() != '.nfo':
                raise ValueError("必须提供.nfo文件")
            
            # 加载并解析NFO 
            meta = self.parse_nfo(input_path)
            
            # 生成输出路径 
            output_path = self.get_output_path(input_path, output_dir)
            
            # 转换并保存VSMETA 
            vsmeta_data = self.generate_vsmeta(meta)
            with open(output_path, 'wb') as f:
                f.write(vsmeta_data)
                
            return str(output_path)
            
        except Exception as e:
            print(f"[ERROR] 转换失败: {str(e)}")
            return None 
 
    def parse_nfo(self, nfo_path):
        """解析NFO文件内容"""
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        
        meta = {
            'title': root.findtext('title', '').strip(),
            'original_title': root.findtext('originaltitle', '').strip(),
            'description': root.findtext('plot', '').strip(),
            'year': int(root.findtext('year', '0')),
            'rating': min(10, float(root.findtext('rating', '0')) * 2),
            'poster': self.find_media_file(nfo_path, ['poster.jpg', 'folder.jpg']),
            'backdrop': self.find_media_file(nfo_path, ['fanart.jpg', 'backdrop.jpg'])
        }
        return meta 
 
    def find_media_file(self, nfo_path, candidates):
        """查找关联的媒体文件"""
        base_dir = nfo_path.parent 
        for filename in candidates:
            filepath = base_dir / filename 
            if filepath.exists():
                return filepath 
        return None 
 
    def generate_vsmeta(self, meta):
        """生成VSMETA二进制数据"""
        buffer = bytearray()
        buffer.extend(VSMETA_HEADER)
        
        # 添加文本字段 
        for field in ['title', 'original_title', 'description']:
            if meta[field]:
                data = meta[field].encode('utf-16le')
                buffer.extend(struct.pack('<II', self.FIELD_MAP[field], len(data)))
                buffer.extend(data)
                
        # 添加数值字段 
        buffer.extend(struct.pack('<III', 0x04, 4, meta['year']))
        buffer.extend(struct.pack('<IIf', 0x05, 4, meta['rating']))
        
        return bytes(buffer)
 
    def batch_convert(self, input_dir, output_dir=None):
        """批量转换整个目录"""
        results = []
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith('.nfo'):
                    nfo_path = Path(root) / file 
                    results.append(self.convert(nfo_path, output_dir))
        return results 
 
    def get_output_path(self, input_path, output_dir=None):
        """确定输出文件路径"""
        base_dir = output_dir if output_dir else input_path.parent 
        media_name = input_path.stem 
        return Path(base_dir) / f"{media_name}.vsmeta"
 
# DSM 7.2字段映射 
FIELD_MAP = {
    'title': 0x01,
    'original_title': 0x02,
    'description': 0x03,
    'year': 0x04,
    'rating': 0x05 
}
 
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("使用方法:") 
        print("  单文件转换: python3 nfo2vsmeta.py <nfo文件路径> [输出目录]")
        print("  批量转换: python3 nfo2vsmeta.py <目录路径> [输出目录]")
        sys.exit(1)
    
    converter = DSM7Converter()
    converter.convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
