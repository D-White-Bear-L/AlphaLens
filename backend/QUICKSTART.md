# 快速开始指南

## 1. 环境准备

确保已安装 Python 3.11+ 和 pip。

## 2. 安装步骤

### 步骤 1: 安装 mira 库

```bash
# 从 backend 目录返回到项目根目录
cd ../mira
pip install -e .
cd ../backend
```

### 步骤 2: 安装其他依赖

```bash
pip install -r requirements.txt
```

### 步骤 3: 安装 Playwright 浏览器

```bash
playwright install chromium
```

## 3. 配置

创建 `.env` 文件（参考 `.env.example`）：

```bash
# Mira LLM Configuration
MIRA_API_KEY=your_api_key_here
MIRA_BASE_URL=https://api.openrouter.ai/v1
MIRA_MODEL=openai/gpt-4o

# Serper API Configuration  
SERPER_API_KEY=your_serper_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///./news_trace.db

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

**重要**: 
- 从 https://serper.dev 获取 Serper API key
- 配置你的 mira API key 和 base URL

## 4. 运行服务

```bash
python run.py
```

服务将在 http://localhost:8000 启动。

## 5. 测试 API

### 使用 curl

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 新闻溯源
curl -X POST "http://localhost:8000/api/v1/trace" \
  -H "Content-Type: application/json" \
  -d '{"claim": "某公司宣布重大收购"}'

# Google 搜索
curl -X POST "http://localhost:8000/api/v1/search/google" \
  -H "Content-Type: application/json" \
  -d '{"query": "金融新闻", "num_results": 5}'
```

### 使用 Python

```python
import httpx

# 新闻溯源
response = httpx.post(
    "http://localhost:8000/api/v1/trace",
    json={"claim": "某公司宣布重大收购"}
)
print(response.json())
```

## 6. 访问 API 文档

启动服务后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 故障排除

### 问题: 导入 mira 库失败

**解决**: 确保已正确安装 mira 库：
```bash
cd ../mira
pip install -e .
```

### 问题: Playwright 浏览器未安装

**解决**: 运行 `playwright install chromium`

### 问题: API key 错误

**解决**: 检查 `.env` 文件中的配置是否正确

### 问题: 数据库表不存在

**解决**: 服务启动时会自动创建表，如果失败，检查数据库 URL 配置

