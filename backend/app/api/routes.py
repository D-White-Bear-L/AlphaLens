"""FastAPI routes for news tracing."""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger
from pydantic import BaseModel

from app.agent.news_trace_agent import NewsTraceAgent
from app.agent.financial_agent import FinancialAgent
from app.agent.strategy_backtest import StrategyBacktest
from app.agent.stock_prediction import StockPrediction
from app.models import (
    NewsSource, SearchQuery, TraceResult, WebScrapeRequest,
    FinancialAnalysisRequest, FinancialAnalysisResult,
    StockRecommendationRequest, StockRecommendationResult,
    BacktestRequest, BacktestResult,
    PredictionRequest, PredictionResult
)

# 任务存储（生产环境应使用 Redis 或数据库）
tasks: Dict[str, Dict] = {}
# 任务取消标志
task_cancelled: Dict[str, bool] = {}

router = APIRouter()
agent = NewsTraceAgent()
financial_agent = FinancialAgent()
backtest_engine = StrategyBacktest(financial_agent=financial_agent)
prediction_engine = StockPrediction(financial_agent=financial_agent)


class TraceRequest(BaseModel):
    """Request model for news tracing."""
    claim: str
    max_depth: Optional[int] = 2  # 默认深度为2（中等）


class TaskStatus(BaseModel):
    """Task status response."""
    task_id: str
    status: str  # pending, processing, completed, failed, cancelled
    progress: float = 0.0  # 0.0 to 1.0
    message: Optional[str] = None
    result: Optional[dict] = None  # 使用 dict 而不是 TraceResult，因为存储的是字典
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


def update_task_progress(task_id: str, progress: float, message: str):
    """更新任务进度（线程安全）"""
    if task_id in tasks:
        tasks[task_id]["progress"] = progress
        tasks[task_id]["message"] = message
        tasks[task_id]["updated_at"] = datetime.now()

async def process_trace_task(task_id: str, claim: str, max_depth: int = 2):
    """Background task to process news tracing.
    
    Args:
        task_id: Task ID
        claim: News claim to trace
        max_depth: Maximum depth for tracing (1-4, default 2)
    """
    try:
        logger.info(f"Starting background task {task_id} for claim: {claim[:50]}... (depth: {max_depth})")
        
        # 初始化取消标志
        task_cancelled[task_id] = False
        
        # 更新任务状态为处理中
        tasks[task_id]["status"] = "processing"
        update_task_progress(task_id, 0.05, "初始化任务...")
        await asyncio.sleep(0.1)  # 短暂延迟确保状态更新
        
        # 检查是否已取消
        if task_cancelled.get(task_id, False):
            tasks[task_id]["status"] = "cancelled"
            tasks[task_id]["message"] = "任务已取消"
            tasks[task_id]["updated_at"] = datetime.now()
            logger.info(f"Task {task_id} cancelled before processing")
            return
        
        # 阶段1: 开始搜索
        update_task_progress(task_id, 0.15, "开始搜索相关来源...")
        logger.info(f"Task {task_id} status updated to processing")
        
        # 创建一个包装任务来监控进度
        from datetime import datetime as dt
        
        start_time = dt.now()
        estimated_duration = 120  # 估算总时长120秒
        
        # 启动进度监控任务
        async def progress_monitor():
            while tasks[task_id]["status"] == "processing":
                # 检查是否已取消
                if task_cancelled.get(task_id, False):
                    break
                    
                elapsed = (dt.now() - start_time).total_seconds()
                # 基于时间估算进度（最多到90%，留10%给最终处理）
                estimated_progress = min(0.15 + (elapsed / estimated_duration) * 0.75, 0.90)
                
                # 根据进度更新消息
                if estimated_progress < 0.3:
                    message = "正在搜索相关来源..."
                elif estimated_progress < 0.5:
                    message = "正在抓取网页内容..."
                elif estimated_progress < 0.7:
                    message = "正在分析信息来源..."
                elif estimated_progress < 0.85:
                    message = "正在构建知识图谱..."
                else:
                    message = "正在生成分析报告..."
                
                update_task_progress(task_id, estimated_progress, message)
                await asyncio.sleep(2)  # 每2秒更新一次进度
        
        # 启动进度监控
        monitor_task = asyncio.create_task(progress_monitor())
        
        try:
            # 检查是否已取消
            if task_cancelled.get(task_id, False):
                tasks[task_id]["status"] = "cancelled"
                tasks[task_id]["message"] = "任务已取消"
                tasks[task_id]["updated_at"] = datetime.now()
                logger.info(f"Task {task_id} cancelled before trace_news")
                return
            
            # 定义取消检查函数
            def check_cancelled():
                return task_cancelled.get(task_id, False)
            
            # 计算最大迭代次数（基于深度）
            # 深度1: 2-3轮, 深度2: 5-6轮, 深度3: 8-9轮, 深度4: 10-12轮
            max_iterations_map = {
                1: 3,
                2: 6,
                3: 9,
                4: 12
            }
            max_iterations = max_iterations_map.get(max_depth, 6)
            
            # 执行溯源任务（传递取消检查函数和最大迭代次数）
            logger.info(f"Task {task_id} starting trace_news with max_iterations={max_iterations} (depth={max_depth})...")
            result = await agent.trace_news(claim, max_iterations=max_iterations, check_cancelled=check_cancelled)
            
            # 再次检查是否已取消（虽然不应该到达这里如果已取消）
            if task_cancelled.get(task_id, False):
                tasks[task_id]["status"] = "cancelled"
                tasks[task_id]["message"] = "任务已取消"
                tasks[task_id]["updated_at"] = datetime.now()
                logger.info(f"Task {task_id} cancelled after trace_news")
                return
                
            logger.info(f"Task {task_id} trace_news completed")
        except asyncio.CancelledError:
            # 任务被取消
            tasks[task_id]["status"] = "cancelled"
            tasks[task_id]["message"] = "任务已取消"
            tasks[task_id]["updated_at"] = datetime.now()
            logger.info(f"Task {task_id} cancelled during execution")
            # 不重新抛出异常，让任务正常结束
            return
        finally:
            # 停止进度监控
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
        
        # 检查是否已取消
        if task_cancelled.get(task_id, False):
            tasks[task_id]["status"] = "cancelled"
            tasks[task_id]["message"] = "任务已取消"
            tasks[task_id]["updated_at"] = datetime.now()
            logger.info(f"Task {task_id} cancelled before finalizing")
            return
        
        # 更新任务为完成
        update_task_progress(task_id, 0.95, "正在整理结果...")
        await asyncio.sleep(0.2)  # 短暂延迟
        
        tasks[task_id]["status"] = "completed"
        tasks[task_id]["progress"] = 1.0
        # 将 Pydantic 模型转换为字典（兼容 v1 和 v2）
        if hasattr(result, 'model_dump'):
            tasks[task_id]["result"] = result.model_dump()
        elif hasattr(result, 'dict'):
            tasks[task_id]["result"] = result.dict()
        else:
            tasks[task_id]["result"] = result
        tasks[task_id]["message"] = "溯源完成"
        tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Task {task_id} completed successfully")
        
    except asyncio.CancelledError:
        # 任务被取消
        tasks[task_id]["status"] = "cancelled"
        tasks[task_id]["message"] = "任务已取消"
        tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Task {task_id} cancelled")
    except Exception as e:
        logger.error(f"Error processing trace task {task_id}: {str(e)}")
        logger.exception(e)
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        tasks[task_id]["message"] = f"处理失败: {str(e)}"
        tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Task {task_id} marked as failed")
    finally:
        # 清理取消标志
        task_cancelled.pop(task_id, None)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "news-trace-backend"}


@router.post("/trace", response_model=TraceResult)
async def trace_news(request: TraceRequest):
    """Trace sources for a news claim (synchronous, for backward compatibility).
    
    Args:
        request: Request containing the news claim or article text to trace
        
    Returns:
        TraceResult with sources and analysis
    """
    try:
        if not request.claim or not request.claim.strip():
            raise HTTPException(status_code=400, detail="Claim cannot be empty")
        
        # 获取深度参数（默认为2）
        max_depth = request.max_depth if request.max_depth else 2
        max_depth = max(1, min(4, max_depth))
        
        # 计算最大迭代次数
        max_iterations_map = {
            1: 3,
            2: 6,
            3: 9,
            4: 12
        }
        max_iterations = max_iterations_map.get(max_depth, 6)
        
        result = await agent.trace_news(request.claim, max_iterations=max_iterations)
        return result
        
    except Exception as e:
        logger.error(f"Error tracing news: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error tracing news: {str(e)}")


@router.post("/trace/async", response_model=TaskStatus)
async def trace_news_async(request: TraceRequest, background_tasks: BackgroundTasks):
    """Start an asynchronous news tracing task.
    
    Args:
        request: Request containing the news claim or article text to trace
        background_tasks: FastAPI background tasks
        
    Returns:
        TaskStatus with task_id and initial status
    """
    if not request.claim or not request.claim.strip():
        raise HTTPException(status_code=400, detail="Claim cannot be empty")
    
    try:
        # 创建任务
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        # 获取深度参数（默认为2）
        max_depth = request.max_depth if request.max_depth is not None else 2
        # 限制深度范围在1-4之间
        max_depth = max(1, min(4, max_depth))
        
        logger.info(f"Creating task {task_id} with max_depth={max_depth}, claim length={len(request.claim)}")
        
        tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "message": "任务已创建，等待处理...",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "claim": request.claim,
            "max_depth": max_depth  # 保存深度信息到任务中
        }
        
        # 启动后台任务
        background_tasks.add_task(process_trace_task, task_id, request.claim, max_depth)
        
        logger.info(f"Task {task_id} created and background task started. Total tasks: {len(tasks)}")
        
        task_data = tasks[task_id].copy()
        # 确保 datetime 对象可以序列化
        if isinstance(task_data.get("created_at"), datetime):
            task_data["created_at"] = task_data["created_at"].isoformat()
        if isinstance(task_data.get("updated_at"), datetime):
            task_data["updated_at"] = task_data["updated_at"].isoformat()
        
        return TaskStatus(**task_data)
    except Exception as e:
        logger.error(f"Error creating async task: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@router.get("/trace/status/{task_id}", response_model=TaskStatus)
async def get_trace_status(task_id: str):
    """Get the status of a tracing task.
    
    Args:
        task_id: The task ID returned from /trace/async
        
    Returns:
        TaskStatus with current status and progress
    """
    if task_id not in tasks:
        logger.warning(f"Task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = tasks[task_id].copy()
    # 确保 datetime 对象可以序列化
    if isinstance(task_data.get("created_at"), datetime):
        task_data["created_at"] = task_data["created_at"].isoformat()
    if isinstance(task_data.get("updated_at"), datetime):
        task_data["updated_at"] = task_data["updated_at"].isoformat()
    
    logger.debug(f"Returning task {task_id} status: {task_data.get('status')}, progress: {task_data.get('progress')}")
    return TaskStatus(**task_data)


@router.post("/trace/cancel/{task_id}")
async def cancel_trace_task(task_id: str):
    """Cancel a tracing task.
    
    Args:
        task_id: The task ID to cancel
        
    Returns:
        TaskStatus with cancelled status
    """
    if task_id not in tasks:
        logger.warning(f"Task {task_id} not found for cancellation")
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查任务状态
    current_status = tasks[task_id]["status"]
    if current_status in ["completed", "failed", "cancelled"]:
        logger.warning(f"Task {task_id} cannot be cancelled, current status: {current_status}")
        raise HTTPException(status_code=400, detail=f"Task cannot be cancelled, current status: {current_status}")
    
    # 设置取消标志
    task_cancelled[task_id] = True
    
    # 更新任务状态
    tasks[task_id]["status"] = "cancelled"
    tasks[task_id]["message"] = "任务已取消"
    tasks[task_id]["updated_at"] = datetime.now()
    
    logger.info(f"Task {task_id} cancelled by user")
    
    task_data = tasks[task_id].copy()
    # 确保 datetime 对象可以序列化
    if isinstance(task_data.get("created_at"), datetime):
        task_data["created_at"] = task_data["created_at"].isoformat()
    if isinstance(task_data.get("updated_at"), datetime):
        task_data["updated_at"] = task_data["updated_at"].isoformat()
    
    return TaskStatus(**task_data)


@router.post("/search/google")
async def google_search(query: SearchQuery):
    """Search Google using Serper API.
    
    Args:
        query: Search query with query string and num_results
        
    Returns:
        Search results
    """
    try:
        from app.tools.google_search import GoogleSearch
        
        search_tool = GoogleSearch(
            query=query.query,
            num_results=query.num_results
        )
        result = search_tool()
        return result
        
    except Exception as e:
        logger.error(f"Error in Google search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in Google search: {str(e)}")


@router.post("/scrape")
async def scrape_web(request: WebScrapeRequest):
    """Scrape content from a web page.
    
    Args:
        request: Web scraping request with URL
        
    Returns:
        Scraped content
    """
    try:
        from app.tools.web_scraper import WebScraper
        
        scraper = WebScraper(
            url=request.url,
            extract_content=request.extract_content
        )
        result = scraper()
        return result
        
    except Exception as e:
        logger.error(f"Error scraping web page: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error scraping web page: {str(e)}")


@router.get("/sources", response_model=List[NewsSource])
async def get_sources(claim: str):
    """Get sources for a news claim (simplified endpoint).
    
    Args:
        claim: The news claim to trace
        
    Returns:
        List of news sources
    """
    try:
        result = await agent.trace_news(claim)
        return result.sources
        
    except Exception as e:
        logger.error(f"Error getting sources: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting sources: {str(e)}")


# ==================== Financial Analysis Routes ====================

# 金融分析任务存储
financial_tasks: Dict[str, Dict] = {}
financial_task_cancelled: Dict[str, bool] = {}
# 股票推荐任务存储
recommendation_tasks: Dict[str, Dict] = {}
recommendation_task_cancelled: Dict[str, bool] = {}


def update_financial_task_progress(task_id: str, progress: float, message: str):
    """更新金融分析任务进度（线程安全）"""
    if task_id in financial_tasks:
        financial_tasks[task_id]["progress"] = progress
        financial_tasks[task_id]["message"] = message
        financial_tasks[task_id]["updated_at"] = datetime.now()


async def process_financial_analysis_task(
    task_id: str, 
    stock_code: str, 
    start_date: str, 
    end_date: str
):
    """Background task to process financial analysis.
    
    Args:
        task_id: Task ID
        stock_code: Stock code (e.g., '000001')
        start_date: Start date in format 'YYYYMMDD'
        end_date: End date in format 'YYYYMMDD'
    """
    try:
        logger.info(f"Starting financial analysis task {task_id} for {stock_code} ({start_date} to {end_date})")
        
        # 初始化取消标志
        financial_task_cancelled[task_id] = False
        
        # 更新任务状态为处理中
        financial_tasks[task_id]["status"] = "processing"
        update_financial_task_progress(task_id, 0.05, "初始化任务...")
        await asyncio.sleep(0.1)
        
        # 检查是否已取消
        if financial_task_cancelled.get(task_id, False):
            financial_tasks[task_id]["status"] = "cancelled"
            financial_tasks[task_id]["message"] = "任务已取消"
            financial_tasks[task_id]["updated_at"] = datetime.now()
            logger.info(f"Financial task {task_id} cancelled before processing")
            return
        
        # 阶段1: 获取股票数据
        update_financial_task_progress(task_id, 0.15, "正在获取股票数据...")
        
        # 检查是否已取消
        if financial_task_cancelled.get(task_id, False):
            financial_tasks[task_id]["status"] = "cancelled"
            financial_tasks[task_id]["message"] = "任务已取消"
            financial_tasks[task_id]["updated_at"] = datetime.now()
            return
        
        # 阶段2: 计算技术指标
        update_financial_task_progress(task_id, 0.40, "正在计算技术指标...")
        
        # 检查是否已取消
        if financial_task_cancelled.get(task_id, False):
            financial_tasks[task_id]["status"] = "cancelled"
            financial_tasks[task_id]["message"] = "任务已取消"
            financial_tasks[task_id]["updated_at"] = datetime.now()
            return
        
        # 阶段3: 分析数据
        update_financial_task_progress(task_id, 0.60, "正在分析数据...")
        
        # 执行金融分析
        result = await financial_agent.analyze_stock(stock_code, start_date, end_date)
        
        # 检查是否已取消
        if financial_task_cancelled.get(task_id, False):
            financial_tasks[task_id]["status"] = "cancelled"
            financial_tasks[task_id]["message"] = "任务已取消"
            financial_tasks[task_id]["updated_at"] = datetime.now()
            return
        
        # 阶段4: 生成报告
        update_financial_task_progress(task_id, 0.90, "正在生成分析报告...")
        
        # 更新任务为完成
        financial_tasks[task_id]["status"] = "completed"
        financial_tasks[task_id]["progress"] = 1.0
        # 将 Pydantic 模型转换为字典
        if hasattr(result, 'model_dump'):
            financial_tasks[task_id]["result"] = result.model_dump()
        elif hasattr(result, 'dict'):
            financial_tasks[task_id]["result"] = result.dict()
        else:
            financial_tasks[task_id]["result"] = result
        financial_tasks[task_id]["message"] = "分析完成"
        financial_tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Financial task {task_id} completed successfully")
        
    except asyncio.CancelledError:
        financial_tasks[task_id]["status"] = "cancelled"
        financial_tasks[task_id]["message"] = "任务已取消"
        financial_tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Financial task {task_id} cancelled")
    except Exception as e:
        logger.error(f"Error processing financial analysis task {task_id}: {str(e)}")
        logger.exception(e)
        financial_tasks[task_id]["status"] = "failed"
        financial_tasks[task_id]["error"] = str(e)
        financial_tasks[task_id]["message"] = f"处理失败: {str(e)}"
        financial_tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Financial task {task_id} marked as failed")
    finally:
        # 清理取消标志
        financial_task_cancelled.pop(task_id, None)


@router.post("/financial/analyze", response_model=FinancialAnalysisResult)
async def analyze_stock(request: FinancialAnalysisRequest):
    """Analyze a stock (synchronous, for backward compatibility).
    
    Args:
        request: Request containing stock code and date range
        
    Returns:
        FinancialAnalysisResult with complete analysis
    """
    try:
        if not request.stock_code or not request.stock_code.strip():
            raise HTTPException(status_code=400, detail="Stock code cannot be empty")
        
        if not request.start_date or not request.end_date:
            raise HTTPException(status_code=400, detail="Start date and end date are required")
        
        # Validate date format (should be YYYYMMDD)
        if len(request.start_date) != 8 or len(request.end_date) != 8:
            raise HTTPException(status_code=400, detail="Date format should be YYYYMMDD")
        
        result = await financial_agent.analyze_stock(
            request.stock_code,
            request.start_date,
            request.end_date
        )
        return result
        
    except ValueError as e:
        logger.error(f"Value error in stock analysis: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing stock: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error analyzing stock: {str(e)}")


@router.post("/financial/analyze/async", response_model=TaskStatus)
async def analyze_stock_async(request: FinancialAnalysisRequest, background_tasks: BackgroundTasks):
    """Start an asynchronous financial analysis task.
    
    Args:
        request: Request containing stock code and date range
        background_tasks: FastAPI background tasks
        
    Returns:
        TaskStatus with task_id and initial status
    """
    if not request.stock_code or not request.stock_code.strip():
        raise HTTPException(status_code=400, detail="Stock code cannot be empty")
    
    if not request.start_date or not request.end_date:
        raise HTTPException(status_code=400, detail="Start date and end date are required")
    
    # Validate date format
    if len(request.start_date) != 8 or len(request.end_date) != 8:
        raise HTTPException(status_code=400, detail="Date format should be YYYYMMDD")
    
    try:
        # 创建任务
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        logger.info(f"Creating financial analysis task {task_id} for {request.stock_code} ({request.start_date} to {request.end_date})")
        
        financial_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "message": "任务已创建，等待处理...",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "stock_code": request.stock_code,
            "start_date": request.start_date,
            "end_date": request.end_date
        }
        
        # 启动后台任务
        background_tasks.add_task(
            process_financial_analysis_task,
            task_id,
            request.stock_code,
            request.start_date,
            request.end_date
        )
        
        logger.info(f"Financial task {task_id} created and background task started. Total tasks: {len(financial_tasks)}")
        
        task_data = financial_tasks[task_id].copy()
        # 确保 datetime 对象可以序列化
        if isinstance(task_data.get("created_at"), datetime):
            task_data["created_at"] = task_data["created_at"].isoformat()
        if isinstance(task_data.get("updated_at"), datetime):
            task_data["updated_at"] = task_data["updated_at"].isoformat()
        
        return TaskStatus(**task_data)
    except Exception as e:
        logger.error(f"Error creating async financial task: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@router.get("/financial/status/{task_id}", response_model=TaskStatus)
async def get_financial_status(task_id: str):
    """Get the status of a financial analysis task.
    
    Args:
        task_id: The task ID returned from /financial/analyze/async
        
    Returns:
        TaskStatus with current status and progress
    """
    if task_id not in financial_tasks:
        logger.warning(f"Financial task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = financial_tasks[task_id].copy()
    # 确保 datetime 对象可以序列化
    if isinstance(task_data.get("created_at"), datetime):
        task_data["created_at"] = task_data["created_at"].isoformat()
    if isinstance(task_data.get("updated_at"), datetime):
        task_data["updated_at"] = task_data["updated_at"].isoformat()
    
    logger.debug(f"Returning financial task {task_id} status: {task_data.get('status')}, progress: {task_data.get('progress')}")
    return TaskStatus(**task_data)


@router.post("/financial/cancel/{task_id}")
async def cancel_financial_task(task_id: str):
    """Cancel a financial analysis task.
    
    Args:
        task_id: The task ID to cancel
        
    Returns:
        TaskStatus with cancelled status
    """
    if task_id not in financial_tasks:
        logger.warning(f"Financial task {task_id} not found for cancellation")
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查任务状态
    current_status = financial_tasks[task_id]["status"]
    if current_status in ["completed", "failed", "cancelled"]:
        logger.warning(f"Financial task {task_id} cannot be cancelled, current status: {current_status}")
        raise HTTPException(status_code=400, detail=f"Task cannot be cancelled, current status: {current_status}")
    
    # 设置取消标志
    financial_task_cancelled[task_id] = True
    
    # 更新任务状态
    financial_tasks[task_id]["status"] = "cancelled"
    financial_tasks[task_id]["message"] = "任务已取消"
    financial_tasks[task_id]["updated_at"] = datetime.now()
    
    logger.info(f"Financial task {task_id} cancelled by user")
    
    task_data = financial_tasks[task_id].copy()
    # 确保 datetime 对象可以序列化
    if isinstance(task_data.get("created_at"), datetime):
        task_data["created_at"] = task_data["created_at"].isoformat()
    if isinstance(task_data.get("updated_at"), datetime):
        task_data["updated_at"] = task_data["updated_at"].isoformat()
    
    return TaskStatus(**task_data)


def update_recommendation_task_progress(task_id: str, progress: float, message: str):
    """更新股票推荐任务进度（线程安全）"""
    if task_id in recommendation_tasks:
        recommendation_tasks[task_id]["progress"] = progress
        recommendation_tasks[task_id]["message"] = message
        recommendation_tasks[task_id]["updated_at"] = datetime.now()


async def process_recommendation_task(
    task_id: str,
    stock_codes: Optional[List[str]],
    max_stocks: int,
    start_date: str,
    end_date: str,
    min_recommendation_score: float,
    focus_sector: Optional[str]
):
    """Background task to process stock recommendation.
    
    Args:
        task_id: Task ID
        stock_codes: Optional list of stock codes to analyze
        max_stocks: Maximum number of stocks to recommend
        start_date: Start date in format 'YYYYMMDD'
        end_date: End date in format 'YYYYMMDD'
        min_recommendation_score: Minimum recommendation score
        focus_sector: Optional sector filter
    """
    try:
        logger.info(f"Starting stock recommendation task {task_id} (max_stocks={max_stocks}, "
                   f"period={start_date} to {end_date})")
        
        # 初始化取消标志
        recommendation_task_cancelled[task_id] = False
        
        # 更新任务状态为处理中
        recommendation_tasks[task_id]["status"] = "processing"
        update_recommendation_task_progress(task_id, 0.05, "初始化任务...")
        await asyncio.sleep(0.1)
        
        # 检查是否已取消
        if recommendation_task_cancelled.get(task_id, False):
            recommendation_tasks[task_id]["status"] = "cancelled"
            recommendation_tasks[task_id]["message"] = "任务已取消"
            recommendation_tasks[task_id]["updated_at"] = datetime.now()
            logger.info(f"Recommendation task {task_id} cancelled before processing")
            return
        
        # 阶段1: 获取股票数据
        update_recommendation_task_progress(task_id, 0.15, "正在获取股票数据...")
        
        if recommendation_task_cancelled.get(task_id, False):
            recommendation_tasks[task_id]["status"] = "cancelled"
            recommendation_tasks[task_id]["message"] = "任务已取消"
            recommendation_tasks[task_id]["updated_at"] = datetime.now()
            return
        
        # 阶段2: 分析股票
        update_recommendation_task_progress(task_id, 0.40, "正在分析股票指标...")
        
        if recommendation_task_cancelled.get(task_id, False):
            recommendation_tasks[task_id]["status"] = "cancelled"
            recommendation_tasks[task_id]["message"] = "任务已取消"
            recommendation_tasks[task_id]["updated_at"] = datetime.now()
            return
        
        # 阶段3: 计算推荐分数
        update_recommendation_task_progress(task_id, 0.60, "正在计算推荐分数...")
        
        if recommendation_task_cancelled.get(task_id, False):
            recommendation_tasks[task_id]["status"] = "cancelled"
            recommendation_tasks[task_id]["message"] = "任务已取消"
            recommendation_tasks[task_id]["updated_at"] = datetime.now()
            return
        
        # 阶段4: 生成推荐理由
        update_recommendation_task_progress(task_id, 0.80, "正在生成推荐理由...")
        
        # 执行股票推荐
        result = await financial_agent.recommend_stocks(
            stock_codes=stock_codes,
            max_stocks=max_stocks,
            start_date=start_date,
            end_date=end_date,
            min_recommendation_score=min_recommendation_score,
            focus_sector=focus_sector
        )
        
        # 检查是否已取消
        if recommendation_task_cancelled.get(task_id, False):
            recommendation_tasks[task_id]["status"] = "cancelled"
            recommendation_tasks[task_id]["message"] = "任务已取消"
            recommendation_tasks[task_id]["updated_at"] = datetime.now()
            return
        
        # 阶段5: 整理结果
        update_recommendation_task_progress(task_id, 0.90, "正在整理推荐结果...")
        
        # 更新任务为完成
        recommendation_tasks[task_id]["status"] = "completed"
        recommendation_tasks[task_id]["progress"] = 1.0
        # 将 Pydantic 模型转换为字典
        if hasattr(result, 'model_dump'):
            recommendation_tasks[task_id]["result"] = result.model_dump()
        elif hasattr(result, 'dict'):
            recommendation_tasks[task_id]["result"] = result.dict()
        else:
            recommendation_tasks[task_id]["result"] = result
        recommendation_tasks[task_id]["message"] = "推荐完成"
        recommendation_tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Recommendation task {task_id} completed successfully")
        
    except asyncio.CancelledError:
        recommendation_tasks[task_id]["status"] = "cancelled"
        recommendation_tasks[task_id]["message"] = "任务已取消"
        recommendation_tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Recommendation task {task_id} cancelled")
    except Exception as e:
        logger.error(f"Error processing recommendation task {task_id}: {str(e)}")
        logger.exception(e)
        recommendation_tasks[task_id]["status"] = "failed"
        recommendation_tasks[task_id]["error"] = str(e)
        recommendation_tasks[task_id]["message"] = f"处理失败: {str(e)}"
        recommendation_tasks[task_id]["updated_at"] = datetime.now()
        logger.info(f"Recommendation task {task_id} marked as failed")
    finally:
        # 清理取消标志
        recommendation_task_cancelled.pop(task_id, None)


@router.post("/financial/recommend", response_model=StockRecommendationResult)
async def recommend_stocks(request: StockRecommendationRequest):
    """Get stock recommendations with ranking and analysis (synchronous, for backward compatibility).
    
    Args:
        request: Stock recommendation request
        
    Returns:
        StockRecommendationResult with ranked recommendations
    """
    try:
        logger.info(f"Starting stock recommendation: max_stocks={request.max_stocks}, "
                   f"period={request.start_date} to {request.end_date}")
        
        result = await financial_agent.recommend_stocks(
            stock_codes=request.stock_codes,
            max_stocks=request.max_stocks,
            start_date=request.start_date,
            end_date=request.end_date,
            min_recommendation_score=request.min_recommendation_score,
            focus_sector=request.focus_sector
        )
        
        logger.info(f"Stock recommendation completed: {len(result.recommendations)} recommendations")
        return result
        
    except Exception as e:
        logger.error(f"Error in stock recommendation: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error in stock recommendation: {str(e)}")


@router.post("/financial/recommend/async", response_model=TaskStatus)
async def recommend_stocks_async(request: StockRecommendationRequest, background_tasks: BackgroundTasks):
    """Start an asynchronous stock recommendation task.
    
    Args:
        request: Stock recommendation request
        background_tasks: FastAPI background tasks
        
    Returns:
        TaskStatus with task_id and initial status
    """
    if not request.start_date or not request.end_date:
        raise HTTPException(status_code=400, detail="Start date and end date are required")
    
    # Validate date format
    if len(request.start_date) != 8 or len(request.end_date) != 8:
        raise HTTPException(status_code=400, detail="Date format should be YYYYMMDD")
    
    try:
        # 创建任务
        task_id = str(uuid.uuid4())
        now = datetime.now()
        
        logger.info(f"Creating recommendation task {task_id} (max_stocks={request.max_stocks}, "
                   f"period={request.start_date} to {request.end_date})")
        
        recommendation_tasks[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0.0,
            "message": "任务已创建，等待处理...",
            "result": None,
            "error": None,
            "created_at": now,
            "updated_at": now,
            "stock_codes": request.stock_codes,
            "max_stocks": request.max_stocks,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "min_recommendation_score": request.min_recommendation_score,
            "focus_sector": request.focus_sector
        }
        
        # 启动后台任务
        background_tasks.add_task(
            process_recommendation_task,
            task_id,
            request.stock_codes,
            request.max_stocks,
            request.start_date,
            request.end_date,
            request.min_recommendation_score,
            request.focus_sector
        )
        
        logger.info(f"Recommendation task {task_id} created and background task started. Total tasks: {len(recommendation_tasks)}")
        
        task_data = recommendation_tasks[task_id].copy()
        # 确保 datetime 对象可以序列化
        if isinstance(task_data.get("created_at"), datetime):
            task_data["created_at"] = task_data["created_at"].isoformat()
        if isinstance(task_data.get("updated_at"), datetime):
            task_data["updated_at"] = task_data["updated_at"].isoformat()
        
        return TaskStatus(**task_data)
    except Exception as e:
        logger.error(f"Error creating async recommendation task: {str(e)}")
        logger.exception(e)
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")


@router.get("/financial/recommend/status/{task_id}", response_model=TaskStatus)
async def get_recommendation_status(task_id: str):
    """Get the status of a stock recommendation task.
    
    Args:
        task_id: The task ID returned from /financial/recommend/async
        
    Returns:
        TaskStatus with current status and progress
    """
    if task_id not in recommendation_tasks:
        logger.warning(f"Recommendation task {task_id} not found")
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = recommendation_tasks[task_id].copy()
    # 确保 datetime 对象可以序列化
    if isinstance(task_data.get("created_at"), datetime):
        task_data["created_at"] = task_data["created_at"].isoformat()
    if isinstance(task_data.get("updated_at"), datetime):
        task_data["updated_at"] = task_data["updated_at"].isoformat()
    
    logger.debug(f"Returning recommendation task {task_id} status: {task_data.get('status')}, progress: {task_data.get('progress')}")
    return TaskStatus(**task_data)


@router.post("/financial/recommend/cancel/{task_id}")
async def cancel_recommendation_task(task_id: str):
    """Cancel a stock recommendation task.
    
    Args:
        task_id: The task ID to cancel
        
    Returns:
        TaskStatus with cancelled status
    """
    if task_id not in recommendation_tasks:
        logger.warning(f"Recommendation task {task_id} not found for cancellation")
        raise HTTPException(status_code=404, detail="Task not found")
    
    # 检查任务状态
    current_status = recommendation_tasks[task_id]["status"]
    if current_status in ["completed", "failed", "cancelled"]:
        logger.warning(f"Recommendation task {task_id} cannot be cancelled, current status: {current_status}")
        raise HTTPException(status_code=400, detail=f"Task cannot be cancelled, current status: {current_status}")
    
    # 设置取消标志
    recommendation_task_cancelled[task_id] = True
    
    # 更新任务状态
    recommendation_tasks[task_id]["status"] = "cancelled"
    recommendation_tasks[task_id]["message"] = "任务已取消"
    recommendation_tasks[task_id]["updated_at"] = datetime.now()
    
    logger.info(f"Recommendation task {task_id} cancelled by user")
    
    task_data = recommendation_tasks[task_id].copy()
    # 确保 datetime 对象可以序列化
    if isinstance(task_data.get("created_at"), datetime):
        task_data["created_at"] = task_data["created_at"].isoformat()
    if isinstance(task_data.get("updated_at"), datetime):
        task_data["updated_at"] = task_data["updated_at"].isoformat()
    
    return TaskStatus(**task_data)


# ==================== Strategy Backtest Routes ====================

@router.post("/financial/backtest", response_model=BacktestResult)
async def backtest_strategy(request: BacktestRequest):
    """Backtest a trading strategy.
    
    Args:
        request: Backtest request parameters
        
    Returns:
        BacktestResult with performance metrics and trade history
    """
    try:
        logger.info(f"Starting strategy backtest: stock={request.stock_code}, "
                   f"strategy={request.strategy_type}, period={request.start_date} to {request.end_date}")
        
        if request.strategy_type == "signal_based":
            result = await backtest_engine.backtest_signal_based_strategy(request)
        elif request.strategy_type == "ma_cross":
            result = await backtest_engine.backtest_ma_cross_strategy(request)
        elif request.strategy_type == "rsi":
            result = await backtest_engine.backtest_rsi_strategy(request)
        elif request.strategy_type == "macd":
            result = await backtest_engine.backtest_macd_strategy(request)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported strategy type: {request.strategy_type}. Supported types: 'signal_based', 'ma_cross', 'rsi', 'macd'."
            )
        
        logger.info(f"Backtest completed: {result.metrics.total_trades} trades, "
                   f"return: {result.metrics.total_return_rate:.2f}%")
        return result
        
    except ValueError as e:
        logger.error(f"Value error in backtest: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error in strategy backtest: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error in strategy backtest: {str(e)}")


# ==================== Stock Prediction Routes ====================

@router.post("/financial/predict", response_model=PredictionResult)
async def predict_stock_price(request: PredictionRequest):
    """
    Predict future stock prices using machine learning.
    
    Args:
        request: Prediction request with stock code, dates, and model parameters
        
    Returns:
        PredictionResult with predictions for future dates
    """
    try:
        logger.info(f"Starting stock price prediction: stock={request.stock_code}, "
                   f"model={request.model_type}, days={request.prediction_days}")
        
        result = await prediction_engine.predict_stock_price(request)
        
        logger.info(f"Prediction completed: {len(result.predictions)} predictions, "
                   f"accuracy: {result.model_accuracy:.4f if result.model_accuracy else 'N/A'}")
        return result
        
    except ValueError as e:
        logger.error(f"Value error in prediction: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except ImportError as e:
        logger.error(f"Import error in prediction: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Machine learning library not available: {str(e)}. Please install scikit-learn: pip install scikit-learn"
        )
    except Exception as e:
        logger.error(f"Error in stock prediction: {str(e)}")
        import traceback
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error in stock prediction: {str(e)}")


@router.post("/financial/predict/async", response_model=TaskStatus)
async def predict_stock_price_async(
    request: PredictionRequest,
    background_tasks: BackgroundTasks
):
    """
    Asynchronously predict future stock prices.
    
    Returns immediately with a task_id for status checking.
    """
    task_id = str(uuid.uuid4())
    tasks[task_id] = {
        "status": "pending",
        "progress": 0.0,
        "message": "Prediction task created",
        "result": None,
        "error": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }
    task_cancelled[task_id] = False
    
    background_tasks.add_task(process_prediction_task, task_id, request)
    
    return TaskStatus(**tasks[task_id])


async def process_prediction_task(task_id: str, request: PredictionRequest):
    """Background task for stock price prediction."""
    try:
        update_task_progress(task_id, 0.1, "Starting prediction...")
        
        result = await prediction_engine.predict_stock_price(request)
        
        update_task_progress(task_id, 1.0, "Prediction completed")
        tasks[task_id]["result"] = result.dict()
        tasks[task_id]["status"] = "completed"
        
    except Exception as e:
        logger.error(f"Error in prediction task {task_id}: {str(e)}")
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
    finally:
        tasks[task_id]["updated_at"] = datetime.now()


@router.get("/financial/predict/status/{task_id}", response_model=TaskStatus)
async def get_prediction_status(task_id: str):
    """Get the status of an async prediction task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatus(**tasks[task_id])


@router.post("/financial/predict/cancel/{task_id}")
async def cancel_prediction_task(task_id: str):
    """Cancel an async prediction task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_cancelled[task_id] = True
    tasks[task_id]["status"] = "cancelled"
    tasks[task_id]["updated_at"] = datetime.now()
    
    return {"message": "Task cancelled", "task_id": task_id}
