"""测试 WebScraper 工具，验证 Windows 事件循环问题是否已修复"""
import asyncio
import os
import sys
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

from app.tools.web_scraper import WebScraper, PLAYWRIGHT_AVAILABLE, USE_SYNC_API


def test_web_scraper_sync():
    """测试同步调用 WebScraper（不在事件循环中）"""
    logger.info("=" * 60)
    logger.info("测试 1: 同步调用 WebScraper（不在事件循环中）")
    logger.info("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("⚠️  Playwright 未安装，跳过测试")
        return False
    
    logger.info(f"使用 {'同步' if USE_SYNC_API else '异步'} API")
    
    try:
        scraper = WebScraper(
            url="https://www.example.com",
            extract_content=True
        )
        result = scraper()
        
        if result.get('success'):
            logger.info("✅ 测试通过！")
            logger.info(f"   标题: {result.get('title', 'N/A')}")
            logger.info(f"   内容长度: {result.get('content_length', 0)} 字符")
            logger.info(f"   URL: {result.get('url', 'N/A')}")
            
            # 显示内容预览
            content = result.get('content', '')
            if content:
                preview_length = 300
                content_preview = content[:preview_length]
                if len(content) > preview_length:
                    content_preview += "..."
                logger.info(f"   内容预览 ({len(content)} 字符):")
                logger.info(f"   {'-' * 50}")
                content_lines = content.split('\n')
                for line in content_preview.split('\n')[:10]:  # 最多显示10行
                    if line.strip():
                        logger.info(f"   {line[:80]}")
                if len(content_lines) > 10:
                    remaining_lines = len(content_lines) - 10
                    logger.info(f"   ... (还有 {remaining_lines} 行)")
                logger.info(f"   {'-' * 50}")
            
            return True
        else:
            logger.error(f"❌ 测试失败: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_web_scraper_async():
    """测试在事件循环中调用 WebScraper"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 2: 在事件循环中调用 WebScraper")
    logger.info("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("⚠️  Playwright 未安装，跳过测试")
        return False
    
    logger.info(f"使用 {'同步' if USE_SYNC_API else '异步'} API")
    logger.info("注意: 这个测试会模拟在已有事件循环中调用的情况")
    
    try:
        scraper = WebScraper(
            url="https://www.example.com",
            extract_content=True
        )
        
        # 在事件循环中调用（这会触发线程隔离逻辑）
        result = scraper()
        
        if result.get('success'):
            logger.info("✅ 测试通过！")
            logger.info(f"   标题: {result.get('title', 'N/A')}")
            logger.info(f"   内容长度: {result.get('content_length', 0)} 字符")
            logger.info(f"   URL: {result.get('url', 'N/A')}")
            
            # 显示内容预览
            content = result.get('content', '')
            if content:
                preview_length = 300
                content_preview = content[:preview_length]
                if len(content) > preview_length:
                    content_preview += "..."
                logger.info(f"   内容预览 ({len(content)} 字符):")
                logger.info(f"   {'-' * 50}")
                content_lines = content.split('\n')
                for line in content_preview.split('\n')[:10]:  # 最多显示10行
                    if line.strip():
                        logger.info(f"   {line[:80]}")
                if len(content_lines) > 10:
                    remaining_lines = len(content_lines) - 10
                    logger.info(f"   ... (还有 {remaining_lines} 行)")
                logger.info(f"   {'-' * 50}")
            
            return True
        else:
            logger.error(f"❌ 测试失败: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"❌ 测试失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def test_web_scraper_multiple():
    """测试多次调用 WebScraper（模拟实际使用场景）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 3: 多次调用 WebScraper（模拟 Agent 使用场景）")
    logger.info("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("⚠️  Playwright 未安装，跳过测试")
        return False
    
    test_urls = [
        "https://www.example.com",
        "https://httpbin.org/html",
        "https://www.example.com"  # 重复测试
    ]
    
    success_count = 0
    for i, url in enumerate(test_urls, 1):
        logger.info(f"\n测试 URL {i}/{len(test_urls)}: {url}")
        try:
            scraper = WebScraper(url=url, extract_content=True)
            result = scraper()
            
            if result.get('success'):
                logger.info(f"  ✅ 成功: {result.get('title', 'N/A')[:50]}")
                content = result.get('content', '')
                if content:
                    preview = content[:150].replace('\n', ' ')
                    if len(content) > 150:
                        preview += "..."
                    logger.info(f"     内容预览: {preview}")
                success_count += 1
            else:
                logger.warning(f"  ⚠️  失败: {result.get('error', 'Unknown')}")
        except Exception as e:
            logger.error(f"  ❌ 异常: {str(e)}")
    
    logger.info(f"\n结果: {success_count}/{len(test_urls)} 成功")
    return success_count > 0


async def test_web_scraper_real_urls():
    """测试真实 URL（可能会失败的）"""
    logger.info("\n" + "=" * 60)
    logger.info("测试 4: 测试真实 URL（包括可能失败的）")
    logger.info("=" * 60)
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning("⚠️  Playwright 未安装，跳过测试")
        return False
    
    test_urls = [
        {
            "url": "https://www.example.com",
            "expected": True,
            "description": "简单测试页面"
        },
        {
            "url": "https://zh.wikipedia.org/zh-hans/%E8%94%A1%E5%BE%90%E5%9D%A4%E7%AF%AE%E7%90%83%E8%A7%86%E9%A2%91%E4%BA%8B%E4%BB%B6",
            "expected": True,
            "description": "HTML 测试页面"
        },
        {
            "url": "https://www.baidu.com",
            "expected": True,
            "description": "百度首页（可能较慢）"
        }
    ]
    
    results = []
    for test_case in test_urls:
        url = test_case["url"]
        description = test_case["description"]
        logger.info(f"\n测试: {description}")
        logger.info(f"URL: {url}")
        
        try:
            scraper = WebScraper(url=url, extract_content=True)
            result = scraper()
            
            if result.get('success'):
                logger.info(f"  ✅ 成功")
                logger.info(f"     标题: {result.get('title', 'N/A')[:60]}")
                logger.info(f"     内容长度: {result.get('content_length', 0)} 字符")
                
                # 显示内容预览
                content = result.get('content', '')
                if content:
                    preview_length = 400
                    content_preview = content[:preview_length]
                    if len(content) > preview_length:
                        content_preview += "..."
                    logger.info(f"     内容预览:")
                    logger.info(f"     {'-' * 60}")
                    content_lines = content.split('\n')
                    for line in content_preview.split('\n')[:15]:  # 最多显示15行
                        if line.strip():
                            logger.info(f"     {line[:70]}")
                    if len(content_lines) > 15:
                        remaining_lines = len(content_lines) - 15
                        logger.info(f"     ... (还有 {remaining_lines} 行)")
                    logger.info(f"     {'-' * 60}")
                
                results.append(True)
            else:
                logger.warning(f"  ⚠️  失败: {result.get('error', 'Unknown')}")
                results.append(False)
        except Exception as e:
            logger.error(f"  ❌ 异常: {str(e)}")
            results.append(False)
    
    success_count = sum(results)
    logger.info(f"\n结果: {success_count}/{len(test_urls)} 成功")
    return success_count > 0


async def main():
    """主测试函数"""
    logger.info("开始测试 WebScraper 工具...")
    logger.info(f"工作目录: {os.getcwd()}")
    logger.info(f"Playwright 可用: {PLAYWRIGHT_AVAILABLE}")
    if PLAYWRIGHT_AVAILABLE:
        logger.info(f"使用 API 类型: {'同步' if USE_SYNC_API else '异步'}")
    
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("❌ Playwright 未安装，无法进行测试")
        logger.info("请运行: pip install playwright")
        logger.info("然后运行: playwright install chromium")
        return
    
    # 测试 1: 同步调用
    test1_result = test_web_scraper_sync()
    
    # 测试 2: 在事件循环中调用
    test2_result = await test_web_scraper_async()
    
    # 测试 3: 多次调用
    test3_result = await test_web_scraper_multiple()
    
    # 测试 4: 真实 URL
    test4_result = await test_web_scraper_real_urls()
    
    # 总结
    logger.info("\n" + "=" * 60)
    logger.info("测试总结")
    logger.info("=" * 60)
    logger.info(f"测试 1 (同步调用): {'✅ 通过' if test1_result else '❌ 失败'}")
    logger.info(f"测试 2 (事件循环中): {'✅ 通过' if test2_result else '❌ 失败'}")
    logger.info(f"测试 3 (多次调用): {'✅ 通过' if test3_result else '❌ 失败'}")
    logger.info(f"测试 4 (真实 URL): {'✅ 通过' if test4_result else '❌ 失败'}")
    
    all_passed = all([test1_result, test2_result, test3_result, test4_result])
    if all_passed:
        logger.info("\n🎉 所有测试通过！")
    else:
        logger.warning("\n⚠️  部分测试失败，请检查日志")
    
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

