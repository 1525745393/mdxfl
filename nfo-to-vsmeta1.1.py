#!/usr/bin/env python

import os
import json
import logging
import time
import hashlib
import xml.dom.minidom as xmldom
import base64

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_file="config.json"):
    """从 config.json 文件加载配置"""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件 {config_file} 不存在，请创建配置文件并设置参数。")
    with open(config_file, 'r', encoding='utf-8') as file:
        return json.load(file)

def get_video_files(directory, video_extensions):
    """获取指定目录及其子目录中符合视频扩展名的文件"""
    for root, _, files in os.walk(directory):
        if '@eaDir' in root:
            continue
        for filename in files:
            _, ext = os.path.splitext(filename)
            if ext.lower() in video_extensions:
                yield root, filename

def process_files(config):
    """处理配置中的文件"""
    directory = config['directory']
    poster_suffix = config['poster_suffix']
    fanart_suffix = config['fanart_suffix']
    video_extensions = config['video_extensions']
    delete_vsmeta = config.get('delete_vsmeta'， False)  # 默认为False
    
    convert_list = []

    for root, filename in get_video_files(directory, video_extensions):
        vsmeta_path = os.path.join(root, filename + '.vsmeta')
        poster_path = os.path.join(root, os.path.splitext(filename)[0] + poster_suffix)
        fanart_path = os.path.join(root, os.path.splitext(filename)[0] + fanart_suffix)

        # 删除已有的 vsmeta 文件
        if delete_vsmeta and os.path.exists(vsmeta_path):
            try:
                logging.info(f"删除已有 vsmeta 文件: {vsmeta_path}")
                os.remove(vsmeta_path)
            except OSError as e:
                logging.error(f"无法删除 vsmeta 文件 {vsmeta_path}: {e}")
        
        # 检查 nfo 文件并处理
        nfo_path = os.path.join(root, os.path.splitext(filename)[0] + '.nfo')
        if os.path.exists(nfo_path) and not os.path.exists(vsmeta_path):
            convert_list.append(nfo_path)
            try:
                create_vsmeta(nfo_path, vsmeta_path, poster_path, fanart_path)
            except Exception as e:
                logging.error(f"处理文件 {nfo_path} 时出错: {e}")

    logging.info(f"处理完成，共处理 {len(convert_list)} 个文件")
    return convert_list

def create_vsmeta(nfo_path, target_path, poster_path, fanart_path):
    """根据 nfo 文件创建 vsmeta 文件"""
    doc = xmldom.parse(nfo_path)
    metadata = extract_metadata(doc)
    buf = build_vsmeta_content(metadata, poster_path, fanart_path)

    try:
        with open(target_path, 'wb') as op:
            op.write(buf)
        logging.info(f"成功创建 vsmeta 文件: {target_path}")
    except IOError as e:
        logging.error(f"写入 vsmeta 文件 {target_path} 时出错: {e}")

def extract_metadata(doc):
    """从 nfo 文件中提取元数据"""
    return {
        'title': get_node(doc, 'title', '无标题'),
        'sorttitle': get_node(doc, 'sorttitle', '无标题'),
        'tagline': get_node(doc, 'tagline', '无标题'),
        'plot': get_node(doc, 'plot'),
        'year': get_node(doc, 'year', '1900'),
        'level': get_node(doc, 'mpaa', 'G'),
        'date': get_node(doc, 'premiered', '1900-01-01'),
        'rate': get_node(doc, 'rating', '0'),
        'genre': get_node_list(doc, 'genre'),
        'actors': get_node_list(doc, 'actor', 'name'),
        'directors': get_node_list(doc, 'director'),
        'writers': get_node_list(doc, 'writer'),
    }

def build_vsmeta_content(metadata, poster_path, fanart_path):
    """根据元数据构建 vsmeta 文件内容"""
    buf, group = bytearray(), bytearray()
    write_byte(buf, 0x08)
    write_byte(buf, 0x01)

    write_byte(buf, 0x12)
    write_string(buf, metadata['title'])

    # 其他元数据处理省略...

    if os.path.exists(poster_path):
        try:
            poster_final = to_base64(poster_path)
            poster_md5 = to_md5(poster_final)
            write_byte(buf, 0x8A)
            write_byte(buf, 0x01)
            write_string(buf, poster_final)
            write_byte(buf, 0x92)
            write_byte(buf, 0x01)
            write_string(buf, poster_md5)
        except Exception as e:
            logging.error(f"处理海报文件 {poster_path} 时出错: {e}")

    if os.path.exists(fanart_path):
        try:
            fanart_final = to_base64(fanart_path)
            fanart_md5 = to_md5(fanart_final)
            write_byte(group, 0x0A)
            write_string(group, fanart_final)
            write_byte(group, 0x12)
            write_string(group, fanart_md5)
            write_byte(group, 0x18)
            write_int(group, int(time.time()))
            write_int(buf, len(group))
            buf.extend(group)
            group.clear()
        except Exception as e:
            logging.error(f"处理背景文件 {fanart_path} 时出错: {e}")

    return buf

def write_byte(ba, t):
    ba.extend(bytes([int(str(t))]))

def write_string(ba, string):
    byte = string.encode('utf-8')
    length = len(byte)
    write_int(ba, length)
    ba.extend(byte)

def write_int(ba, length):
    while length > 128:
        write_byte(ba, length % 128 + 128)
        length = length // 128
    write_byte(ba, length)

def get_node(doc, tag, default=''):
    nd = doc.getElementsByTagName(tag)
    return nd[0].firstChild.nodeValue if len(nd) > 0 and nd[0].hasChildNodes() else default

def get_node_list(doc, tag, child_tag='', default=[]):
    nds = doc.getElementsByTagName(tag)
    if len(child_tag) == 0:
        return [nd.firstChild.nodeValue for nd in nds if nd.hasChildNodes()]
    return [get_node(nd, child_tag, '') for nd in nds]

def to_base64(pic_path):
    with open(pic_path, "rb") as p:
        return base64.b64encode(p.read()).decode('utf-8')

def to_md5(content):
    return hashlib.md5(content.encode("utf-8")).hexdigest()

def main():
    try:
        config = load_config()
        logging.info("加载配置成功")
        process_files(config)
    except Exception as e:
        logging.error(f"程序运行出错: {e}")

if __name__ == '__main__':
    main()
