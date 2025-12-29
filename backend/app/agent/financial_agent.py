"""Financial analysis agent using mira library."""
import asyncio
import time
from typing import Optional, Tuple, List
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from loguru import logger
from mira import HumanMessage, OpenAIArgs, OpenRouterLLM, SystemMessage

from app.config import settings
from app.models import (
    FinancialAnalysisResult, PriceStatistics, VolumeStatistics, TechnicalIndicators,
    TradingSignal, RiskMetrics, TrendAnalysis, StockRecommendation, StockRecommendationResult
)

# Try to import akshare, but make it optional
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    ak = None
    logger.warning("akshare not installed, FinancialAgent will not be able to fetch stock data")


class FinancialAgent:
    """Agent for financial stock analysis."""
    
    def __init__(self):
        """Initialize the agent with LLM."""
        # Initialize LLM with mira - use settings from .env file
        llm_args = OpenAIArgs(
            api_key=settings.get_api_key(),
            base_url=settings.get_base_url(),
            model=settings.model,
            temperature=0.7,
            max_completion_tokens=4000,
            verbose=True
        )
        self.llm = OpenRouterLLM(args=llm_args)
        logger.info(f"FinancialAgent LLM initialized with model: {settings.model}")
        
        # Request delay to avoid rate limiting
        self.request_delay = 1.5
    
    def get_stock_data(self, stock_code: str, start_date: str, end_date: str, max_retries: int = 3) -> pd.DataFrame:
        """
        Get stock data using akshare.
        
        Args:
            stock_code: Stock code (e.g., '000001')
            start_date: Start date in format 'YYYYMMDD'
            end_date: End date in format 'YYYYMMDD'
            max_retries: Maximum retry attempts
            
        Returns:
            DataFrame with stock data
        """
        if not AKSHARE_AVAILABLE:
            logger.error("akshare not available, cannot fetch stock data")
            return pd.DataFrame()
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = self.request_delay * (2 ** attempt)
                    logger.info(f"Retrying after {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                
                logger.info(f"Fetching stock data for {stock_code} (attempt {attempt + 1}/{max_retries})")
                
                # Get stock data
                df = ak.stock_zh_a_hist(
                    symbol=stock_code,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="qfq"  # 前复权
                )
                
                if df.empty:
                    logger.warning(f"Empty data returned for stock {stock_code}")
                    continue
                
                # Check required columns
                required_cols = ['日期', '开盘', '收盘', '最高', '最低', '成交量']
                missing_cols = [col for col in required_cols if col not in df.columns]
                if missing_cols:
                    logger.warning(f"Missing columns for {stock_code}: {missing_cols}")
                    continue
                
                # Process data
                df = df[required_cols].copy()
                df.columns = ['date', 'open', 'close', 'high', 'low', 'volume']
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                
                logger.info(f"Successfully fetched {len(df)} data points for {stock_code}")
                time.sleep(self.request_delay)
                
                return df
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Failed to fetch stock {stock_code} (attempt {attempt + 1}): {error_msg[:100]}")
                
                if "Connection" in error_msg or "timeout" in error_msg.lower():
                    time.sleep(5)
        
        logger.error(f"Failed to fetch stock {stock_code} after {max_retries} attempts")
        return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators."""
        df = df.copy()
        
        # Moving averages
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma30'] = df['close'].rolling(window=30).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # RSI calculation
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD calculation
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bollinger_middle'] = df['close'].rolling(window=20).mean()
        std = df['close'].rolling(window=20).std()
        df['bollinger_upper'] = df['bollinger_middle'] + (std * 2)
        df['bollinger_lower'] = df['bollinger_middle'] - (std * 2)
        
        return df
    
    def _calculate_rsi_signal_strength(self, rsi_value: float, signal_type: str) -> float:
        """
        Calculate RSI signal strength based on deviation from thresholds.
        
        Args:
            rsi_value: Current RSI value
            signal_type: 'buy' (oversold) or 'sell' (overbought)
            
        Returns:
            Signal strength (0.0-1.0)
        """
        if signal_type == 'buy':
            # RSI < 30: stronger signal the lower it is
            if rsi_value < 20:
                return 0.9  # Very oversold
            elif rsi_value < 25:
                return 0.8
            elif rsi_value < 30:
                return 0.6 + (30 - rsi_value) / 10 * 0.2  # 0.6-0.8
        elif signal_type == 'sell':
            # RSI > 70: stronger signal the higher it is
            if rsi_value > 80:
                return 0.9  # Very overbought
            elif rsi_value > 75:
                return 0.8
            elif rsi_value > 70:
                return 0.6 + (rsi_value - 70) / 10 * 0.2  # 0.6-0.8
        return 0.5
    
    def _calculate_ma_cross_strength(self, df: pd.DataFrame, window: int = 5) -> float:
        """
        Calculate MA cross signal strength based on:
        - Volume confirmation (volume increase)
        - Trend consistency in recent window
        - Price momentum
        
        Args:
            df: DataFrame with technical indicators
            window: Number of days to look back
            
        Returns:
            Signal strength (0.0-1.0)
        """
        if len(df) < window + 1:
            return 0.5
        
        latest = df.iloc[-1]
        recent = df.iloc[-window-1:-1]  # Last N days (excluding today)
        
        strength = 0.5  # Base strength
        
        # Volume confirmation: check if volume increased during cross
        if pd.notna(latest['volume']) and len(recent) > 0:
            avg_volume = recent['volume'].mean()
            if latest['volume'] > avg_volume * 1.2:  # 20% volume increase
                strength += 0.15
            elif latest['volume'] > avg_volume * 1.1:  # 10% volume increase
                strength += 0.1
        
        # Trend consistency: check if price trend aligns with cross direction
        if len(recent) >= 3:
            price_trend = (latest['close'] - recent['close'].iloc[0]) / recent['close'].iloc[0]
            if abs(price_trend) > 0.02:  # At least 2% move
                strength += 0.1
        
        # MA separation: larger separation = stronger signal
        if pd.notna(latest['ma5']) and pd.notna(latest['ma30']):
            separation = abs(latest['ma5'] - latest['ma30']) / latest['ma30']
            if separation > 0.05:  # 5% separation
                strength += 0.1
            elif separation > 0.03:  # 3% separation
                strength += 0.05
        
        return min(strength, 1.0)
    
    def _check_rsi_divergence(self, df: pd.DataFrame, window: int = 5) -> Tuple[bool, str]:
        """
        Check for RSI divergence (price vs RSI moving in opposite directions).
        
        Args:
            df: DataFrame with price and RSI
            window: Number of days to check
            
        Returns:
            (has_divergence, divergence_type)
        """
        if len(df) < window + 1:
            return False, ""
        
        recent = df.iloc[-window-1:]
        
        # Check if price and RSI are moving in opposite directions
        price_change = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0]
        rsi_change = recent['rsi'].iloc[-1] - recent['rsi'].iloc[0]
        
        # Bullish divergence: price down but RSI up
        if price_change < -0.02 and rsi_change > 5:
            return True, "bullish"
        # Bearish divergence: price up but RSI down
        elif price_change > 0.02 and rsi_change < -5:
            return True, "bearish"
        
        return False, ""
    
    def detect_trading_signals(self, df: pd.DataFrame, window: int = 5) -> list:
        """
        Detect trading signals from technical indicators with dynamic strength calculation.
        
        Signal Layer职责：
        - 发现结构化市场信号
        - 计算信号强度（基于指标偏离度、趋势一致性等）
        - 不负责最终决策（买多少/是否买/组合决策）
        
        Args:
            df: DataFrame with technical indicators
            window: Window size for trend consistency check
            
        Returns:
            List of signal dictionaries
        """
        signals = []
        
        if len(df) < 30:
            return signals
        
        # Get latest values and recent window
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        recent_window = df.iloc[-window-1:] if len(df) >= window + 1 else df
        
        # 1. Golden cross (5-day MA crosses above 30-day MA)
        if pd.notna(latest['ma5']) and pd.notna(latest['ma30']):
            if latest['ma5'] > latest['ma30'] and prev['ma5'] <= prev['ma30']:
                # Calculate dynamic strength
                base_strength = 0.6
                cross_strength = self._calculate_ma_cross_strength(df, window)
                final_strength = (base_strength + cross_strength) / 2
                
                # Build reason with context
                reason_parts = ['5日均线上穿30日均线（金叉）']
                
                # Check volume confirmation
                if len(recent_window) > 0 and pd.notna(latest['volume']):
                    avg_volume = recent_window['volume'].iloc[:-1].mean() if len(recent_window) > 1 else latest['volume']
                    if latest['volume'] > avg_volume * 1.2:
                        reason_parts.append('成交量放大')
                
                signals.append({
                    'signal_type': 'buy',
                    'signal_strength': final_strength,
                    'signal_reason': '，'.join(reason_parts),
                    'signal_date': latest['date'].strftime('%Y-%m-%d'),
                    'indicators_used': ['MA5', 'MA30']
                })
        
        # 2. Death cross (5-day MA crosses below 30-day MA)
        if pd.notna(latest['ma5']) and pd.notna(latest['ma30']):
            if latest['ma5'] < latest['ma30'] and prev['ma5'] >= prev['ma30']:
                # Calculate dynamic strength
                base_strength = 0.6
                cross_strength = self._calculate_ma_cross_strength(df, window)
                final_strength = (base_strength + cross_strength) / 2
                
                reason_parts = ['5日均线下穿30日均线（死叉）']
                
                # Check volume confirmation
                if len(recent_window) > 0 and pd.notna(latest['volume']):
                    avg_volume = recent_window['volume'].iloc[:-1].mean() if len(recent_window) > 1 else latest['volume']
                    if latest['volume'] > avg_volume * 1.2:
                        reason_parts.append('成交量放大')
                
                signals.append({
                    'signal_type': 'sell',
                    'signal_strength': final_strength,
                    'signal_reason': '，'.join(reason_parts),
                    'signal_date': latest['date'].strftime('%Y-%m-%d'),
                    'indicators_used': ['MA5', 'MA30']
                })
        
        # 3. RSI oversold/overbought with dynamic strength and divergence check
        if pd.notna(latest['rsi']):
            # Check for divergence first (more reliable signal)
            has_divergence, div_type = self._check_rsi_divergence(df, window)
            
            if latest['rsi'] < 30:
                # Calculate dynamic strength based on RSI value
                strength = self._calculate_rsi_signal_strength(latest['rsi'], 'buy')
                
                # Boost strength if divergence detected
                if has_divergence and div_type == 'bullish':
                    strength = min(strength + 0.15, 1.0)
                
                reason = f'RSI超卖（{latest["rsi"]:.1f}）'
                if has_divergence:
                    reason += '，出现看涨背离'
                
                signals.append({
                    'signal_type': 'buy',
                    'signal_strength': strength,
                    'signal_reason': reason,
                    'signal_date': latest['date'].strftime('%Y-%m-%d'),
                    'indicators_used': ['RSI']
                })
            elif latest['rsi'] > 70:
                # Calculate dynamic strength
                strength = self._calculate_rsi_signal_strength(latest['rsi'], 'sell')
                
                # Boost strength if divergence detected
                if has_divergence and div_type == 'bearish':
                    strength = min(strength + 0.15, 1.0)
                
                reason = f'RSI超买（{latest["rsi"]:.1f}）'
                if has_divergence:
                    reason += '，出现看跌背离'
                
                signals.append({
                    'signal_type': 'sell',
                    'signal_strength': strength,
                    'signal_reason': reason,
                    'signal_date': latest['date'].strftime('%Y-%m-%d'),
                    'indicators_used': ['RSI']
                })
        
        # 4. MACD signal with histogram confirmation
        if pd.notna(latest['macd']) and pd.notna(latest['macd_signal']):
            if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
                # Base strength
                strength = 0.6
                
                # Check histogram momentum
                if pd.notna(latest['macd_histogram']):
                    if latest['macd_histogram'] > 0:
                        strength += 0.1  # Histogram positive
                    if len(df) > 1 and pd.notna(prev['macd_histogram']):
                        if latest['macd_histogram'] > prev['macd_histogram']:
                            strength += 0.1  # Histogram increasing
                
                reason = 'MACD上穿信号线'
                if pd.notna(latest['macd_histogram']) and latest['macd_histogram'] > 0:
                    reason += '，柱状图转正'
                
                signals.append({
                    'signal_type': 'buy',
                    'signal_strength': min(strength, 1.0),
                    'signal_reason': reason,
                    'signal_date': latest['date'].strftime('%Y-%m-%d'),
                    'indicators_used': ['MACD']
                })
            elif latest['macd'] < latest['macd_signal'] and prev['macd'] >= prev['macd_signal']:
                # MACD death cross
                strength = 0.6
                
                if pd.notna(latest['macd_histogram']):
                    if latest['macd_histogram'] < 0:
                        strength += 0.1
                    if len(df) > 1 and pd.notna(prev['macd_histogram']):
                        if latest['macd_histogram'] < prev['macd_histogram']:
                            strength += 0.1
                
                reason = 'MACD下穿信号线'
                if pd.notna(latest['macd_histogram']) and latest['macd_histogram'] < 0:
                    reason += '，柱状图转负'
                
                signals.append({
                    'signal_type': 'sell',
                    'signal_strength': min(strength, 1.0),
                    'signal_reason': reason,
                    'signal_date': latest['date'].strftime('%Y-%m-%d'),
                    'indicators_used': ['MACD']
                })
        
        # 5. If no signals detected, add a hold signal with calculated strength
        if not signals:
            # Calculate hold strength based on market uncertainty
            hold_strength = 0.5
            hold_reason_parts = []
            
            # Check MA position and separation
            if pd.notna(latest['ma5']) and pd.notna(latest['ma30']):
                separation = abs(latest['ma5'] - latest['ma30']) / latest['ma30']
                if separation < 0.02:  # Very close (uncertain)
                    hold_strength = 0.6
                    hold_reason_parts.append('均线粘合，方向不明')
                elif latest['ma5'] > latest['ma30']:
                    hold_reason_parts.append('价格位于均线上方')
                else:
                    hold_reason_parts.append('价格位于均线下方')
            
            # Check RSI
            if pd.notna(latest['rsi']):
                if 30 <= latest['rsi'] <= 70:
                    hold_strength = 0.55
                    hold_reason_parts.append('RSI处于中性区间')
            
            # Check trend consistency (if trends conflict, higher hold strength)
            if len(df) >= 20:
                short_trend = 'up' if df['close'].iloc[-1] > df['close'].iloc[-5] else 'down'
                medium_trend = 'up' if df['close'].iloc[-1] > df['close'].iloc[-20] else 'down'
                if short_trend != medium_trend:
                    hold_strength = 0.6
                    hold_reason_parts.append('短期与中期趋势不一致')
            
            if hold_reason_parts:
                hold_reason = f"当前无明确买卖信号，建议持有观望（{', '.join(hold_reason_parts)}）"
            else:
                hold_reason = "当前无明确买卖信号，建议持有观望"
            
            signals.append({
                'signal_type': 'hold',
                'signal_strength': hold_strength,
                'signal_reason': hold_reason,
                'signal_date': latest['date'].strftime('%Y-%m-%d'),
                'indicators_used': ['综合指标']
            })
        
        return signals
    
    def detect_trading_signals_for_backtest(self, df: pd.DataFrame, window: int = 5) -> list:
        """
        Detect trading signals for backtesting - scans entire historical period.
        
        Unlike detect_trading_signals which only checks the latest day,
        this method scans all days in the DataFrame to find buy/sell signals
        throughout the entire backtest period.
        
        Args:
            df: DataFrame with technical indicators
            window: Window size for trend consistency check
            
        Returns:
            List of signal dictionaries for all days
        """
        all_signals = []
        
        if len(df) < 30:
            return all_signals
        
        # Scan through all days (starting from day 30 to ensure indicators are calculated)
        for i in range(30, len(df)):
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1] if i > 0 else current_row
            current_date = current_row['date'].strftime('%Y-%m-%d')
            
            # Get recent window for this day
            recent_window = df.iloc[max(0, i-window):i+1]
            
            day_signals = []
            
            # 1. Check MA cross signals
            if pd.notna(current_row['ma5']) and pd.notna(current_row['ma30']):
                if pd.notna(prev_row['ma5']) and pd.notna(prev_row['ma30']):
                    # Golden cross
                    if current_row['ma5'] > current_row['ma30'] and prev_row['ma5'] <= prev_row['ma30']:
                        base_strength = 0.6
                        cross_strength = self._calculate_ma_cross_strength(df.iloc[:i+1], window)
                        final_strength = (base_strength + cross_strength) / 2
                        
                        reason_parts = ['5日均线上穿30日均线（金叉）']
                        if pd.notna(current_row['volume']) and len(recent_window) > 1:
                            avg_volume = recent_window['volume'].iloc[:-1].mean()
                            if current_row['volume'] > avg_volume * 1.2:
                                reason_parts.append('成交量放大')
                        
                        day_signals.append({
                            'signal_type': 'buy',
                            'signal_strength': final_strength,
                            'signal_reason': '，'.join(reason_parts),
                            'signal_date': current_date,
                            'indicators_used': ['MA5', 'MA30']
                        })
                    
                    # Death cross
                    elif current_row['ma5'] < current_row['ma30'] and prev_row['ma5'] >= prev_row['ma30']:
                        base_strength = 0.6
                        cross_strength = self._calculate_ma_cross_strength(df.iloc[:i+1], window)
                        final_strength = (base_strength + cross_strength) / 2
                        
                        reason_parts = ['5日均线下穿30日均线（死叉）']
                        if pd.notna(current_row['volume']) and len(recent_window) > 1:
                            avg_volume = recent_window['volume'].iloc[:-1].mean()
                            if current_row['volume'] > avg_volume * 1.2:
                                reason_parts.append('成交量放大')
                        
                        day_signals.append({
                            'signal_type': 'sell',
                            'signal_strength': final_strength,
                            'signal_reason': '，'.join(reason_parts),
                            'signal_date': current_date,
                            'indicators_used': ['MA5', 'MA30']
                        })
            
            # 2. Check RSI signals
            if pd.notna(current_row['rsi']):
                has_divergence, div_type = self._check_rsi_divergence(df.iloc[:i+1], window)
                
                if current_row['rsi'] < 30:
                    strength = self._calculate_rsi_signal_strength(current_row['rsi'], 'buy')
                    if has_divergence and div_type == 'bullish':
                        strength = min(strength + 0.15, 1.0)
                    
                    reason = f'RSI超卖（{current_row["rsi"]:.1f}）'
                    if has_divergence:
                        reason += '，出现看涨背离'
                    
                    day_signals.append({
                        'signal_type': 'buy',
                        'signal_strength': strength,
                        'signal_reason': reason,
                        'signal_date': current_date,
                        'indicators_used': ['RSI']
                    })
                elif current_row['rsi'] > 70:
                    strength = self._calculate_rsi_signal_strength(current_row['rsi'], 'sell')
                    if has_divergence and div_type == 'bearish':
                        strength = min(strength + 0.15, 1.0)
                    
                    reason = f'RSI超买（{current_row["rsi"]:.1f}）'
                    if has_divergence:
                        reason += '，出现看跌背离'
                    
                    day_signals.append({
                        'signal_type': 'sell',
                        'signal_strength': strength,
                        'signal_reason': reason,
                        'signal_date': current_date,
                        'indicators_used': ['RSI']
                    })
            
            # 3. Check MACD signals
            if pd.notna(current_row['macd']) and pd.notna(current_row['macd_signal']):
                if pd.notna(prev_row['macd']) and pd.notna(prev_row['macd_signal']):
                    # MACD golden cross
                    if current_row['macd'] > current_row['macd_signal'] and prev_row['macd'] <= prev_row['macd_signal']:
                        strength = 0.6
                        if pd.notna(current_row['macd_histogram']):
                            if current_row['macd_histogram'] > 0:
                                strength += 0.1
                            if pd.notna(prev_row['macd_histogram']):
                                if current_row['macd_histogram'] > prev_row['macd_histogram']:
                                    strength += 0.1
                        
                        reason = 'MACD上穿信号线'
                        if pd.notna(current_row['macd_histogram']) and current_row['macd_histogram'] > 0:
                            reason += '，柱状图转正'
                        
                        day_signals.append({
                            'signal_type': 'buy',
                            'signal_strength': min(strength, 1.0),
                            'signal_reason': reason,
                            'signal_date': current_date,
                            'indicators_used': ['MACD']
                        })
                    
                    # MACD death cross
                    elif current_row['macd'] < current_row['macd_signal'] and prev_row['macd'] >= prev_row['macd_signal']:
                        strength = 0.6
                        if pd.notna(current_row['macd_histogram']):
                            if current_row['macd_histogram'] < 0:
                                strength += 0.1
                            if pd.notna(prev_row['macd_histogram']):
                                if current_row['macd_histogram'] < prev_row['macd_histogram']:
                                    strength += 0.1
                        
                        reason = 'MACD下穿信号线'
                        if pd.notna(current_row['macd_histogram']) and current_row['macd_histogram'] < 0:
                            reason += '，柱状图转负'
                        
                        day_signals.append({
                            'signal_type': 'sell',
                            'signal_strength': min(strength, 1.0),
                            'signal_reason': reason,
                            'signal_date': current_date,
                            'indicators_used': ['MACD']
                        })
            
            # Add all signals for this day
            all_signals.extend(day_signals)
        
        return all_signals
    
    def calculate_price_statistics(self, df: pd.DataFrame) -> PriceStatistics:
        """Calculate price statistics."""
        if df.empty:
            return PriceStatistics(
                current_price=0.0,
                highest_price=0.0,
                lowest_price=0.0,
                average_price=0.0,
                price_change=0.0,
                price_change_pct=0.0,
                volatility=0.0
            )
        
        current_price = df['close'].iloc[-1]
        highest_price = df['high'].max()
        lowest_price = df['low'].min()
        average_price = df['close'].mean()
        start_price = df['close'].iloc[0]
        price_change = current_price - start_price
        price_change_pct = (price_change / start_price) * 100 if start_price > 0 else 0.0
        volatility = df['close'].std()
        
        return PriceStatistics(
            current_price=float(current_price),
            highest_price=float(highest_price),
            lowest_price=float(lowest_price),
            average_price=float(average_price),
            price_change=float(price_change),
            price_change_pct=float(price_change_pct),
            volatility=float(volatility)
        )
    
    def calculate_volume_statistics(self, df: pd.DataFrame) -> VolumeStatistics:
        """Calculate volume statistics."""
        if df.empty:
            return VolumeStatistics(
                total_volume=0.0,
                average_volume=0.0,
                max_volume=0.0,
                min_volume=0.0,
                volume_trend='stable'
            )
        
        total_volume = df['volume'].sum()
        average_volume = df['volume'].mean()
        max_volume = df['volume'].max()
        min_volume = df['volume'].min()
        
        # Determine volume trend
        if len(df) >= 10:
            recent_avg = df['volume'].tail(10).mean()
            earlier_avg = df['volume'].head(10).mean()
            if recent_avg > earlier_avg * 1.1:
                volume_trend = 'increasing'
            elif recent_avg < earlier_avg * 0.9:
                volume_trend = 'decreasing'
            else:
                volume_trend = 'stable'
        else:
            volume_trend = 'stable'
        
        return VolumeStatistics(
            total_volume=float(total_volume),
            average_volume=float(average_volume),
            max_volume=float(max_volume),
            min_volume=float(min_volume),
            volume_trend=volume_trend
        )
    
    def calculate_risk_metrics(self, df: pd.DataFrame) -> RiskMetrics:
        """Calculate risk metrics."""
        if df.empty or len(df) < 2:
            return RiskMetrics(
                volatility=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
                beta=None,
                risk_level='low'
            )
        
        # Volatility (already calculated in price stats)
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized volatility
        
        # Maximum drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(drawdown.min()) * 100
        
        # Sharpe ratio (simplified, assuming risk-free rate = 0)
        sharpe_ratio = None
        if len(returns) > 0 and returns.std() > 0:
            sharpe_ratio = (returns.mean() * 252) / (returns.std() * np.sqrt(252))
        
        # Risk level
        if volatility > 0.3 or max_drawdown > 30:
            risk_level = 'high'
        elif volatility > 0.15 or max_drawdown > 15:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return RiskMetrics(
            volatility=float(volatility),
            max_drawdown=float(max_drawdown),
            sharpe_ratio=float(sharpe_ratio) if sharpe_ratio is not None else None,
            beta=None,  # Beta requires market data comparison
            risk_level=risk_level
        )
    
    def analyze_trend(self, df: pd.DataFrame) -> TrendAnalysis:
        """Analyze price trends."""
        if df.empty or len(df) < 60:
            return TrendAnalysis(
                short_term_trend='sideways',
                medium_term_trend='sideways',
                long_term_trend='sideways',
                trend_strength=0.5,
                support_level=None,
                resistance_level=None
            )
        
        # Short-term trend (last 5 days)
        if len(df) >= 5:
            short_term = 'up' if df['close'].iloc[-1] > df['close'].iloc[-5] else 'down'
        else:
            short_term = 'sideways'
        
        # Medium-term trend (last 20 days)
        if len(df) >= 20:
            medium_term = 'up' if df['close'].iloc[-1] > df['close'].iloc[-20] else 'down'
        else:
            medium_term = 'sideways'
        
        # Long-term trend (last 60 days)
        if len(df) >= 60:
            long_term = 'up' if df['close'].iloc[-1] > df['close'].iloc[-60] else 'down'
        else:
            long_term = 'sideways'
        
        # Trend strength (based on consistency)
        trends = [short_term, medium_term, long_term]
        if all(t == 'up' for t in trends):
            trend_strength = 0.9
        elif all(t == 'down' for t in trends):
            trend_strength = 0.9
        elif trends.count('up') == 2 or trends.count('down') == 2:
            trend_strength = 0.7
        else:
            trend_strength = 0.5
        
        # Support and resistance levels
        support_level = float(df['low'].tail(20).min()) if len(df) >= 20 else None
        resistance_level = float(df['high'].tail(20).max()) if len(df) >= 20 else None
        
        return TrendAnalysis(
            short_term_trend=short_term,
            medium_term_trend=medium_term,
            long_term_trend=long_term,
            trend_strength=trend_strength,
            support_level=support_level,
            resistance_level=resistance_level
        )
    
    async def generate_overall_assessment(
        self, 
        price_stats: PriceStatistics,
        volume_stats: VolumeStatistics,
        technical_indicators: TechnicalIndicators,
        trading_signals: list,
        risk_metrics: RiskMetrics,
        trend_analysis: TrendAnalysis
    ) -> tuple[str, float]:
        """Generate overall assessment using LLM."""
        # Format technical indicators with proper handling of None values
        ma5_str = f"{technical_indicators.ma5:.2f}" if technical_indicators.ma5 is not None else "N/A"
        ma30_str = f"{technical_indicators.ma30:.2f}" if technical_indicators.ma30 is not None else "N/A"
        rsi_str = f"{technical_indicators.rsi:.2f}" if technical_indicators.rsi is not None else "N/A"
        macd_str = f"{technical_indicators.macd:.2f}" if technical_indicators.macd is not None else "N/A"
        
        # Format trading signals (trading_signals is a list of TradingSignal objects, not dicts)
        signals_text = "\n".join([f"- {s.signal_type}: {s.signal_reason}" for s in trading_signals[:5]])
        if not signals_text:
            signals_text = "- 暂无交易信号"
        
        assessment_prompt = f"""基于以下股票分析数据，生成综合评估和投资建议。

价格统计:
- 当前价格: {price_stats.current_price:.2f}
- 最高价: {price_stats.highest_price:.2f}
- 最低价: {price_stats.lowest_price:.2f}
- 平均价: {price_stats.average_price:.2f}
- 价格变化: {price_stats.price_change:.2f} ({price_stats.price_change_pct:.2f}%)

成交量统计:
- 平均成交量: {volume_stats.average_volume:.0f}
- 成交量趋势: {volume_stats.volume_trend}

技术指标（最新）:
- MA5: {ma5_str}
- MA30: {ma30_str}
- RSI: {rsi_str}
- MACD: {macd_str}

交易信号:
{signals_text}

风险指标:
- 波动率: {risk_metrics.volatility:.2%}
- 最大回撤: {risk_metrics.max_drawdown:.2f}%
- 风险等级: {risk_metrics.risk_level}

趋势分析:
- 短期趋势: {trend_analysis.short_term_trend}
- 中期趋势: {trend_analysis.medium_term_trend}
- 长期趋势: {trend_analysis.long_term_trend}
- 趋势强度: {trend_analysis.trend_strength:.2f}

请生成：
1. 综合评估（200-300字，使用中文）
2. 投资建议（买入/持有/卖出）
3. 风险评估
4. 置信度评分（0-1之间）

只返回评估文本，使用中文。"""

        try:
            assessment_messages = [
                SystemMessage(content="你是一个专业的金融分析师。基于技术指标和市场数据，生成客观、专业的股票分析评估。使用中文。"),
                HumanMessage(content=assessment_prompt)
            ]
            
            assessment_response = await self.llm.forward(
                messages=assessment_messages,
                tools=[],
                response_format=None,
                max_completion_tokens=2000
            )
            
            if assessment_response and len(assessment_response) > 0:
                response_messages = assessment_response[0] if isinstance(assessment_response[0], list) else assessment_response
                if response_messages:
                    last_msg = response_messages[-1]
                    content = getattr(last_msg, 'content', '')
                    
                    if content:
                        # Calculate confidence based on data quality
                        confidence = 0.7  # Base confidence
                        if technical_indicators.ma5 and technical_indicators.ma30:
                            confidence += 0.1
                        if technical_indicators.rsi:
                            confidence += 0.1
                        if trading_signals:
                            confidence += 0.1
                        confidence = min(confidence, 1.0)
                        
                        return content, confidence
        except Exception as e:
            logger.warning(f"Error generating assessment: {e}")
        
        # Fallback assessment
        fallback = f"""基于技术分析，该股票在分析期间价格变化{price_stats.price_change_pct:.2f}%，"
        "当前风险等级为{risk_metrics.risk_level}。"
        "建议根据个人风险承受能力和投资目标做出决策。"""
        return fallback, 0.6
    
    async def analyze_stock(
        self, 
        stock_code: str, 
        start_date: str, 
        end_date: str
    ) -> FinancialAnalysisResult:
        """
        Analyze a stock and return structured analysis result.
        
        Args:
            stock_code: Stock code (e.g., '000001')
            start_date: Start date in format 'YYYYMMDD'
            end_date: End date in format 'YYYYMMDD'
            
        Returns:
            FinancialAnalysisResult with complete analysis
        """
        logger.info(f"Starting financial analysis for {stock_code} from {start_date} to {end_date}")
        
        # Get stock data
        df = self.get_stock_data(stock_code, start_date, end_date)
        
        if df.empty:
            logger.error(f"Failed to get data for stock {stock_code}")
            raise ValueError(f"无法获取股票 {stock_code} 的数据")
        
        # Calculate technical indicators
        df = self.calculate_technical_indicators(df)
        
        # Get latest technical indicators
        latest = df.iloc[-1]
        technical_indicators = TechnicalIndicators(
            ma5=float(latest['ma5']) if pd.notna(latest['ma5']) else None,
            ma10=float(latest['ma10']) if pd.notna(latest['ma10']) else None,
            ma20=float(latest['ma20']) if pd.notna(latest['ma20']) else None,
            ma30=float(latest['ma30']) if pd.notna(latest['ma30']) else None,
            ma60=float(latest['ma60']) if pd.notna(latest['ma60']) else None,
            rsi=float(latest['rsi']) if pd.notna(latest['rsi']) else None,
            macd=float(latest['macd']) if pd.notna(latest['macd']) else None,
            macd_signal=float(latest['macd_signal']) if pd.notna(latest['macd_signal']) else None,
            macd_histogram=float(latest['macd_histogram']) if pd.notna(latest['macd_histogram']) else None,
            bollinger_upper=float(latest['bollinger_upper']) if pd.notna(latest['bollinger_upper']) else None,
            bollinger_middle=float(latest['bollinger_middle']) if pd.notna(latest['bollinger_middle']) else None,
            bollinger_lower=float(latest['bollinger_lower']) if pd.notna(latest['bollinger_lower']) else None,
        )
        
        # Detect trading signals
        signal_data = self.detect_trading_signals(df)
        trading_signals = [TradingSignal(**s) for s in signal_data]
        
        # Calculate statistics
        price_stats = self.calculate_price_statistics(df)
        volume_stats = self.calculate_volume_statistics(df)
        risk_metrics = self.calculate_risk_metrics(df)
        trend_analysis = self.analyze_trend(df)
        
        # Generate overall assessment
        overall_assessment, confidence_score = await self.generate_overall_assessment(
            price_stats, volume_stats, technical_indicators, 
            trading_signals, risk_metrics, trend_analysis
        )
        
        # Prepare historical data
        from app.models import HistoricalDataPoint
        historical_data = []
        for _, row in df.iterrows():
            historical_data.append(HistoricalDataPoint(
                date=row['date'].strftime('%Y-%m-%d'),
                open=float(row['open']) if pd.notna(row['open']) else 0.0,
                close=float(row['close']) if pd.notna(row['close']) else 0.0,
                high=float(row['high']) if pd.notna(row['high']) else 0.0,
                low=float(row['low']) if pd.notna(row['low']) else 0.0,
                volume=float(row['volume']) if pd.notna(row['volume']) else 0.0,
                ma5=float(row['ma5']) if pd.notna(row['ma5']) else None,
                ma10=float(row['ma10']) if pd.notna(row['ma10']) else None,
                ma20=float(row['ma20']) if pd.notna(row['ma20']) else None,
                ma30=float(row['ma30']) if pd.notna(row['ma30']) else None,
                ma60=float(row['ma60']) if pd.notna(row['ma60']) else None,
                rsi=float(row['rsi']) if pd.notna(row['rsi']) else None,
                macd=float(row['macd']) if pd.notna(row['macd']) else None,
                macd_signal=float(row['macd_signal']) if pd.notna(row['macd_signal']) else None,
                macd_histogram=float(row['macd_histogram']) if pd.notna(row['macd_histogram']) else None,
                bollinger_upper=float(row['bollinger_upper']) if pd.notna(row['bollinger_upper']) else None,
                bollinger_middle=float(row['bollinger_middle']) if pd.notna(row['bollinger_middle']) else None,
                bollinger_lower=float(row['bollinger_lower']) if pd.notna(row['bollinger_lower']) else None,
            ))
        
        # Build result
        result = FinancialAnalysisResult(
            stock_code=stock_code,
            stock_name=None,  # Could be fetched from akshare if needed
            analysis_period=f"{start_date} to {end_date}",
            start_date=start_date,
            end_date=end_date,
            data_points=len(df),
            historical_data=historical_data,
            price_stats=price_stats,
            volume_stats=volume_stats,
            technical_indicators=technical_indicators,
            trading_signals=trading_signals,
            risk_metrics=risk_metrics,
            trend_analysis=trend_analysis,
            overall_assessment=overall_assessment,
            confidence_score=confidence_score
        )
        
        logger.info(f"Financial analysis completed for {stock_code}: {len(df)} data points, {len(trading_signals)} signals")
        return result
    
    def get_stock_list(self, max_stocks: int = 100, focus_sector: Optional[str] = None) -> List[Tuple[str, str]]:
        """
        Get list of A-share stocks from akshare.
        
        Args:
            max_stocks: Maximum number of stocks to return
            focus_sector: Optional sector filter (e.g., '科技', '金融')
            
        Returns:
            List of (stock_code, stock_name) tuples
        """
        if not AKSHARE_AVAILABLE:
            logger.error("akshare not available, cannot fetch stock list")
            return []
        
        # Try multiple akshare APIs to get stock list
        stock_list_df = None
        
        # Method 1: Try stock_zh_a_spot_em (real-time stock list)
        try:
            logger.info(f"Fetching stock list using stock_zh_a_spot_em (max={max_stocks}, sector={focus_sector})")
            stock_list_df = ak.stock_zh_a_spot_em()
            if stock_list_df is not None and not stock_list_df.empty:
                logger.info(f"Successfully fetched stock list using stock_zh_a_spot_em: {len(stock_list_df)} rows")
        except Exception as e:
            logger.warning(f"Failed to fetch using stock_zh_a_spot_em: {str(e)}")
            stock_list_df = None
        
        # Method 2: Try stock_info_a_code_name (A-share code and name list)
        if stock_list_df is None or stock_list_df.empty:
            try:
                logger.info("Trying stock_info_a_code_name as fallback")
                stock_list_df = ak.stock_info_a_code_name()
                if stock_list_df is not None and not stock_list_df.empty:
                    logger.info(f"Successfully fetched stock list using stock_info_a_code_name: {len(stock_list_df)} rows")
            except Exception as e:
                logger.warning(f"Failed to fetch using stock_info_a_code_name: {str(e)}")
                stock_list_df = None
        
        # Method 3: Use a predefined list of popular stocks as last resort
        if stock_list_df is None or stock_list_df.empty:
            logger.warning("All akshare APIs failed, using predefined popular stock list")
            # Popular A-share stocks as fallback
            popular_stocks = [
                ("000001", "平安银行"), ("000002", "万科A"), ("000858", "五粮液"),
                ("000876", "新希望"), ("002415", "海康威视"), ("002594", "比亚迪"),
                ("600000", "浦发银行"), ("600036", "招商银行"), ("600519", "贵州茅台"),
                ("600887", "伊利股份"), ("000063", "中兴通讯"), ("002304", "洋河股份"),
                ("600276", "恒瑞医药"), ("000725", "京东方A"), ("002142", "宁波银行"),
                ("600031", "三一重工"), ("000166", "申万宏源"), ("600585", "海螺水泥"),
                ("000069", "华侨城A"), ("002230", "科大讯飞"), ("600009", "上海机场"),
                ("000568", "泸州老窖"), ("600104", "上汽集团"), ("000157", "中联重科"),
                ("600028", "中国石化"), ("000002", "万科A"), ("600016", "民生银行"),
                ("000858", "五粮液"), ("600519", "贵州茅台"), ("000001", "平安银行")
            ]
            # Remove duplicates while preserving order
            seen = set()
            unique_stocks = []
            for code, name in popular_stocks:
                if code not in seen:
                    seen.add(code)
                    unique_stocks.append((code, name))
            
            logger.info(f"Using {len(unique_stocks)} predefined popular stocks")
            return unique_stocks[:max_stocks]
        
        # Process the fetched DataFrame
        try:
            # Log column names for debugging
            logger.debug(f"DataFrame columns: {list(stock_list_df.columns)}")
            logger.debug(f"DataFrame shape: {stock_list_df.shape}")
            logger.debug(f"First few rows:\n{stock_list_df.head(3)}")
            
            # Extract stock code and name
            # Column names may vary, try common ones
            code_col = None
            name_col = None
            
            for col in stock_list_df.columns:
                col_lower = str(col).lower()
                if '代码' in str(col) or 'code' in col_lower:
                    code_col = col
                if '名称' in str(col) or 'name' in col_lower or '简称' in str(col):
                    name_col = col
            
            if not code_col or not name_col:
                # Fallback: use first two columns
                if len(stock_list_df.columns) >= 2:
                    code_col = stock_list_df.columns[0]
                    name_col = stock_list_df.columns[1]
                    logger.info(f"Using fallback columns: code_col={code_col}, name_col={name_col}")
                elif len(stock_list_df.columns) == 1:
                    code_col = stock_list_df.columns[0]
                    name_col = stock_list_df.columns[0]
                    logger.warning(f"Only one column found, using it for both code and name: {code_col}")
                else:
                    logger.error("No columns found in stock list DataFrame")
                    # Return predefined list as fallback
                    return self._get_fallback_stock_list(max_stocks)
            else:
                logger.info(f"Found columns: code_col={code_col}, name_col={name_col}")
            
            # Filter by sector if specified
            if focus_sector:
                # Try to find sector column
                sector_col = None
                for col in stock_list_df.columns:
                    if '行业' in str(col) or 'sector' in str(col).lower() or '板块' in str(col) or 'industry' in str(col).lower():
                        sector_col = col
                        break
                
                if sector_col:
                    try:
                        before_filter = len(stock_list_df)
                        stock_list_df = stock_list_df[stock_list_df[sector_col].astype(str).str.contains(focus_sector, na=False)]
                        logger.info(f"Filtered by sector '{focus_sector}': {before_filter} -> {len(stock_list_df)} rows")
                    except Exception as e:
                        logger.warning(f"Failed to filter by sector: {str(e)}")
            
            # Get stock codes and names
            stocks = []
            processed_count = 0
            invalid_count = 0
            
            for idx, row in stock_list_df.head(max_stocks * 3).iterrows():  # Get more to filter
                try:
                    processed_count += 1
                    code_raw = row[code_col]
                    code = str(code_raw).strip() if pd.notna(code_raw) else ""
                    
                    # Handle cases where code might have suffix like ".SZ" or ".SH"
                    if '.' in code:
                        code = code.split('.')[0]
                    
                    name_raw = row[name_col] if name_col != code_col else code_raw
                    name = str(name_raw).strip() if pd.notna(name_raw) else None
                    
                    # More lenient validation: 6 digits starting with 0, 3, or 6
                    # Also accept codes that are numeric and 6 digits after cleaning
                    if len(code) == 6 and code.isdigit() and code[0] in ['0', '3', '6']:
                        stocks.append((code, name))
                    else:
                        invalid_count += 1
                        if invalid_count <= 5:  # Log first few invalid codes for debugging
                            logger.debug(f"Invalid code format: '{code}' (length={len(code)}, isdigit={code.isdigit() if code else False})")
                except Exception as e:
                    logger.debug(f"Error processing row {idx}: {str(e)}")
                    continue
            
            logger.info(f"Processed {processed_count} rows, found {len(stocks)} valid stocks, {invalid_count} invalid")
            
            # Remove duplicates
            seen_codes = set()
            unique_stocks = []
            for code, name in stocks:
                if code not in seen_codes:
                    seen_codes.add(code)
                    unique_stocks.append((code, name))
            
            result = unique_stocks[:max_stocks]
            
            # If we got no results, use fallback
            if not result:
                logger.warning(f"No valid stocks found after processing, using fallback list")
                return self._get_fallback_stock_list(max_stocks)
            
            logger.info(f"Successfully fetched {len(result)} unique stocks")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process stock list: {str(e)}")
            import traceback
            logger.debug(traceback.format_exc())
            # Return predefined list as fallback
            return self._get_fallback_stock_list(max_stocks)
    
    def _get_fallback_stock_list(self, max_stocks: int = 100) -> List[Tuple[str, str]]:
        """Get fallback list of popular A-share stocks.
        
        Args:
            max_stocks: Maximum number of stocks to return
            
        Returns:
            List of (stock_code, stock_name) tuples
        """
        popular_stocks = [
            ("000001", "平安银行"), ("000002", "万科A"), ("000858", "五粮液"),
            ("000876", "新希望"), ("002415", "海康威视"), ("002594", "比亚迪"),
            ("600000", "浦发银行"), ("600036", "招商银行"), ("600519", "贵州茅台"),
            ("600887", "伊利股份"), ("000063", "中兴通讯"), ("002304", "洋河股份"),
            ("600276", "恒瑞医药"), ("000725", "京东方A"), ("002142", "宁波银行"),
            ("600031", "三一重工"), ("000166", "申万宏源"), ("600585", "海螺水泥"),
            ("000069", "华侨城A"), ("002230", "科大讯飞"), ("600009", "上海机场"),
            ("000568", "泸州老窖"), ("600104", "上汽集团"), ("000157", "中联重科"),
            ("600028", "中国石化"), ("600016", "民生银行"), ("600050", "中国联通"),
            ("000100", "TCL科技"), ("002241", "歌尔股份"), ("600703", "三安光电")
        ]
        # Remove duplicates while preserving order
        seen = set()
        unique_stocks = []
        for code, name in popular_stocks:
            if code not in seen:
                seen.add(code)
                unique_stocks.append((code, name))
        
        logger.info(f"Using {len(unique_stocks)} predefined popular stocks as fallback")
        return unique_stocks[:max_stocks]
    
    async def batch_analyze_stocks(
        self,
        stock_codes: List[str],
        start_date: str,
        end_date: str,
        max_concurrent: int = 3
    ) -> List[FinancialAnalysisResult]:
        """
        Batch analyze multiple stocks concurrently.
        
        Args:
            stock_codes: List of stock codes to analyze
            start_date: Start date in format 'YYYYMMDD'
            end_date: End date in format 'YYYYMMDD'
            max_concurrent: Maximum concurrent analyses
            
        Returns:
            List of analysis results (may contain fewer results if some fail)
        """
        logger.info(f"Starting batch analysis for {len(stock_codes)} stocks")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_one(stock_code: str):
            async with semaphore:
                try:
                    result = await self.analyze_stock(stock_code, start_date, end_date)
                    return result
                except Exception as e:
                    logger.warning(f"Failed to analyze {stock_code}: {str(e)}")
                    return None
        
        # Create tasks for all stocks
        tasks = [analyze_one(code) for code in stock_codes]
        
        # Execute with progress tracking
        completed = 0
        for task in asyncio.as_completed(tasks):
            result = await task
            if result:
                results.append(result)
            completed += 1
            if completed % 5 == 0:
                logger.info(f"Batch analysis progress: {completed}/{len(stock_codes)}")
        
        logger.info(f"Batch analysis completed: {len(results)}/{len(stock_codes)} successful")
        return results
    
    def _calculate_recommendation_score(self, analysis: FinancialAnalysisResult) -> float:
        """
        Calculate recommendation score (0-1) based on multiple factors.
        
        Args:
            analysis: Financial analysis result
            
        Returns:
            Recommendation score (0.0-1.0)
        """
        score = 0.5  # Base score
        
        # 1. Price performance (30% weight)
        price_change_pct = analysis.price_stats.price_change_pct
        if price_change_pct > 10:
            score += 0.15
        elif price_change_pct > 5:
            score += 0.1
        elif price_change_pct > 0:
            score += 0.05
        elif price_change_pct < -10:
            score -= 0.1
        elif price_change_pct < -5:
            score -= 0.05
        
        # 2. Trading signals (25% weight)
        buy_signals = [s for s in analysis.trading_signals if s.signal_type == 'buy']
        sell_signals = [s for s in analysis.trading_signals if s.signal_type == 'sell']
        
        if buy_signals:
            avg_buy_strength = sum(s.signal_strength for s in buy_signals) / len(buy_signals)
            score += avg_buy_strength * 0.15
        if sell_signals:
            avg_sell_strength = sum(s.signal_strength for s in sell_signals) / len(sell_signals)
            score -= avg_sell_strength * 0.1
        
        # 3. Trend strength (20% weight)
        if analysis.trend_analysis.trend_strength > 0.7:
            if analysis.trend_analysis.short_term_trend == 'up':
                score += 0.1
            elif analysis.trend_analysis.short_term_trend == 'down':
                score -= 0.05
        score += (analysis.trend_analysis.trend_strength - 0.5) * 0.1
        
        # 4. Risk level (15% weight) - lower risk is better
        if analysis.risk_metrics.risk_level == 'low':
            score += 0.1
        elif analysis.risk_metrics.risk_level == 'medium':
            score += 0.05
        else:  # high
            score -= 0.05
        
        # 5. Technical indicators (10% weight)
        if analysis.technical_indicators.rsi:
            if 30 < analysis.technical_indicators.rsi < 70:
                score += 0.05  # Neutral RSI is good
            elif analysis.technical_indicators.rsi < 30:
                score += 0.03  # Oversold might be opportunity
        
        # Normalize to 0-1 range
        score = max(0.0, min(1.0, score))
        return score
    
    async def recommend_stocks(
        self,
        stock_codes: Optional[List[str]] = None,
        max_stocks: int = 10,
        start_date: str = None,
        end_date: str = None,
        min_recommendation_score: float = 0.5,
        focus_sector: Optional[str] = None
    ) -> StockRecommendationResult:
        """
        Recommend stocks with ranking and detailed analysis.
        
        Args:
            stock_codes: Specific stock codes to analyze (if None, fetches popular stocks)
            max_stocks: Maximum number of stocks to recommend
            start_date: Start date in format 'YYYYMMDD' (defaults to 90 days ago)
            end_date: End date in format 'YYYYMMDD' (defaults to today)
            min_recommendation_score: Minimum score to include in recommendations
            focus_sector: Optional sector filter
            
        Returns:
            StockRecommendationResult with ranked recommendations
        """
        from datetime import datetime, timedelta
        
        # Set default dates if not provided
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
        
        logger.info(f"Starting stock recommendation (max_stocks={max_stocks}, period={start_date} to {end_date})")
        
        # Get stock list if not provided
        if stock_codes is None:
            stock_list = self.get_stock_list(max_stocks=max_stocks * 2, focus_sector=focus_sector)
            stock_codes = [code for code, _ in stock_list]
            stock_names = {code: name for code, name in stock_list}
        else:
            stock_names = {}
        
        if not stock_codes:
            raise ValueError("无法获取股票列表")
        
        # Batch analyze stocks
        analyses = await self.batch_analyze_stocks(stock_codes, start_date, end_date)
        
        if not analyses:
            raise ValueError("无法分析任何股票")
        
        # Calculate recommendation scores and create recommendations
        recommendations_data = []
        for analysis in analyses:
            score = self._calculate_recommendation_score(analysis)
            
            if score < min_recommendation_score:
                continue
            
            # Get stock name if available
            stock_name = stock_names.get(analysis.stock_code, analysis.stock_name)
            
            # Extract key highlights
            highlights = []
            if analysis.price_stats.price_change_pct > 5:
                highlights.append(f"近期涨幅{analysis.price_stats.price_change_pct:.2f}%")
            if analysis.trend_analysis.trend_strength > 0.7:
                highlights.append(f"趋势强度{analysis.trend_analysis.trend_strength:.2f}")
            if analysis.risk_metrics.risk_level == 'low':
                highlights.append("低风险")
            buy_signals = [s for s in analysis.trading_signals if s.signal_type == 'buy']
            if buy_signals:
                highlights.append(f"{len(buy_signals)}个买入信号")
            
            # Determine trend direction
            if analysis.trend_analysis.short_term_trend == 'up':
                trend_dir = 'up'
            elif analysis.trend_analysis.short_term_trend == 'down':
                trend_dir = 'down'
            else:
                trend_dir = 'sideways'
            
            recommendations_data.append({
                'stock_code': analysis.stock_code,
                'stock_name': stock_name,
                'score': score,
                'analysis': analysis,
                'current_price': analysis.price_stats.current_price,
                'price_change_pct': analysis.price_stats.price_change_pct,
                'risk_level': analysis.risk_metrics.risk_level,
                'trend_direction': trend_dir,
                'highlights': highlights
            })
        
        # Sort by score (descending)
        recommendations_data.sort(key=lambda x: x['score'], reverse=True)
        
        # Generate recommendation reasons using LLM
        recommendations = []
        for idx, rec_data in enumerate(recommendations_data[:max_stocks], 1):
            reason = await self._generate_recommendation_reason(rec_data['analysis'], rec_data['score'])
            
            recommendation = StockRecommendation(
                rank=idx,
                stock_code=rec_data['stock_code'],
                stock_name=rec_data['stock_name'],
                recommendation_score=rec_data['score'],
                recommendation_reason=reason,
                current_price=rec_data['current_price'],
                price_change_pct=rec_data['price_change_pct'],
                risk_level=rec_data['risk_level'],
                trend_direction=rec_data['trend_direction'],
                key_highlights=rec_data['highlights'],
                analysis_summary=rec_data['analysis']
            )
            recommendations.append(recommendation)
        
        # Generate comparison summary using LLM
        comparison_summary = await self._generate_comparison_summary(recommendations)
        
        result = StockRecommendationResult(
            recommendations=recommendations,
            total_analyzed=len(analyses),
            analysis_period=f"{start_date} to {end_date}",
            comparison_summary=comparison_summary
        )
        
        logger.info(f"Stock recommendation completed: {len(recommendations)} recommendations generated")
        return result
    
    async def _generate_recommendation_reason(
        self,
        analysis: FinancialAnalysisResult,
        score: float
    ) -> str:
        """Generate detailed recommendation reason using LLM."""
        # Pre-format technical indicators to avoid f-string formatting errors
        ma5_str = f"{analysis.technical_indicators.ma5:.2f}" if analysis.technical_indicators.ma5 is not None else "N/A"
        ma30_str = f"{analysis.technical_indicators.ma30:.2f}" if analysis.technical_indicators.ma30 is not None else "N/A"
        rsi_str = f"{analysis.technical_indicators.rsi:.2f}" if analysis.technical_indicators.rsi is not None else "N/A"
        
        prompt = f"""基于以下股票分析数据，生成详细的推荐理由（使用中文，200-300字）。

股票代码: {analysis.stock_code}
当前价格: {analysis.price_stats.current_price:.2f}
价格变化: {analysis.price_stats.price_change_pct:.2f}%
风险等级: {analysis.risk_metrics.risk_level}
趋势方向: {analysis.trend_analysis.short_term_trend}
推荐评分: {score:.2f}

技术指标:
- MA5: {ma5_str}
- MA30: {ma30_str}
- RSI: {rsi_str}

交易信号:
{chr(10).join([f"- {s.signal_type}: {s.signal_reason} (强度: {s.signal_strength:.2f})" for s in analysis.trading_signals[:3]])}

请生成：
1. 该股票的核心优势
2. 主要风险点
3. 适合的投资者类型
4. 投资建议

使用中文，客观专业。"""

        try:
            messages = [
                SystemMessage(content="你是一个专业的金融分析师。基于技术分析数据，生成客观、专业的股票推荐理由。使用中文。"),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.forward(
                messages=messages,
                tools=[],
                response_format=None,
                max_completion_tokens=1000
            )
            
            if response and len(response) > 0:
                response_messages = response[0] if isinstance(response[0], list) else response
                if response_messages:
                    last_msg = response_messages[-1]
                    content = getattr(last_msg, 'content', '')
                    if content:
                        return content
        except Exception as e:
            logger.warning(f"Error generating recommendation reason: {e}")
        
        # Fallback reason
        return (f"基于技术分析，该股票推荐评分为{score:.2f}。当前价格{analysis.price_stats.current_price:.2f}元，"
                f"分析期间价格变化{analysis.price_stats.price_change_pct:.2f}%，风险等级为{analysis.risk_metrics.risk_level}。"
                f"建议根据个人风险承受能力做出投资决策。")
    
    async def _generate_comparison_summary(self, recommendations: List[StockRecommendation]) -> str:
        """Generate comparison summary of recommended stocks using LLM."""
        if not recommendations:
            return "暂无推荐股票。"
        
        # Build comparison data
        comparison_data = []
        for rec in recommendations[:10]:  # Top 10 for comparison
            comparison_data.append({
                'rank': rec.rank,
                'code': rec.stock_code,
                'name': rec.stock_name or rec.stock_code,
                'score': rec.recommendation_score,
                'price': rec.current_price,
                'change_pct': rec.price_change_pct,
                'risk': rec.risk_level,
                'trend': rec.trend_direction,
                'highlights': ', '.join(rec.key_highlights[:3])
            })
        
        prompt = f"""基于以下推荐的股票列表，生成综合对比分析（使用中文，300-400字）。

推荐股票列表:
{chr(10).join([f"{d['rank']}. {d['name']} ({d['code']}): 评分{d['score']:.2f}, 价格{d['price']:.2f}元, "
                f"涨跌{d['change_pct']:.2f}%, 风险{d['risk']}, 趋势{d['trend']}, "
                f"亮点: {d['highlights']}" for d in comparison_data])}

请生成：
1. 整体市场趋势分析
2. 推荐股票的共同特点
3. 不同股票的优势对比
4. 投资组合建议

使用中文，客观专业。"""

        try:
            messages = [
                SystemMessage(content="你是一个专业的金融分析师。基于多只股票的对比分析，生成综合的投资建议。使用中文。"),
                HumanMessage(content=prompt)
            ]
            
            response = await self.llm.forward(
                messages=messages,
                tools=[],
                response_format=None,
                max_completion_tokens=1500
            )
            
            if response and len(response) > 0:
                response_messages = response[0] if isinstance(response[0], list) else response
                if response_messages:
                    last_msg = response_messages[-1]
                    content = getattr(last_msg, 'content', '')
                    if content:
                        return content
        except Exception as e:
            logger.warning(f"Error generating comparison summary: {e}")
        
        # Fallback summary
        avg_score = sum(r.recommendation_score for r in recommendations) / len(recommendations) if recommendations else 0.0
        return (f"共推荐{len(recommendations)}只股票，平均推荐评分为{avg_score:.2f}。"
                f"建议根据个人风险偏好和投资目标选择合适的股票。")

