# 金融量化 Agent 模块技术文档

## 📋 目录

- [概述](#概述)
- [架构设计](#架构设计)
- [核心模块](#核心模块)
  - [FinancialAgent](#financialagent-金融分析智能体)
  - [StrategyBacktest](#strategybacktest-策略回测引擎)
  - [StockPrediction](#stockprediction-机器学习预测引擎)
- [算法实现](#算法实现)
  - [技术指标计算](#技术指标计算)
  - [交易信号检测](#交易信号检测)
  - [动态信号强度计算](#动态信号强度计算)
  - [策略回测算法](#策略回测算法)
  - [机器学习预测算法](#机器学习预测算法)
- [创新点](#创新点)
- [Agent 实现机制](#agent-实现机制)
- [API 接口](#api-接口)
- [使用示例](#使用示例)

---

## 概述

金融量化 Agent 模块是一个基于 LLM（大语言模型）的智能金融分析系统，结合传统量化分析技术与现代 AI 能力，提供股票分析、交易信号生成和策略回测功能。

### 核心特性

- 🤖 **AI 驱动的分析**：使用 LLM 生成专业的投资建议和风险评估
- 📊 **多维度技术分析**：支持 MA、RSI、MACD、Bollinger Bands 等多种技术指标
- 🎯 **动态信号强度**：基于指标偏离度、趋势一致性等动态计算信号强度
- 🔄 **策略回测引擎**：支持多种交易策略的历史回测
- 📈 **股票推荐系统**：基于多因子评分模型的智能股票推荐
- 🧠 **机器学习预测**：使用多种 ML 模型预测股票未来价格走势

---

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Backend                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────┐      ┌──────────────────────┐      │
│  │ FinancialAgent   │      │ StrategyBacktest    │      │
│  │                  │      │                      │      │
│  │ - 数据获取        │      │ - 信号回测策略        │      │
│  │ - 指标计算        │◄────►│ - MA交叉策略         │      │
│  │ - 信号检测        │      │ - RSI策略           │      │
│  │ - LLM分析        │      │ - 性能评估           │      │
│  └──────────────────┘      └──────────────────────┘      │
│           │                          │                     │
│           │                          │                     │
│  ┌────────▼──────────────────────────┐                    │
│  │ StockPrediction                  │                    │
│  │                                  │                    │
│  │ - 特征工程                        │                    │
│  │ - ML模型训练                      │                    │
│  │ - 价格预测                        │                    │
│  └──────────────────────────────────┘                    │
│           │                          │                     │
│           └──────────┬───────────────┘                     │
│                      │                                     │
│           ┌──────────▼──────────┐                         │
│           │   Data Models       │                         │
│           │  (Pydantic)         │                         │
│           └─────────────────────┘                         │
│                                                           │
└─────────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│              External Data Sources                        │
│  - akshare (股票数据)                                     │
│  - OpenRouter LLM API                                    │
└─────────────────────────────────────────────────────────┘
```

---

## 核心模块

### FinancialAgent - 金融分析智能体

`FinancialAgent` 是系统的核心智能体，负责股票数据的获取、技术指标计算、交易信号生成和 AI 驱动的综合分析。

#### 1. 初始化与 LLM 集成

```python
class FinancialAgent:
    def __init__(self):
        # 使用 mira 库集成 OpenRouter LLM
        llm_args = OpenAIArgs(
            api_key=settings.get_api_key(),
            base_url=settings.get_base_url(),
            model=settings.model,
            temperature=0.7,
            max_completion_tokens=4000
        )
        self.llm = OpenRouterLLM(args=llm_args)
```

**设计亮点**：
- 使用 `mira` 库统一 LLM 接口，支持多种模型提供商
- 通过配置文件管理 API 密钥和模型参数
- 设置请求延迟避免 API 限流

#### 2. 数据获取模块

```python
def get_stock_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用 akshare 获取股票历史数据
    
    特性：
    - 指数退避重试机制（最多3次）
    - 前复权数据处理
    - 数据验证和清洗
    """
```

**算法特点**：
- **重试策略**：指数退避（`wait_time = delay * (2 ** attempt)`）
- **数据标准化**：统一列名为英文，便于后续处理
- **容错处理**：检查必需列，处理空数据

#### 3. 技术指标计算

```python
def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
    """计算多种技术指标"""
    
    # 移动平均线（MA）
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma10'] = df['close'].rolling(window=10).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    df['ma30'] = df['close'].rolling(window=30).mean()
    df['ma60'] = df['close'].rolling(window=60).mean()
    
    # RSI（相对强弱指标）
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # MACD（指数平滑移动平均线）
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['macd_signal']
    
    # 布林带（Bollinger Bands）
    df['bollinger_middle'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['bollinger_upper'] = df['bollinger_middle'] + (std * 2)
    df['bollinger_lower'] = df['bollinger_middle'] - (std * 2)
```

**指标说明**：
- **MA（移动平均线）**：平滑价格波动，识别趋势
- **RSI（相对强弱指标）**：0-100，<30 超卖，>70 超买
- **MACD**：趋势跟踪指标，金叉/死叉信号
- **Bollinger Bands**：波动性指标，识别价格突破

---

### StrategyBacktest - 策略回测引擎

`StrategyBacktest` 提供完整的策略回测功能，支持多种交易策略的历史模拟。

#### 支持的策略类型

1. **signal_based**：基于综合交易信号的策略（多指标综合）
2. **ma_cross**：均线交叉策略（MA5 与 MA30 金叉/死叉）
3. **rsi**：RSI 超买超卖策略（RSI < 30 买入，RSI > 70 卖出）
4. **macd**：MACD 交叉策略（MACD 上穿/下穿信号线）

#### 回测流程

```python
async def backtest_signal_based_strategy(self, request: BacktestRequest) -> BacktestResult:
    """
    回测流程：
    1. 获取历史数据
    2. 计算技术指标
    3. 检测交易信号（扫描整个历史期间）
    4. 过滤信号（按类型和强度）
    5. 模拟交易执行
    6. 计算性能指标
    7. 生成权益曲线
    """
```

#### 回测专用信号检测

**关键创新**：`detect_trading_signals_for_backtest` 方法

传统方法只检测最后一天，回测需要扫描整个历史期间：

```python
def detect_trading_signals_for_backtest(self, df: pd.DataFrame, window: int = 5) -> list:
    """
    扫描整个历史数据期间，检测每一天的信号
    
    与 detect_trading_signals 的区别：
    - detect_trading_signals: 只检测最后一天（用于实时分析）
    - detect_trading_signals_for_backtest: 扫描所有历史日期（用于回测）
    """
    all_signals = []
    
    # 从第30天开始扫描（确保技术指标已计算）
    for i in range(30, len(df)):
        current_row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # 检测 MA 交叉、RSI、MACD 信号
        # 使用到当前日期的历史数据计算信号强度
        day_signals = detect_signals_for_day(...)
        all_signals.extend(day_signals)
    
    return all_signals
```

**优势**：
- 完整覆盖：检测回测期间的所有信号
- 历史上下文：使用到当前日期的历史数据计算强度
- 准确性：避免遗漏历史信号

---

### StockPrediction - 机器学习预测引擎

`StockPrediction` 使用机器学习模型预测股票未来价格走势，支持多种回归算法和特征工程。

#### 支持的模型类型

1. **linear**：线性回归（简单快速）
2. **ridge**：Ridge 回归（L2 正则化，防止过拟合）
3. **lasso**：Lasso 回归（L1 正则化，特征选择）
4. **random_forest**：随机森林回归（非线性，特征重要性）
5. **gradient_boosting**：梯度提升回归（强非线性拟合）
6. **ensemble**：集成模型（投票回归器，结合多个模型）

#### 预测流程

```python
async def predict_stock_price(self, request: PredictionRequest) -> PredictionResult:
    """
    预测流程：
    1. 获取历史数据
    2. 计算技术指标
    3. 特征工程（价格、成交量、技术指标特征）
    4. 数据预处理（标准化、缺失值处理）
    5. 模型训练（80% 训练，20% 验证）
    6. 模型评估（MAE、RMSE、R²）
    7. 滚动预测未来 N 天价格
    8. 计算置信区间和置信度
    """
```

---

## 算法实现

### 技术指标计算

#### RSI 计算算法

```python
# RSI 计算公式
delta = close.diff()                    # 价格变化
gain = (delta > 0) * delta              # 上涨幅度
loss = -(delta < 0) * delta             # 下跌幅度

# 14 日平均
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()

# RSI 值
RS = avg_gain / avg_loss
RSI = 100 - (100 / (1 + RS))
```

**特点**：
- 使用 `pandas` 的 `rolling` 和 `where` 方法高效计算
- 处理边界情况（除零、NaN 值）

#### MACD 计算算法

```python
# MACD 使用指数移动平均（EMA）
EMA12 = close.ewm(span=12, adjust=False).mean()
EMA26 = close.ewm(span=26, adjust=False).mean()

MACD = EMA12 - EMA26
Signal = MACD.ewm(span=9, adjust=False).mean()
Histogram = MACD - Signal
```

**优势**：
- EMA 对近期价格更敏感，反应更快
- Histogram 提供动量信息

---

### 交易信号检测

#### 信号检测架构

```python
def detect_trading_signals(self, df: pd.DataFrame, window: int = 5) -> list:
    """
    信号检测层次：
    1. MA 交叉信号（金叉/死叉）
    2. RSI 超买超卖信号（含背离检测）
    3. MACD 交叉信号（含柱状图确认）
    4. Hold 信号（无明确信号时）
    """
```

#### 1. MA 交叉信号

```python
# 金叉：MA5 上穿 MA30
if latest['ma5'] > latest['ma30'] and prev['ma5'] <= prev['ma30']:
    # 计算动态强度
    base_strength = 0.6
    cross_strength = self._calculate_ma_cross_strength(df, window)
    final_strength = (base_strength + cross_strength) / 2
    
    # 成交量确认
    if latest['volume'] > avg_volume * 1.2:
        reason_parts.append('成交量放大')
```

**创新点**：
- 不仅检测交叉，还考虑成交量确认
- 动态计算信号强度，而非固定值

#### 2. RSI 信号（含背离检测）

```python
# 检测 RSI 背离
def _check_rsi_divergence(self, df: pd.DataFrame, window: int = 5):
    """
    背离检测：
    - 看涨背离：价格下跌但 RSI 上升
    - 看跌背离：价格上涨但 RSI 下降
    """
    price_change = (recent['close'].iloc[-1] - recent['close'].iloc[0]) / recent['close'].iloc[0]
    rsi_change = recent['rsi'].iloc[-1] - recent['rsi'].iloc[0]
    
    # 看涨背离
    if price_change < -0.02 and rsi_change > 5:
        return True, "bullish"
```

**创新点**：
- **背离检测**：识别价格与指标的背离，提高信号可靠性
- **动态强度调整**：检测到背离时，信号强度提升 0.15

#### 3. Hold 信号生成

```python
# 当无明确买卖信号时，生成 Hold 信号
if not signals:
    hold_strength = 0.5
    
    # 检查均线粘合
    if separation < 0.02:
        hold_strength = 0.6
        hold_reason_parts.append('均线粘合，方向不明')
    
    # 检查趋势冲突
    if short_trend != medium_trend:
        hold_strength = 0.6
        hold_reason_parts.append('短期与中期趋势不一致')
```

**设计理念**：
- **明确职责**：Signal 层只产生信号，不负责最终决策
- **Hold 信号**：明确表达"无明确方向"的状态，而非缺失信号

---

### 动态信号强度计算

#### 核心创新：从硬编码到动态计算

传统方法：
```python
# ❌ 硬编码
signal_strength = 0.7  # 固定值
```

本系统方法：
```python
# ✅ 动态计算
signal_strength = f(rsi_value, volume_confirmation, trend_consistency, ...)
```

#### RSI 信号强度算法

```python
def _calculate_rsi_signal_strength(self, rsi_value: float, signal_type: str) -> float:
    """
    基于 RSI 偏离度计算强度：
    - RSI < 20: 0.9（极度超卖）
    - RSI < 25: 0.8
    - RSI < 30: 0.6 + (30 - rsi) / 10 * 0.2  # 线性插值
    """
    if signal_type == 'buy':
        if rsi_value < 20:
            return 0.9
        elif rsi_value < 25:
            return 0.8
        elif rsi_value < 30:
            # 线性插值：RSI 越低，强度越高
            return 0.6 + (30 - rsi_value) / 10 * 0.2
```

**优势**：
- **可学习性**：强度值可作为机器学习特征
- **连续性**：提供更细粒度的信号强度
- **可组合性**：多个信号可叠加计算

#### MA 交叉强度算法

```python
def _calculate_ma_cross_strength(self, df: pd.DataFrame, window: int = 5) -> float:
    """
    综合考虑：
    1. 成交量确认（+0.15 if volume > 1.2x avg）
    2. 价格动量（+0.1 if price_move > 2%）
    3. MA 分离度（+0.1 if separation > 5%）
    """
    strength = 0.5  # 基础强度
    
    # 成交量确认
    if latest['volume'] > avg_volume * 1.2:
        strength += 0.15
    
    # 价格趋势
    if abs(price_trend) > 0.02:
        strength += 0.1
    
    # MA 分离度
    separation = abs(ma5 - ma30) / ma30
    if separation > 0.05:
        strength += 0.1
    
    return min(strength, 1.0)
```

**多因子模型**：
- 结合成交量、价格动量、指标分离度
- 提供更可靠的信号强度评估

---

### 策略回测算法

#### 回测执行流程

```python
async def backtest_signal_based_strategy(self, request: BacktestRequest):
    # 1. 获取历史数据
    df = self.financial_agent.get_stock_data(...)
    
    # 2. 计算技术指标
    df = self.financial_agent.calculate_technical_indicators(df)
    
    # 3. 检测交易信号（扫描整个历史期间）
    signal_data = self.financial_agent.detect_trading_signals_for_backtest(df)
    
    # 4. 过滤信号（按类型和强度）
    signal_types_filter = request.signal_types or ['buy', 'sell']
    min_strength = request.min_signal_strength
    
    eligible_signals = [
        s for s in signal_data
        if s.get('signal_type') in signal_types_filter
        and s.get('signal_strength', 0) >= min_strength
    ]
    
    # 5. 模拟交易执行
    for i in range(len(df)):
        current_date = df.iloc[i]['date'].strftime('%Y-%m-%d')
        current_price = df.iloc[i]['close']
        
        # 匹配当天的信号
        day_signals = [
            s for s in eligible_signals
            if s.get('signal_date') == current_date
        ]
        
        # 处理买入信号
        if signal_type == 'buy' and position is None:
            shares = (request.shares_per_trade // 100) * 100  # 100股整数倍
            cost = current_price * shares
            if capital >= cost:
                position = {
                    'buy_date': current_date,
                    'buy_price': current_price,
                    'shares': shares
                }
                capital -= cost
        
        # 处理卖出信号
        elif signal_type == 'sell' and position is not None:
            profit = (current_price - position['buy_price']) * position['shares']
            capital += current_price * position['shares']
            trades.append(BacktestTrade(...))
            position = None
        
        # 检查持有天数限制
        if position and request.hold_days:
            if days_held >= request.hold_days:
                # 强制平仓
                ...
    
    # 6. 回测结束时平仓未平仓持仓
    if position is not None:
        # 使用最后一天价格强制平仓
        ...
    
    # 7. 计算性能指标
    metrics = self._calculate_metrics(trades, initial_capital, equity_curve)
```

#### 信号过滤机制

```python
# 多维度过滤
eligible_signals = [
    s for s in signal_data
    if s.get('signal_type') in signal_types_filter  # 类型过滤
    and s.get('signal_strength', 0) >= min_strength  # 强度过滤
]

# 调试信息
logger.info(f"Signal strength stats: min={min(strengths):.2f}, "
           f"max={max(strengths):.2f}, mean={mean(strengths):.2f}")
logger.info(f"Signal strength distribution: {strength_distribution}")
```

**过滤维度**：
- **信号类型**：buy、sell、hold
- **信号强度**：0.0-1.0，可设置最小阈值
- **日期匹配**：确保信号日期与数据日期一致

---

### 机器学习预测算法

#### 特征工程

**核心创新**：多维度特征提取

```python
def _prepare_features(self, df: pd.DataFrame, use_technical_indicators: bool = True):
    """
    特征工程包括：
    1. 价格特征
    2. 成交量特征
    3. 技术指标特征
    4. 滞后特征
    """
    # 1. 价格特征
    features_df['price_change'] = df['close'].pct_change()
    features_df['price_change_2'] = df['close'].pct_change(periods=2)
    features_df['price_change_5'] = df['close'].pct_change(periods=5)
    
    # 2. 成交量特征
    features_df['volume_change'] = df['volume'].pct_change()
    features_df['volume_ratio'] = df['volume'] / df['volume'].rolling(5).mean()
    
    # 3. 价格位置特征
    features_df['high_low_ratio'] = df['high'] / df['low']
    features_df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
    
    # 4. 技术指标特征（如果启用）
    if use_technical_indicators:
        # MA 特征
        features_df['ma5_ratio'] = df['close'] / df['ma5']
        features_df['ma5_slope'] = df['ma5'].diff()
        features_df['ma5_ma30_diff'] = (df['ma5'] - df['ma30']) / df['ma30']
        
        # RSI 特征（归一化到 -1 到 1）
        features_df['rsi_normalized'] = (df['rsi'] - 50) / 50
        
        # MACD 特征
        features_df['macd_diff'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands 特征
        features_df['bb_width'] = (df['bollinger_upper'] - df['bollinger_lower']) / df['bollinger_middle']
        features_df['bb_position'] = (df['close'] - df['bollinger_lower']) / (df['bollinger_upper'] - df['bollinger_lower'])
    
    # 5. 滞后特征（捕捉时间序列模式）
    features_df['close_lag1'] = df['close'].shift(1)
    features_df['close_lag2'] = df['close'].shift(2)
    features_df['close_lag3'] = df['close'].shift(3)
    
    return features_df
```

**特征类别**：
- **价格特征**：价格变化率（1日、2日、5日）
- **成交量特征**：成交量变化、成交量比率
- **位置特征**：高低比、收盘价在当日区间的位置
- **技术指标特征**：MA 比率、MA 斜率、RSI 归一化、MACD 差值、BB 宽度和位置
- **滞后特征**：前 1-3 天的收盘价（捕捉时间序列依赖）

#### 模型训练与评估

```python
# 1. 数据划分（80% 训练，20% 验证）
split_idx = int(len(X) * 0.8)
X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_val = y[:split_idx], y[split_idx:]

# 2. 特征标准化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_val_scaled = scaler.transform(X_val)

# 3. 模型训练
model = self._create_model(request.model_type)
model.fit(X_train_scaled, y_train)

# 4. 模型评估
y_val_pred = model.predict(X_val_scaled)
val_mae = mean_absolute_error(y_val, y_val_pred)
val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
val_r2 = r2_score(y_val, y_val_pred)
```

**评估指标**：
- **MAE（平均绝对误差）**：预测误差的平均值
- **RMSE（均方根误差）**：对大误差更敏感
- **R²（决定系数）**：模型解释的方差比例（0-1，越高越好）

#### 滚动预测机制

```python
# 预测未来 N 天
for day in range(1, prediction_days + 1):
    # 1. 使用当前特征预测下一天价格
    predicted_price = model.predict(current_features_scaled)[0]
    
    # 2. 计算置信区间
    lower, upper = self._calculate_confidence_interval(
        np.array([predicted_price]),
        residuals  # 使用训练残差计算标准误差
    )
    
    # 3. 计算预测置信度
    # 置信度随预测天数增加而降低
    confidence = max(0.3, 1.0 - (price_change_pct * 2) - (day / prediction_days * 0.3))
    
    # 4. 更新特征用于下一次预测
    current_features['close_lag1'] = predicted_price
    current_features['price_change'] = (predicted_price - prev_price) / prev_price
    # ... 更新其他特征
```

**预测特点**：
- **滚动预测**：使用预测值更新特征，逐日预测
- **置信区间**：基于训练残差的标准误差计算 95% 置信区间
- **置信度衰减**：预测天数越远，置信度越低

#### 置信区间计算

```python
def _calculate_confidence_interval(self, predictions, residuals, alpha=0.05):
    """
    计算 95% 置信区间：
    - 使用训练残差的标准误差
    - 假设误差服从正态分布
    - z_score = 1.96 (95% CI)
    """
    std_error = np.std(residuals)
    z_score = 1.96
    
    lower = predictions - z_score * std_error
    upper = predictions + z_score * std_error
    
    return lower, upper
```

#### 特征重要性分析

```python
# 对于树模型（随机森林、梯度提升）
if hasattr(model, 'feature_importances_'):
    feature_importance = dict(zip(feature_names, model.feature_importances_))

# 对于线性模型
elif hasattr(model, 'coef_'):
    coef_abs = np.abs(model.coef_)
    feature_importance = dict(zip(feature_names, coef_abs / coef_abs.sum()))
```

**用途**：
- 识别最重要的特征
- 特征选择优化
- 模型可解释性

#### 性能指标计算

```python
def _calculate_metrics(self, trades, initial_capital, equity_curve):
    """
    计算指标：
    - 总收益率
    - 年化收益率
    - 胜率
    - 最大回撤
    - Sharpe 比率
    - 盈亏比（Profit Factor）
    """
    # 总收益率
    total_return_rate = (final_capital - initial_capital) / initial_capital * 100
    
    # 年化收益率
    years = days / 365.25
    annualized_return = ((final_capital / initial_capital) ** (1 / years) - 1) * 100
    
    # 胜率
    win_rate = successful_trades / total_trades
    
    # 最大回撤
    max_drawdown = self._calculate_max_drawdown(equity_curve)
    
    # Sharpe 比率
    sharpe_ratio = (annualized_return - risk_free_rate) / annualized_std
    
    # 盈亏比
    profit_factor = total_profit / abs(total_loss)
```

#### 权益曲线计算

```python
def _calculate_equity_curve(self, trades, initial_capital, start_date, end_date):
    """
    生成每日权益曲线：
    1. 创建日期范围
    2. 按日期分组交易
    3. 逐日计算资本变化
    """
    date_range = pd.date_range(start=start, end=end, freq='D')
    current_capital = initial_capital
    
    # 按日期分组交易
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
    
    # 逐日计算资本变化
    for date in date_range:
        if date in trades_by_date:
            # 应用买入交易
            for trade in trades_by_date[date].get('buy', []):
                current_capital -= trade.buy_price * trade.shares
            
            # 应用卖出交易
            for trade in trades_by_date[date].get('sell', []):
                current_capital += trade.sell_price * trade.shares
        
        equity_curve.append({
            'date': date.strftime('%Y-%m-%d'),
            'capital': current_capital
        })
    
    return equity_curve
```

#### 回测调试与诊断

系统提供详细的调试信息，帮助诊断回测问题：

```python
# 信号检测统计
logger.info(f"Detected {len(signal_data)} trading signals")
logger.info(f"Signal breakdown: {len(buy_signals)} buy, "
           f"{len(sell_signals)} sell, {len(hold_signals)} hold")

# 信号强度统计
logger.info(f"Signal strength stats: min={min(strengths):.2f}, "
           f"max={max(strengths):.2f}, mean={mean(strengths):.2f}")

# 信号过滤统计
logger.info(f"After filtering: {len(eligible_signals)}/{len(signal_data)} signals eligible")
logger.info(f"Signal strength distribution: {strength_distribution}")

# 交易执行日志
logger.info(f"BUY: {date} @ {price:.2f}, shares: {shares}")
logger.info(f"SELL: {date} @ {price:.2f}, profit: {profit:.2f}")
```

**调试信息包括**：
- 信号检测数量与类型分布
- 信号强度统计（最小值、最大值、平均值、中位数）
- 信号强度分布（按区间统计）
- 过滤后的可用信号数量
- 每笔交易的详细信息

---

## 创新点

### 1. 动态信号强度计算

**传统方法**：硬编码信号强度（如 0.6、0.7）

**本系统**：
- 基于指标偏离度动态计算（RSI 距离阈值越远，强度越高）
- 考虑成交量确认、趋势一致性等多因子
- 支持信号叠加和归一化

**优势**：
- 信号强度可作为机器学习特征
- 提供更细粒度的信号评估
- 便于策略优化和参数调优

### 2. 窗口化信号检测

**传统方法**：仅基于最后一天的数据判断

**本系统**：
- 使用滑动窗口（默认 5 天）检查趋势一致性
- 检测 RSI 背离（价格与指标反向运动）
- 考虑短期与中期趋势的冲突

**优势**：
- 减少假信号
- 提高信号稳定性
- 更适合回测场景

### 3. 分层信号架构

```
Indicators → Signals → Strategy → Backtest → ML
```

**设计理念**：
- **Signal 层**：只产生信号，不负责最终决策
- **Strategy 层**：基于信号制定交易策略
- **Backtest 层**：评估策略性能
- **ML 层**（未来）：学习信号有效性

**优势**：
- 职责清晰，易于扩展
- 信号可复用
- 便于 A/B 测试

### 4. AI 驱动的综合分析

```python
async def generate_overall_assessment(self, ...):
    """
    使用 LLM 生成：
    1. 综合评估（200-300字）
    2. 投资建议（买入/持有/卖出）
    3. 风险评估
    4. 置信度评分
    """
    assessment_prompt = f"""
    基于以下股票分析数据，生成综合评估和投资建议。
    
    价格统计: ...
    技术指标: ...
    交易信号: ...
    风险指标: ...
    """
    
    response = await self.llm.forward(messages=[...])
```

**创新点**：
- 结合量化分析与自然语言生成
- 提供可解释的投资建议
- 动态置信度评分

### 5. 多策略回测引擎

支持四种策略类型：
- **signal_based**：综合信号策略（多指标综合，动态强度）
- **ma_cross**：均线交叉策略（MA5 与 MA30 金叉/死叉）
- **rsi**：RSI 超买超卖策略（RSI < 30 买入，RSI > 70 卖出）
- **macd**：MACD 交叉策略（MACD 上穿/下穿信号线）

**统一接口**：
```python
if strategy_type == "signal_based":
    result = await backtest_engine.backtest_signal_based_strategy(request)
elif strategy_type == "ma_cross":
    result = await backtest_engine.backtest_ma_cross_strategy(request)
elif strategy_type == "rsi":
    result = await backtest_engine.backtest_rsi_strategy(request)
elif strategy_type == "macd":
    result = await backtest_engine.backtest_macd_strategy(request)
```

**策略特点**：

| 策略类型 | 买入条件 | 卖出条件 | 特点 |
|---------|---------|---------|------|
| signal_based | 综合信号（MA/RSI/MACD） | 综合信号 | 多指标综合，动态强度 |
| ma_cross | MA5 上穿 MA30 | MA5 下穿 MA30 | 趋势跟踪，适合趋势市场 |
| rsi | RSI < 30（超卖） | RSI > 70（超买） | 反转策略，适合震荡市场 |
| macd | MACD 上穿信号线 | MACD 下穿信号线 | 动量指标，确认趋势 |

**优势**：
- 易于添加新策略
- 统一的性能评估标准
- 支持策略对比
- 每种策略都有独立的回测逻辑

### 6. 机器学习价格预测

**核心创新**：多模型集成预测系统

```python
class StockPrediction:
    """
    预测系统特点：
    1. 多维度特征工程（价格、成交量、技术指标）
    2. 多种 ML 模型支持
    3. 滚动预测机制
    4. 置信区间和置信度计算
    """
    
    def predict_stock_price(self, request: PredictionRequest):
        # 1. 特征工程
        features = self._prepare_features(df, use_technical_indicators=True)
        
        # 2. 模型训练
        model = self._create_model(request.model_type)
        model.fit(X_train, y_train)
        
        # 3. 滚动预测
        for day in range(1, prediction_days + 1):
            predicted_price = model.predict(current_features)
            # 更新特征用于下一次预测
            update_features(predicted_price)
        
        # 4. 返回预测结果
        return PredictionResult(...)
```

**创新点**：
- **多维度特征**：结合价格、成交量、技术指标
- **滚动预测**：使用预测值更新特征，逐日预测
- **置信区间**：提供预测的不确定性估计
- **多模型支持**：线性、树模型、集成模型

**优势**：
- 可解释性：特征重要性分析
- 灵活性：支持多种模型类型
- 实用性：提供置信区间和置信度

### 7. 智能股票推荐系统

```python
async def recommend_stocks(self, ...):
    """
    推荐流程：
    1. 批量分析股票
    2. 计算推荐评分（多因子模型）
    3. LLM 生成推荐理由
    4. LLM 生成对比总结
    """
    
    # 多因子评分
    score = (
        price_performance * 0.3 +
        trading_signals * 0.25 +
        trend_strength * 0.2 +
        risk_level * 0.15 +
        technical_indicators * 0.1
    )
```

**创新点**：
- 多因子评分模型
- LLM 生成个性化推荐理由
- 批量并发分析

---

## Agent 实现机制

### 1. LLM 集成架构

使用 `mira` 库统一 LLM 接口：

```python
from mira import HumanMessage, SystemMessage, OpenRouterLLM

# 初始化
llm = OpenRouterLLM(args=OpenAIArgs(...))

# 调用
response = await llm.forward(
    messages=[
        SystemMessage(content="你是一个专业的金融分析师..."),
        HumanMessage(content=prompt)
    ],
    tools=[],
    response_format=None,
    max_completion_tokens=2000
)
```

**优势**：
- 支持多种 LLM 提供商（OpenAI、Anthropic、OpenRouter 等）
- 统一的接口，易于切换模型
- 支持结构化输出（LLMJson）

### 2. 异步处理

```python
async def analyze_stock(self, stock_code, start_date, end_date):
    # 数据获取（同步）
    df = self.get_stock_data(...)
    
    # 指标计算（同步）
    df = self.calculate_technical_indicators(df)
    
    # LLM 分析（异步）
    assessment, confidence = await self.generate_overall_assessment(...)
```

**设计考虑**：
- 数据计算使用同步方法（CPU 密集型）
- LLM 调用使用异步方法（IO 密集型）
- 批量分析使用并发控制（`asyncio.Semaphore`）

### 3. 错误处理与容错

```python
# 数据获取重试
for attempt in range(max_retries):
    try:
        df = ak.stock_zh_a_hist(...)
        return df
    except Exception as e:
        if attempt < max_retries - 1:
            wait_time = delay * (2 ** attempt)  # 指数退避
            time.sleep(wait_time)

# LLM 调用容错
try:
    response = await self.llm.forward(...)
    return response
except Exception as e:
    logger.warning(f"LLM error: {e}")
    return fallback_assessment  # 返回备用结果
```

### 4. 数据模型设计

使用 Pydantic 定义结构化数据模型：

```python
class TradingSignal(BaseModel):
    signal_type: str  # buy, sell, hold
    signal_strength: float  # 0.0-1.0
    signal_reason: str
    signal_date: Optional[str]
    indicators_used: List[str]

class FinancialAnalysisResult(BaseModel):
    stock_code: str
    price_stats: PriceStatistics
    technical_indicators: TechnicalIndicators
    trading_signals: List[TradingSignal]
    risk_metrics: RiskMetrics
    trend_analysis: TrendAnalysis
    overall_assessment: str
    confidence_score: float
```

**优势**：
- 类型安全
- 自动验证
- API 文档生成（FastAPI）

---

## API 接口

### 1. 股票分析接口

```http
POST /api/v1/financial/analyze
Content-Type: application/json

{
  "stock_code": "000001",
  "start_date": "20240101",
  "end_date": "20241226"
}
```

**响应**：
```json
{
  "stock_code": "000001",
  "price_stats": {...},
  "technical_indicators": {...},
  "trading_signals": [...],
  "risk_metrics": {...},
  "overall_assessment": "...",
  "confidence_score": 0.85
}
```

### 2. 策略回测接口

```http
POST /api/v1/financial/backtest
Content-Type: application/json

{
  "stock_code": "000001",
  "start_date": "20240101",
  "end_date": "20241226",
  "strategy_type": "signal_based",
  "initial_capital": 100000.0,
  "shares_per_trade": 100,
  "min_signal_strength": 0.5,
  "hold_days": null
}
```

**响应**：
```json
{
  "stock_code": "000001",
  "strategy_type": "signal_based",
  "metrics": {
    "total_return_rate": 15.5,
    "win_rate": 0.65,
    "max_drawdown": 8.2,
    "sharpe_ratio": 1.2
  },
  "trades": [...],
  "equity_curve": [...]
}
```

### 3. 股票推荐接口

```http
POST /api/v1/financial/recommend
Content-Type: application/json

{
  "max_stocks": 10,
  "start_date": "20240101",
  "end_date": "20241226"
}
```

### 4. 股票价格预测接口

```http
POST /api/v1/financial/predict
Content-Type: application/json

{
  "stock_code": "000001",
  "start_date": "20240101",
  "end_date": "20241226",
  "prediction_days": 5,
  "model_type": "ensemble",
  "use_technical_indicators": true
}
```

**响应**：
```json
{
  "stock_code": "000001",
  "training_period": "20240101 to 20241226",
  "prediction_days": 5,
  "model_type": "ensemble",
  "model_accuracy": 0.85,
  "predictions": [
    {
      "date": "2024-12-27",
      "predicted_price": 12.50,
      "confidence_interval_lower": 12.20,
      "confidence_interval_upper": 12.80,
      "prediction_confidence": 0.85
    },
    ...
  ],
  "feature_importance": {
    "price_change": 0.15,
    "ma5_ratio": 0.12,
    "rsi_normalized": 0.10,
    ...
  }
}
```

**异步接口**：
```http
POST /api/v1/financial/predict/async
GET /api/v1/financial/predict/status/{task_id}
POST /api/v1/financial/predict/cancel/{task_id}
```

---

## 使用示例

### 基本股票分析

```python
from app.agent.financial_agent import FinancialAgent

agent = FinancialAgent()

# 分析股票
result = await agent.analyze_stock(
    stock_code="000001",
    start_date="20240101",
    end_date="20241226"
)

# 查看交易信号
for signal in result.trading_signals:
    print(f"{signal.signal_type}: {signal.signal_reason} (强度: {signal.signal_strength:.2f})")

# 查看 LLM 生成的评估
print(result.overall_assessment)
```

### 策略回测

```python
from app.agent.strategy_backtest import StrategyBacktest
from app.models import BacktestRequest

backtest = StrategyBacktest()

request = BacktestRequest(
    stock_code="000001",
    start_date="20240101",
    end_date="20241226",
    strategy_type="ma_cross",  # 可选: signal_based, ma_cross, rsi, macd
    initial_capital=100000.0,
    shares_per_trade=100,
    min_signal_strength=0.5,  # 信号强度阈值
    hold_days=None  # 持有天数限制（可选）
)

result = await backtest.backtest_ma_cross_strategy(request)

print(f"总收益率: {result.metrics.total_return_rate:.2f}%")
print(f"胜率: {result.metrics.win_rate:.2%}")
print(f"最大回撤: {result.metrics.max_drawdown:.2f}%")
```

### 股票推荐

```python
result = await agent.recommend_stocks(
    max_stocks=10,
    start_date="20240101",
    end_date="20241226"
)

for rec in result.recommendations:
    print(f"{rec.rank}. {rec.stock_name} ({rec.stock_code})")
    print(f"   评分: {rec.recommendation_score:.2f}")
    print(f"   理由: {rec.recommendation_reason}")
```

### 股票价格预测

```python
from app.agent.stock_prediction import StockPrediction
from app.models import PredictionRequest

prediction = StockPrediction()

request = PredictionRequest(
    stock_code="000001",
    start_date="20240101",
    end_date="20241226",
    prediction_days=5,
    model_type="ensemble",  # 可选: linear, ridge, lasso, random_forest, gradient_boosting, ensemble
    use_technical_indicators=True
)

result = await prediction.predict_stock_price(request)

print(f"模型准确度 (R²): {result.model_accuracy:.4f}")
print(f"特征重要性: {result.feature_importance}")

for pred in result.predictions:
    print(f"{pred.date}: 预测价格 {pred.predicted_price:.2f} "
          f"(置信区间: {pred.confidence_interval_lower:.2f} - {pred.confidence_interval_upper:.2f}, "
          f"置信度: {pred.prediction_confidence:.2%})")
```

---

## 技术栈

- **Python 3.8+**
- **pandas / numpy**：数据处理和计算
- **akshare**：股票数据获取
- **mira**：LLM 接口统一
- **scikit-learn**：机器学习模型（线性回归、随机森林、梯度提升等）
- **Pydantic**：数据模型和验证
- **FastAPI**：RESTful API
- **asyncio**：异步处理

---

## 未来扩展

1. **深度学习模型**：
   - LSTM/GRU 时间序列模型
   - Transformer 模型
   - 强化学习策略优化

2. **更多策略**：
   - 网格交易策略
   - 动量策略
   - 均值回归策略

3. **实时交易**：
   - 实时数据流处理
   - 实时信号生成
   - 自动交易执行

4. **组合优化**：
   - 多股票组合分析
   - 风险分散
   - 资产配置建议

5. **模型优化**：
   - 超参数自动调优
   - 模型集成优化
   - 在线学习（增量更新）

---

## 总结

本金融量化 Agent 模块通过结合传统量化分析技术与现代 AI 能力，实现了：

- ✅ **智能信号生成**：动态强度计算，多因子模型
- ✅ **策略回测**：完整的回测引擎，多策略支持
- ✅ **AI 驱动分析**：LLM 生成专业投资建议
- ✅ **机器学习预测**：多模型价格预测，置信区间估计
- ✅ **可扩展架构**：分层设计，易于扩展

系统设计遵循"信号 → 策略 → 回测 → 预测 → 学习"的完整流程，为量化交易提供了坚实的基础。

## 模块关系图

```
┌─────────────────────────────────────────────────────────┐
│                    FinancialAgent                        │
│  (数据获取、指标计算、信号检测、LLM分析)                    │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴────────┬──────────────────┐
       │                │                  │
       ▼                ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│StrategyBacktest│  │StockPrediction│  │Recommendation│
│                │  │                │  │              │
│- 信号回测      │  │- 特征工程      │  │- 多因子评分  │
│- MA交叉       │  │- ML模型训练    │  │- LLM推荐理由 │
│- RSI策略      │  │- 价格预测      │  │              │
│- MACD策略     │  │- 置信区间      │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

**数据流**：
1. `FinancialAgent` 提供数据和指标
2. `StrategyBacktest` 使用信号进行回测
3. `StockPrediction` 使用指标进行预测
4. `Recommendation` 综合分析和推荐

