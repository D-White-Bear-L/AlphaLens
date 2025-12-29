# Financial News Trace Backend

基于 Agent 的金融类新闻溯源工具后端，使用 FastAPI 和 mira 库构建。

## 功能特性

- 🤖 **AI Agent**: 使用 mira 库调用大模型进行智能新闻溯源
- 🔍 **Google 检索**: 集成 Serper API 进行 Google 搜索
- 💾 **数据库检索**: 支持从数据库中检索已存储的新闻信息
- 🌐 **网页抓取**: 使用 Playwright 抓取网页内容
- 📊 **结构化输出**: 提供结构化的溯源结果

## 安装

1. 首先安装 mira 库（本地路径）：

```bash
# 从 backend 目录返回到项目根目录
cd ../mira
pip install -e .
cd ../backend
```

2. 安装其他依赖：

```bash
pip install -r requirements.txt
```

3. 安装 Playwright 浏览器：

```bash
playwright install chromium
```

4. 配置环境变量：

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入：
- `MIRA_API_KEY`: mira 库使用的 API key
- `MIRA_BASE_URL`: API 基础 URL（例如：https://api.openrouter.ai/v1）
- `MIRA_MODEL`: 使用的模型名称（例如：openai/gpt-4o）
- `SERPER_API_KEY`: Serper API key（用于 Google 搜索，从 https://serper.dev 获取）

## 运行

```bash
# 使用 run.py 脚本（推荐）
python run.py

# 或使用 uvicorn 直接运行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用模块方式
python -m app.main
```

## API 文档

启动服务后，访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 端点

### 健康检查
```
GET /api/v1/health
```

### 新闻溯源
```
POST /api/v1/trace
Body: {"claim": "新闻内容"}
```

### Google 搜索
```
POST /api/v1/search/google
Body: {"query": "搜索关键词", "num_results": 10}
```

### 网页抓取
```
POST /api/v1/scrape
Body: {"url": "https://example.com", "extract_content": true}
```

### 获取来源
```
GET /api/v1/sources?claim=新闻内容
```

## 项目结构

```
backend/
├── app/
│   ├── agent/           # Agent 核心逻辑
│   │   └── news_trace_agent.py
│   ├── api/             # API 路由
│   │   └── routes.py
│   ├── models.py        # 数据模型
│   ├── tools/           # 工具类
│   │   ├── google_search.py
│   │   ├── database_search.py
│   │   └── web_scraper.py
│   ├── config.py        # 配置管理
│   └── main.py          # 主应用
├── requirements.txt     # 依赖
├── .env.example         # 环境变量示例
└── README.md
```

## 使用示例

### Python 客户端示例

```python
import httpx

# 新闻溯源
response = httpx.post(
    "http://localhost:8000/api/v1/trace",
    json={"claim": "某公司宣布重大收购"}
)
result = response.json()
print(result)
```

### cURL 示例

```bash
# 新闻溯源
curl -X POST "http://localhost:8000/api/v1/trace" \
  -H "Content-Type: application/json" \
  -d '{"claim": "某公司宣布重大收购"}'
```

## 开发说明

### 添加新工具

1. 在 `app/tools/` 目录下创建新工具类
2. 继承 `mira.LLMTool` 基类
3. 实现 `__call__` 方法
4. 在 `NewsTraceAgent` 中注册工具

### 自定义 Agent 行为

修改 `app/agent/news_trace_agent.py` 中的 `system_prompt` 来改变 Agent 的行为。

## 注意事项

1. 确保已正确配置所有 API keys
2. Playwright 需要安装浏览器驱动
3. 数据库表需要初始化（当前使用 SQLite，可根据需要修改）
4. 生产环境建议使用 PostgreSQL 等更强大的数据库

