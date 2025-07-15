import flet as ft
from pathlib import Path
import sys

class FirstRunWizard:
    """首次运行配置向导（GUI版）"""
    
    def __init__(self):
        self.config_data = {
            'DEEPSEEK_API_KEY': '',
            'DEEPSEEK_API_BASE': 'https://api.deepseek.com',
            'GITHUB_TOKEN': '',
            'GITHUB_REPO': '',
            'GITHUB_BRANCH': 'main',
            'USE_QWEN_MODEL': 'false',
            'QWEN_MODEL_SIZE': '0.6B',
            'EMBEDDING_MODEL': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
            'APP_DATA_DIR': './data'
        }
        self.current_step = 0
        
    def main(self, page: ft.Page):
        page.title = "复盘日志 - 初始设置"
        page.window_width = 600
        page.window_height = 500
        page.window_resizable = False
        
        self.page = page
        self.show_welcome()
        
    def show_welcome(self):
        """欢迎页面"""
        self.page.controls.clear()
        
        logo = ft.Icon(ft.Icons.BOOK, size=80, color=ft.Colors.BLUE_400)
        title = ft.Text("欢迎使用复盘日志", size=28, weight=ft.FontWeight.BOLD)
        subtitle = ft.Text("让我们快速完成初始设置", size=16, color=ft.Colors.GREY_700)
        
        features = ft.Column([
            self._create_feature_row(ft.Icons.EDIT, "记录每日想法和复盘"),
            self._create_feature_row(ft.Icons.AUTO_AWESOME, "AI智能分析和分类"),
            self._create_feature_row(ft.Icons.SEARCH, "强大的搜索功能"),
            self._create_feature_row(ft.Icons.CLOUD_SYNC, "多设备自动同步"),
        ], spacing=10)
        
        start_btn = ft.ElevatedButton(
            "开始设置",
            on_click=lambda e: self.show_ai_config(),
            width=200,
            height=40
        )
        
        skip_btn = ft.TextButton(
            "跳过设置，使用默认配置",
            on_click=lambda e: self.skip_setup()
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column([
                    logo,
                    title,
                    subtitle,
                    ft.Container(height=30),
                    features,
                    ft.Container(height=40),
                    start_btn,
                    skip_btn,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=40,
                expand=True,
            )
        )
        self.page.update()
        
    def _create_feature_row(self, icon, text):
        return ft.Row([
            ft.Icon(icon, size=24, color=ft.Colors.BLUE_400),
            ft.Text(text, size=14)
        ])
        
    def show_ai_config(self):
        """AI配置页面"""
        self.page.controls.clear()
        
        title = ft.Text("AI分析设置", size=24, weight=ft.FontWeight.BOLD)
        subtitle = ft.Text("配置AI功能以获得智能分析和标签", size=14, color=ft.Colors.GREY_700)
        
        use_ai = ft.Checkbox(
            label="启用AI分析功能",
            value=False,
            on_change=self.toggle_ai_fields
        )
        
        self.api_key_field = ft.TextField(
            label="DeepSeek API密钥",
            hint_text="sk-...",
            password=True,
            can_reveal_password=True,
            disabled=True,
            on_change=lambda e: setattr(self.config_data, 'DEEPSEEK_API_KEY', e.control.value)
        )
        
        help_link = ft.TextButton(
            "获取API密钥",
            url="https://platform.deepseek.com/",
            disabled=True
        )
        self.help_link = help_link
        
        info = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE, size=16, color=ft.Colors.BLUE_400),
                ft.Text("不配置API也可使用，但AI分析功能将受限", size=12)
            ]),
            bgcolor=ft.Colors.BLUE_50,
            padding=10,
            border_radius=5
        )
        
        next_btn = ft.ElevatedButton(
            "下一步",
            on_click=lambda e: self.show_sync_config(),
            width=100
        )
        
        back_btn = ft.TextButton(
            "上一步",
            on_click=lambda e: self.show_welcome()
        )
        
        self.use_ai = use_ai
        
        self.page.add(
            ft.Container(
                content=ft.Column([
                    title,
                    subtitle,
                    ft.Container(height=20),
                    use_ai,
                    self.api_key_field,
                    help_link,
                    ft.Container(height=20),
                    info,
                    ft.Container(expand=True),
                    ft.Row([back_btn, next_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ]),
                padding=40,
                expand=True,
            )
        )
        self.page.update()
        
    def toggle_ai_fields(self, e):
        """切换AI字段状态"""
        enabled = e.control.value
        self.api_key_field.disabled = not enabled
        self.help_link.disabled = not enabled
        if not enabled:
            self.config_data['DEEPSEEK_API_KEY'] = ''
        self.page.update()
        
    def show_sync_config(self):
        """同步配置页面"""
        self.page.controls.clear()
        
        title = ft.Text("数据同步设置", size=24, weight=ft.FontWeight.BOLD)
        subtitle = ft.Text("配置GitHub实现多设备同步", size=14, color=ft.Colors.GREY_700)
        
        use_sync = ft.Checkbox(
            label="启用GitHub同步",
            value=False,
            on_change=self.toggle_sync_fields
        )
        
        self.token_field = ft.TextField(
            label="GitHub Token",
            hint_text="ghp_...",
            password=True,
            can_reveal_password=True,
            disabled=True,
            on_change=lambda e: setattr(self.config_data, 'GITHUB_TOKEN', e.control.value)
        )
        
        self.repo_field = ft.TextField(
            label="仓库名称",
            hint_text="username/repository-name",
            disabled=True,
            on_change=lambda e: setattr(self.config_data, 'GITHUB_REPO', e.control.value)
        )
        
        help_text = ft.Column([
            ft.Text("设置步骤：", size=12, weight=ft.FontWeight.BOLD),
            ft.Text("1. 在GitHub创建私有仓库", size=12),
            ft.Text("2. 获取Personal Access Token (需要repo权限)", size=12),
            ft.Text("3. 填入上方字段", size=12),
        ])
        
        next_btn = ft.ElevatedButton(
            "下一步",
            on_click=lambda e: self.show_model_config(),
            width=100
        )
        
        back_btn = ft.TextButton(
            "上一步",
            on_click=lambda e: self.show_ai_config()
        )
        
        self.use_sync = use_sync
        
        self.page.add(
            ft.Container(
                content=ft.Column([
                    title,
                    subtitle,
                    ft.Container(height=20),
                    use_sync,
                    self.token_field,
                    self.repo_field,
                    ft.Container(height=20),
                    help_text,
                    ft.Container(expand=True),
                    ft.Row([back_btn, next_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ]),
                padding=40,
                expand=True,
            )
        )
        self.page.update()
        
    def toggle_sync_fields(self, e):
        """切换同步字段状态"""
        enabled = e.control.value
        self.token_field.disabled = not enabled
        self.repo_field.disabled = not enabled
        if not enabled:
            self.config_data['GITHUB_TOKEN'] = ''
            self.config_data['GITHUB_REPO'] = ''
        self.page.update()
        
    def show_model_config(self):
        """模型配置页面"""
        self.page.controls.clear()
        
        title = ft.Text("嵌入模型选择", size=24, weight=ft.FontWeight.BOLD)
        subtitle = ft.Text("选择适合你设备的模型", size=14, color=ft.Colors.GREY_700)
        
        model_choice = ft.RadioGroup(
            content=ft.Column([
                ft.Radio(
                    value="qwen",
                    label="Qwen3 0.6B - 推荐",
                ),
                ft.Radio(
                    value="light",
                    label="轻量级模型 - 快速",
                ),
            ]),
            value="light",
            on_change=self.on_model_change
        )
        
        model_info = ft.Container(
            content=ft.Column([
                ft.Text("模型对比：", size=12, weight=ft.FontWeight.BOLD),
                ft.Text("• Qwen3: 更准确的语义理解，需要1.2GB下载", size=12),
                ft.Text("• 轻量级: 更快的速度，需要400MB下载", size=12),
                ft.Text("• 两种模型都支持中文", size=12),
            ]),
            bgcolor=ft.Colors.GREY_100,
            padding=10,
            border_radius=5
        )
        
        complete_btn = ft.ElevatedButton(
            "完成设置",
            on_click=lambda e: self.complete_setup(),
            width=100
        )
        
        back_btn = ft.TextButton(
            "上一步",
            on_click=lambda e: self.show_sync_config()
        )
        
        self.model_choice = model_choice
        
        self.page.add(
            ft.Container(
                content=ft.Column([
                    title,
                    subtitle,
                    ft.Container(height=20),
                    model_choice,
                    ft.Container(height=20),
                    model_info,
                    ft.Container(expand=True),
                    ft.Row([back_btn, complete_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ]),
                padding=40,
                expand=True,
            )
        )
        self.page.update()
        
    def on_model_change(self, e):
        """模型选择变化"""
        if e.control.value == "qwen":
            self.config_data['USE_QWEN_MODEL'] = 'true'
        else:
            self.config_data['USE_QWEN_MODEL'] = 'false'
            
    def skip_setup(self):
        """跳过设置，使用默认配置"""
        self.save_config()
        self.launch_app()
        
    def complete_setup(self):
        """完成设置"""
        self.save_config()
        
        # 显示完成页面
        self.page.controls.clear()
        
        icon = ft.Icon(ft.Icons.CHECK_CIRCLE, size=80, color=ft.Colors.GREEN_400)
        title = ft.Text("设置完成！", size=28, weight=ft.FontWeight.BOLD)
        subtitle = ft.Text("应用即将启动...", size=16, color=ft.Colors.GREY_700)
        
        # 显示配置摘要
        summary = []
        if self.config_data['DEEPSEEK_API_KEY']:
            summary.append("✓ AI分析已配置")
        if self.config_data['GITHUB_TOKEN']:
            summary.append("✓ GitHub同步已配置")
        if self.config_data['USE_QWEN_MODEL'] == 'true':
            summary.append("✓ 使用Qwen3嵌入模型")
        else:
            summary.append("✓ 使用轻量级模型")
            
        summary_column = ft.Column([
            ft.Text(item, size=14) for item in summary
        ])
        
        launch_btn = ft.ElevatedButton(
            "启动应用",
            on_click=lambda e: self.launch_app(),
            width=200,
            height=40
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column([
                    icon,
                    title,
                    subtitle,
                    ft.Container(height=30),
                    summary_column,
                    ft.Container(height=40),
                    launch_btn,
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=40,
                expand=True,
            )
        )
        self.page.update()
        
    def save_config(self):
        """保存配置到.env文件"""
        config_lines = []
        for key, value in self.config_data.items():
            config_lines.append(f"{key}={value}")
            
        with open('.env', 'w', encoding='utf-8') as f:
            f.write('\n'.join(config_lines))
            
    def launch_app(self):
        """启动主应用"""
        self.page.window_close()
        
        # 导入并运行主程序
        from main import ReflectionJournalApp
        app = ReflectionJournalApp()
        ft.app(target=app.main)

def check_and_run():
    """检查是否需要运行配置向导"""
    if not Path('.env').exists():
        # 首次运行，显示配置向导
        wizard = FirstRunWizard()
        ft.app(target=wizard.main)
    else:
        # 直接运行主程序
        from main import ReflectionJournalApp
        app = ReflectionJournalApp()
        ft.app(target=app.main)

if __name__ == "__main__":
    check_and_run() 