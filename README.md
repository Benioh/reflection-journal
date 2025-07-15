# 复盘日志 - Reflection Journal

一个用于记录和管理个人想法、总结和复盘的桌面应用。支持AI智能分类、标签生成、向量搜索和GitHub同步。

## 功能特点

- 📝 **多类型记录**：支持日常记录、周/月/年总结、项目复盘等
- 🤖 **AI智能分析**：使用DeepSeek API自动生成摘要、标签和分类
- 🔍 **双重搜索**：支持关键词搜索和语义向量搜索
- 🚀 **先进嵌入模型**：支持最新的Qwen3嵌入模型，提供更准确的语义理解
- ☁️ **GitHub同步**：自动备份数据到GitHub，实现多设备同步
- 📊 **统计分析**：查看记录统计和分布情况
- 🎨 **现代UI**：基于Flet的美观界面

## 安装使用

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

注意：首次运行会下载嵌入模型，大小取决于你的选择：
- Qwen3-Embedding-0.6B：约1.2GB（推荐CPU使用）
- Qwen3-Embedding-4B：约8GB（建议GPU使用）
- 备用轻量模型：约400MB

### 2. 配置环境

（可选）创建配置文件：

```bash
cp env_example .env
```

注意：不创建配置文件也可以正常使用，应用会使用智能默认值。

编辑`.env`文件，填入你的配置：

```env
# DeepSeek API配置
DEEPSEEK_API_KEY=你的DeepSeek API密钥
DEEPSEEK_API_BASE=https://api.deepseek.com

# GitHub配置（可选）
GITHUB_TOKEN=你的GitHub Token
GITHUB_REPO=你的用户名/reflection-journal-data
GITHUB_BRANCH=main

# 嵌入模型配置
USE_QWEN_MODEL=true          # 是否使用Qwen模型
QWEN_MODEL_SIZE=0.6B         # 0.6B（推荐CPU）或 4B（需要GPU）
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2  # 备用模型
```

### 3. 运行应用

```bash
python main.py
```

## 嵌入模型选择指南

### Qwen3-Embedding-0.6B（推荐）
- **优点**：平衡了性能和效率，CPU友好
- **适用场景**：个人笔记本、普通配置电脑
- **内存需求**：约2.4GB
- **推理速度**：CPU约0.5-1秒/次

### Qwen3-Embedding-4B
- **优点**：更强的语义理解能力
- **适用场景**：配备GPU的高性能电脑
- **内存需求**：约16GB
- **推理速度**：GPU约0.1-0.3秒/次，CPU约3-5秒/次

### 备用轻量模型
- **优点**：极小的资源占用
- **适用场景**：配置较低的电脑或Qwen模型加载失败时
- **内存需求**：约400MB
- **推理速度**：CPU约0.2-0.5秒/次

## 获取API密钥

### DeepSeek API
1. 访问 [DeepSeek官网](https://platform.deepseek.com/)
2. 注册账号并获取API密钥
3. 将密钥填入配置文件

### GitHub Token
1. 访问 GitHub Settings > Developer settings > Personal access tokens
2. 创建新的Token，勾选`repo`权限
3. 创建一个新的私有仓库用于存储数据
4. 将Token和仓库名填入配置文件

## 打包发布

### Windows打包

```bash
python build.py windows
```

### macOS打包

```bash
python build.py macos
```

生成的可执行文件在`dist`目录下。

## 使用说明

### 写记录
1. 点击"写记录"标签
2. 选择记录类型（日常、周总结等）
3. 输入内容
4. 点击保存，AI会自动分析并生成标签

### 搜索记录
1. 点击"搜索"标签
2. 选择搜索模式：
   - 关键词搜索：快速匹配文本
   - 语义搜索：找到意思相近的内容（使用Qwen3嵌入模型）
3. 输入搜索词，查看结果

### 数据同步
1. 在设置页面配置GitHub
2. 点击"同步到GitHub"备份数据
3. 在其他设备上点击"从GitHub导入"恢复数据

## 技术栈

- **前端**：Flet (Flutter for Python)
- **数据库**：SQLite
- **AI服务**：DeepSeek API
- **向量搜索**：Qwen3-Embedding / Sentence Transformers
- **数据同步**：GitHub API

## 系统要求

- Python 3.8+
- 内存：最低4GB（使用0.6B模型），推荐8GB+
- 存储：2-10GB（取决于选择的模型）
- 操作系统：Windows 10+、macOS 10.15+、Linux

## 注意事项

1. 首次使用时会下载嵌入模型，请确保网络连接稳定
2. GitHub同步需要创建私有仓库保护隐私
3. 建议定期备份本地数据库文件
4. CPU推理时，0.6B模型性能更好；如有GPU，可尝试4B模型

## 开发计划

- [ ] 支持更多AI模型接口（如通义千问、文心一言等）
- [ ] 添加数据导出功能（PDF、Markdown等格式）
- [ ] 支持标签管理和批量操作
- [ ] 添加数据可视化图表
- [ ] 支持主题切换和自定义界面
- [ ] 优化向量搜索性能

## License

MIT License 

## 同步策略说明

### 当前同步策略（默认）
- **完全同步**：包括新增和删除操作都会同步到所有设备
- **数据备份**：删除的记录会自动备份到 GitHub 的 `deleted_records` 目录
- **冲突处理**：智能合并，优先保留最新的修改

### 为什么可以安全地同步删除？
1. **自动备份**：所有删除的记录都会备份到 GitHub
2. **可恢复性**：可以随时从 `deleted_records` 目录恢复
3. **版本控制**：GitHub 保留完整的历史记录

### 删除记录的处理
- 删除的记录会先备份到 GitHub 的 `deleted_records/YYYY-MM/` 目录
- 备份完成后，删除操作会同步到所有设备
- 可以在设置页面查看和恢复已删除的记录

### 如果需要禁用删除同步
如果您希望采用更保守的策略，可以禁用删除同步：
```python
# 在 main.py 中修改
self.sync_manager = SyncManager(Config.DB_PATH, sync_deletions=False)
```

**注意**：禁用删除同步后，每个设备需要独立管理删除操作。 