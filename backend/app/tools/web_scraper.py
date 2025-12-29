"""Web scraping tool using Playwright."""
import asyncio
import os
import queue
import sys
import threading
from typing import Optional

from loguru import logger
from mira import LLMTool
from pydantic import Field

# Detect if we're on Windows
IS_WINDOWS = sys.platform == 'win32'

# Try to import playwright, but make it optional
# Import both sync and async APIs if available
PLAYWRIGHT_AVAILABLE = False
USE_SYNC_API = False
SYNC_API_AVAILABLE = False
ASYNC_API_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright, Browser as SyncBrowser, Page as SyncPage
    SYNC_API_AVAILABLE = True
    PLAYWRIGHT_AVAILABLE = True
    USE_SYNC_API = True
except ImportError:
    sync_playwright = None
    SyncBrowser = None
    SyncPage = None

try:
    from playwright.async_api import async_playwright, Browser as AsyncBrowser, Page as AsyncPage
    ASYNC_API_AVAILABLE = True
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None
    AsyncBrowser = None
    AsyncPage = None

if not PLAYWRIGHT_AVAILABLE:
    logger.warning("playwright not installed, WebScraper will return empty results")


class WebScraper(LLMTool):
    """Scrape content from web pages using Playwright.
    
    This tool allows you to fetch and extract content from web pages,
    including the main text content, title, and metadata.
    
    Returns detailed structured information including:
    - Full article content (up to 15000 characters)
    - Title, author, published date
    - Paragraphs and headings for structured analysis
    - Meta description and keywords
    """
    
    url: str = Field(..., description="URL to scrape")
    extract_content: bool = Field(default=True, description="Whether to extract main content")
    
    def _format_result_for_llm(self, result: dict) -> str:
        """Format result dictionary as a readable string for LLM."""
        if not result.get('success'):
            return f"Web scraping failed for {result.get('url', 'unknown')}: {result.get('error', 'unknown error')}"
        
        lines = [
            f"URL: {result.get('url', 'N/A')}",
            f"Title: {result.get('title', 'N/A')}",
        ]
        
        if result.get('author'):
            lines.append(f"Author: {result.get('author')}")
        
        if result.get('published_date'):
            lines.append(f"Published Date: {result.get('published_date')}")
        
        if result.get('meta_description'):
            lines.append(f"Description: {result.get('meta_description')}")
        
        if result.get('headings'):
            lines.append(f"\nHeadings ({len(result.get('headings', []))}):")
            for i, heading in enumerate(result.get('headings', [])[:10], 1):
                lines.append(f"  {i}. {heading}")
        
        if result.get('key_paragraphs'):
            lines.append(f"\nKey Paragraphs (showing {len(result.get('key_paragraphs', []))} of {result.get('paragraphs_count', 0)}):")
            for i, para in enumerate(result.get('key_paragraphs', [])[:5], 1):
                para_text = para[:200] + "..." if len(para) > 200 else para
                lines.append(f"  {i}. {para_text}")
        
        lines.append(f"\nFull Content ({result.get('full_content_length', 0)} characters):")
        content = result.get('content', '')
        if content:
            lines.append(content)
        else:
            lines.append("No content extracted")
        
        return "\n".join(lines)
    
    @classmethod
    def schema(cls):
        """Override schema to fix required fields."""
        schema = super().schema()
        # Remove extract_content from required since it has a default value
        if 'function' in schema and 'parameters' in schema['function']:
            params = schema['function']['parameters']
            if 'required' in params and 'extract_content' in params['required']:
                params['required'].remove('extract_content')
        return schema
    
    def __call__(self):
        """Execute web scraping."""
        # If playwright is not available, return empty results
        if not PLAYWRIGHT_AVAILABLE:
            logger.info(f"Web scraping skipped (playwright not installed) for URL '{self.url}'")
            return {
                "success": False,
                "error": "playwright not installed",
                "url": self.url,
                "title": "",
                "content": "",
                "note": "Web scraping is disabled (playwright not installed)"
            }
        
        # First check if we're in a running event loop
        # On Windows, sync API also creates an event loop internally, which fails with NotImplementedError
        # So we must use async API in a completely isolated thread with its own event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an event loop - must use async API in isolated thread
            logger.info(f"Detected running event loop (id={id(loop)}), using async API in isolated thread for {self.url}")
            if not ASYNC_API_AVAILABLE:
                logger.error(f"Cannot use async API (not available) while in event loop for {self.url}")
                return {
                    "success": False,
                    "error": "async API not available while in event loop",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
            return self._run_async_in_thread()
        except RuntimeError:
            # No running event loop, can use sync API if available
            logger.info(f"No event loop detected, checking available APIs for {self.url}")
            if SYNC_API_AVAILABLE:
                logger.info(f"Using sync API for {self.url}")
                try:
                    return self._scrape_sync()
                except Exception as e:
                    logger.error(f"Sync scraping failed for {self.url}: {str(e)}")
                    import traceback
                    logger.debug(f"Sync scraping traceback: {traceback.format_exc()}")
                    return {
                        "success": False,
                        "error": f"sync scraping failed: {str(e)}",
                        "url": self.url,
                        "title": "",
                        "content": ""
                    }
            elif ASYNC_API_AVAILABLE:
                # No sync API available, use async API with asyncio.run
                logger.info(f"No sync API available, using async API with asyncio.run for {self.url}")
                try:
                    return asyncio.run(self._scrape())
                except Exception as e:
                    logger.error(f"Async scraping with asyncio.run failed for {self.url}: {str(e)}")
                    import traceback
                    logger.debug(f"Async scraping traceback: {traceback.format_exc()}")
                    return {
                        "success": False,
                        "error": f"async scraping failed: {str(e)}",
                        "url": self.url,
                        "title": "",
                        "content": ""
                    }
            else:
                logger.error(f"No Playwright API available for {self.url}")
                return {
                    "success": False,
                    "error": "no playwright API available",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
        except Exception as e:
            logger.error(f"Unexpected error in web scraping for {self.url}: {str(e)}")
            import traceback
            logger.error(f"Unexpected error traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"unexpected error: {str(e)}",
                "url": self.url,
                "title": "",
                "content": ""
            }
    
    def _run_sync_in_thread(self):
        """Run sync scraping in a separate thread (for Windows when in event loop).
        
        On Windows, we must ensure the thread has NO event loop at all.
        Uses queue for thread-safe communication.
        """
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def run_in_thread():
            """Run in thread with no event loop."""
            try:
                # Explicitly set event loop to None for this thread
                # This is critical on Windows to avoid NotImplementedError
                try:
                    # Try to get and close any existing loop
                    loop = asyncio.get_event_loop()
                    if not loop.is_closed():
                        loop.close()
                except RuntimeError:
                    # No event loop exists, which is what we want
                    pass
                except AttributeError:
                    # get_event_loop() might not exist in some Python versions
                    pass
                
                # Ensure no event loop is set for this thread
                # This is critical on Windows
                asyncio.set_event_loop(None)
                
                logger.debug(f"Starting sync scraping in thread (no event loop) for {self.url}")
                result = self._scrape_sync()
                result_queue.put(result)
                logger.debug(f"Sync scraping completed in thread for {self.url}")
            except Exception as e:
                exception_queue.put(e)
                import traceback
                logger.error(f"Thread error for {self.url}: {str(e)}")
                logger.debug(f"Thread traceback: {traceback.format_exc()}")
        
        try:
            logger.debug(f"Creating thread for sync scraping of {self.url}")
            thread = threading.Thread(
                target=run_in_thread, 
                daemon=False, 
                name=f"WebScraper-Sync-{self.url[:50]}"
            )
            thread.start()
            thread.join(timeout=60)  # 60 second timeout
            
            if thread.is_alive():
                logger.warning(f"Web scraping timeout for {self.url} (thread still alive after 60s)")
                return {
                    "success": False,
                    "error": "timeout (thread did not complete within 60 seconds)",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
            
            # Check for exceptions first
            if not exception_queue.empty():
                exc = exception_queue.get()
                logger.error(f"Exception in scraping thread for {self.url}: {str(exc)}")
                return {
                    "success": False,
                    "error": f"thread exception: {str(exc)}",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
            
            # Return result if available
            if not result_queue.empty():
                return result_queue.get()
            else:
                logger.error(f"No result returned from scraping thread for {self.url}")
                return {
                    "success": False,
                    "error": "no result returned from scraping thread",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
        except Exception as e:
            logger.error(f"Error managing scraping thread for {self.url}: {str(e)}")
            import traceback
            logger.debug(f"Thread management traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"thread management error: {str(e)}",
                "url": self.url,
                "title": "",
                "content": ""
            }
    
    def _run_async_in_thread(self):
        """Run async scraping in a separate thread with its own event loop.
        
        This is necessary on Windows when the main thread has an event loop,
        because Playwright's async API needs to create subprocesses, which
        requires a proper event loop in the thread.
        """
        result_queue = queue.Queue()
        exception_queue = queue.Queue()
        
        def run_in_thread():
            """Run async scraping in thread with new event loop."""
            try:
                # Create a completely new event loop for this thread
                # This is critical on Windows to allow subprocess creation
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    logger.debug(f"Starting async scraping in thread (new event loop) for {self.url}")
                    result = new_loop.run_until_complete(self._scrape())
                    result_queue.put(result)
                    logger.debug(f"Async scraping completed in thread for {self.url}")
                finally:
                    try:
                        # Cancel any pending tasks
                        pending = asyncio.all_tasks(new_loop)
                        for task in pending:
                            task.cancel()
                        # Wait for tasks to be cancelled
                        if pending:
                            new_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception:
                        pass
                    finally:
                        new_loop.close()
                        asyncio.set_event_loop(None)
            except Exception as e:
                exception_queue.put(e)
                import traceback
                logger.error(f"Thread error for {self.url}: {str(e)}")
                logger.debug(f"Thread traceback: {traceback.format_exc()}")
        
        try:
            logger.debug(f"Creating thread for async scraping of {self.url}")
            thread = threading.Thread(target=run_in_thread, daemon=False, name=f"WebScraper-Async-{self.url[:50]}")
            thread.start()
            thread.join(timeout=60)  # 60 second timeout
            
            if thread.is_alive():
                logger.warning(f"Web scraping timeout for {self.url} (thread still alive after 60s)")
                return {
                    "success": False,
                    "error": "timeout (thread did not complete within 60 seconds)",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
            
            # Check for exceptions first
            if not exception_queue.empty():
                exc = exception_queue.get()
                logger.error(f"Exception in scraping thread for {self.url}: {str(exc)}")
                return {
                    "success": False,
                    "error": f"thread exception: {str(exc)}",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
            
            # Return result if available
            if not result_queue.empty():
                return result_queue.get()
            else:
                logger.error(f"No result returned from scraping thread for {self.url}")
                return {
                    "success": False,
                    "error": "no result returned from scraping thread",
                    "url": self.url,
                    "title": "",
                    "content": ""
                }
        except Exception as e:
            logger.error(f"Error managing scraping thread for {self.url}: {str(e)}")
            import traceback
            logger.debug(f"Thread management traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": f"thread management error: {str(e)}",
                "url": self.url,
                "title": "",
                "content": ""
            }
    
    def _scrape_sync(self):
        """Synchronous web scraping using Playwright sync API."""
        if not SYNC_API_AVAILABLE or sync_playwright is None:
            raise RuntimeError("Playwright sync API is not available")
        
        browser = None
        context = None
        page = None
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = context.new_page()
                
                # Navigate to URL with error handling
                try:
                    page.goto(self.url, wait_until="networkidle", timeout=30000)
                except Exception as nav_error:
                    # If networkidle fails, try with domcontentloaded
                    logger.warning(f"networkidle failed for {self.url}, trying domcontentloaded: {str(nav_error)}")
                    try:
                        page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
                    except Exception as nav_error2:
                        logger.warning(f"domcontentloaded also failed for {self.url}, trying load: {str(nav_error2)}")
                        page.goto(self.url, wait_until="load", timeout=30000)
                
                # Extract basic information
                title = page.title()
                
                # Extract main content with better structure
                content = ""
                full_content = ""
                paragraphs = []
                headings = []
                
                if self.extract_content:
                    # Try to find main content area with priority
                    content_selectors = [
                        "article",
                        "main",
                        "[role='main']",
                        ".article-content",
                        ".post-content",
                        ".entry-content",
                        ".content",
                        "#content",
                        ".main-content"
                    ]
                    
                    for selector in content_selectors:
                        try:
                            element = page.query_selector(selector)
                            if element:
                                full_content = element.inner_text()
                                if len(full_content) > 200:  # Found substantial content
                                    # Extract paragraphs
                                    para_elements = element.query_selector_all("p")
                                    paragraphs = [p.inner_text().strip() for p in para_elements if p.inner_text().strip()]
                                    
                                    # Extract headings
                                    heading_elements = element.query_selector_all("h1, h2, h3, h4, h5, h6")
                                    headings = [h.inner_text().strip() for h in heading_elements if h.inner_text().strip()]
                                    
                                    content = full_content
                                    logger.debug(f"Found content using selector: {selector}, length: {len(content)}")
                                    break
                        except Exception as e:
                            logger.debug(f"Selector {selector} failed: {str(e)}")
                            continue
                    
                    # If no content found, get body text
                    if not content or len(content) < 200:
                        body = page.query_selector("body")
                        if body:
                            full_content = body.inner_text()
                            content = full_content
                            # Try to extract paragraphs from body
                            try:
                                para_elements = body.query_selector_all("p")
                                paragraphs = [p.inner_text().strip() for p in para_elements if p.inner_text().strip() and len(p.inner_text().strip()) > 20]
                            except:
                                pass
                
                # Extract metadata
                meta_description = ""
                meta_keywords = ""
                author = ""
                try:
                    meta_desc_element = page.query_selector('meta[name="description"]')
                    if meta_desc_element:
                        meta_description = meta_desc_element.get_attribute("content") or ""
                    
                    meta_keywords_element = page.query_selector('meta[name="keywords"]')
                    if meta_keywords_element:
                        meta_keywords = meta_keywords_element.get_attribute("content") or ""
                    
                    # Try to find author
                    author_selectors = [
                        'meta[name="author"]',
                        '[rel="author"]',
                        '.author',
                        '.byline',
                        '[itemprop="author"]'
                    ]
                    for selector in author_selectors:
                        try:
                            author_element = page.query_selector(selector)
                            if author_element:
                                author = author_element.get_attribute("content") or author_element.inner_text() or ""
                                if author:
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Metadata extraction error: {str(e)}")
                
                # Extract published date if available
                published_date = None
                date_selectors = [
                    'time[datetime]',
                    '[itemprop="datePublished"]',
                    'meta[property="article:published_time"]',
                    '.published-date',
                    '.date',
                    '.publish-date',
                    '[datetime]'
                ]
                for selector in date_selectors:
                    try:
                        date_element = page.query_selector(selector)
                        if date_element:
                            published_date = date_element.get_attribute("datetime") or date_element.get_attribute("content") or date_element.inner_text()
                            if published_date:
                                break
                    except:
                        continue
                
                # Build structured content for LLM
                # Note: browser will be closed automatically when exiting the 'with' block
                # Use full content but limit to 15000 chars for LLM processing
                content_for_llm = content[:15000] if content else ""
                if len(content) > 15000:
                    content_for_llm += f"\n\n[内容已截断，原始长度: {len(content)} 字符]"
                
                # Format result for better LLM understanding
                result_dict = {
                    "success": True,
                    "url": self.url,
                    "title": title,
                    "content": content_for_llm,  # Increased limit for better analysis
                    "full_content_length": len(content) if content else 0,
                    "meta_description": meta_description,
                    "meta_keywords": meta_keywords,
                    "author": author,
                    "published_date": published_date,
                    "paragraphs_count": len(paragraphs),
                    "headings": headings[:10] if headings else [],  # First 10 headings
                    "key_paragraphs": paragraphs[:5] if paragraphs else [],  # First 5 paragraphs as key content
                    "content_summary": content[:1000] if content else ""  # First 1000 chars as summary
                }
                
                # Create a formatted string version for LLM (mira will call str() on the result)
                formatted_output = self._format_result_for_llm(result_dict)
                result_dict["formatted_output"] = formatted_output
                
                logger.info(f"Web scraping completed for URL: {self.url}, extracted {len(content)} chars, {len(paragraphs)} paragraphs, {len(headings)} headings")
                
                # Return a custom dict that formats nicely when converted to string
                class FormattedResult(dict):
                    def __str__(self):
                        return self.get("formatted_output", super().__str__())
                
                return FormattedResult(result_dict)
                
        except Exception as e:
            logger.error(f"Web scraping failed for {self.url}: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            
            # Ensure cleanup
            try:
                if page:
                    page.close()
                if context:
                    context.close()
                if browser:
                    browser.close()
            except:
                pass
            
            return {
                "success": False,
                "error": str(e),
                "url": self.url,
                "title": "",
                "content": ""
            }
    
    async def _scrape(self):
        """Async web scraping implementation."""
        if not ASYNC_API_AVAILABLE or async_playwright is None:
            raise RuntimeError("Playwright async API is not available")
        
        browser = None
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
                page = await context.new_page()
                
                # Navigate to URL
                logger.debug(f"Navigating to {self.url}")
                await page.goto(self.url, wait_until="networkidle", timeout=30000)
                
                # Extract basic information
                title = await page.title()
                logger.debug(f"Extracted title: {title[:50]}...")
                
                # Extract main content with better structure
                content = ""
                full_content = ""
                paragraphs = []
                headings = []
                
                if self.extract_content:
                    # Try to find main content area with priority
                    content_selectors = [
                        "article",
                        "main",
                        "[role='main']",
                        ".article-content",
                        ".post-content",
                        ".entry-content",
                        ".content",
                        "#content",
                        ".main-content"
                    ]
                    
                    for selector in content_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                full_content = await element.inner_text()
                                if len(full_content) > 200:  # Found substantial content
                                    # Extract paragraphs
                                    para_elements = await element.query_selector_all("p")
                                    paragraphs = [await p.inner_text() for p in para_elements if await p.inner_text()]
                                    paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
                                    
                                    # Extract headings
                                    heading_elements = await element.query_selector_all("h1, h2, h3, h4, h5, h6")
                                    headings = [await h.inner_text() for h in heading_elements if await h.inner_text()]
                                    headings = [h.strip() for h in headings if h.strip()]
                                    
                                    content = full_content
                                    logger.debug(f"Found content using selector: {selector}, length: {len(content)}")
                                    break
                        except Exception as e:
                            logger.debug(f"Selector {selector} failed: {str(e)}")
                            continue
                    
                    # If no content found, get body text
                    if not content or len(content) < 200:
                        body = await page.query_selector("body")
                        if body:
                            full_content = await body.inner_text()
                            content = full_content
                            # Try to extract paragraphs from body
                            try:
                                para_elements = await body.query_selector_all("p")
                                paragraphs = [await p.inner_text() for p in para_elements if await p.inner_text()]
                                paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
                            except:
                                pass
                            logger.debug(f"Using body text, length: {len(content)}")
                
                # Extract metadata
                meta_description = ""
                meta_keywords = ""
                author = ""
                try:
                    meta_desc_element = await page.query_selector('meta[name="description"]')
                    if meta_desc_element:
                        meta_description = await meta_desc_element.get_attribute("content") or ""
                    
                    meta_keywords_element = await page.query_selector('meta[name="keywords"]')
                    if meta_keywords_element:
                        meta_keywords = await meta_keywords_element.get_attribute("content") or ""
                    
                    # Try to find author
                    author_selectors = [
                        'meta[name="author"]',
                        '[rel="author"]',
                        '.author',
                        '.byline',
                        '[itemprop="author"]'
                    ]
                    for selector in author_selectors:
                        try:
                            author_element = await page.query_selector(selector)
                            if author_element:
                                author = await author_element.get_attribute("content") or await author_element.inner_text() or ""
                                if author:
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Metadata extraction error: {str(e)}")
                
                # Extract published date if available
                published_date = None
                date_selectors = [
                    'time[datetime]',
                    '[itemprop="datePublished"]',
                    'meta[property="article:published_time"]',
                    '.published-date',
                    '.date',
                    '.publish-date',
                    '[datetime]'
                ]
                for selector in date_selectors:
                    try:
                        date_element = await page.query_selector(selector)
                        if date_element:
                            published_date = await date_element.get_attribute("datetime") or await date_element.get_attribute("content") or await date_element.inner_text()
                            if published_date:
                                break
                    except Exception as e:
                        logger.debug(f"Date selector {selector} failed: {str(e)}")
                        continue
                
                # Close browser before returning
                await browser.close()
                browser = None
                
                # Build structured content for LLM
                # Use full content but limit to 15000 chars for LLM processing
                content_for_llm = content[:15000] if content else ""
                if len(content) > 15000:
                    content_for_llm += f"\n\n[内容已截断，原始长度: {len(content)} 字符]"
                
                # Format result for better LLM understanding
                result_dict = {
                    "success": True,
                    "url": self.url,
                    "title": title,
                    "content": content_for_llm,  # Increased limit for better analysis
                    "full_content_length": len(content) if content else 0,
                    "meta_description": meta_description,
                    "meta_keywords": meta_keywords,
                    "author": author,
                    "published_date": published_date,
                    "paragraphs_count": len(paragraphs),
                    "headings": headings[:10] if headings else [],  # First 10 headings
                    "key_paragraphs": paragraphs[:5] if paragraphs else [],  # First 5 paragraphs as key content
                    "content_summary": content[:1000] if content else ""  # First 1000 chars as summary
                }
                
                # Create a formatted string version for LLM (mira will call str() on the result)
                formatted_output = self._format_result_for_llm(result_dict)
                result_dict["formatted_output"] = formatted_output
                
                logger.info(f"Web scraping completed for URL: {self.url}, extracted {len(content)} chars, {len(paragraphs)} paragraphs, {len(headings)} headings")
                
                # Return a custom dict that formats nicely when converted to string
                class FormattedResult(dict):
                    def __str__(self):
                        return self.get("formatted_output", super().__str__())
                
                return FormattedResult(result_dict)
                
        except Exception as e:
            logger.error(f"Web scraping failed for {self.url}: {str(e)}")
            import traceback
            logger.debug(f"Async scraping traceback: {traceback.format_exc()}")
            
            # Ensure browser is closed even on error
            if browser:
                try:
                    await browser.close()
                except Exception as close_error:
                    logger.debug(f"Error closing browser: {str(close_error)}")
            
            return {
                "success": False,
                "error": str(e),
                "url": self.url,
                "title": "",
                "content": ""
            }

