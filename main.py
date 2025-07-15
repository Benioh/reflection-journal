import flet as ft
from datetime import datetime
import logging
import threading
import queue
from database import Database
from ai_service import AIService
from github_sync import GitHubSync
from sync_manager import SyncManager  # 新增
from config import Config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReflectionJournalApp:
    def __init__(self):
        self.db = Database()
        self.ai_service = AIService()
        self.github_sync = GitHubSync()
        self.sync_manager = SyncManager(Config.DB_PATH)  # 新增
        self.current_page = "write"
        self.search_mode = "keyword"  # keyword or vector
        
        # 创建备份队列和处理线程，避免GitHub并发冲突
        self.backup_queue = queue.Queue()
        self.backup_thread = threading.Thread(target=self._process_backup_queue, daemon=True)
        self.backup_thread.start()
        
        # 用于跟踪文本选择状态（模拟）
        self.last_text_length = 0
        self.selection_start = -1
        self.selection_end = -1
        
    def main(self, page: ft.Page):
        page.title = "复盘日志 - Reflection Journal"
        page.window_width = Config.WINDOW_WIDTH
        page.window_height = Config.WINDOW_HEIGHT
        page.theme_mode = Config.THEME_MODE
        page.padding = 0
        
        # 创建UI组件
        self.page = page
        self.create_ui()
        
        # 启动自动同步（新增）
        self.sync_manager.start_auto_sync()
        
        # 添加同步完成回调，刷新当前页面（新增）
        self.sync_manager.add_sync_callback(self.on_sync_complete)
        
        # 显示同步状态（新增）
        if self.github_sync.is_configured():
            self.show_snackbar("正在同步数据...")
        
        # 添加全局键盘事件监听
        page.on_keyboard_event = self.handle_keyboard_event

    def on_sync_complete(self):
        """同步完成后的回调"""
        # 如果在浏览页面，刷新列表
        if self.current_page == "browse":
            self.show_browse_page()
        # 更新同步状态显示
        if hasattr(self, 'sync_status_text'):
            self.update_sync_status()
            
    def create_ui(self):
        # 导航栏
        self.nav_rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=100,
            min_extended_width=200,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.EDIT_OUTLINED,
                    selected_icon=ft.Icons.EDIT,
                    label="写记录",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.LIST_OUTLINED,
                    selected_icon=ft.Icons.LIST,
                    label="浏览",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SEARCH_OUTLINED,
                    selected_icon=ft.Icons.SEARCH,
                    label="搜索",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ANALYTICS_OUTLINED,
                    selected_icon=ft.Icons.ANALYTICS,
                    label="统计",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="设置",
                ),
            ],
            on_change=self.nav_changed,
        )
        
        # 内容区域
        self.content_area = ft.Container(
            expand=True,
            padding=20,
        )
        
        # 同步状态栏（新增）
        self.sync_status_bar = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.SYNC, size=16),
                self.create_sync_status_text(),
            ]),
            padding=5,
            visible=self.github_sync.is_configured(),
        )
        
        # 主布局
        self.page.add(
            ft.Column([
                self.sync_status_bar,  # 新增状态栏
                ft.Row(
                    [
                        self.nav_rail,
                        ft.VerticalDivider(width=1),
                        self.content_area,
                    ],
                    expand=True,
                ),
            ], expand=True)
        )
        
        # 显示初始页面
        self.show_write_page()
        
    def create_sync_status_text(self):
        """创建同步状态文本（新增）"""
        status = self.sync_manager.get_sync_status()
        if status['is_syncing']:
            text = "正在同步..."
            color = ft.Colors.BLUE_600
        elif status['last_sync_time']:
            # 计算距离上次同步的时间
            # 确保时间比较使用相同的时区
            from datetime import timezone
            current_time = datetime.now(timezone.utc) if status['last_sync_time'].tzinfo else datetime.now()
            time_diff = current_time - status['last_sync_time']
            
            total_seconds = time_diff.total_seconds()
            if total_seconds < 60:
                text = "刚刚同步"
            elif total_seconds < 3600:
                text = f"{int(total_seconds // 60)}分钟前同步"
            elif total_seconds < 86400:  # 24小时
                text = f"{int(total_seconds // 3600)}小时前同步"
            else:
                days = int(total_seconds // 86400)
                text = f"{days}天前同步"
            color = ft.Colors.GREEN_600
        else:
            # 检查是否配置了GitHub
            if hasattr(self, 'sync_manager') and self.sync_manager.github_sync.is_configured():
                text = "从未同步"
            else:
                text = "未配置同步"
            color = ft.Colors.GREY_600
            
        self.sync_status_text = ft.Text(text, size=12, color=color)
        return self.sync_status_text
        
    def update_sync_status(self):
        """更新同步状态显示（新增）"""
        status = self.sync_manager.get_sync_status()
        if status['is_syncing']:
            self.sync_status_text.value = "正在同步..."
            self.sync_status_text.color = ft.Colors.BLUE_600
        elif status['last_sync_time']:
            # 确保时间比较使用相同的时区
            from datetime import timezone
            current_time = datetime.now(timezone.utc) if status['last_sync_time'].tzinfo else datetime.now()
            time_diff = current_time - status['last_sync_time']
            
            total_seconds = time_diff.total_seconds()
            if total_seconds < 60:
                self.sync_status_text.value = "刚刚同步"
            elif total_seconds < 3600:
                self.sync_status_text.value = f"{int(total_seconds // 60)}分钟前同步"
            elif total_seconds < 86400:  # 24小时
                self.sync_status_text.value = f"{int(total_seconds // 3600)}小时前同步"
            else:
                days = int(total_seconds // 86400)
                self.sync_status_text.value = f"{days}天前同步"
            self.sync_status_text.color = ft.Colors.GREEN_600
        else:
            # 检查是否配置了GitHub
            if status['is_configured']:
                self.sync_status_text.value = "从未同步"
            else:
                self.sync_status_text.value = "未配置同步"
            self.sync_status_text.color = ft.Colors.GREY_600
        self.page.update()
    
    def nav_changed(self, e):
        index = e.control.selected_index
        if index == 0:
            self.current_page = "write"  # 记录当前页面
            self.show_write_page()
        elif index == 1:
            self.current_page = "browse"
            self.show_browse_page()
        elif index == 2:
            self.current_page = "search"
            self.show_search_page()
        elif index == 3:
            self.current_page = "stats"
            self.show_stats_page()
        elif index == 4:
            self.current_page = "settings"
            self.show_settings_page()
    
    def show_write_page(self):
        """显示写作页面"""
        self.content_input = ft.TextField(
            label="记录你的想法...",
            multiline=True,
            min_lines=10,
            max_lines=20,
            expand=True,
            on_change=self.update_preview,
        )
        

        
        # Markdown 预览区
        self.markdown_preview = ft.Markdown(
            "预览将在这里显示...",
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            code_theme="github",
            on_tap_link=lambda e: self.page.launch_url(e.data),
        )
        
        self.preview_container = ft.Container(
            content=self.markdown_preview,
            bgcolor=ft.Colors.GREY_100,
            border_radius=10,
            padding=20,
            expand=True,
            visible=False,  # 默认隐藏
        )
        
        # 预览开关
        self.preview_switch = ft.Switch(
            label="显示预览",
            value=False,
            on_change=self.toggle_preview,
        )
        
        self.type_dropdown = ft.Dropdown(
            label="类型",
            width=200,
            value="灵光一闪",
            options=[
                ft.dropdown.Option("灵光一闪", "灵光一闪"),
                ft.dropdown.Option("阶段总结", "阶段总结"),
                ft.dropdown.Option("项目复盘", "项目复盘"),
            ],
        )
        
        save_button = ft.ElevatedButton(
            "保存",
            icon=ft.Icons.SAVE,
            on_click=self.save_reflection,
        )
        

        
        # Markdown 帮助提示
        markdown_help = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=ft.Colors.BLUE_400),
                    ft.Text(
                        "支持 Markdown：**粗体** *斜体* `代码` # 标题 - 列表 [链接](url)",
                        size=12,
                        color=ft.Colors.BLUE_400,
                    ),
                ]),
                ft.Row([
                    ft.Icon(ft.Icons.KEYBOARD, size=16, color=ft.Colors.BLUE_400),
                    ft.Text(
                        self._get_keyboard_shortcuts_text(),
                        size=12,
                        color=ft.Colors.BLUE_400,
                    ),
                ]),
            ], spacing=5),
            padding=ft.padding.only(top=5),
        )
        
        # 编辑区和预览区的容器
        self.edit_preview_container = ft.Row(
            [
                ft.Container(self.content_input, expand=True),
                ft.Container(width=10),  # 间隔
                self.preview_container,
            ],
            expand=True,
        )
        
        self.content_area.content = ft.Column(
            [
                ft.Row([
                    ft.Text("写下你的想法", size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    self.preview_switch,
                ]),
                markdown_help,
                ft.Container(height=20),
                self.type_dropdown,
                ft.Container(height=10),
                self.edit_preview_container,
                ft.Container(height=20),
                ft.Row([save_button], alignment=ft.MainAxisAlignment.END),
            ],
            expand=True,
        )
        self.page.update()
    
    def _get_keyboard_shortcuts_text(self):
        """获取键盘快捷键提示文本（根据平台）"""
        import platform
        is_mac = platform.system() == "Darwin"
        modifier = "Cmd" if is_mac else "Ctrl"
        return f"快捷键：{modifier}+B 粗体 | {modifier}+I 斜体"
    
    def update_preview(self, e):
        """更新 Markdown 预览"""
        if hasattr(self, 'markdown_preview') and self.content_input.value:
            self.markdown_preview.value = self.content_input.value
            self.page.update()
    
    def toggle_preview(self, e):
        """切换预览显示"""
        show_preview = self.preview_switch.value
        self.preview_container.visible = show_preview
        
        if show_preview:
            # 显示预览时，编辑区和预览区各占一半
            self.edit_preview_container.controls = [
                ft.Container(self.content_input, expand=True),
                ft.Container(width=10),
                self.preview_container,
            ]
            # 更新预览内容
            if self.content_input.value:
                self.markdown_preview.value = self.content_input.value
            else:
                self.markdown_preview.value = "预览将在这里显示..."
        else:
            # 隐藏预览时，编辑区占满
            self.edit_preview_container.controls = [
                ft.Container(self.content_input, expand=True),
            ]
        
        self.page.update()
    
    def handle_keyboard_event(self, e: ft.KeyboardEvent):
        """处理全局键盘事件"""
        # 只在写作页面处理快捷键
        if self.current_page != "write" or not hasattr(self, 'content_input'):
            return
        
        # 检测平台，Mac 使用 meta（Command），其他平台使用 ctrl
        import platform
        is_mac = platform.system() == "Darwin"
        modifier_pressed = e.meta if is_mac else e.ctrl
        
        # Command/Ctrl + B 粗体
        if modifier_pressed and e.key == "B":
            self.insert_markdown_format("**", "**", "粗体文本")
        # Command/Ctrl + I 斜体
        elif modifier_pressed and e.key == "I":
            self.insert_markdown_format("*", "*", "斜体文本")
    
    def insert_markdown_format(self, prefix, suffix, default_text):
        """插入 Markdown 格式 - 简单在文本末尾添加格式标记"""
        if not hasattr(self, 'content_input'):
            return
        
        text = self.content_input.value or ""
        
        # 简单地在文本末尾添加格式标记
        formatted_text = prefix + suffix
        new_text = text + formatted_text
        
        self.content_input.value = new_text
        if hasattr(self, 'markdown_preview') and self.preview_container.visible:
            self.markdown_preview.value = new_text
        self.page.update()
        self.content_input.focus()
    

    
    def save_reflection(self, e):
        """保存反思记录"""
        content = self.content_input.value
        if not content:
            self.show_snackbar("请输入内容")
            return
        
        # 立即清空输入
        self.content_input.value = ""
        reflection_type = self.type_dropdown.value
        self.page.update()
        
        # 先保存记录到数据库（不等待AI分析）
        try:
            # 立即保存基础记录
            reflection_id = self.db.add_reflection(
                content=content,
                summary="",
                tags=[],
                category="其他",
                type=reflection_type,
                embedding=None
            )
            
            # 显示保存成功的提示
            print("[DEBUG] 准备显示保存成功提示")
            self.show_snackbar("保存成功！", success=True)
            
            # 在后台线程中进行AI分析并更新记录
            def background_analyze():
                try:
                    # AI分析
                    analysis = self.ai_service.analyze_content(content)
                    
                    # 生成向量
                    embedding = self.ai_service.generate_embedding(content)
                    
                    # 更新记录
                    self.db.update_reflection(
                        reflection_id,
                        summary=analysis['summary'],
                        tags=analysis['tags'],
                        category=analysis['category'],
                        embedding=embedding
                    )
                    
                    # 使用线程安全的方式显示消息
                    message = f"AI分析完成！分类: {analysis['category']}, 标签: {', '.join(analysis['tags'])}"
                    logger.info(message)
                    
                    # 在主线程中显示消息
                    def show_ai_complete():
                        self.show_snackbar(message)
                    
                    # 使用page的线程安全方法
                    self.page.run_thread(show_ai_complete)
                    
                except Exception as e:
                    logger.error(f"AI分析失败: {e}")
            
            # 启动后台线程进行AI分析
            thread = threading.Thread(target=background_analyze)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"保存失败: {e}")
            self.show_snackbar("保存失败，请重试")

    def show_browse_page(self):
        """显示浏览页面"""
        # 检查是否有过滤条件
        if hasattr(self, '_pending_filter'):
            filter_type = self._pending_filter.get('type')
            filter_value = self._pending_filter.get('value')
            
            if filter_type == 'category':
                reflections = self.db.get_reflections_by_category(filter_value)
            elif filter_type == 'days':
                reflections = self.db.get_recent_reflections(filter_value)
            elif filter_type == 'type':
                reflections = self.db.get_reflections_by_type(filter_value)
            elif filter_type == 'tag':
                reflections = self.db.get_reflections_by_tag(filter_value)
            else:
                reflections = self.db.get_reflections(limit=50)
                
            # 清除过滤条件
            delattr(self, '_pending_filter')
        else:
            # 获取反思记录
            reflections = self.db.get_reflections(limit=50)
        
        # 创建列表
        self.reflections_list = ft.ListView(
            expand=True,
            spacing=10,
            padding=ft.padding.all(20),
        )
        
        if not reflections:
            self.reflections_list.controls.append(
                ft.Container(
                    content=ft.Text("没有找到记录", color=ft.Colors.GREY_600, size=16),
                    alignment=ft.alignment.center,
                    padding=50,
                )
            )
        else:
            for reflection in reflections:
                card = self.create_reflection_card(reflection)
                self.reflections_list.controls.append(card)
        
        self.content_area.content = ft.Column(
            [
                ft.Text("浏览记录", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                self.reflections_list,
            ],
            expand=True,
        )
        self.page.update()
    
    def create_reflection_card(self, reflection):
        """创建反思记录卡片"""
        # 格式化日期
        created_at = datetime.fromisoformat(reflection['created_at'])
        date_str = created_at.strftime("%Y-%m-%d %H:%M")
        
        # 保存reflection_id以便后续使用
        reflection_id = reflection['id']
        
        # 标签
        tags_row = ft.Row([
            ft.Chip(
                label=ft.Text(tag, color=ft.Colors.BLUE_900),
                bgcolor=ft.Colors.BLUE_200,
                on_click=lambda e, t=tag: self.show_tag_records(t)
            )
            for tag in reflection['tags']
        ])
        
        # 创建编辑按钮
        edit_button = ft.IconButton(
            icon=ft.Icons.EDIT_OUTLINED,
            icon_size=18,
            icon_color=ft.Colors.BLUE_400,
            tooltip="编辑",
        )
        
        # 创建删除按钮
        delete_button = ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE,
            icon_size=18,
            icon_color=ft.Colors.RED_400,
            tooltip="删除",
        )
        
        # 定义编辑处理函数
        def on_edit_click(e):
            logger.info(f"编辑按钮被点击，记录ID: {reflection_id}")
            print(f"[DEBUG] 编辑按钮被点击，记录ID: {reflection_id}")
            # 改为切换到编辑页面
            self.show_edit_page(reflection)
        
        # 定义删除处理函数
        def on_delete_click(e):
            logger.info(f"删除按钮被点击，记录ID: {reflection_id}")
            print(f"[DEBUG] 删除按钮被点击，记录ID: {reflection_id}")
            
            # 直接执行删除（先备份）
            self.delete_with_backup(reflection)
        
        # 绑定点击事件
        edit_button.on_click = on_edit_click
        delete_button.on_click = on_delete_click
        
        # 预览内容（保留Markdown格式并渲染）
        preview_content = reflection['content'][:300] + "..." if len(reflection['content']) > 300 else reflection['content']
        is_long_content = len(reflection['content']) > 300
        
        # 创建可展开的内容容器
        content_container = ft.Container(
            content=ft.Markdown(
                preview_content,
                selectable=True,
                extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                code_theme="github",
                on_tap_link=lambda e: self.page.launch_url(e.data),
            ),
            height=120,  # 默认限制预览高度
            padding=ft.padding.only(top=8),
        )
        
        # 展开/收起按钮
        def toggle_content(e):
            if content_container.height == 120:
                # 展开：移除高度限制，显示完整内容
                content_container.height = None
                content_container.content.value = reflection['content']
                e.control.text = "收起"
                e.control.icon = ft.Icons.KEYBOARD_ARROW_UP
            else:
                # 收起：恢复高度限制，显示预览内容
                content_container.height = 120
                content_container.content.value = preview_content
                e.control.text = "展开"
                e.control.icon = ft.Icons.KEYBOARD_ARROW_DOWN
            self.page.update()
        
        expand_button = ft.TextButton(
            "展开",
            icon=ft.Icons.KEYBOARD_ARROW_DOWN,
            on_click=toggle_content,
        ) if is_long_content else None
        
        # 构建列内容
        column_content = [
            ft.Text(
                reflection['summary'] or "点击查看详情...",
                weight=ft.FontWeight.BOLD,
                size=14,
            ),
            content_container,
        ]
        
        if expand_button:
            column_content.append(expand_button)
            
        column_content.append(tags_row)
        
        card_content = ft.Container(
            content=ft.Column(column_content, spacing=8),
            on_click=lambda e: self.show_reflection_detail(reflection),
            padding=ft.padding.only(left=15, right=15, bottom=15),
        )
        
        card = ft.Card(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text(date_str, size=12, color=ft.Colors.GREY_600),
                        ft.Container(expand=True),
                        edit_button,
                        delete_button,
                        ft.Chip(
                            label=ft.Text(reflection['category']),
                            bgcolor=ft.Colors.GREEN_100
                        ),
                    ]),
                    padding=ft.padding.only(left=15, right=15, top=15),
                ),
                card_content,
            ]),
        )
        
        # 将reflection_id存储在卡片对象上，方便后续识别
        card.data = reflection_id
        
        return card
    
    def show_reflection_detail(self, reflection):
        """显示反思记录详情"""
        dialog = ft.AlertDialog(
            title=ft.Text("记录详情"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"时间: {reflection['created_at']}", size=12),
                    ft.Text(f"类型: {reflection['type']}", size=12),
                    ft.Text(f"分类: {reflection['category']}", size=12),
                    ft.Divider(),
                    ft.Markdown(
                        reflection['content'],
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                        code_theme="github",
                        on_tap_link=lambda e: self.page.launch_url(e.data),
                    ),
                    ft.Divider(),
                    ft.Text(f"摘要: {reflection['summary']}", weight=ft.FontWeight.BOLD),
                    ft.Text(f"标签: {', '.join(reflection['tags'])}", size=12),
                ]),
                width=600,
                height=400,
            ),
            actions=[
                ft.TextButton(
                    "编辑",
                    on_click=lambda e: (self.close_dialog(), self.show_edit_page(reflection)),
                    style=ft.ButtonStyle(color=ft.Colors.BLUE)
                ),
                ft.TextButton(
                    "删除", 
                    on_click=lambda e: (self.close_dialog(), self.delete_with_backup(reflection)),
                    style=ft.ButtonStyle(color=ft.Colors.RED)
                ),
                ft.Container(expand=True),  # 占位符，让删除和关闭按钮分开
                ft.TextButton("关闭", on_click=lambda e: self.close_dialog()),
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()
    
    def close_dialog(self):
        self.page.dialog.open = False
        self.page.update()
    
    def show_edit_page(self, reflection):
        """显示编辑页面"""
        # 保存正在编辑的记录
        self.editing_reflection = reflection
        
        # 创建编辑控件
        self.edit_content_field = ft.TextField(
            label="内容",
            multiline=True,
            min_lines=5,
            max_lines=15,
            value=reflection['content'],
        )
        
        # 将标签列表转换为逗号分隔的字符串
        tags_text = ", ".join(reflection['tags']) if reflection['tags'] else ""
        self.edit_tags_field = ft.TextField(
            label="标签（用逗号分隔）",
            value=tags_text,
            hint_text="例如：工作总结, 项目复盘, 个人成长",
        )
        
        self.edit_category_field = ft.TextField(
            label="分类",
            value=reflection.get('category', ''),
        )
        
        self.edit_summary_field = ft.TextField(
            label="摘要",
            value=reflection.get('summary', ''),
            multiline=True,
            min_lines=2,
            max_lines=3,
        )
        
        # 类型选择
        self.edit_type_dropdown = ft.Dropdown(
            label="类型",
            value=reflection.get('type', 'daily'),
            options=[
                ft.dropdown.Option("灵光一闪", "灵光一闪"),
                ft.dropdown.Option("阶段总结", "阶段总结"),
                ft.dropdown.Option("项目复盘", "项目复盘"),
            ],
        )
        
        # 是否重新AI分析的开关
        self.edit_ai_reanalyze_switch = ft.Switch(
            label="重新进行AI分析（仅当内容修改时）",
            value=True,
        )
        
        # 保存按钮
        save_button = ft.ElevatedButton(
            "保存修改",
            icon=ft.Icons.SAVE,
            on_click=self.save_edit,
        )
        
        # 取消按钮
        cancel_button = ft.TextButton(
            "取消",
            on_click=lambda e: self.show_browse_page(),
        )
        
        # 更新内容区域
        self.content_area.content = ft.Column(
            [
                ft.Row([
                    ft.Text(f"编辑记录 (ID: {reflection['id']})", size=24, weight=ft.FontWeight.BOLD),
                    ft.Container(expand=True),
                    cancel_button,
                ]),
                ft.Container(height=20),
                self.edit_content_field,
                ft.Container(height=10),
                self.edit_tags_field,
                ft.Container(height=10),
                self.edit_category_field,
                ft.Container(height=10),
                self.edit_summary_field,
                ft.Container(height=10),
                self.edit_type_dropdown,
                ft.Container(height=20),
                self.edit_ai_reanalyze_switch,
                ft.Text(
                    "提示：如果关闭AI重新分析，将保留您手动编辑的标签和分类",
                    size=12,
                    color=ft.Colors.GREY_600,
                ),
                ft.Container(height=20),
                save_button,
            ],
            scroll=ft.ScrollMode.AUTO,
        )
        
        self.page.update()
    
    def save_edit(self, e):
        """保存编辑"""
        try:
            reflection = self.editing_reflection
            
            # 获取编辑后的内容
            new_content = self.edit_content_field.value
            new_tags = [tag.strip() for tag in self.edit_tags_field.value.split(',') if tag.strip()]
            new_category = self.edit_category_field.value
            new_summary = self.edit_summary_field.value
            new_type = self.edit_type_dropdown.value
            
            # 检查内容是否有变化
            content_changed = new_content != reflection['content']
            
            # 如果内容变化且开启了AI重新分析
            if content_changed and self.edit_ai_reanalyze_switch.value and self.ai_service.api_key:
                self.show_snackbar("正在进行AI分析...")
                # 在后台进行AI分析
                def analyze_and_update():
                    try:
                        analysis = self.ai_service.analyze_reflection(new_content, new_type)
                        # 使用AI分析的结果
                        self.db.update_reflection(
                            reflection['id'],
                            content=new_content,
                            summary=analysis['summary'],
                            tags=analysis['tags'],
                            category=analysis['category'],
                            type=new_type
                        )
                    except Exception as e:
                        logger.error(f"AI分析失败，使用手动输入: {e}")
                        # AI分析失败时使用手动输入
                        self.db.update_reflection(
                            reflection['id'],
                            content=new_content,
                            summary=new_summary,
                            tags=new_tags,
                            category=new_category,
                            type=new_type
                        )
                
                thread = threading.Thread(target=analyze_and_update)
                thread.start()
            else:
                # 不进行AI分析，直接使用手动输入
                self.db.update_reflection(
                    reflection['id'],
                    content=new_content,
                    summary=new_summary,
                    tags=new_tags,
                    category=new_category,
                    type=new_type
                )
            
            self.show_snackbar("记录已更新", success=True)
            
            # 返回浏览页面
            self.nav_rail.selected_index = 1
            self.show_browse_page()
                    
        except Exception as e:
            logger.error(f"保存编辑失败: {e}")
            print(f"[DEBUG] 保存编辑失败: {e}")
            self.show_snackbar("保存失败，请重试")
    

    
    def delete_with_backup(self, reflection):
        """删除记录并备份到GitHub（优化版）"""
        print(f"[DEBUG] 准备删除记录 ID: {reflection['id']}")
        
        # 立即从UI中移除卡片，提供即时反馈
        self._remove_card_from_ui(reflection['id'])
        
        # 显示删除中的提示
        self.show_snackbar("正在删除...", success=True)
        
        # 在后台线程中执行数据库删除和GitHub备份
        def async_delete():
            try:
                # 1. 先执行数据库删除
                success = self.db.delete_reflection(reflection['id'])
                
                if success:
                    print(f"[DEBUG] 数据库删除成功")
                    
                    # 2. 异步备份到GitHub（不阻塞）
                    backup_success = self.backup_deleted_record(reflection)
                    if backup_success:
                        print(f"[DEBUG] GitHub备份成功")
                    else:
                        print(f"[DEBUG] GitHub备份失败，但记录已删除")
                else:
                    print(f"[DEBUG] 数据库删除失败")
                    # 如果删除失败，需要恢复UI
                    self.page.update()
                    
            except Exception as e:
                logger.error(f"删除过程出错: {e}")
                print(f"[DEBUG] 删除过程出错: {e}")
        
        # 启动异步删除线程
        threading.Thread(target=async_delete, daemon=True).start()
    
    def _remove_card_from_ui(self, reflection_id):
        """立即从UI中移除指定的卡片"""
        try:
            # 检查当前页面并移除对应的卡片
            current_index = self.nav_rail.selected_index
            
            if current_index == 1:  # 浏览页面
                if hasattr(self, 'reflections_list') and self.reflections_list.controls:
                    # 找到并移除对应的卡片
                    for i, card in enumerate(self.reflections_list.controls):
                        # 检查是否是我们要删除的卡片
                        # 注意：这里需要一种方式来识别卡片，比如在创建时存储ID
                        self.reflections_list.controls = [
                            card for card in self.reflections_list.controls
                            if not self._is_card_for_reflection(card, reflection_id)
                        ]
                    self.page.update()
                    
            elif current_index == 2:  # 搜索页面
                if hasattr(self, 'search_results') and self.search_results.controls:
                    # 从搜索结果中移除
                    self.search_results.controls = [
                        card for card in self.search_results.controls
                        if not self._is_card_for_reflection(card, reflection_id)
                    ]
                    self.page.update()
                    
        except Exception as e:
            logger.error(f"移除UI卡片失败: {e}")
    
    def _is_card_for_reflection(self, card, reflection_id):
        """检查卡片是否对应特定的reflection ID"""
        # 使用卡片的data属性来存储的reflection_id进行比较
        return hasattr(card, 'data') and card.data == reflection_id
    
    def _process_backup_queue(self):
        """处理备份队列，串行化GitHub操作避免并发冲突"""
        while True:
            try:
                # 从队列获取备份任务（阻塞等待）
                reflection = self.backup_queue.get()
                
                # 执行实际的备份操作
                self._do_backup_to_github(reflection)
                
                # 标记任务完成
                self.backup_queue.task_done()
                
            except Exception as e:
                logger.error(f"备份队列处理出错: {e}")
    
    def backup_deleted_record(self, reflection):
        """将删除的记录加入备份队列"""
        try:
            # 检查是否配置了GitHub
            if not self.github_sync.is_configured():
                logger.info("GitHub未配置，跳过备份")
                return False
            
            # 将备份任务加入队列（不会阻塞）
            self.backup_queue.put(reflection)
            logger.info(f"已将记录 {reflection['id']} 加入备份队列")
            return True
                
        except Exception as e:
            logger.error(f"加入备份队列失败: {e}")
            return False
    
    def _do_backup_to_github(self, reflection):
        """实际执行GitHub备份（在队列处理线程中串行执行）"""
        try:
            # 创建备份文件内容
            import json
            from datetime import datetime
            
            backup_data = {
                "deleted_at": datetime.now().isoformat(),
                "record": reflection
            }
            
            # 备份文件名（按月份分组）
            now = datetime.now()
            filename = f"deleted_records/{now.strftime('%Y-%m')}/deleted_{reflection['id']}_{now.strftime('%Y%m%d_%H%M%S')}.json"
            
            # 上传到GitHub（这里会串行执行，避免并发冲突）
            try:
                content = json.dumps(backup_data, ensure_ascii=False, indent=2)
                self.github_sync.repo.create_file(
                    path=filename,
                    message=f"Backup deleted record {reflection['id']}",
                    content=content,
                    branch=self.github_sync.branch
                )
                logger.info(f"成功备份记录到GitHub: {filename}")
                return True
            except Exception as e:
                logger.error(f"备份到GitHub失败: {e}")
                # 如果是409冲突，可能需要先拉取最新状态
                if "409" in str(e):
                    logger.info("检测到Git冲突，尝试重新获取最新状态...")
                    # 这里可以添加重试逻辑
                return False
                
        except Exception as e:
            logger.error(f"备份过程出错: {e}")
            return False
    
    def view_deleted_records(self):
        """查看已删除的记录（从GitHub获取）"""
        print("[DEBUG] 查看已删除记录")
        
        try:
            if not self.github_sync.is_configured():
                self.show_snackbar("GitHub未配置，无法查看已删除记录")
                return
            
            # 获取deleted_records目录下的所有文件
            try:
                contents = self.github_sync.repo.get_contents("deleted_records", ref=self.github_sync.branch)
                
                # 如果是目录，递归获取所有文件
                all_files = []
                dirs_to_process = [content for content in contents if content.type == "dir"]
                files = [content for content in contents if content.type == "file"]
                all_files.extend(files)
                
                while dirs_to_process:
                    current_dir = dirs_to_process.pop()
                    sub_contents = self.github_sync.repo.get_contents(current_dir.path, ref=self.github_sync.branch)
                    for content in sub_contents:
                        if content.type == "dir":
                            dirs_to_process.append(content)
                        else:
                            all_files.append(content)
                
                if not all_files:
                    self.show_snackbar("没有找到已删除的记录")
                    return
                
                # 显示已删除记录的数量
                self.show_snackbar(f"找到 {len(all_files)} 条已删除的记录")
                print(f"[DEBUG] 找到 {len(all_files)} 条已删除的记录")
                
                # TODO: 可以在这里添加一个新页面来显示已删除的记录列表
                # 现在只是简单地打印文件名
                for file in all_files:
                    print(f"[DEBUG] 已删除记录: {file.path}")
                    
            except Exception as e:
                if "404" in str(e):
                    self.show_snackbar("没有找到已删除的记录")
                else:
                    self.show_snackbar(f"获取已删除记录失败: {str(e)}")
                    logger.error(f"获取已删除记录失败: {e}")
                    
        except Exception as e:
            logger.error(f"查看已删除记录出错: {e}")
            self.show_snackbar("查看已删除记录失败")
    

    
    def show_search_page(self):
        """显示搜索页面"""
        self.search_input = ft.TextField(
            label="搜索内容",
            prefix_icon=ft.Icons.SEARCH,
            on_submit=self.perform_search,
        )
        
        self.search_mode_radio = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="keyword", label="关键词搜索"),
                ft.Radio(value="vector", label="语义搜索"),
            ]),
            value="keyword",
        )
        
        search_button = ft.ElevatedButton(
            "搜索",
            icon=ft.Icons.SEARCH,
            on_click=self.perform_search,
        )
        
        self.search_results = ft.ListView(
            expand=True,
            spacing=10,
            padding=ft.padding.all(20),
        )
        
        self.content_area.content = ft.Column(
            [
                ft.Text("搜索记录", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                self.search_mode_radio,
                ft.Row([
                    self.search_input,
                    search_button,
                ]),
                ft.Container(height=20),
                self.search_results,
            ],
            expand=True,
        )
        self.page.update()
    
    def perform_search(self, e):
        """执行搜索"""
        query = self.search_input.value
        if not query:
            return
        
        self.search_results.controls.clear()
        
        if self.search_mode_radio.value == "keyword":
            # 关键词搜索
            results = self.db.search_reflections(query)
            for reflection in results:
                card = self.create_reflection_card(reflection)
                self.search_results.controls.append(card)
        else:
            # 向量搜索
            query_embedding = self.ai_service.generate_embedding(query)
            if query_embedding is not None:
                results = self.db.search_by_embedding(query_embedding)
                for reflection, similarity in results:
                    card = self.create_reflection_card(reflection)
                    # 添加相似度显示
                    similarity_text = ft.Text(f"相似度: {similarity:.2%}", size=12, color=ft.Colors.BLUE_600)
                    # 获取卡片内容区域的Column
                    content_column = card.content.controls[1].content
                    content_column.controls.insert(0, similarity_text)
                    self.search_results.controls.append(card)
        
        if not self.search_results.controls:
            self.search_results.controls.append(
                ft.Text("没有找到相关记录", color=ft.Colors.GREY_600)
            )
        
        self.page.update()
    
    def show_stats_page(self):
        """显示统计页面"""
        stats = self.db.get_statistics()
        
        # 创建统计卡片
        total_card = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.NOTES, size=40, color=ft.Colors.BLUE_400),
                        ft.Text(str(stats['total_count']), size=32, weight=ft.FontWeight.BOLD),
                        ft.Text("总记录数", size=14, color=ft.Colors.GREY_600),
                    ]),
                    padding=20,
                    alignment=ft.alignment.center,
                ),
                width=200,
            ),
            on_click=lambda e: self.show_all_records(),
        )
        
        recent_card = ft.Container(
            content=ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.CALENDAR_TODAY, size=40, color=ft.Colors.GREEN_400),
                        ft.Text(str(stats['recent_count']), size=32, weight=ft.FontWeight.BOLD),
                        ft.Text("最近7天", size=14, color=ft.Colors.GREY_600),
                    ]),
                    padding=20,
                    alignment=ft.alignment.center,
                ),
                width=200,
            ),
            on_click=lambda e: self.show_recent_records(7),
        )
        
        # 类型统计
        type_stats = []
        for type_name, count in stats['type_stats'].items():
            type_stats.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(type_name, expand=True),
                        ft.Text(str(count), weight=ft.FontWeight.BOLD),
                    ]),
                    padding=10,
                    on_click=lambda e, t=type_name: self.show_type_records(t),
                    ink=True,  # 添加点击波纹效果
                )
            )
        
        # 分类统计
        category_stats = []
        for category, count in stats['category_stats'].items():
            category_stats.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(category, expand=True),
                        ft.Text(str(count), weight=ft.FontWeight.BOLD),
                    ]),
                    padding=10,
                    on_click=lambda e, c=category: self.show_category_records(c),
                    ink=True,  # 添加点击波纹效果
                )
            )
        
        self.content_area.content = ft.Column(
            [
                ft.Text("统计信息", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                ft.Row([total_card, recent_card]),
                ft.Container(height=20),
                ft.Text("按类型统计", size=18, weight=ft.FontWeight.BOLD),
                ft.Column(type_stats),
                ft.Container(height=20),
                ft.Text("按分类统计", size=18, weight=ft.FontWeight.BOLD),
                ft.Column(category_stats),
            ],
            scroll=ft.ScrollMode.AUTO,
        )
        self.page.update()
    
    def show_settings_page(self):
        """显示设置页面"""
        # GitHub同步状态（修改）
        sync_status = self.sync_manager.get_sync_status()
        sync_info = self.github_sync.get_last_sync_info(Config.DB_PATH) if self.github_sync.is_configured() else None
        
        # 新增：自动同步开关
        auto_sync_switch = ft.Switch(
            label="自动同步",
            value=sync_status['auto_sync_enabled'],
            on_change=self.toggle_auto_sync,
        )
        
        sync_button = ft.ElevatedButton(
            "立即同步",
            icon=ft.Icons.SYNC,
            on_click=lambda e: self.manual_sync("both"),
        )
        
        upload_button = ft.ElevatedButton(
            "仅上传",
            icon=ft.Icons.CLOUD_UPLOAD,
            on_click=lambda e: self.manual_sync("upload"),
        )
        
        download_button = ft.ElevatedButton(
            "仅下载",
            icon=ft.Icons.CLOUD_DOWNLOAD,
            on_click=lambda e: self.manual_sync("download"),
        )
        
        # 查看已删除记录按钮
        view_deleted_button = ft.ElevatedButton(
            "查看已删除记录",
            icon=ft.Icons.RESTORE_FROM_TRASH,
            on_click=lambda e: self.view_deleted_records(),
        )
        
        self.content_area.content = ft.Column(
            [
                ft.Text("设置", size=24, weight=ft.FontWeight.BOLD),
                ft.Container(height=20),
                ft.Text("GitHub同步", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"状态: {'已配置' if sync_status['is_configured'] else '未配置'}", size=14),
                ft.Text(f"仓库: {Config.GITHUB_REPO or '未设置'}", size=14),
                ft.Text(f"自动同步: {'开启' if sync_status['auto_sync_enabled'] else '关闭'}", size=14),
                ft.Container(height=10),
                auto_sync_switch,
                ft.Container(height=10),
                ft.Row([sync_button, upload_button, download_button]),
                ft.Container(height=10),
                view_deleted_button,
            ],
            scroll=ft.ScrollMode.AUTO,
        )
        self.page.update()
    
    def toggle_auto_sync(self, e):
        """切换自动同步（新增）"""
        if e.control.value:
            self.sync_manager.start_auto_sync()
            self.show_snackbar("自动同步已开启")
        else:
            # 停止自动同步（需要在SyncManager中实现）
            self.show_snackbar("自动同步已关闭")
    
    def manual_sync(self, direction):
        """手动同步（修改）"""
        self.show_snackbar(f"正在同步...")
        self.update_sync_status()
        
        success = self.sync_manager.manual_sync(direction)
        
        if success:
            if direction == "upload":
                self.show_snackbar("上传成功！")
            elif direction == "download":
                self.show_browse_page()  # 刷新页面
            else:
                self.show_snackbar("同步成功！")
        else:
            self.show_snackbar("同步失败，请检查配置")
        
        self.update_sync_status()
    
    def show_snackbar(self, message, success=False):
        """显示提示消息"""
        print(f"[DEBUG] 显示snackbar: {message}, success={success}")
        
        try:
            if success:
                snack = ft.SnackBar(
                    content=ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.WHITE, size=20),
                        ft.Text(message, color=ft.Colors.WHITE)
                    ], tight=True),
                    bgcolor=ft.Colors.GREEN,
                )
            else:
                snack = ft.SnackBar(
                    content=ft.Text(message),
                )
            
            self.page.snack_bar = snack
            self.page.snack_bar.open = True
            self.page.update()
            print(f"[DEBUG] snackbar应该已经显示")
            
        except Exception as e:
            print(f"[DEBUG] 显示snackbar失败: {e}")
            logger.error(f"显示snackbar失败: {e}")
    

    
    def show_tag_records(self, tag):
        """显示特定标签的所有记录"""
        # 设置过滤条件
        self._pending_filter = {'type': 'tag', 'value': tag}
        
        # 切换到浏览页面
        self.nav_rail.selected_index = 1
        self.show_browse_page()
        self.show_snackbar(f"显示标签 '{tag}' 的记录")
    
    def show_category_records(self, category):
        """显示特定分类的所有记录"""
        # 设置过滤条件
        self._pending_filter = {'type': 'category', 'value': category}
        
        # 切换到浏览页面
        self.nav_rail.selected_index = 1
        self.show_browse_page()
        self.show_snackbar(f"显示分类 '{category}' 的记录")
    
    def show_recent_records(self, days=7):
        """显示最近N天的记录"""
        # 设置过滤条件
        self._pending_filter = {'type': 'days', 'value': days}
        
        # 切换到浏览页面
        self.nav_rail.selected_index = 1
        self.show_browse_page()
        self.show_snackbar(f"显示最近 {days} 天的记录")
    

    

    
    def show_all_records(self):
        """显示所有记录"""
        # 切换到浏览页面
        self.nav_rail.selected_index = 1
        self.show_browse_page()
        self.show_snackbar("显示所有记录")
    
    def show_type_records(self, type_name):
        """显示特定类型的记录"""
        # 设置过滤条件
        self._pending_filter = {'type': 'type', 'value': type_name}
        
        # 切换到浏览页面
        self.nav_rail.selected_index = 1
        self.show_browse_page()
        self.show_snackbar(f"显示类型 '{type_name}' 的记录")

if __name__ == "__main__":
    app = ReflectionJournalApp()
    ft.app(target=app.main) 