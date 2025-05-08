#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
SynoVSMeta Converter (DSM7.2版)
功能：将影视库的NFO文件转换为同目录的VSMETA文件 
特点：自动路径识别/智能缓存/低内存占用 
"""
 
import os 
import sys 
import hashlib 
import struct 
import xml.etree.ElementTree as ET 
from typing import List, Dict, Optional 
 
# VSMETA 7.2格式头 
VSMETA_HEADER = b'\x56\x53\x4D\x01\x00\x00\x00'
FIELD_TAGS = {
    'title': 0x01,
    'originaltitle': 0x02,
    'plot': 0x03,
    'year': 0x04,
    'rating': 0x05,
    'actor': 0x06,
    'director': 0x07,
    'genre': 0x08,
    'mpaa': 0x09,
    'studio': 0x0C,
    'runtime': 0x0D 
}
 
class SynoMetaConverter:
    def __init__(self, base_path: str):
        """
        :param base_path: 影视库根目录（如`/volume1/video`）
        """
        self.base_path = os.path.normpath(base_path)
        self.cache_file = os.path.join(os.path.dirname(__file__), '.synoconvert_cache')
 
    def scan_and_convert(self):
        """扫描目录并转换所有NFO文件"""
        for root, _, files in os.walk(self.base_path):
            for file in files:
                if file.lower().endswith('.nfo'):
                    nfo_path = os.path.join(root, file)
                    self.convert_nfo(nfo_path)
 
    def convert_nfo(self, nfo_path: str):
        """单个NFO文件转换"""
        vsmeta_path = os.path.splitext(nfo_path)[0] + '.vsmeta'
        
        # 校验缓存 
        if self._check_cache(nfo_path, vsmeta_path):
            print(f"⏩ 已跳过 [ {os.path.basename(nfo_path)} ] (无变更)")
            return 
 
        try:
            meta = self._parse_nfo(nfo_path)
            vsmeta_data = self._generate_vsmeta(meta)
            with open(vsmeta_path, 'wb') as f:
                f.write(vsmeta_data)
            self._update_cache(nfo_path)
            print(f"✅ 已生成 [ {os.path.basename(vsmeta_path)} ]")
        except Exception as e:
            print(f"❌ 转换失败 [ {os.path.basename(nfo_path)} ]: {str(e)}")
 
    def _parse_nfo(self, nfo_path: str) -> Dict:
        """解析NFO文件内容"""
        meta = {k: None for k in FIELD_TAGS.keys()}
        meta['actors'] = []
        
        tree = ET.parse(nfo_path)
        root = tree.getroot()
        
        # 基础字段 
        for tag in FIELD_TAGS:
            if tag in ['actor', 'studio']: continue 
            elem = root.find(tag)
            if elem is not None and elem.text:
                meta[tag] = elem.text.strip()
        
        # 列表型字段 
        meta['actors'] = [a.findtext('name', '').strip() 
                         for a in root.findall('actor') if a.findtext('name')]
        meta['studio'] = [s.text.strip() 
                         for s in root.findall('studio') if s.text]
        
        # 数值处理 
        meta['rating'] = min(float(meta.get('rating', 0)) * 2, 10)  # 10分制 
        meta['year'] = int(meta.get('year', 0))
        meta['runtime'] = int(meta.get('runtime', 0))
        
        return meta 
 
    def _generate_vsmeta(self, meta: Dict) -> bytes:
        """生成VSMETA二进制数据"""
        buffer = bytearray()
        buffer.extend(VSMETA_HEADER)
        
        # 写入标准字段 
        for field, tag in FIELD_TAGS.items():
            if field in ['actor', 'studio']: continue 
            
            value = meta.get(field)
            if value is None: continue 
            
            if isinstance(value, str):
                encoded = value.encode('utf-16le')
                buffer.extend(struct.pack('<II', tag, len(encoded)))
                buffer.extend(encoded)
            elif isinstance(value, (int, float)):
                buffer.extend(struct.pack('<III', tag, 4, value))
        
        # 写入列表字段 
        for item in meta.get('actors', []):
            encoded = item.encode('utf-16le')
            buffer.extend(struct.pack('<II', FIELD_TAGS['actor'], len(encoded)))
            buffer.extend(encoded)
            
        for item in meta.get('studio', []):
            encoded = item.encode('utf-16le')
            buffer.extend(struct.pack('<II', FIELD_TAGS['studio'], len(encoded)))
            buffer.extend(encoded)
            
        buffer.extend(struct.pack('<I', 0xFF))  # 结束标记 
        return bytes(buffer)
 
    def _check_cache(self, nfo_path: str, vsmeta_path: str) -> bool:
        """检查文件是否需要更新"""
        if not os.path.exists(vsmeta_path):
            return False 
            
        nfo_mtime = os.path.getmtime(nfo_path)
        vsmeta_mtime = os.path.getmtime(vsmeta_path)
        return nfo_mtime <= vsmeta_mtime 
 
    def _update_cache(self, nfo_path: str):
        """更新缓存记录"""
        with open(self.cache_file, 'a') as f:
            f.write(f"{nfo_path}\n")
 
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("使用方法: python3 syno_converter.py <影视库路径>")
        print("示例: python3 syno_converter.py /volume1/video")
        sys.exit(1)
        
    converter = SynoMetaConverter(sys.argv[1])
    print("🔄 开始扫描转换...")
    converter.scan_and_convert()
    print("🎉 所有文件处理完成！")
