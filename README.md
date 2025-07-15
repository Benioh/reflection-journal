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
python build_improved.py windows
```

### macOS打包

```bash
python build_improved.py macos
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
