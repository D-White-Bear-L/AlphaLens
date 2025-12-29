"""Data models for structured output."""
from datetime import datetime
from typing import List, Optional, Dict, Any, Union

from pydantic import BaseModel, Field

# Try to import LLMJson for structured output
try:
    from mira import LLMJson
    LLM_JSON_AVAILABLE = True
except ImportError:
    LLM_JSON_AVAILABLE = False
    # Fallback: create a dummy LLMJson class
    class LLMJson(BaseModel):
        @classmethod
        def schema(cls):
            return {"type": "json_schema", "json_schema": {"schema": cls.model_json_schema()}}


class NewsSource(BaseModel):
    """News source information."""
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Article title")
    snippet: Optional[str] = Field(None, description="Article snippet or summary")
    published_date: Optional[str] = Field(None, description="Publication date")
    author: Optional[str] = Field(None, description="Article author")
    relevance_score: Optional[float] = Field(None, description="Relevance score (0-1)")


class TimelineEvent(BaseModel):
    """Timeline event in the news trace."""
    date: Optional[str] = Field(None, description="Event date")
    event: str = Field(..., description="Event description")
    source_url: Optional[str] = Field(None, description="Source URL for this event")
    importance: Optional[str] = Field(None, description="Event importance: high, medium, low")


class CausalRelation(BaseModel):
    """Causal relationship between events."""
    cause: str = Field(..., description="Cause event")
    effect: str = Field(..., description="Effect event")
    relationship_type: str = Field(..., description="Type: direct, indirect, correlation")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this relationship")
    evidence: Optional[str] = Field(None, description="Evidence supporting this relationship")


class KnowledgeGraphNode(BaseModel):
    """Node in the knowledge graph."""
    id: str = Field(..., description="Node ID")
    label: str = Field(..., description="Node label")
    type: str = Field(..., description="Node type: person, organization, event, concept, location")
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional properties")


class KnowledgeGraphEdge(BaseModel):
    """Edge in the knowledge graph."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship: str = Field(..., description="Relationship type")
    weight: Optional[float] = Field(None, description="Edge weight/strength")


class KnowledgeGraph(BaseModel):
    """Knowledge graph structure."""
    nodes: List[KnowledgeGraphNode] = Field(default_factory=list, description="Graph nodes")
    edges: List[KnowledgeGraphEdge] = Field(default_factory=list, description="Graph edges")


class HierarchyNode(BaseModel):
    """Node in the hierarchy graph representing trace depth."""
    id: str = Field(..., description="Node ID")
    label: str = Field(..., description="Node label/name")
    level: int = Field(..., ge=0, description="Hierarchy level (0 = root, higher = deeper)")
    parent_id: Optional[str] = Field(None, description="Parent node ID (None for root)")
    source_urls: List[str] = Field(default_factory=list, description="Source URLs supporting this node")
    description: Optional[str] = Field(None, description="Node description or summary")
    source_count: int = Field(default=0, description="Number of sources at this level")
    children_count: int = Field(default=0, description="Number of child nodes")


class HierarchyGraph(BaseModel):
    """Hierarchical graph structure showing trace depth."""
    root_id: str = Field(..., description="Root node ID")
    nodes: List[HierarchyNode] = Field(default_factory=list, description="All nodes in the hierarchy")
    max_depth: int = Field(default=0, description="Maximum depth of the hierarchy")


class TraceResult(BaseModel):
    """Trace result for a news item."""
    original_claim: str = Field(..., description="Original news claim to trace")
    sources: List[NewsSource] = Field(default_factory=list, description="List of traced sources")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the trace")
    summary: str = Field(..., description="Summary of the trace findings")
    trace_timestamp: datetime = Field(default_factory=datetime.now, description="When the trace was performed")
    
    # Enhanced trace information
    timeline: List[TimelineEvent] = Field(default_factory=list, description="Chronological timeline of events")
    causal_relations: List[CausalRelation] = Field(default_factory=list, description="Causal relationships between events")
    knowledge_graph: Optional[KnowledgeGraph] = Field(None, description="Knowledge graph of entities and relationships")
    hierarchy_graph: Optional[HierarchyGraph] = Field(None, description="Hierarchical graph showing trace depth and structure")
    analysis: Optional[str] = Field(None, description="Deep analysis of the trace findings")


class SearchQuery(BaseModel):
    """Search query request."""
    query: str = Field(..., description="Search query")
    num_results: int = Field(default=10, ge=1, le=50, description="Number of results to return")


class WebScrapeRequest(BaseModel):
    """Web scraping request."""
    url: str = Field(..., description="URL to scrape")
    extract_content: bool = Field(default=True, description="Whether to extract main content")


class DatabaseQuery(BaseModel):
    """Database query request."""
    query: str = Field(..., description="SQL-like query or natural language query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")


# Structured output models for LLM (inherit from LLMJson)
if LLM_JSON_AVAILABLE:
    class TimelineOutput(LLMJson):
        """Structured output for timeline extraction."""
        events: List[TimelineEvent] = Field(..., description="Chronological timeline of events")
    
    class CausalRelationsOutput(LLMJson):
        """Structured output for causal relations extraction."""
        relations: List[CausalRelation] = Field(..., description="Causal relationships between events")
    
    class KnowledgeGraphOutput(LLMJson):
        """Structured output for knowledge graph building."""
        nodes: List[KnowledgeGraphNode] = Field(..., description="Graph nodes")
        edges: List[KnowledgeGraphEdge] = Field(..., description="Graph edges")
    
    class HierarchyGraphOutput(LLMJson):
        """Structured output for hierarchy graph building."""
        root_id: str = Field(..., description="Root node ID")
        nodes: List[HierarchyNode] = Field(..., description="All nodes in the hierarchy")
        max_depth: int = Field(..., ge=0, description="Maximum depth of the hierarchy")
else:
    # Fallback models if LLMJson is not available
    class TimelineOutput(BaseModel):
        events: List[TimelineEvent] = Field(..., description="Chronological timeline of events")
    
    class CausalRelationsOutput(BaseModel):
        relations: List[CausalRelation] = Field(..., description="Causal relationships between events")
    
    class KnowledgeGraphOutput(BaseModel):
        nodes: List[KnowledgeGraphNode] = Field(..., description="Graph nodes")
        edges: List[KnowledgeGraphEdge] = Field(..., description="Graph edges")
    
    class HierarchyGraphOutput(BaseModel):
        root_id: str = Field(..., description="Root node ID")
        nodes: List[HierarchyNode] = Field(..., description="All nodes in the hierarchy")
        max_depth: int = Field(..., ge=0, description="Maximum depth of the hierarchy")


# ==================== Financial Analysis Models ====================

class PriceStatistics(BaseModel):
    """Price statistics for a stock."""
    current_price: float = Field(..., description="Current/latest closing price")
    highest_price: float = Field(..., description="Highest price in the period")
    lowest_price: float = Field(..., description="Lowest price in the period")
    average_price: float = Field(..., description="Average closing price")
    price_change: float = Field(..., description="Price change from start to end")
    price_change_pct: float = Field(..., description="Price change percentage")
    volatility: float = Field(..., description="Price volatility (standard deviation)")


class VolumeStatistics(BaseModel):
    """Volume statistics for a stock."""
    total_volume: float = Field(..., description="Total trading volume")
    average_volume: float = Field(..., description="Average daily trading volume")
    max_volume: float = Field(..., description="Maximum single-day volume")
    min_volume: float = Field(..., description="Minimum single-day volume")
    volume_trend: str = Field(..., description="Volume trend: increasing, decreasing, stable")


class TechnicalIndicators(BaseModel):
    """Technical indicators for stock analysis."""
    ma5: Optional[float] = Field(None, description="5-day moving average")
    ma10: Optional[float] = Field(None, description="10-day moving average")
    ma20: Optional[float] = Field(None, description="20-day moving average")
    ma30: Optional[float] = Field(None, description="30-day moving average")
    ma60: Optional[float] = Field(None, description="60-day moving average")
    rsi: Optional[float] = Field(None, description="Relative Strength Index (0-100)")
    macd: Optional[float] = Field(None, description="MACD value")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    bollinger_upper: Optional[float] = Field(None, description="Bollinger Bands upper")
    bollinger_middle: Optional[float] = Field(None, description="Bollinger Bands middle")
    bollinger_lower: Optional[float] = Field(None, description="Bollinger Bands lower")


class TradingSignal(BaseModel):
    """Trading signal for a stock."""
    signal_type: str = Field(..., description="Signal type: buy, sell, hold")
    signal_strength: float = Field(..., ge=0.0, le=1.0, description="Signal strength (0-1)")
    signal_reason: str = Field(..., description="Reason for the signal")
    signal_date: Optional[str] = Field(None, description="Date when signal occurred")
    indicators_used: List[str] = Field(default_factory=list, description="Technical indicators used")


class RiskMetrics(BaseModel):
    """Risk metrics for a stock."""
    volatility: float = Field(..., description="Price volatility")
    max_drawdown: float = Field(..., description="Maximum drawdown percentage")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio (risk-adjusted return)")
    beta: Optional[float] = Field(None, description="Beta coefficient (market correlation)")
    risk_level: str = Field(..., description="Risk level: low, medium, high")


class TrendAnalysis(BaseModel):
    """Trend analysis for a stock."""
    short_term_trend: str = Field(..., description="Short-term trend: up, down, sideways")
    medium_term_trend: str = Field(..., description="Medium-term trend: up, down, sideways")
    long_term_trend: str = Field(..., description="Long-term trend: up, down, sideways")
    trend_strength: float = Field(..., ge=0.0, le=1.0, description="Trend strength (0-1)")
    support_level: Optional[float] = Field(None, description="Support price level")
    resistance_level: Optional[float] = Field(None, description="Resistance price level")


class HistoricalDataPoint(BaseModel):
    """Single historical data point for a stock."""
    date: str = Field(..., description="Trading date in format 'YYYY-MM-DD'")
    open: float = Field(..., description="Opening price")
    close: float = Field(..., description="Closing price")
    high: float = Field(..., description="Highest price")
    low: float = Field(..., description="Lowest price")
    volume: float = Field(..., description="Trading volume")
    ma5: Optional[float] = Field(None, description="5-day moving average")
    ma10: Optional[float] = Field(None, description="10-day moving average")
    ma20: Optional[float] = Field(None, description="20-day moving average")
    ma30: Optional[float] = Field(None, description="30-day moving average")
    ma60: Optional[float] = Field(None, description="60-day moving average")
    rsi: Optional[float] = Field(None, description="RSI indicator")
    macd: Optional[float] = Field(None, description="MACD value")
    macd_signal: Optional[float] = Field(None, description="MACD signal line")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    bollinger_upper: Optional[float] = Field(None, description="Bollinger upper band")
    bollinger_middle: Optional[float] = Field(None, description="Bollinger middle band")
    bollinger_lower: Optional[float] = Field(None, description="Bollinger lower band")


class FinancialAnalysisResult(BaseModel):
    """Complete financial analysis result for a stock."""
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    analysis_period: str = Field(..., description="Analysis period (start_date to end_date)")
    start_date: str = Field(..., description="Start date of analysis")
    end_date: str = Field(..., description="End date of analysis")
    data_points: int = Field(..., description="Number of data points analyzed")
    
    # Historical data
    historical_data: List[HistoricalDataPoint] = Field(default_factory=list, description="Historical price and volume data with technical indicators")
    
    # Price and volume statistics
    price_stats: PriceStatistics = Field(..., description="Price statistics")
    volume_stats: VolumeStatistics = Field(..., description="Volume statistics")
    
    # Technical indicators
    technical_indicators: TechnicalIndicators = Field(..., description="Technical indicators")
    
    # Trading signals
    trading_signals: List[TradingSignal] = Field(default_factory=list, description="Trading signals")
    
    # Risk metrics
    risk_metrics: RiskMetrics = Field(..., description="Risk metrics")
    
    # Trend analysis
    trend_analysis: TrendAnalysis = Field(..., description="Trend analysis")
    
    # Overall assessment
    overall_assessment: str = Field(..., description="Overall assessment and recommendation")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score of the analysis")
    
    # Timestamp
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When the analysis was performed")


class FinancialAnalysisRequest(BaseModel):
    """Request model for financial analysis."""
    stock_code: str = Field(..., description="Stock code (e.g., '000001')")
    start_date: str = Field(..., description="Start date in format 'YYYYMMDD'")
    end_date: str = Field(..., description="End date in format 'YYYYMMDD'")


class StockRecommendation(BaseModel):
    """Stock recommendation with ranking and analysis."""
    rank: int = Field(..., ge=1, description="Recommendation rank (1 = best)")
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    recommendation_score: float = Field(..., ge=0.0, le=1.0, description="Overall recommendation score (0-1)")
    recommendation_reason: str = Field(..., description="Detailed reason for recommendation (in Chinese)")
    current_price: float = Field(..., description="Current stock price")
    price_change_pct: float = Field(..., description="Price change percentage in analysis period")
    risk_level: str = Field(..., description="Risk level: low, medium, high")
    trend_direction: str = Field(..., description="Trend direction: up, down, sideways")
    key_highlights: List[str] = Field(default_factory=list, description="Key highlights (in Chinese)")
    analysis_summary: Optional[FinancialAnalysisResult] = Field(None, description="Full analysis result for this stock")


class StockRecommendationRequest(BaseModel):
    """Request model for stock recommendations."""
    stock_codes: Optional[List[str]] = Field(None, description="Specific stock codes to analyze (if None, will fetch popular stocks)")
    max_stocks: int = Field(default=10, ge=1, le=50, description="Maximum number of stocks to analyze and recommend")
    start_date: str = Field(..., description="Start date in format 'YYYYMMDD'")
    end_date: str = Field(..., description="End date in format 'YYYYMMDD'")
    min_recommendation_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum recommendation score to include")
    focus_sector: Optional[str] = Field(None, description="Focus on specific sector (e.g., '科技', '金融', '消费')")


class StockRecommendationResult(BaseModel):
    """Result of stock recommendation analysis."""
    recommendations: List[StockRecommendation] = Field(..., description="Ranked list of stock recommendations")
    total_analyzed: int = Field(..., description="Total number of stocks analyzed")
    analysis_period: str = Field(..., description="Analysis period (start_date to end_date)")
    recommendation_timestamp: datetime = Field(default_factory=datetime.now, description="When the recommendation was generated")
    comparison_summary: str = Field(..., description="Summary comparison of recommended stocks (in Chinese)")


# ==================== Strategy Backtest Models ====================

class BacktestTrade(BaseModel):
    """Single trade record in backtest."""
    trade_id: int = Field(..., description="Trade ID")
    buy_date: str = Field(..., description="Buy date (YYYY-MM-DD)")
    buy_price: float = Field(..., description="Buy price")
    sell_date: str = Field(..., description="Sell date (YYYY-MM-DD)")
    sell_price: float = Field(..., description="Sell price")
    shares: int = Field(..., description="Number of shares traded")
    profit: float = Field(..., description="Profit/loss from this trade")
    return_rate: float = Field(..., description="Return rate of this trade")
    signal_type: str = Field(..., description="Signal type that triggered this trade")
    hold_days: int = Field(..., description="Number of days held")


class BacktestMetrics(BaseModel):
    """Backtest performance metrics."""
    initial_capital: float = Field(..., description="Initial capital")
    final_capital: float = Field(..., description="Final capital")
    total_return: float = Field(..., description="Total return")
    total_return_rate: float = Field(..., description="Total return rate (percentage)")
    annualized_return_rate: Optional[float] = Field(None, description="Annualized return rate")
    total_trades: int = Field(..., description="Total number of trades")
    successful_trades: int = Field(..., description="Number of profitable trades")
    failed_trades: int = Field(..., description="Number of losing trades")
    win_rate: float = Field(..., ge=0.0, le=1.0, description="Win rate (0-1)")
    average_profit: float = Field(..., description="Average profit per trade")
    max_profit: float = Field(..., description="Maximum profit in a single trade")
    max_loss: float = Field(..., description="Maximum loss in a single trade")
    max_drawdown: float = Field(..., description="Maximum drawdown (percentage)")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio")
    profit_factor: Optional[float] = Field(None, description="Profit factor (total profit / total loss)")


class BacktestRequest(BaseModel):
    """Request model for strategy backtest."""
    stock_code: str = Field(..., description="Stock code (e.g., '000001')")
    start_date: str = Field(..., description="Backtest start date in format 'YYYYMMDD'")
    end_date: str = Field(..., description="Backtest end date in format 'YYYYMMDD'")
    initial_capital: float = Field(default=100000.0, ge=1000.0, description="Initial capital (default: 100,000)")
    strategy_type: str = Field(default="signal_based", description="Strategy type: signal_based, ma_cross, rsi, macd")
    # Strategy parameters
    shares_per_trade: int = Field(default=100, ge=100, description="Shares per trade (must be multiple of 100)")
    hold_days: Optional[int] = Field(None, description="Hold days (if None, use signal-based exit)")
    # Signal filters
    min_signal_strength: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum signal strength to trigger trade")
    signal_types: Optional[List[str]] = Field(None, description="Signal types to use (buy, sell, hold)")


class BacktestResult(BaseModel):
    """Result of strategy backtest."""
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    backtest_period: str = Field(..., description="Backtest period (start_date to end_date)")
    strategy_type: str = Field(..., description="Strategy type used")
    metrics: BacktestMetrics = Field(..., description="Backtest performance metrics")
    trades: List[BacktestTrade] = Field(default_factory=list, description="List of all trades")
    equity_curve: Optional[List[Dict[str, Union[str, float]]]] = Field(None, description="Equity curve data (date: str, capital: float)")
    backtest_timestamp: datetime = Field(default_factory=datetime.now, description="When the backtest was performed")


# ==================== Stock Prediction Models ====================

class PredictionPoint(BaseModel):
    """Single prediction point for future date."""
    date: str = Field(..., description="Predicted date in format 'YYYY-MM-DD'")
    predicted_price: float = Field(..., description="Predicted closing price")
    confidence_interval_lower: Optional[float] = Field(None, description="Lower bound of confidence interval")
    confidence_interval_upper: Optional[float] = Field(None, description="Upper bound of confidence interval")
    prediction_confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence (0-1)")


class PredictionRequest(BaseModel):
    """Request model for stock price prediction."""
    stock_code: str = Field(..., description="Stock code (e.g., '000001')")
    start_date: str = Field(..., description="Training data start date in format 'YYYYMMDD'")
    end_date: str = Field(..., description="Training data end date in format 'YYYYMMDD'")
    prediction_days: int = Field(default=5, ge=1, le=30, description="Number of days to predict (default: 5, max: 30)")
    model_type: str = Field(default="linear", description="Model type: linear, ridge, lasso, ensemble")
    use_technical_indicators: bool = Field(default=True, description="Whether to use technical indicators as features")


class PredictionResult(BaseModel):
    """Result of stock price prediction."""
    stock_code: str = Field(..., description="Stock code")
    stock_name: Optional[str] = Field(None, description="Stock name")
    training_period: str = Field(..., description="Training period (start_date to end_date)")
    prediction_days: int = Field(..., description="Number of days predicted")
    model_type: str = Field(..., description="Model type used")
    model_accuracy: Optional[float] = Field(None, ge=0.0, le=1.0, description="Model accuracy on validation set")
    predictions: List[PredictionPoint] = Field(..., description="List of predictions for future dates")
    feature_importance: Optional[Dict[str, float]] = Field(None, description="Feature importance scores")
    prediction_timestamp: datetime = Field(default_factory=datetime.now, description="When the prediction was made")

