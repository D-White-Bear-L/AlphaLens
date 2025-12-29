"""Strategy backtesting module for stock trading strategies."""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from loguru import logger

from app.models import (
    BacktestRequest, BacktestResult, BacktestTrade, BacktestMetrics
)
# Import FinancialAgent with TYPE_CHECKING to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.agent.financial_agent import FinancialAgent


class StrategyBacktest:
    """Strategy backtesting engine."""
    
    def __init__(self, financial_agent: Optional['FinancialAgent'] = None):
        """Initialize the backtest engine.
        
        Args:
            financial_agent: Optional FinancialAgent instance for data fetching
        """
        if financial_agent is None:
            from app.agent.financial_agent import FinancialAgent
            financial_agent = FinancialAgent()
        self.financial_agent = financial_agent
        logger.info("StrategyBacktest initialized")
    
    def _calculate_equity_curve(
        self,
        trades: List[BacktestTrade],
        initial_capital: float,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, float]]:
        """Calculate equity curve from trades.
        
        Args:
            trades: List of trades
            initial_capital: Initial capital
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            
        Returns:
            List of {date, capital} dictionaries
        """
        # Parse dates
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        
        # Create date range
        date_range = pd.date_range(start=start, end=end, freq='D')
        
        # Initialize equity curve
        equity_curve = []
        current_capital = initial_capital
        
        # Group trades by date
        trades_by_date = {}
        for trade in trades:
            buy_date = datetime.strptime(trade.buy_date, '%Y-%m-%d')
            sell_date = datetime.strptime(trade.sell_date, '%Y-%m-%d')
            
            if buy_date not in trades_by_date:
                trades_by_date[buy_date] = {'buy': [], 'sell': []}
            if sell_date not in trades_by_date:
                trades_by_date[sell_date] = {'buy': [], 'sell': []}
            
            trades_by_date[buy_date]['buy'].append(trade)
            trades_by_date[sell_date]['sell'].append(trade)
        
        # Calculate equity over time
        for date in date_range:
            # Apply buy trades
            if date in trades_by_date:
                for trade in trades_by_date[date].get('buy', []):
                    current_capital -= trade.buy_price * trade.shares
                
                # Apply sell trades
                for trade in trades_by_date[date].get('sell', []):
                    current_capital += trade.sell_price * trade.shares
            
            equity_curve.append({
                'date': date.strftime('%Y-%m-%d'),
                'capital': current_capital
            })
        
        return equity_curve
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict[str, float]]) -> float:
        """Calculate maximum drawdown from equity curve.
        
        Args:
            equity_curve: List of {date, capital} dictionaries
            
        Returns:
            Maximum drawdown (percentage)
        """
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        
        capitals = [point['capital'] for point in equity_curve]
        peak = capitals[0]
        max_dd = 0.0
        
        for capital in capitals:
            if capital > peak:
                peak = capital
            dd = (peak - capital) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
        
        return max_dd * 100  # Convert to percentage
    
    def _calculate_sharpe_ratio(
        self,
        trades: List[BacktestTrade],
        risk_free_rate: float = 0.03
    ) -> Optional[float]:
        """Calculate Sharpe ratio from trades.
        
        Args:
            trades: List of trades
            risk_free_rate: Risk-free rate (default: 3% annual)
            
        Returns:
            Sharpe ratio or None if insufficient data
        """
        if not trades or len(trades) < 2:
            return None
        
        returns = [trade.return_rate for trade in trades]
        
        if not returns or len(returns) < 2:
            return None
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return None
        
        # Annualize (assuming average trade duration)
        avg_hold_days = np.mean([trade.hold_days for trade in trades]) if trades else 30
        trading_days_per_year = 252
        
        annualized_return = mean_return * (trading_days_per_year / avg_hold_days)
        annualized_std = std_return * np.sqrt(trading_days_per_year / avg_hold_days)
        
        if annualized_std == 0:
            return None
        
        sharpe = (annualized_return - risk_free_rate) / annualized_std
        return float(sharpe)
    
    def _calculate_metrics(
        self,
        trades: List[BacktestTrade],
        initial_capital: float,
        equity_curve: List[Dict[str, float]],
        start_date: str,
        end_date: str
    ) -> BacktestMetrics:
        """Calculate backtest performance metrics.
        
        Args:
            trades: List of trades
            initial_capital: Initial capital
            equity_curve: Equity curve data
            start_date: Start date (YYYYMMDD)
            end_date: End date (YYYYMMDD)
            
        Returns:
            BacktestMetrics object
        """
        if not trades:
            return BacktestMetrics(
                initial_capital=initial_capital,
                final_capital=initial_capital,
                total_return=0.0,
                total_return_rate=0.0,
                annualized_return_rate=None,
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                win_rate=0.0,
                average_profit=0.0,
                max_profit=0.0,
                max_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
                profit_factor=None
            )
        
        # Calculate final capital
        total_profit = sum(trade.profit for trade in trades)
        final_capital = initial_capital + total_profit
        
        # Basic metrics
        total_return = final_capital - initial_capital
        total_return_rate = (total_return / initial_capital) * 100 if initial_capital > 0 else 0.0
        
        # Annualized return
        start = datetime.strptime(start_date, '%Y%m%d')
        end = datetime.strptime(end_date, '%Y%m%d')
        days = (end - start).days
        years = days / 365.25 if days > 0 else 1.0
        annualized_return_rate = ((final_capital / initial_capital) ** (1 / years) - 1) * 100 if years > 0 and initial_capital > 0 else None
        
        # Trade statistics
        total_trades = len(trades)
        successful_trades = sum(1 for trade in trades if trade.profit > 0)
        failed_trades = total_trades - successful_trades
        win_rate = successful_trades / total_trades if total_trades > 0 else 0.0
        
        # Profit statistics
        profits = [trade.profit for trade in trades]
        average_profit = np.mean(profits) if profits else 0.0
        max_profit = max(profits) if profits else 0.0
        max_loss = min(profits) if profits else 0.0
        
        # Drawdown
        max_drawdown = self._calculate_max_drawdown(equity_curve)
        
        # Sharpe ratio
        sharpe_ratio = self._calculate_sharpe_ratio(trades)
        
        # Profit factor
        total_profit_amount = sum(p for p in profits if p > 0)
        total_loss_amount = abs(sum(p for p in profits if p < 0))
        profit_factor = total_profit_amount / total_loss_amount if total_loss_amount > 0 else None
        
        return BacktestMetrics(
            initial_capital=initial_capital,
            final_capital=final_capital,
            total_return=total_return,
            total_return_rate=total_return_rate,
            annualized_return_rate=annualized_return_rate,
            total_trades=total_trades,
            successful_trades=successful_trades,
            failed_trades=failed_trades,
            win_rate=win_rate,
            average_profit=average_profit,
            max_profit=max_profit,
            max_loss=max_loss,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            profit_factor=profit_factor
        )
    
    async def backtest_signal_based_strategy(
        self,
        request: BacktestRequest
    ) -> BacktestResult:
        """Backtest a signal-based trading strategy.
        
        This strategy uses trading signals from FinancialAgent to make buy/sell decisions.
        
        Args:
            request: Backtest request parameters
            
        Returns:
            BacktestResult with performance metrics and trade history
        """
        logger.info(f"Starting signal-based backtest for {request.stock_code} "
                   f"({request.start_date} to {request.end_date})")
        
        # Get stock data
        df = self.financial_agent.get_stock_data(
            request.stock_code,
            request.start_date,
            request.end_date
        )
        
        if df.empty:
            raise ValueError(f"无法获取股票 {request.stock_code} 的数据")
        
        # Calculate technical indicators
        df = self.financial_agent.calculate_technical_indicators(df)
        
        # Check if we have enough data for signal detection
        if len(df) < 30:
            logger.warning(f"Insufficient data for signal-based strategy: {len(df)} data points (need at least 30)")
            # Return empty result
            empty_metrics = BacktestMetrics(
                initial_capital=request.initial_capital,
                final_capital=request.initial_capital,
                total_return=0.0,
                total_return_rate=0.0,
                annualized_return_rate=None,
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                win_rate=0.0,
                average_profit=0.0,
                max_profit=0.0,
                max_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
                profit_factor=None
            )
            return BacktestResult(
                stock_code=request.stock_code,
                stock_name=None,
                backtest_period=f"{request.start_date} to {request.end_date}",
                strategy_type=request.strategy_type,
                metrics=empty_metrics,
                trades=[],
                equity_curve=None
            )
        
        # Detect trading signals for backtesting (scans entire period, not just last day)
        signal_data = self.financial_agent.detect_trading_signals_for_backtest(df)
        
        logger.info(f"Detected {len(signal_data)} trading signals for {request.stock_code}")
        if signal_data:
            # Log signal summary
            buy_signals = [s for s in signal_data if s.get('signal_type') == 'buy']
            sell_signals = [s for s in signal_data if s.get('signal_type') == 'sell']
            hold_signals = [s for s in signal_data if s.get('signal_type') == 'hold']
            logger.info(f"Signal breakdown: {len(buy_signals)} buy, {len(sell_signals)} sell, {len(hold_signals)} hold")
            if buy_signals or sell_signals:
                # Log first few signals for debugging
                for sig in (buy_signals + sell_signals)[:3]:
                    logger.debug(f"Sample signal: {sig.get('signal_type')} on {sig.get('signal_date')}, "
                               f"strength={sig.get('signal_strength', 0):.2f}")
        
        if not signal_data:
            logger.warning(f"No trading signals detected for {request.stock_code} (data points: {len(df)})")
            # Return empty result
            empty_metrics = BacktestMetrics(
                initial_capital=request.initial_capital,
                final_capital=request.initial_capital,
                total_return=0.0,
                total_return_rate=0.0,
                annualized_return_rate=None,
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                win_rate=0.0,
                average_profit=0.0,
                max_profit=0.0,
                max_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
                profit_factor=None
            )
            return BacktestResult(
                stock_code=request.stock_code,
                stock_name=None,
                backtest_period=f"{request.start_date} to {request.end_date}",
                strategy_type=request.strategy_type,
                metrics=empty_metrics,
                trades=[],
                equity_curve=None
            )
        
        # Execute backtest
        trades = []
        capital = request.initial_capital
        position = None  # Current position: {buy_date, buy_price, shares, signal_type}
        trade_id = 1
        
        # Filter signals by type and strength
        signal_types_filter = request.signal_types or ['buy', 'sell']
        min_strength = request.min_signal_strength
        
        logger.info(f"Signal filter: types={signal_types_filter}, min_strength={min_strength:.2f}")
        
        # Track signal matching statistics
        signals_matched = 0
        signals_filtered_by_strength = 0
        signals_filtered_by_type = 0
        signals_filtered_by_date = 0
        
        # Show signal strength distribution for debugging
        if signal_data:
            strengths = [s.get('signal_strength', 0) for s in signal_data]
            if strengths:
                import numpy as np
                logger.info(f"Signal strength stats: min={min(strengths):.2f}, max={max(strengths):.2f}, "
                           f"mean={np.mean(strengths):.2f}, median={np.median(strengths):.2f}")
        
        # Pre-filter signals by type and strength for efficiency
        eligible_signals = [
            s for s in signal_data
            if s.get('signal_type') in signal_types_filter
            and s.get('signal_strength', 0) >= min_strength
        ]
        logger.info(f"After filtering by type and strength: {len(eligible_signals)}/{len(signal_data)} signals eligible")
        
        if not eligible_signals:
            logger.warning(f"No eligible signals after filtering (type={signal_types_filter}, min_strength={min_strength:.2f})")
            # Show why signals were filtered
            if signal_data:
                type_counts = {}
                strength_below_threshold = 0
                strength_distribution = {}
                for s in signal_data:
                    sig_type = s.get('signal_type', 'unknown')
                    type_counts[sig_type] = type_counts.get(sig_type, 0) + 1
                    strength = s.get('signal_strength', 0)
                    if strength < min_strength:
                        strength_below_threshold += 1
                    # Count by strength ranges
                    if strength < 0.3:
                        strength_distribution['<0.3'] = strength_distribution.get('<0.3', 0) + 1
                    elif strength < 0.5:
                        strength_distribution['0.3-0.5'] = strength_distribution.get('0.3-0.5', 0) + 1
                    elif strength < 0.7:
                        strength_distribution['0.5-0.7'] = strength_distribution.get('0.5-0.7', 0) + 1
                    elif strength < 0.9:
                        strength_distribution['0.7-0.9'] = strength_distribution.get('0.7-0.9', 0) + 1
                    else:
                        strength_distribution['>=0.9'] = strength_distribution.get('>=0.9', 0) + 1
                logger.info(f"Signal type distribution: {type_counts}")
                logger.info(f"Signal strength distribution: {strength_distribution}")
                logger.info(f"Signals below strength threshold ({min_strength:.2f}): {strength_below_threshold}/{len(signal_data)}")
        
        for i in range(len(df)):
            current_row = df.iloc[i]
            current_date = current_row['date'].strftime('%Y-%m-%d')
            current_price = current_row['close']
            
            # Check for signals on this day (only check eligible signals)
            day_signals = []
            for s in eligible_signals:
                signal_date = s.get('signal_date')
                signal_strength = s.get('signal_strength', 0)
                
                # Check date match
                if signal_date != current_date:
                    signals_filtered_by_date += 1
                    continue
                
                # Double-check strength (should already be filtered, but just in case)
                if signal_strength < min_strength:
                    signals_filtered_by_strength += 1
                    continue
                
                signals_matched += 1
                day_signals.append(s)
            
            if not day_signals:
                continue
            
            logger.debug(f"Found {len(day_signals)} signal(s) on {current_date}")
            
            # Process signals (prioritize buy signals if we have no position)
            for signal in day_signals:
                signal_type = signal.get('signal_type')
                
                # Buy signal
                if signal_type == 'buy' and position is None:
                    # Calculate shares (must be multiple of 100)
                    shares = (request.shares_per_trade // 100) * 100
                    cost = current_price * shares
                    
                    if capital >= cost:
                        position = {
                            'buy_date': current_date,
                            'buy_price': current_price,
                            'shares': shares,
                            'signal_type': signal.get('signal_reason', 'buy')
                        }
                        capital -= cost
                        logger.info(f"BUY: {current_date} @ {current_price:.2f}, shares: {shares}, cost: {cost:.2f}, remaining capital: {capital:.2f}")
                    else:
                        logger.warning(f"Buy signal on {current_date} but insufficient capital: {capital:.2f} < {cost:.2f}")
                
                # Sell signal
                elif signal_type == 'sell' and position is not None:
                    # Sell position
                    sell_price = current_price
                    profit = (sell_price - position['buy_price']) * position['shares']
                    capital += sell_price * position['shares']
                    
                    # Calculate hold days
                    buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                    sell_date = datetime.strptime(current_date, '%Y-%m-%d')
                    hold_days = (sell_date - buy_date).days
                    
                    # Calculate return rate
                    return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                    
                    trade = BacktestTrade(
                        trade_id=trade_id,
                        buy_date=position['buy_date'],
                        buy_price=position['buy_price'],
                        sell_date=current_date,
                        sell_price=sell_price,
                        shares=position['shares'],
                        profit=profit,
                        return_rate=return_rate * 100,  # Convert to percentage
                        signal_type=position['signal_type'],
                        hold_days=hold_days
                    )
                    trades.append(trade)
                    trade_id += 1
                    
                    logger.debug(f"Sell signal: {current_date} @ {sell_price:.2f}, profit: {profit:.2f}")
                    position = None
            
            # Check hold_days constraint
            if position is not None and request.hold_days is not None:
                buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
                days_held = (current_date_obj - buy_date).days
                
                if days_held >= request.hold_days:
                    # Force sell
                    sell_price = current_price
                    profit = (sell_price - position['buy_price']) * position['shares']
                    capital += sell_price * position['shares']
                    
                    return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                    
                    trade = BacktestTrade(
                        trade_id=trade_id,
                        buy_date=position['buy_date'],
                        buy_price=position['buy_price'],
                        sell_date=current_date,
                        sell_price=sell_price,
                        shares=position['shares'],
                        profit=profit,
                        return_rate=return_rate * 100,
                        signal_type=f"{position['signal_type']} (hold_days)",
                        hold_days=days_held
                    )
                    trades.append(trade)
                    trade_id += 1
                    position = None
        
        # Close any remaining position at the end
        if position is not None:
            final_price = df.iloc[-1]['close']
            final_date = df.iloc[-1]['date'].strftime('%Y-%m-%d')
            profit = (final_price - position['buy_price']) * position['shares']
            capital += final_price * position['shares']
            
            buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
            sell_date = datetime.strptime(final_date, '%Y-%m-%d')
            hold_days = (sell_date - buy_date).days
            return_rate = (final_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
            
            logger.info(f"SELL (end of backtest): {final_date} @ {final_price:.2f}, "
                       f"buy_date: {position['buy_date']}, profit: {profit:.2f}, return: {return_rate*100:.2f}%")
            
            trade = BacktestTrade(
                trade_id=trade_id,
                buy_date=position['buy_date'],
                buy_price=position['buy_price'],
                sell_date=final_date,
                sell_price=final_price,
                shares=position['shares'],
                profit=profit,
                return_rate=return_rate * 100,
                signal_type=f"{position['signal_type']} (end)",
                hold_days=hold_days
            )
            trades.append(trade)
        else:
            logger.info("No open position at end of backtest")
        
        # Calculate equity curve
        equity_curve = self._calculate_equity_curve(
            trades, request.initial_capital, request.start_date, request.end_date
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            trades, request.initial_capital, equity_curve,
            request.start_date, request.end_date
        )
        
        result = BacktestResult(
            stock_code=request.stock_code,
            stock_name=None,
            backtest_period=f"{request.start_date} to {request.end_date}",
            strategy_type=request.strategy_type,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve
        )
        
        # Log signal matching statistics
        logger.info(f"Signal matching stats: total_signals={len(signal_data)}, eligible_signals={len(eligible_signals)}, "
                   f"matched={signals_matched}, filtered_by_date={signals_filtered_by_date}")
        
        logger.info(f"Backtest completed: {len(trades)} trades, "
                   f"total return: {metrics.total_return_rate:.2f}%")
        
        return result
    
    async def backtest_ma_cross_strategy(
        self,
        request: BacktestRequest
    ) -> BacktestResult:
        """Backtest a MA (Moving Average) cross strategy.
        
        This strategy buys when short MA crosses above long MA (golden cross)
        and sells when short MA crosses below long MA (death cross).
        
        Args:
            request: Backtest request parameters
            
        Returns:
            BacktestResult with performance metrics and trade history
        """
        logger.info(f"Starting MA cross backtest for {request.stock_code} "
                   f"({request.start_date} to {request.end_date})")
        
        # Get stock data
        df = self.financial_agent.get_stock_data(
            request.stock_code,
            request.start_date,
            request.end_date
        )
        
        if df.empty:
            raise ValueError(f"无法获取股票 {request.stock_code} 的数据")
        
        # Calculate technical indicators
        df = self.financial_agent.calculate_technical_indicators(df)
        
        # Check if we have enough data for MA calculation
        if len(df) < 30:
            logger.warning(f"Insufficient data for MA cross strategy: {len(df)} data points (need at least 30)")
            # Return empty result
            empty_metrics = BacktestMetrics(
                initial_capital=request.initial_capital,
                final_capital=request.initial_capital,
                total_return=0.0,
                total_return_rate=0.0,
                annualized_return_rate=None,
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                win_rate=0.0,
                average_profit=0.0,
                max_profit=0.0,
                max_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
                profit_factor=None
            )
            return BacktestResult(
                stock_code=request.stock_code,
                stock_name=None,
                backtest_period=f"{request.start_date} to {request.end_date}",
                strategy_type=request.strategy_type,
                metrics=empty_metrics,
                trades=[],
                equity_curve=None
            )
        
        # Execute MA cross strategy
        trades = []
        capital = request.initial_capital
        position = None  # Current position: {buy_date, buy_price, shares}
        trade_id = 1
        
        # Use MA5 and MA30 for cross signals
        short_ma = 'ma5'
        long_ma = 'ma30'
        
        for i in range(1, len(df)):  # Start from index 1 to compare with previous
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            current_date = current_row['date'].strftime('%Y-%m-%d')
            current_price = current_row['close']
            
            # Check if MA values are available
            if pd.isna(current_row[short_ma]) or pd.isna(current_row[long_ma]):
                continue
            if pd.isna(prev_row[short_ma]) or pd.isna(prev_row[long_ma]):
                continue
            
            # Golden cross: short MA crosses above long MA (buy signal)
            if (current_row[short_ma] > current_row[long_ma] and 
                prev_row[short_ma] <= prev_row[long_ma] and 
                position is None):
                # Buy signal
                shares = (request.shares_per_trade // 100) * 100
                cost = current_price * shares
                
                if capital >= cost:
                    position = {
                        'buy_date': current_date,
                        'buy_price': current_price,
                        'shares': shares
                    }
                    capital -= cost
                    logger.debug(f"Golden cross buy: {current_date} @ {current_price:.2f}, shares: {shares}")
            
            # Death cross: short MA crosses below long MA (sell signal)
            elif (current_row[short_ma] < current_row[long_ma] and 
                  prev_row[short_ma] >= prev_row[long_ma] and 
                  position is not None):
                # Sell signal
                sell_price = current_price
                profit = (sell_price - position['buy_price']) * position['shares']
                capital += sell_price * position['shares']
                
                # Calculate hold days
                buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                sell_date = datetime.strptime(current_date, '%Y-%m-%d')
                hold_days = (sell_date - buy_date).days
                
                # Calculate return rate
                return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                
                trade = BacktestTrade(
                    trade_id=trade_id,
                    buy_date=position['buy_date'],
                    buy_price=position['buy_price'],
                    sell_date=current_date,
                    sell_price=sell_price,
                    shares=position['shares'],
                    profit=profit,
                    return_rate=return_rate * 100,
                    signal_type="MA死亡交叉",
                    hold_days=hold_days
                )
                trades.append(trade)
                trade_id += 1
                
                logger.debug(f"Death cross sell: {current_date} @ {sell_price:.2f}, profit: {profit:.2f}")
                position = None
            
            # Check hold_days constraint
            if position is not None and request.hold_days is not None:
                buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
                days_held = (current_date_obj - buy_date).days
                
                if days_held >= request.hold_days:
                    # Force sell
                    sell_price = current_price
                    profit = (sell_price - position['buy_price']) * position['shares']
                    capital += sell_price * position['shares']
                    
                    return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                    
                    trade = BacktestTrade(
                        trade_id=trade_id,
                        buy_date=position['buy_date'],
                        buy_price=position['buy_price'],
                        sell_date=current_date,
                        sell_price=sell_price,
                        shares=position['shares'],
                        profit=profit,
                        return_rate=return_rate * 100,
                        signal_type="MA金叉(持有到期)",
                        hold_days=days_held
                    )
                    trades.append(trade)
                    trade_id += 1
                    position = None
        
        # Close any remaining position at the end
        if position is not None:
            final_price = df.iloc[-1]['close']
            final_date = df.iloc[-1]['date'].strftime('%Y-%m-%d')
            profit = (final_price - position['buy_price']) * position['shares']
            capital += final_price * position['shares']
            
            buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
            sell_date = datetime.strptime(final_date, '%Y-%m-%d')
            hold_days = (sell_date - buy_date).days
            return_rate = (final_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
            
            trade = BacktestTrade(
                trade_id=trade_id,
                buy_date=position['buy_date'],
                buy_price=position['buy_price'],
                sell_date=final_date,
                sell_price=final_price,
                shares=position['shares'],
                profit=profit,
                return_rate=return_rate * 100,
                signal_type="MA金叉(回测结束)",
                hold_days=hold_days
            )
            trades.append(trade)
        
        # Calculate equity curve
        equity_curve = self._calculate_equity_curve(
            trades, request.initial_capital, request.start_date, request.end_date
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            trades, request.initial_capital, equity_curve,
            request.start_date, request.end_date
        )
        
        result = BacktestResult(
            stock_code=request.stock_code,
            stock_name=None,
            backtest_period=f"{request.start_date} to {request.end_date}",
            strategy_type=request.strategy_type,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve
        )
        
        logger.info(f"MA cross backtest completed: {len(trades)} trades, "
                   f"total return: {metrics.total_return_rate:.2f}%")
        
        return result
    
    async def backtest_rsi_strategy(
        self,
        request: BacktestRequest
    ) -> BacktestResult:
        """Backtest an RSI (Relative Strength Index) strategy.
        
        This strategy buys when RSI < 30 (oversold) and sells when RSI > 70 (overbought).
        
        Args:
            request: Backtest request parameters
            
        Returns:
            BacktestResult with performance metrics and trade history
        """
        logger.info(f"Starting RSI backtest for {request.stock_code} "
                   f"({request.start_date} to {request.end_date})")
        
        # Get stock data
        df = self.financial_agent.get_stock_data(
            request.stock_code,
            request.start_date,
            request.end_date
        )
        
        if df.empty:
            raise ValueError(f"无法获取股票 {request.stock_code} 的数据")
        
        # Calculate technical indicators
        df = self.financial_agent.calculate_technical_indicators(df)
        
        # Check if we have enough data for RSI calculation
        if len(df) < 30:
            logger.warning(f"Insufficient data for RSI strategy: {len(df)} data points (need at least 30)")
            # Return empty result
            empty_metrics = BacktestMetrics(
                initial_capital=request.initial_capital,
                final_capital=request.initial_capital,
                total_return=0.0,
                total_return_rate=0.0,
                annualized_return_rate=None,
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                win_rate=0.0,
                average_profit=0.0,
                max_profit=0.0,
                max_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
                profit_factor=None
            )
            return BacktestResult(
                stock_code=request.stock_code,
                stock_name=None,
                backtest_period=f"{request.start_date} to {request.end_date}",
                strategy_type=request.strategy_type,
                metrics=empty_metrics,
                trades=[],
                equity_curve=None
            )
        
        # Execute RSI strategy
        trades = []
        capital = request.initial_capital
        position = None  # Current position: {buy_date, buy_price, shares, rsi_value}
        trade_id = 1
        
        # RSI thresholds
        oversold_threshold = 30  # Buy when RSI < 30
        overbought_threshold = 70  # Sell when RSI > 70
        
        for i in range(len(df)):
            current_row = df.iloc[i]
            current_date = current_row['date'].strftime('%Y-%m-%d')
            current_price = current_row['close']
            current_rsi = current_row['rsi']
            
            # Skip if RSI is not available
            if pd.isna(current_rsi):
                continue
            
            # Buy signal: RSI < oversold_threshold (oversold)
            if current_rsi < oversold_threshold and position is None:
                # Calculate shares (must be multiple of 100)
                shares = (request.shares_per_trade // 100) * 100
                cost = current_price * shares
                
                if capital >= cost:
                    position = {
                        'buy_date': current_date,
                        'buy_price': current_price,
                        'shares': shares,
                        'rsi_value': current_rsi
                    }
                    capital -= cost
                    logger.debug(f"RSI oversold buy: {current_date} @ {current_price:.2f}, RSI: {current_rsi:.2f}, shares: {shares}")
            
            # Sell signal: RSI > overbought_threshold (overbought)
            elif current_rsi > overbought_threshold and position is not None:
                # Sell position
                sell_price = current_price
                profit = (sell_price - position['buy_price']) * position['shares']
                capital += sell_price * position['shares']
                
                # Calculate hold days
                buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                sell_date = datetime.strptime(current_date, '%Y-%m-%d')
                hold_days = (sell_date - buy_date).days
                
                # Calculate return rate
                return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                
                trade = BacktestTrade(
                    trade_id=trade_id,
                    buy_date=position['buy_date'],
                    buy_price=position['buy_price'],
                    sell_date=current_date,
                    sell_price=sell_price,
                    shares=position['shares'],
                    profit=profit,
                    return_rate=return_rate * 100,
                    signal_type=f"RSI超买({current_rsi:.1f})",
                    hold_days=hold_days
                )
                trades.append(trade)
                trade_id += 1
                
                logger.debug(f"RSI overbought sell: {current_date} @ {sell_price:.2f}, RSI: {current_rsi:.2f}, profit: {profit:.2f}")
                position = None
            
            # Check hold_days constraint
            if position is not None and request.hold_days is not None:
                buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
                days_held = (current_date_obj - buy_date).days
                
                if days_held >= request.hold_days:
                    # Force sell
                    sell_price = current_price
                    profit = (sell_price - position['buy_price']) * position['shares']
                    capital += sell_price * position['shares']
                    
                    return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                    
                    trade = BacktestTrade(
                        trade_id=trade_id,
                        buy_date=position['buy_date'],
                        buy_price=position['buy_price'],
                        sell_date=current_date,
                        sell_price=sell_price,
                        shares=position['shares'],
                        profit=profit,
                        return_rate=return_rate * 100,
                        signal_type=f"RSI超卖(持有到期, RSI: {position['rsi_value']:.1f})",
                        hold_days=days_held
                    )
                    trades.append(trade)
                    trade_id += 1
                    position = None
        
        # Close any remaining position at the end
        if position is not None:
            final_price = df.iloc[-1]['close']
            final_date = df.iloc[-1]['date'].strftime('%Y-%m-%d')
            final_rsi = df.iloc[-1]['rsi'] if pd.notna(df.iloc[-1]['rsi']) else None
            profit = (final_price - position['buy_price']) * position['shares']
            capital += final_price * position['shares']
            
            buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
            sell_date = datetime.strptime(final_date, '%Y-%m-%d')
            hold_days = (sell_date - buy_date).days
            return_rate = (final_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
            
            rsi_info = f", RSI: {final_rsi:.1f}" if final_rsi is not None else ""
            trade = BacktestTrade(
                trade_id=trade_id,
                buy_date=position['buy_date'],
                buy_price=position['buy_price'],
                sell_date=final_date,
                sell_price=final_price,
                shares=position['shares'],
                profit=profit,
                return_rate=return_rate * 100,
                signal_type=f"RSI超卖(回测结束{rsi_info})",
                hold_days=hold_days
            )
            trades.append(trade)
        
        # Calculate equity curve
        equity_curve = self._calculate_equity_curve(
            trades, request.initial_capital, request.start_date, request.end_date
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            trades, request.initial_capital, equity_curve,
            request.start_date, request.end_date
        )
        
        result = BacktestResult(
            stock_code=request.stock_code,
            stock_name=None,
            backtest_period=f"{request.start_date} to {request.end_date}",
            strategy_type=request.strategy_type,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve
        )
        
        logger.info(f"RSI backtest completed: {len(trades)} trades, "
                   f"total return: {metrics.total_return_rate:.2f}%")
        
        return result
    
    async def backtest_macd_strategy(
        self,
        request: BacktestRequest
    ) -> BacktestResult:
        """Backtest a MACD (Moving Average Convergence Divergence) strategy.
        
        This strategy buys when MACD crosses above signal line (golden cross)
        and sells when MACD crosses below signal line (death cross).
        
        Args:
            request: Backtest request parameters
            
        Returns:
            BacktestResult with performance metrics and trade history
        """
        logger.info(f"Starting MACD backtest for {request.stock_code} "
                   f"({request.start_date} to {request.end_date})")
        
        # Get stock data
        df = self.financial_agent.get_stock_data(
            request.stock_code,
            request.start_date,
            request.end_date
        )
        
        if df.empty:
            raise ValueError(f"无法获取股票 {request.stock_code} 的数据")
        
        # Calculate technical indicators
        df = self.financial_agent.calculate_technical_indicators(df)
        
        # Check if we have enough data for MACD calculation
        if len(df) < 30:
            logger.warning(f"Insufficient data for MACD strategy: {len(df)} data points (need at least 30)")
            # Return empty result
            empty_metrics = BacktestMetrics(
                initial_capital=request.initial_capital,
                final_capital=request.initial_capital,
                total_return=0.0,
                total_return_rate=0.0,
                annualized_return_rate=None,
                total_trades=0,
                successful_trades=0,
                failed_trades=0,
                win_rate=0.0,
                average_profit=0.0,
                max_profit=0.0,
                max_loss=0.0,
                max_drawdown=0.0,
                sharpe_ratio=None,
                profit_factor=None
            )
            return BacktestResult(
                stock_code=request.stock_code,
                stock_name=None,
                backtest_period=f"{request.start_date} to {request.end_date}",
                strategy_type=request.strategy_type,
                metrics=empty_metrics,
                trades=[],
                equity_curve=None
            )
        
        # Execute MACD strategy
        trades = []
        capital = request.initial_capital
        position = None  # Current position: {buy_date, buy_price, shares, macd_value}
        trade_id = 1
        
        for i in range(1, len(df)):  # Start from index 1 to compare with previous
            current_row = df.iloc[i]
            prev_row = df.iloc[i-1]
            current_date = current_row['date'].strftime('%Y-%m-%d')
            current_price = current_row['close']
            current_macd = current_row['macd']
            current_signal = current_row['macd_signal']
            prev_macd = prev_row['macd']
            prev_signal = prev_row['macd_signal']
            
            # Skip if MACD values are not available
            if pd.isna(current_macd) or pd.isna(current_signal):
                continue
            if pd.isna(prev_macd) or pd.isna(prev_signal):
                continue
            
            # Golden cross: MACD crosses above signal line (buy signal)
            if (current_macd > current_signal and 
                prev_macd <= prev_signal and 
                position is None):
                # Buy signal
                shares = (request.shares_per_trade // 100) * 100
                cost = current_price * shares
                
                if capital >= cost:
                    position = {
                        'buy_date': current_date,
                        'buy_price': current_price,
                        'shares': shares,
                        'macd_value': current_macd
                    }
                    capital -= cost
                    logger.info(f"MACD golden cross buy: {current_date} @ {current_price:.2f}, "
                               f"MACD: {current_macd:.4f}, Signal: {current_signal:.4f}, shares: {shares}")
            
            # Death cross: MACD crosses below signal line (sell signal)
            elif (current_macd < current_signal and 
                  prev_macd >= prev_signal and 
                  position is not None):
                # Sell signal
                sell_price = current_price
                profit = (sell_price - position['buy_price']) * position['shares']
                capital += sell_price * position['shares']
                
                # Calculate hold days
                buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                sell_date = datetime.strptime(current_date, '%Y-%m-%d')
                hold_days = (sell_date - buy_date).days
                
                # Calculate return rate
                return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                
                trade = BacktestTrade(
                    trade_id=trade_id,
                    buy_date=position['buy_date'],
                    buy_price=position['buy_price'],
                    sell_date=current_date,
                    sell_price=sell_price,
                    shares=position['shares'],
                    profit=profit,
                    return_rate=return_rate * 100,
                    signal_type=f"MACD死叉(MACD: {current_macd:.4f})",
                    hold_days=hold_days
                )
                trades.append(trade)
                trade_id += 1
                
                logger.info(f"MACD death cross sell: {current_date} @ {sell_price:.2f}, "
                           f"MACD: {current_macd:.4f}, Signal: {current_signal:.4f}, profit: {profit:.2f}")
                position = None
            
            # Check hold_days constraint
            if position is not None and request.hold_days is not None:
                buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
                current_date_obj = datetime.strptime(current_date, '%Y-%m-%d')
                days_held = (current_date_obj - buy_date).days
                
                if days_held >= request.hold_days:
                    # Force sell
                    sell_price = current_price
                    profit = (sell_price - position['buy_price']) * position['shares']
                    capital += sell_price * position['shares']
                    
                    return_rate = (sell_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
                    
                    trade = BacktestTrade(
                        trade_id=trade_id,
                        buy_date=position['buy_date'],
                        buy_price=position['buy_price'],
                        sell_date=current_date,
                        sell_price=sell_price,
                        shares=position['shares'],
                        profit=profit,
                        return_rate=return_rate * 100,
                        signal_type=f"MACD金叉(持有到期, MACD: {position['macd_value']:.4f})",
                        hold_days=days_held
                    )
                    trades.append(trade)
                    trade_id += 1
                    position = None
        
        # Close any remaining position at the end
        if position is not None:
            final_price = df.iloc[-1]['close']
            final_date = df.iloc[-1]['date'].strftime('%Y-%m-%d')
            final_macd = df.iloc[-1]['macd'] if pd.notna(df.iloc[-1]['macd']) else None
            profit = (final_price - position['buy_price']) * position['shares']
            capital += final_price * position['shares']
            
            buy_date = datetime.strptime(position['buy_date'], '%Y-%m-%d')
            sell_date = datetime.strptime(final_date, '%Y-%m-%d')
            hold_days = (sell_date - buy_date).days
            return_rate = (final_price - position['buy_price']) / position['buy_price'] if position['buy_price'] > 0 else 0.0
            
            macd_info = f", MACD: {final_macd:.4f}" if final_macd is not None else ""
            trade = BacktestTrade(
                trade_id=trade_id,
                buy_date=position['buy_date'],
                buy_price=position['buy_price'],
                sell_date=final_date,
                sell_price=final_price,
                shares=position['shares'],
                profit=profit,
                return_rate=return_rate * 100,
                signal_type=f"MACD金叉(回测结束{macd_info})",
                hold_days=hold_days
            )
            trades.append(trade)
            logger.info(f"SELL (end of backtest): {final_date} @ {final_price:.2f}, "
                       f"buy_date: {position['buy_date']}, profit: {profit:.2f}, return: {return_rate*100:.2f}%")
        else:
            logger.info("No open position at end of backtest")
        
        # Calculate equity curve
        equity_curve = self._calculate_equity_curve(
            trades, request.initial_capital, request.start_date, request.end_date
        )
        
        # Calculate metrics
        metrics = self._calculate_metrics(
            trades, request.initial_capital, equity_curve,
            request.start_date, request.end_date
        )
        
        result = BacktestResult(
            stock_code=request.stock_code,
            stock_name=None,
            backtest_period=f"{request.start_date} to {request.end_date}",
            strategy_type=request.strategy_type,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve
        )
        
        logger.info(f"MACD backtest completed: {len(trades)} trades, "
                   f"total return: {metrics.total_return_rate:.2f}%")
        
        return result

