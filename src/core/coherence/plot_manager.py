"""
剧情线管理系统 - 追踪主线、副线、伏笔、悬念

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import json
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class PlotStatus(Enum):
    """剧情线状态"""
    ONGOING = "ongoing"          # 进行中
    RESOLVED = "resolved"        # 已解决
    ABANDONED = "abandoned"      # 已放弃
    PAUSED = "paused"            # 暂停


class PlotType(Enum):
    """剧情线类型"""
    MAIN = "main"                # 主线
    SIDE = "side"                # 副线
    CHARACTER = "character"      # 角色线
    ROMANCE = "romance"          # 感情线
    MYSTERY = "mystery"          # 悬疑线
    CONFLICT = "conflict"        # 冲突线


@dataclass
class PlotEvent:
    """剧情事件"""
    chapter_num: int              # 发生的章节
    description: str             # 事件描述
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PlotThread:
    """剧情线"""
    id: str                      # 唯一标识
    name: str                    # 剧线名称
    plot_type: str               # 类型
    status: str = PlotStatus.ONGOING.value  # 状态
    description: str = ""        # 描述
    key_events: List[PlotEvent] = field(default_factory=list)  # 关键事件
    foreshadowing: List[str] = field(default_factory=list)     # 伏笔列表
    cliffhangers: List[str] = field(default_factory=list)      # 悬念列表
    related_characters: List[str] = field(default_factory=list)  # 相关角色
    introduced_chapter: int = 0  # 引入章节
    resolved_chapter: Optional[int] = None  # 解决章节
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['key_events'] = [event.__dict__ for event in self.key_events]
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'PlotThread':
        """从字典创建"""
        key_events = [
            PlotEvent(**event_data)
            for event_data in data.pop('key_events', [])
        ]
        return cls(key_events=key_events, **data)


class PlotManager:
    """
    剧情线管理器

    功能：
    1. 管理所有剧情线（主线、副线、角色线等）
    2. 追踪伏笔和悬念
    3. 检测剧情连贯性
    4. 提供剧情进展查询
    """

    def __init__(self, project_id: str, cache_dir: Optional[Path] = None):
        """
        初始化剧情管理器

        Args:
            project_id: 项目ID
            cache_dir: 缓存目录
        """
        self.project_id = project_id
        self.cache_dir = cache_dir or Path("cache/coherence")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # 所有剧情线 {thread_id: PlotThread}
        self.plot_threads: Dict[str, PlotThread] = {}

        # 章节 -> 剧情线索引 {chapter_num: [thread_ids]}
        self.chapter_to_plots: Dict[int, List[str]] = {}

        # 未解决的伏笔
        self.unresolved_foreshadowing: Dict[str, str] = {}  # {description: thread_id}

        # 未解决的悬念
        self.unresolved_cliffhangers: Dict[str, str] = {}  # {description: thread_id}

        # 加载已有数据
        self._load_from_disk()

    def add_plot_thread(
        self,
        thread_id: str,
        name: str,
        plot_type: str,
        description: str = "",
        chapter_num: int = 0,
        related_characters: Optional[List[str]] = None
    ) -> PlotThread:
        """
        添加新剧情线

        Args:
            thread_id: 剧线ID
            name: 名称
            plot_type: 类型
            description: 描述
            chapter_num: 引入章节
            related_characters: 相关角色

        Returns:
            创建的PlotThread对象
        """
        thread = PlotThread(
            id=thread_id,
            name=name,
            plot_type=plot_type,
            description=description,
            introduced_chapter=chapter_num,
            related_characters=related_characters or []
        )

        self.plot_threads[thread_id] = thread

        if chapter_num not in self.chapter_to_plots:
            self.chapter_to_plots[chapter_num] = []
        self.chapter_to_plots[chapter_num].append(thread_id)

        logger.info(f"添加剧情线: {name} (类型: {plot_type})")
        return thread

    def add_plot_event(
        self,
        thread_id: str,
        chapter_num: int,
        description: str
    ) -> None:
        """
        添加剧情事件

        Args:
            thread_id: 剧线ID
            chapter_num: 章节号
            description: 事件描述
        """
        if thread_id not in self.plot_threads:
            logger.warning(f"剧情线 {thread_id} 不存在")
            return

        event = PlotEvent(
            chapter_num=chapter_num,
            description=description
        )

        self.plot_threads[thread_id].key_events.append(event)

        # 更新章节索引
        if chapter_num not in self.chapter_to_plots:
            self.chapter_to_plots[chapter_num] = []
        if thread_id not in self.chapter_to_plots[chapter_num]:
            self.chapter_to_plots[chapter_num].append(thread_id)

        logger.info(f"添加剧情事件: {thread_id} 在第{chapter_num}章")

    def add_foreshadowing(
        self,
        thread_id: str,
        foreshadowing: str
    ) -> None:
        """
        添加伏笔

        Args:
            thread_id: 剧线ID
            foreshadowing: 伏笔描述
        """
        if thread_id not in self.plot_threads:
            logger.warning(f"剧情线 {thread_id} 不存在")
            return

        self.plot_threads[thread_id].foreshadowing.append(foreshadowing)
        self.unresolved_foreshadowing[foreshadowing] = thread_id

        logger.info(f"添加伏笔: {foreshadowing[:50]}... (剧情线: {thread_id})")

    def add_cliffhanger(
        self,
        thread_id: str,
        cliffhanger: str,
        chapter_num: int
    ) -> None:
        """
        添加悬念

        Args:
            thread_id: 剧线ID
            cliffhanger: 悬念描述
            chapter_num: 章节号
        """
        if thread_id not in self.plot_threads:
            logger.warning(f"剧情线 {thread_id} 不存在")
            return

        self.plot_threads[thread_id].cliffhangers.append(cliffhanger)
        self.unresolved_cliffhangers[cliffhanger] = thread_id

        # 同时作为事件记录
        self.add_plot_event(thread_id, chapter_num, f"悬念: {cliffhanger}")

        logger.info(f"添加悬念: {cliffhanger[:50]}... (第{chapter_num}章)")

    def resolve_foreshadowing(
        self,
        foreshadowing: str,
        resolution_chapter: int,
        resolution_description: str
    ) -> None:
        """
        解决伏笔

        Args:
            foreshadowing: 伏笔描述
            resolution_chapter: 解决章节
            resolution_description: 解决方式描述
        """
        thread_id = self.unresolved_foreshadowing.get(foreshadowing)
        if not thread_id:
            logger.warning(f"未找到伏笔: {foreshadowing}")
            return

        # 添加解决事件
        self.add_plot_event(
            thread_id,
            resolution_chapter,
            f"伏笔回应: {foreshadowing} → {resolution_description}"
        )

        # 从未解决列表中移除
        del self.unresolved_foreshadowing[foreshadowing]

        # 从剧情线的伏笔列表中标记为已解决
        thread = self.plot_threads[thread_id]
        if foreshadowing in thread.foreshadowing:
            thread.foreshadowing.remove(foreshadowing)

        logger.info(f"解决伏笔: {foreshadowing[:50]}... 在第{resolution_chapter}章")

    def resolve_cliffhanger(
        self,
        cliffhanger: str,
        resolution_chapter: int,
        resolution_description: str
    ) -> None:
        """
        解决悬念

        Args:
            cliffhanger: 悬念描述
            resolution_chapter: 解决章节
            resolution_description: 解决方式描述
        """
        thread_id = self.unresolved_cliffhangers.get(cliffhanger)
        if not thread_id:
            logger.warning(f"未找到悬念: {cliffhanger}")
            return

        # 添加解决事件
        self.add_plot_event(
            thread_id,
            resolution_chapter,
            f"悬念揭晓: {cliffhanger} → {resolution_description}"
        )

        # 从未解决列表中移除
        del self.unresolved_cliffhangers[cliffhanger]

        # 从剧情线的悬念列表中标记为已解决
        thread = self.plot_threads[thread_id]
        if cliffhanger in thread.cliffhangers:
            thread.cliffhangers.remove(cliffhanger)

        logger.info(f"解决悬念: {cliffhanger[:50]}... 在第{resolution_chapter}章")

    def update_thread_status(
        self,
        thread_id: str,
        new_status: PlotStatus,
        resolved_chapter: Optional[int] = None
    ) -> None:
        """
        更新剧情线状态

        Args:
            thread_id: 剧线ID
            new_status: 新状态
            resolved_chapter: 解决章节（如果状态为resolved）
        """
        if thread_id not in self.plot_threads:
            logger.warning(f"剧情线 {thread_id} 不存在")
            return

        thread = self.plot_threads[thread_id]
        old_status = thread.status
        thread.status = new_status.value

        if new_status == PlotStatus.RESOLVED and resolved_chapter:
            thread.resolved_chapter = resolved_chapter

        logger.info(f"剧情线 {thread_id} 状态更新: {old_status} -> {new_status.value}")

    def get_active_threads(self) -> List[PlotThread]:
        """获取所有进行中的剧情线"""
        return [
            thread for thread in self.plot_threads.values()
            if thread.status == PlotStatus.ONGOING.value
        ]

    def get_threads_in_chapter(self, chapter_num: int) -> List[PlotThread]:
        """获取指定章节中涉及的所有剧情线"""
        thread_ids = self.chapter_to_plots.get(chapter_num, [])
        return [self.plot_threads[tid] for tid in thread_ids if tid in self.plot_threads]

    def get_unresolved_foreshadowing(self, thread_id: Optional[str] = None) -> List[str]:
        """
        获取未解决的伏笔

        Args:
            thread_id: 指定剧情线ID，None表示所有

        Returns:
            伏笔描述列表
        """
        if thread_id:
            return [
                fs for fs, tid in self.unresolved_foreshadowing.items()
                if tid == thread_id
            ]
        return list(self.unresolved_foreshadowing.keys())

    def get_unresolved_cliffhangers(self, thread_id: Optional[str] = None) -> List[str]:
        """
        获取未解决的悬念

        Args:
            thread_id: 指定剧情线ID，None表示所有

        Returns:
            悬念描述列表
        """
        if thread_id:
            return [
                ch for ch, tid in self.unresolved_cliffhangers.items()
                if tid == thread_id
            ]
        return list(self.unresolved_cliffhangers.keys())

    def check_thread_continuity(self) -> List[str]:
        """
        检查剧情连贯性

        Returns:
            问题列表
        """
        issues = []

        # 检查长时间未更新的剧情线
        for thread in self.plot_threads.values():
            if thread.status != PlotStatus.ONGOING.value:
                continue

            if thread.key_events:
                last_event = thread.key_events[-1]
                # 如果有事件但最后一个事件很早之前，可能被遗忘
                # 这里简化处理，实际应该基于章节间隔判断

                pass

        # 检查长期未解决的伏笔和悬念
        if len(self.unresolved_foreshadowing) > 10:
            issues.append(f"未解决的伏笔过多: {len(self.unresolved_foreshadowing)}个")

        if len(self.unresolved_cliffhangers) > 5:
            issues.append(f"未解决的悬念过多: {len(self.unresolved_cliffhangers)}个")

        return issues

    def get_plot_summary_for_context(
        self,
        current_chapter: int,
        max_length: int = 500
    ) -> str:
        """
        生成剧情摘要，用于上下文生成

        Args:
            current_chapter: 当前章节号
            max_length: 最大长度（字符数）

        Returns:
            剧情摘要文本
        """
        active_threads = self.get_active_threads()

        if not active_threads:
            return ""

        summary_parts = ["【剧情进展】"]

        for thread in active_threads[:3]:  # 最多3条主线
            thread_summary = f"\n{thread.name}（{thread.plot_type}）: "

            # 添加最近的事件
            recent_events = [
                event for event in thread.key_events
                if event.chapter_num < current_chapter
            ]
            if recent_events:
                last_event = recent_events[-1]
                thread_summary += f"{last_event.description}"

            # 添加未解决的伏笔
            foreshadowing = self.get_unresolved_foreshadowing(thread.id)
            if foreshadowing:
                thread_summary += f"\n  未解决伏笔: {foreshadowing[0]}"

            # 添加未解决的悬念
            cliffhangers = self.get_unresolved_cliffhangers(thread.id)
            if cliffhangers:
                thread_summary += f"\n  当前悬念: {cliffhangers[0]}"

            summary_parts.append(thread_summary)

        summary = "\n".join(summary_parts)

        # 截断到最大长度
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    def save_to_disk(self) -> None:
        """保存数据到磁盘"""
        data = {
            "project_id": self.project_id,
            "plot_threads": {
                thread_id: thread.to_dict()
                for thread_id, thread in self.plot_threads.items()
            },
            "chapter_to_plots": self.chapter_to_plots,
            "unresolved_foreshadowing": self.unresolved_foreshadowing,
            "unresolved_cliffhangers": self.unresolved_cliffhangers
        }

        cache_file = self.cache_dir / f"{self.project_id}_plots.json"
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"剧情管理数据已保存: {cache_file}")

    def _load_from_disk(self) -> None:
        """从磁盘加载数据"""
        cache_file = self.cache_dir / f"{self.project_id}_plots.json"

        if not cache_file.exists():
            return

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.chapter_to_plots = data.get("chapter_to_plots", {})
            self.unresolved_foreshadowing = data.get("unresolved_foreshadowing", {})
            self.unresolved_cliffhangers = data.get("unresolved_cliffhangers", {})

            # 加载剧情线
            for thread_id, thread_data in data.get("plot_threads", {}).items():
                self.plot_threads[thread_id] = PlotThread.from_dict(thread_data)

            logger.info(f"剧情管理数据已加载: {cache_file}")

        except Exception as e:
            logger.error(f"加载剧情管理数据失败: {e}")


# AI辅助的剧情分析功能
def analyze_plot_from_chapter(
    chapter_content: str,
    chapter_outline: str,
    chapter_num: int,
    plot_manager: PlotManager,
    api_client
) -> None:
    """
    使用AI分析章节内容，提取剧情信息

    Args:
        chapter_content: 章节内容
        chapter_outline: 章节大纲
        chapter_num: 章节号
        plot_manager: 剧情管理器
        api_client: API客户端
    """
    prompt = f"""分析以下小说章节，提取剧情线信息。

章节大纲：
{chapter_outline}

章节内容：
{chapter_content[:2000]}

【重要】请以JSON格式返回，注意：
1. 只返回JSON，不要有任何其他文字
2. 确保JSON完整，不要中途截断
3. 所有引号使用英文双引号"

JSON格式：
{{
    "plot_threads": [
        {{
            "id": "唯一ID",
            "name": "剧情线名称",
            "type": "main或side或character",
            "description": "简要描述",
            "related_characters": ["角色1"]
        }}
    ],
    "plot_events": [
        {{
            "thread_id": "剧情线ID",
            "description": "事件描述"
        }}
    ],
    "foreshadowing": [
        {{
            "thread_id": "剧情线ID",
            "description": "伏笔描述"
        }}
    ],
    "cliffhangers": [
        {{
            "thread_id": "剧情线ID",
            "description": "悬念描述"
        }}
    ]
}}

现在请直接返回完整的JSON："""

    try:
        response = api_client.generate([
            {"role": "system", "content": "你是一个专业的小说分析助手。你必须只返回有效的JSON格式数据，不要添加任何其他文字。"},
            {"role": "user", "content": prompt}
        ], temperature=0.3, max_tokens=3000)  # 增加max_tokens到3000避免输出被截断

        # 清理响应：移除可能的 Markdown 代码块标记
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()

        # 尝试解析 JSON，带有容错处理
        if not cleaned_response:
            logger.warning(f"AI剧情分析返回空响应")
            return

        result = _parse_json_with_fallback(cleaned_response, logger, "AI剧情分析")
        if result is None:
            return

        # 添加新剧情线
        for thread_data in result.get("plot_threads", []):
            plot_manager.add_plot_thread(
                thread_id=thread_data["id"],
                name=thread_data["name"],
                plot_type=thread_data["type"],
                description=thread_data.get("description", ""),
                chapter_num=chapter_num,
                related_characters=thread_data.get("related_characters", [])
            )

        # 添加剧情事件
        for event in result.get("plot_events", []):
            plot_manager.add_plot_event(
                event["thread_id"],
                chapter_num,
                event["description"]
            )

        # 添加伏笔
        for fs in result.get("foreshadowing", []):
            plot_manager.add_foreshadowing(
                fs["thread_id"],
                fs["description"]
            )

        # 添加悬念
        for ch in result.get("cliffhangers", []):
            plot_manager.add_cliffhanger(
                ch["thread_id"],
                ch["description"],
                chapter_num
            )

        logger.info(f"AI剧情分析完成")

    except Exception as e:
        logger.error(f"AI剧情分析失败: {e}")


def _parse_json_with_fallback(text: str, logger, context: str = "JSON解析"):
    """
    容错的JSON解析函数，尝试修复常见格式问题

    Args:
        text: 要解析的文本
        logger: 日志记录器
        context: 上下文描述

    Returns:
        解析后的字典，失败返回None
    """
    import re

    def try_parse(data: str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return None

    # 预处理：去除markdown标记和前后缀
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # 去除前缀文字
    first_brace = cleaned.find('{')
    if first_brace > 0:
        cleaned = cleaned[first_brace:]

    # 第一次尝试：直接解析
    result = try_parse(cleaned)
    if result:
        return result

    # 第二次尝试：替换中文标点符号
    fixed = cleaned
    chinese_punct_map = {
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '：': ':',
        '，': ',',
        '【': '[',
        '】': ']',
        '（': '(',
        '）': ')',
    }
    for cn, en in chinese_punct_map.items():
        fixed = fixed.replace(cn, en)
    result = try_parse(fixed)
    if result:
        logger.warning(f"{context}: 通过替换中文标点修复成功")
        return result

    # 第三次尝试：修复缺少逗号的问题
    fixed = cleaned
    fixed = re.sub(r'}\s*"', '}, "', fixed)
    fixed = re.sub(r']\s*"', '], "', fixed)
    fixed = re.sub(r',\s*\]', ']', fixed)
    fixed = re.sub(r',\s*\}', '}', fixed)
    result = try_parse(fixed)
    if result:
        logger.warning(f"{context}: 通过修复逗号成功")
        return result

    # 第四次尝试：检测并修复截断的JSON
    open_braces = cleaned.count('{')
    close_braces = cleaned.count('}')
    open_brackets = cleaned.count('[')
    close_brackets = cleaned.count(']')

    if open_braces != close_braces or open_brackets != close_brackets:
        logger.info(f"{context}: 检测到JSON不完整，尝试修复截断")
        
        # 尝试补全缺失的括号
        fixed = cleaned
        # 补全缺失的 ]
        missing_brackets = open_brackets - close_brackets
        fixed += ']' * missing_brackets
        # 补全缺失的 }
        missing_braces = open_braces - close_braces
        fixed += '}' * missing_braces
        
        result = try_parse(fixed)
        if result:
            logger.warning(f"{context}: 通过补全括号修复成功")
            return result

    # 第五次尝试：提取JSON代码块
    json_match = re.search(r'\{[\s\S]*\}', cleaned)
    if json_match:
        result = try_parse(json_match.group(0))
        if result:
            logger.warning(f"{context}: 通过提取JSON块成功")
            return result

    # 第六次尝试：使用更宽松的解析
    try:
        compact = re.sub(r'\s+', ' ', cleaned.strip())
        result = try_parse(compact)
        if result:
            logger.warning(f"{context}: 通过压缩空白成功")
            return result
    except:
        pass

    # 记录原始内容用于调试
    logger.error(f"{context}最终失败，原始内容前500字符: {text[:500]}")
    return None
