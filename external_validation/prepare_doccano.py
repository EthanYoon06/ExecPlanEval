from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = ROOT / "external_validation/results/chinese_translations.jsonl"
OUTPUT = ROOT / "external_validation/doccano"

LABELS = [
    "总体｜有效", "总体｜部分有效", "总体｜无效",
    "工具｜正确", "工具｜部分正确", "工具｜错误",
    "依赖｜正确", "依赖｜缺少必要依赖", "依赖｜依赖错误",
    "执行｜可以执行", "执行｜不确定", "执行｜无法执行",
    "目标｜完整完成", "目标｜部分完成", "目标｜未完成",
    "替代｜是", "替代｜否", "替代｜不确定",
    "错误｜无", "错误｜缺少节点", "错误｜多余节点", "错误｜工具错误",
    "错误｜缺少依赖边", "错误｜依赖边错误", "错误｜顺序错误",
    "错误｜虚构内容", "错误｜其他",
]

# Tool/API identifiers are intentionally preserved verbatim.  The Chinese gloss
# is only an aid for annotators and must not silently change executable names.
TERM_TRANSLATIONS = {
    "No dependency edges": "无依赖边",
    "Dependency edges": "依赖边",
    "action_parameters": "动作参数",
    "parameters": "参数",
    "keywords": "关键词",
    "action": "动作",
    "name": "名称",
    "step": "步骤",
    "search_by_engine": "使用搜索引擎搜索",
    "attend_meeting_online": "参加线上会议",
    "set_alarm": "设置闹钟",
    "daily_bill_payment": "日常账单支付",
    "get_weather": "查询天气",
    "sell_item_online": "在线出售物品",
    "take_note": "记录笔记",
    "software_management": "软件管理",
    "make_video_call": "发起视频通话",
    "play_movie_by_title": "按标题播放电影",
    "play_music_by_title": "按标题播放音乐",
    "share_by_social_network": "通过社交网络分享",
    "apply_for_job": "申请职位",
    "online_shopping": "在线购物",
    "order_food_delivery": "订购外卖",
    "book_car": "预订车辆",
    "auto_driving_to_destination": "自动驾驶到目的地",
    "borrow_book_online": "在线借书",
    "stock_operation": "股票操作",
    "consult_lawyer_online": "在线咨询律师",
    "print_document": "打印文档",
    "book_hotel": "预订酒店",
    "order_taxi": "叫出租车",
    "enroll_in_course": "报名课程",
    "online_banking": "网上银行",
    "buy_insurance": "购买保险",
    "pay_for_credit_card": "偿还信用卡",
    "install": "安装",
    "search": "搜索",
    "click": "点击",
    "Audio Noise Reduction": "音频降噪",
    "Audio Classification": "音频分类",
    "Audio Effects": "音频效果",
    "Audio Downloader": "音频下载",
    "Audio Splicer": "音频拼接",
    "Audio-to-Audio": "音频到音频转换",
    "Audio-to-Text": "音频转文本",
    "Audio-to-Image": "音频转图像",
    "Text-to-Audio": "文本转音频",
    "Text-to-Speech": "文本转语音",
    "Text-to-Image": "文本生成图像",
    "Text-to-Video": "文本生成视频",
    "Text Search": "文本搜索",
    "Text Sentiment Analysis": "文本情感分析",
    "Text Grammar Checker": "文本语法检查",
    "Text Translator": "文本翻译",
    "Text Generation": "文本生成",
    "Image Classification": "图像分类",
    "Image Segmentation": "图像分割",
    "Image Editing": "图像编辑",
    "Image Search (by Image)": "以图搜图",
    "Image Search": "图像搜索",
    "Image-to-Text": "图像转文本",
    "Image-to-Image": "图像到图像转换",
    "Image-to-Video": "图像转视频",
    "Image Colorizer": "图像上色",
    "Image Stitcher": "图像拼接",
    "Image Style Transfer": "图像风格迁移",
    "Image Downloader": "图像下载",
    "Video-to-Image": "视频转图像",
    "Video-to-Text": "视频转文本",
    "Video Voiceover": "视频配音",
    "Video Synchronization": "视频同步",
    "Object Detection": "物体检测",
    "Visual Question Answering": "视觉问答",
    "Document Question Answering": "文档问答",
    "Question Answering": "问答",
    "Sentence Similarity": "句子相似度分析",
    "Depth Estimation": "深度估计",
    "Tabular Classification": "表格分类",
    "Keyword Extractor": "关键词提取",
    "Summarization": "摘要生成",
    "Translation": "翻译",
    "Conversational": "对话",
    "Voice Changer": "变声",
    "go to": "前往",
    "open": "打开",
    "task": "拿取",
    "put": "放置",
    "clean": "清洁",
    "heat": "加热",
    "look at": "查看",
    "examine": "检查",
    "from": "从",
    "with": "使用",
    "in/on": "放入或放在",
    "fridge": "冰箱",
    "drawer": "抽屉",
    "cabinet": "柜子",
    "garbagecan": "垃圾桶",
    "diningtable": "餐桌",
    "sidetable": "边桌",
    "countertop": "台面",
    "sinkbasin": "水槽",
    "bathtubbasin": "浴缸",
    "toilet": "马桶",
    "desk": "书桌",
    "bed": "床",
    "microwave": "微波炉",
    "stoveburner": "炉灶",
    "coffeemachine": "咖啡机",
    "desklamp": "台灯",
    "cellphone": "手机",
    "newspaper": "报纸",
    "potato": "土豆",
    "tomato": "番茄",
    "egg": "鸡蛋",
    "mug": "杯子",
    "candle": "蜡烛",
    "soapbottle": "洗手液瓶",
    "dishsponge": "洗碗海绵",
    "toiletpaperhanger": "厕纸架",
    "ladle": "长柄勺",
    "watch": "手表",
    "pen": "笔",
    "vase": "花瓶",
    "Perform lunges.": "做弓步训练。",
    "Lunge forward with your right leg and put your left knee on the ground.": "右腿向前弓步，左膝触地。",
    "Twist hips forward to form a lunge position.": "髋部向前转动，形成弓步姿势。",
    "Curl your arms toward your shoulder while maintaining the lunge position.": "保持弓步的同时，将手臂弯向肩部。",
    "Do 15 to 20 repetitions of this exercise per set on each side.": "每侧每组重复15至20次。",
    "Do 3 sets 4 days a week for 5 weeks.": "每周训练4天，每次3组，持续5周。",
}


def add_chinese_gloss(plan: str) -> str:
    """Return a bilingual, display-only explanation of a candidate plan."""
    explanation = plan
    for term in sorted(TERM_TRANSLATIONS, key=len, reverse=True):
        gloss = TERM_TRANSLATIONS[term]
        # Do not add the same gloss twice to already bilingual content.
        left = r"(?<![A-Za-z0-9_])" if term[0].isalnum() else ""
        right = r"(?![A-Za-z0-9_])" if term[-1].isalnum() else ""
        pattern = left + re.escape(term) + right + rf"(?!\s*[（(]{re.escape(gloss)}[）)])"
        explanation = re.sub(pattern, f"{term}（{gloss}）", explanation)
    explanation = re.sub(
        r"search（搜索）\[([^\]]+)\]",
        r"search（搜索）[英文关键词原值：\1；中文商品条件见上方任务说明]",
        explanation,
    )
    explanation = explanation.replace(
        "keywords（关键词）",
        "keywords（关键词；英文原值的中文含义见上方任务说明）",
    )
    return explanation


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = [
        json.loads(line)
        for line in TRANSLATIONS.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != 120:
        raise ValueError(f"Expected 120 translated records, found {len(rows)}")
    documents = []
    for row in rows:
        text = (
            f'【标注编号】{row["annotation_id"]}\n'
            f'【任务编号】{row["task_id"]}\n\n'
            f'【任务说明】\n{row["instruction_zh"]}\n\n'
            f'【候选计划（原始结构，工具名不可改）】\n{row["candidate_plan_zh"]}\n\n'
            f'【候选计划中文辅助解释】\n{add_chinese_gloss(row["candidate_plan_zh"])}\n\n'
            "【操作提醒】请从总体、工具、依赖、执行、目标、替代、错误七组标签中各选一个。"
        )
        # Doccano's JSONL importer expects the configured label column to exist.
        # An empty list keeps every record genuinely unlabelled at import time.
        documents.append({"text": text, "label": []})
    for annotator in ("A", "B"):
        path = OUTPUT / f"人工标注_{annotator}_doccano.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for document in documents:
                handle.write(json.dumps(document, ensure_ascii=False) + "\n")
    (OUTPUT / "标签列表.txt").write_text("\n".join(LABELS) + "\n", encoding="utf-8")
    print(f"Wrote {len(documents)} records for each annotator and {len(LABELS)} labels")


if __name__ == "__main__":
    main()
