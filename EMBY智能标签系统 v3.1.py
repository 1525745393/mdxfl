#!/usr/bin/env python3 
# -*- coding: utf-8 -*-
"""
EMBY智能标签系统 v3.1 
最后更新：2025-05-13 农历四月十六 
"""
import requests 
from fuzzywuzzy import fuzz 
from pathlib import Path 
import logging 
import json 
import functools 
from typing import List, Dict, Set 
 
# ==================== 用户必须修改的配置 ====================
CONFIG = {
    # 基础参数 
    "EMBY_SERVER": "http://your_emby_server:8096",  # [必改] 替换为实际Emby地址 
    # 效果：连接到正确的Emby服务器 
    # 后果：地址错误会导致连接失败 
    
    "API_KEY": "your_api_key_here",  # [必改] 从Emby后台获取的API密钥 
    # 获取路径：Emby后台 > 高级 > API密钥 
    # 后果：密钥无效会导致权限拒绝 
 
    # ===== 本地头像库配置 ===== 
    "AVATAR_DIR": "/data/actor_avatars",  # [建议修改] 本地头像库绝对路径 
    # 建议：确保该目录存在且可读 
    # 示例："/mnt/media/actors" (Linux) 或 "D:\\emby\\avatars" (Windows)
 
    # ===== 标签策略 ===== 
    "DEFAULT_TAG": "明星",  # [可选] 默认标签名称 
    "SIMILARITY_THRESHOLD": 78,  # [可选] 匹配敏感度(70-85)
    # 建议：值越高匹配越严格 
    
    # ===== 目录标签映射 ===== 
    "DIR_TAG_MAPPING": {
        "verified": ["官方认证"],  # verified目录下的文件添加此标签 
        "hd": ["高清"],           # hd目录下的文件添加此标签 
        "colored": ["AI上色"]     # colored目录下的文件添加此标签 
    },
    # [可选] 可自由增删改目录和标签 
    # 示例：添加 "fanart": ["饭制图"]
 
    # ===== 开关控制 ===== 
    "ENABLE_DIR_TAGGING": True,  # [可选] 总开关 
    # 效果：False时完全跳过本地头像处理 
    
    "DIR_SWITCHES": {  # [可选] 子目录独立开关 
        "verified": True,   # 处理verified目录 
        "hd": False,        # 跳过hd目录 
        "colored": True     # 处理colored目录 
    },
    # 后果：禁用目录后其内容不会被扫描 
 
    # ===== 高级设置 ===== 
    "IGNORE_PREFIXES": ["temp_", "test_"],  # [可选] 忽略的文件前缀 
    "CACHE_FILE": ".avatar_cache.json",       # [可选] 缓存文件路径 
    "MAX_CACHE_SIZE": 1000,                 # [可选] 缓存条目数 
    "TIMEOUT": 15                            # [可选] 网络超时(秒)
}
 
# ==================== 系统初始化 ====================
logging.basicConfig( 
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("emby_tagger.log",  encoding='utf-8'),
        logging.StreamHandler()
    ]
)
 
class EmbyTagger:
    def __init__(self):
        """初始化请求会话"""
        self.session  = requests.Session()
        self.session.headers.update({ 
            "X-Emby-Token": CONFIG["API_KEY"],
            "Accept": "application/json"
        })
 
    # ================ 核心功能 ================
    @functools.lru_cache(maxsize=CONFIG["MAX_CACHE_SIZE"]) 
    def get_actors(self) -> List[Dict]:
        """
        获取Emby演员列表（带缓存）
        返回值：List[{"Id": str, "Name": str, "Tags": List[str]}]
        """
        try:
            resp = self.session.get( 
                f"{CONFIG['EMBY_SERVER']}/Items",
                params={"IncludeItemTypes": "Person"},
                timeout=CONFIG["TIMEOUT"]
            )
            resp.raise_for_status() 
            return resp.json().get("Items",  [])
        except Exception as e:
            logging.error(f"[Actor  Fetch] Failed: {str(e)}")
            return []
 
    def scan_avatars(self) -> Dict[str, List[str]]:
        """
        扫描本地头像库 
        返回值：{"演员名": ["标签1", "标签2"]}
        """
        if not CONFIG["ENABLE_DIR_TAGGING"]:
            logging.info("[Switch]  目录标签功能已全局禁用")
            return {}
 
        tag_map = {}
        base_dir = Path(CONFIG["AVATAR_DIR"])
        
        for dir_name, tags in CONFIG["DIR_TAG_MAPPING"].items():
            if not CONFIG["DIR_SWITCHES"].get(dir_name, True):
                logging.debug(f"[Switch]  跳过禁用目录: {dir_name}")
                continue 
                
            dir_path = base_dir / dir_name 
            if dir_path.is_dir(): 
                for file in dir_path.glob("*"): 
                    # 跳过非图片文件和临时文件 
                    if file.suffix.lower()  not in [".jpg", ".png", ".webp"]:
                        continue 
                    if any(file.name.startswith(p)  for p in CONFIG["IGNORE_PREFIXES"]):
                        continue 
 
                    # 提取标准化的演员名 
                    actor_name = file.stem.split('_')[0].replace('-',  ' ').strip()
                    if not actor_name:
                        continue 
 
                    if actor_name not in tag_map:
                        tag_map[actor_name] = []
                    tag_map[actor_name].extend(tags)
        
        return tag_map 
 
    def apply_tags(self, actor_id: str, new_tags: List[str]) -> bool:
        """
        智能合并标签（避免重复）
        参数：
          actor_id: Emby演员ID 
          new_tags: 要添加的新标签 
        返回值：是否成功更新 
        """
        try:
            # 获取当前标签 
            resp = self.session.get( 
                f"{CONFIG['EMBY_SERVER']}/Items/{actor_id}",
                timeout=CONFIG["TIMEOUT"]
            )
            current_tags = resp.json().get("Tags",  [])
            
            # 合并去重 
            merged = list(set(current_tags + new_tags))
            if set(current_tags) != set(merged):
                resp = self.session.post( 
                    f"{CONFIG['EMBY_SERVER']}/Items/{actor_id}/Tags",
                    json=merged,
                    timeout=CONFIG["TIMEOUT"]
                )
                return resp.status_code  == 204 
            return False 
        except Exception as e:
            logging.error(f"[Tag  Update] Failed for {actor_id}: {str(e)}")
            return False 
 
    # ================ 业务流程 ================
    def process_local_tags(self):
        """处理本地头像标签"""
        avatar_tags = self.scan_avatars() 
        if not avatar_tags:
            logging.warning("[Local]  未找到可处理的本地头像")
            return 
 
        updated = 0 
        for actor in self.get_actors(): 
            if actor["Name"] in avatar_tags:
                if self.apply_tags(actor["Id"],  avatar_tags[actor["Name"]]):
                    updated += 1 
                    logging.info(f"[Local]  已标记 {actor['Name']}: {avatar_tags[actor['Name']]}")
        
        logging.info(f"[Summary]  本地头像标记完成，共更新 {updated} 位演员")
 
    def process_online_match(self):
        """处理Gfriends在线匹配"""
        try:
            resp = requests.get( 
                "https://raw.githubusercontent.com/gfriends/gfriends/master/index.txt", 
                timeout=CONFIG["TIMEOUT"]
            )
            resp.raise_for_status() 
            gfriends = set(resp.text.splitlines()) 
        except Exception as e:
            logging.error(f"[Gfriends]  数据获取失败: {str(e)}")
            return 
 
        matched_ids = []
        for actor in self.get_actors(): 
            best_match = max(
                [(name, fuzz.token_sort_ratio(actor["Name"],  name)) 
                 for name in gfriends],
                key=lambda x: x[1]
            )
            if best_match[1] >= CONFIG["SIMILARITY_THRESHOLD"]:
                matched_ids.append(actor["Id"]) 
                logging.debug(f"[Match]  匹配 {actor['Name']} → {best_match[0]} ({best_match[1]}%)")
 
        if matched_ids:
            self.session.post( 
                f"{CONFIG['EMBY_SERVER']}/Items/Tags/Batch",
                json={"Ids": matched_ids, "Tags": [CONFIG["DEFAULT_TAG"]]},
                timeout=CONFIG["TIMEOUT"]
            )
            logging.info(f"[Summary]  在线匹配完成，共标记 {len(matched_ids)} 位演员")
 
    def run(self):
        """主执行流程"""
        logging.info("=====  开始执行智能标签处理 =====")
        self.process_local_tags() 
        self.process_online_match() 
        logging.info("=====  处理完成 =====") 
 
# ==================== 执行入口 ====================
if __name__ == "__main__":
    EmbyTagger().run()
