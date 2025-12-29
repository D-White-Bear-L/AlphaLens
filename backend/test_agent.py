"""测试脚本：直接测试 Agent 功能，无需启动 FastAPI 或数据库"""
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# 加载环境变量
env_paths = [
    Path(__file__).parent / ".env",
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent.parent / ".env",
]

for env_path in env_paths:
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded .env from: {env_path}")
        break
else:
    load_dotenv()
    logger.info("Using default .env loading")

from app.agent.news_trace_agent import NewsTraceAgent
from app.tools.google_search import GoogleSearch
from app.tools.web_scraper import WebScraper


async def test_tools():
    """测试各个工具"""
    logger.info("=" * 60)
    logger.info("测试 1: Google 搜索工具")
    logger.info("=" * 60)
    
    try:
        search_tool = GoogleSearch(
            query="金融新闻 2024",
            num_results=5
        )
        result = search_tool()
        logger.info(f"搜索结果: {result.get('total_results', 0)} 条")
        if result.get('success') and result.get('results'):
            for i, item in enumerate(result['results'][:2], 1):
                logger.info(f"  {i}. {item.get('title', 'N/A')}")
                logger.info(f"     URL: {item.get('url', 'N/A')}")
    except Exception as e:
        logger.error(f"Google 搜索测试失败: {e}")
    
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 网页抓取工具")
    logger.info("=" * 60)
    
    try:
        scraper = WebScraper(
            url="https://www.example.com",
            extract_content=True
        )
        result = scraper()
        if result.get('success'):
            logger.info(f"抓取成功: {result.get('title', 'N/A')}")
            logger.info(f"内容长度: {result.get('content_length', 0)} 字符")
        else:
            logger.warning(f"抓取失败: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"网页抓取测试失败: {e}")


async def test_agent_simple():
    """测试 Agent 简单功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: Agent 初始化")
    logger.info("=" * 60)
    
    try:
        agent = NewsTraceAgent()
        logger.info("Agent 初始化成功")
        logger.info(f"使用的 API: {os.getenv('API_PROVIDER', 'ONEAPI')}")
        logger.info(f"使用的模型: {os.getenv('MODEL', 'qwen*/qwen3-8b')}")
    except Exception as e:
        logger.error(f"Agent 初始化失败: {e}")
        return None
    
    return agent


async def test_agent_trace(agent: NewsTraceAgent):
    """测试 Agent 新闻溯源功能"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: Agent 新闻溯源（简单测试）")
    logger.info("=" * 60)
    
    # 使用一个简单的测试用例
    test_claim = "某科技公司宣布获得新一轮融资"
    
    logger.info(f"测试新闻: {test_claim}")
    logger.info("开始溯源...")
    
    try:
        result = await agent.trace_news(test_claim, max_iterations=3)
        
        logger.info("\n" + "-" * 60)
        logger.info("溯源结果:")
        logger.info(f"  原始声明: {result.original_claim}")
        logger.info(f"  找到来源数: {len(result.sources)}")
        logger.info(f"  置信度: {result.confidence:.2f}")
        logger.info(f"  摘要: {result.summary[:200]}..." if len(result.summary) > 200 else f"  摘要: {result.summary}")
        
        if result.sources:
            logger.info("\n来源列表:")
            for i, source in enumerate(result.sources[:3], 1):  # 只显示前3个
                logger.info(f"  {i}. {source.title}")
                logger.info(f"     URL: {source.url}")
                if source.snippet:
                    logger.info(f"     摘要: {source.snippet[:100]}...")
        
    except Exception as e:
        logger.error(f"新闻溯源测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def test_complete_trace_flow(agent: NewsTraceAgent):
    """测试完整的溯源流程：GoogleSearch → WebScraper"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 5: 完整溯源流程（GoogleSearch → WebScraper）")
    logger.info("=" * 60)
    
    # 使用"蔡徐坤的梗"作为测试用例
    test_claim = "蔡徐坤的梗"
    
    logger.info(f"测试主题: {test_claim}")
    logger.info("=" * 60)
    logger.info("预期流程:")
    logger.info("  1. GoogleSearch: 搜索相关信息和来源")
    logger.info("  2. WebScraper: 对搜索结果中的网页进行详细抓取")
    logger.info("  3. 综合分析: 提取完整的溯源信息")
    logger.info("=" * 60)
    logger.info("开始完整溯源...\n")
    
    try:
        result = await agent.trace_news(test_claim, max_iterations=5)
        
        logger.info("\n" + "=" * 60)
        logger.info("完整溯源结果")
        logger.info("=" * 60)
        logger.info(f"原始主题: {result.original_claim}")
        logger.info(f"找到来源数: {len(result.sources)}")
        logger.info(f"置信度: {result.confidence:.2f}")
        
        # 分析来源类型
        google_sources = [s for s in result.sources if s.relevance_score == 0.8]
        scraper_sources = [s for s in result.sources if s.relevance_score == 0.85]
        
        logger.info(f"\n来源类型分析:")
        logger.info(f"  - GoogleSearch 来源: {len(google_sources)} 个")
        logger.info(f"  - WebScraper 来源: {len(scraper_sources)} 个")
        
        logger.info(f"\n完整摘要:")
        logger.info("-" * 60)
        logger.info(result.summary)
        logger.info("-" * 60)
        
        if result.sources:
            logger.info(f"\n详细来源列表 (共 {len(result.sources)} 个):")
            logger.info("=" * 60)
            
            for i, source in enumerate(result.sources, 1):
                source_type = "WebScraper" if source.relevance_score == 0.85 else "GoogleSearch"
                logger.info(f"\n【来源 {i}】类型: {source_type}")
                logger.info(f"  标题: {source.title}")
                logger.info(f"  URL: {source.url}")
                
                if source.published_date:
                    logger.info(f"  发布时间: {source.published_date}")
                
                if source.author:
                    logger.info(f"  作者: {source.author}")
                
                if source.snippet:
                    snippet_preview = source.snippet[:200] + "..." if len(source.snippet) > 200 else source.snippet
                    logger.info(f"  内容摘要: {snippet_preview}")
                
                logger.info(f"  相关性分数: {source.relevance_score}")
        
        # 检查是否使用了 WebScraper
        if scraper_sources:
            logger.info("\n" + "=" * 60)
            logger.info("✅ 成功！完整流程已执行：")
            logger.info("  1. ✅ GoogleSearch 找到初始来源")
            logger.info("  2. ✅ WebScraper 抓取了详细内容")
            logger.info("  3. ✅ 综合分析完成")
        else:
            logger.info("\n" + "=" * 60)
            logger.info("⚠️  注意：本次只使用了 GoogleSearch")
            logger.info("  LLM 可能认为搜索结果已足够，未继续调用 WebScraper")
            logger.info("  这是正常的，取决于 LLM 的决策")
        
    except Exception as e:
        logger.error(f"完整溯源测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())


async def main():
    """主测试函数"""
    logger.info("开始测试新闻溯源 Agent...")
    logger.info(f"工作目录: {os.getcwd()}")
    
    # 检查必要的环境变量
    api_key = os.getenv("ONEAPI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("⚠️  未找到 API Key，某些测试可能会失败")
        logger.warning("请在 .env 文件中配置 ONEAPI_API_KEY 或其他 API Key")
    else:
        logger.info("✓ API Key 已配置")
    
    serper_key = os.getenv("SERPER_API_KEY")
    if not serper_key:
        logger.warning("⚠️  未找到 SERPER_API_KEY，Google 搜索测试可能会失败")
    else:
        logger.info("✓ SERPER_API_KEY 已配置")
    
    # 检查 playwright
    try:
        import playwright
        logger.info("✓ Playwright 已安装")
        logger.info("  注意: 如果网页抓取失败，请运行 'playwright install' 安装浏览器")
    except ImportError:
        logger.warning("⚠️  Playwright 未安装，网页抓取功能将不可用")
    
    # 测试工具
    await test_tools()
    
    # 测试 Agent
    agent = await test_agent_simple()
    if agent:
        # 简单溯源测试
        await test_agent_trace(agent)
        
        # 完整溯源流程测试（GoogleSearch → WebScraper）
        await test_complete_trace_flow(agent)
    
    logger.info("\n" + "=" * 60)
    logger.info("所有测试完成！")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

