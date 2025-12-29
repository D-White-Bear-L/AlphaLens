"""Stock price prediction module using machine learning."""
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

# Try to import sklearn, but make it optional
try:
    from sklearn.linear_model import LinearRegression, Ridge, Lasso
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed, StockPrediction will not be able to make predictions")
    LinearRegression = None
    Ridge = None
    Lasso = None
    RandomForestRegressor = None
    GradientBoostingRegressor = None
    StandardScaler = None
    train_test_split = None

from app.models import PredictionRequest, PredictionResult, PredictionPoint
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.agent.financial_agent import FinancialAgent


class StockPrediction:
    """Machine learning-based stock price prediction engine."""
    
    def __init__(self, financial_agent: Optional['FinancialAgent'] = None):
        """Initialize the prediction engine.
        
        Args:
            financial_agent: Optional FinancialAgent instance for data fetching
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn is required for stock prediction. Install it with: pip install scikit-learn")
        
        if financial_agent is None:
            from app.agent.financial_agent import FinancialAgent
            financial_agent = FinancialAgent()
        self.financial_agent = financial_agent
        logger.info("StockPrediction initialized")
    
    def _prepare_features(self, df: pd.DataFrame, use_technical_indicators: bool = True) -> pd.DataFrame:
        """
        Prepare features for machine learning.
        
        Args:
            df: DataFrame with stock data and technical indicators
            use_technical_indicators: Whether to include technical indicators
            
        Returns:
            DataFrame with features
        """
        features_df = df.copy()
        
        # Basic price features
        features_df['price_change'] = features_df['close'].pct_change()
        features_df['price_change_2'] = features_df['close'].pct_change(periods=2)
        features_df['price_change_5'] = features_df['close'].pct_change(periods=5)
        
        # Volume features
        features_df['volume_change'] = features_df['volume'].pct_change()
        features_df['volume_ma5'] = features_df['volume'].rolling(window=5).mean()
        features_df['volume_ratio'] = features_df['volume'] / features_df['volume_ma5']
        
        # Price position features
        features_df['high_low_ratio'] = features_df['high'] / features_df['low']
        features_df['close_position'] = (features_df['close'] - features_df['low']) / (features_df['high'] - features_df['low'])
        
        if use_technical_indicators:
            # MA features
            if 'ma5' in features_df.columns:
                features_df['ma5_ratio'] = features_df['close'] / features_df['ma5']
                features_df['ma5_slope'] = features_df['ma5'].diff()
            if 'ma10' in features_df.columns:
                features_df['ma10_ratio'] = features_df['close'] / features_df['ma10']
            if 'ma20' in features_df.columns:
                features_df['ma20_ratio'] = features_df['close'] / features_df['ma20']
            if 'ma30' in features_df.columns:
                features_df['ma30_ratio'] = features_df['close'] / features_df['ma30']
                features_df['ma5_ma30_diff'] = (features_df['ma5'] - features_df['ma30']) / features_df['ma30']
            
            # RSI features
            if 'rsi' in features_df.columns:
                features_df['rsi_normalized'] = (features_df['rsi'] - 50) / 50  # Normalize to -1 to 1
            
            # MACD features
            if 'macd' in features_df.columns and 'macd_signal' in features_df.columns:
                features_df['macd_diff'] = features_df['macd'] - features_df['macd_signal']
                features_df['macd_histogram'] = features_df.get('macd_histogram', features_df['macd_diff'])
            
            # Bollinger Bands features
            if 'bollinger_upper' in features_df.columns and 'bollinger_lower' in features_df.columns:
                features_df['bb_width'] = (features_df['bollinger_upper'] - features_df['bollinger_lower']) / features_df['bollinger_middle']
                features_df['bb_position'] = (features_df['close'] - features_df['bollinger_lower']) / (features_df['bollinger_upper'] - features_df['bollinger_lower'])
        
        # Lag features (previous day's values)
        features_df['close_lag1'] = features_df['close'].shift(1)
        features_df['close_lag2'] = features_df['close'].shift(2)
        features_df['close_lag3'] = features_df['close'].shift(3)
        
        return features_df
    
    def _select_features(self, features_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """
        Select and clean features for training.
        
        Args:
            features_df: DataFrame with all features
            
        Returns:
            Tuple of (cleaned features DataFrame, feature names)
        """
        # Select numeric features (exclude date and target)
        feature_columns = [
            'price_change', 'price_change_2', 'price_change_5',
            'volume_change', 'volume_ratio',
            'high_low_ratio', 'close_position',
            'close_lag1', 'close_lag2', 'close_lag3'
        ]
        
        # Add technical indicator features if available
        if 'ma5_ratio' in features_df.columns:
            feature_columns.extend(['ma5_ratio', 'ma5_slope'])
        if 'ma10_ratio' in features_df.columns:
            feature_columns.append('ma10_ratio')
        if 'ma20_ratio' in features_df.columns:
            feature_columns.append('ma20_ratio')
        if 'ma30_ratio' in features_df.columns:
            feature_columns.extend(['ma30_ratio', 'ma5_ma30_diff'])
        if 'rsi_normalized' in features_df.columns:
            feature_columns.append('rsi_normalized')
        if 'macd_diff' in features_df.columns:
            feature_columns.append('macd_diff')
        if 'bb_width' in features_df.columns:
            feature_columns.extend(['bb_width', 'bb_position'])
        
        # Filter to only existing columns
        available_features = [col for col in feature_columns if col in features_df.columns]
        
        # Extract features and remove NaN rows
        X = features_df[available_features].copy()
        X = X.dropna()
        
        return X, available_features
    
    def _create_model(self, model_type: str):
        """
        Create a machine learning model.
        
        Args:
            model_type: Type of model to create
            
        Returns:
            Model instance
        """
        if model_type == "linear":
            return LinearRegression()
        elif model_type == "ridge":
            return Ridge(alpha=1.0)
        elif model_type == "lasso":
            return Lasso(alpha=0.1)
        elif model_type == "random_forest":
            return RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
        elif model_type == "gradient_boosting":
            return GradientBoostingRegressor(n_estimators=100, max_depth=5, random_state=42)
        elif model_type == "ensemble":
            # Simple ensemble: average of multiple models
            from sklearn.ensemble import VotingRegressor
            return VotingRegressor([
                ('ridge', Ridge(alpha=1.0)),
                ('rf', RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1)),
                ('gb', GradientBoostingRegressor(n_estimators=50, max_depth=5, random_state=42))
            ])
        else:
            logger.warning(f"Unknown model type {model_type}, using linear regression")
            return LinearRegression()
    
    def _calculate_confidence_interval(
        self, 
        predictions: np.ndarray, 
        residuals: np.ndarray,
        alpha: float = 0.05
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate confidence intervals for predictions.
        
        Args:
            predictions: Predicted values
            residuals: Residuals from training
            alpha: Significance level (default: 0.05 for 95% CI)
            
        Returns:
            Tuple of (lower_bound, upper_bound)
        """
        # Use standard error of residuals
        std_error = np.std(residuals)
        z_score = 1.96  # For 95% confidence interval
        
        lower = predictions - z_score * std_error
        upper = predictions + z_score * std_error
        
        return lower, upper
    
    async def predict_stock_price(
        self,
        request: PredictionRequest
    ) -> PredictionResult:
        """
        Predict future stock prices using machine learning.
        
        Args:
            request: Prediction request parameters
            
        Returns:
            PredictionResult with predictions
        """
        logger.info(f"Starting stock price prediction for {request.stock_code} "
                   f"(predicting {request.prediction_days} days ahead)")
        
        # Get historical data
        df = self.financial_agent.get_stock_data(
            request.stock_code,
            request.start_date,
            request.end_date
        )
        
        if df.empty:
            raise ValueError(f"无法获取股票 {request.stock_code} 的数据")
        
        if len(df) < 60:
            raise ValueError(f"数据点不足（{len(df)}），至少需要60个数据点进行预测")
        
        # Calculate technical indicators
        df = self.financial_agent.calculate_technical_indicators(df)
        
        # Prepare features
        features_df = self._prepare_features(df, request.use_technical_indicators)
        
        # Select features
        X, feature_names = self._select_features(features_df)
        
        if len(X) < 30:
            raise ValueError(f"有效特征数据不足（{len(X)}），至少需要30个数据点")
        
        # Target: next day's closing price
        y = features_df.loc[X.index, 'close'].values
        
        # Align X and y (remove rows where y is NaN)
        valid_mask = ~pd.isna(y)
        X = X[valid_mask]
        y = y[valid_mask]
        
        if len(X) < 30:
            raise ValueError(f"对齐后的数据不足（{len(X)}），至少需要30个数据点")
        
        # Split data (80% train, 20% validation)
        split_idx = int(len(X) * 0.8)
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        # Create and train model
        model = self._create_model(request.model_type)
        model.fit(X_train_scaled, y_train)
        
        # Evaluate on validation set
        y_val_pred = model.predict(X_val_scaled)
        val_mae = mean_absolute_error(y_val, y_val_pred)
        val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))
        val_r2 = r2_score(y_val, y_val_pred)
        
        logger.info(f"Model validation - MAE: {val_mae:.2f}, RMSE: {val_rmse:.2f}, R2: {val_r2:.4f}")
        
        # Calculate residuals for confidence interval
        train_pred = model.predict(X_train_scaled)
        residuals = y_train - train_pred
        
        # Predict future prices
        predictions = []
        last_date = df['date'].iloc[-1]
        current_features = X.iloc[-1:].copy()  # Start with last known features
        current_price = df['close'].iloc[-1]
        
        # Get feature importance if available
        feature_importance = None
        if hasattr(model, 'feature_importances_'):
            feature_importance = dict(zip(feature_names, model.feature_importances_))
        elif hasattr(model, 'coef_'):
            # For linear models, use absolute coefficients
            coef_abs = np.abs(model.coef_)
            feature_importance = dict(zip(feature_names, coef_abs / coef_abs.sum()))
        
        for day in range(1, request.prediction_days + 1):
            # Scale current features
            current_features_scaled = scaler.transform(current_features)
            
            # Predict next day's price
            predicted_price = model.predict(current_features_scaled)[0]
            
            # Calculate confidence interval
            lower, upper = self._calculate_confidence_interval(
                np.array([predicted_price]),
                residuals
            )
            
            # Calculate prediction confidence (based on distance from current price)
            price_change_pct = abs(predicted_price - current_price) / current_price if current_price > 0 else 0
            # Confidence decreases with larger price changes and further into future
            confidence = max(0.3, 1.0 - (price_change_pct * 2) - (day / request.prediction_days * 0.3))
            
            # Calculate predicted date
            predicted_date = last_date + timedelta(days=day)
            predicted_date_str = predicted_date.strftime('%Y-%m-%d')
            
            predictions.append(PredictionPoint(
                date=predicted_date_str,
                predicted_price=float(predicted_price),
                confidence_interval_lower=float(lower[0]),
                confidence_interval_upper=float(upper[0]),
                prediction_confidence=float(confidence)
            ))
            
            # Update features for next prediction (simplified: use predicted price)
            # In practice, this would need more sophisticated feature updating
            current_price = predicted_price
            
            # Update lag features
            if 'close_lag1' in current_features.columns:
                current_features['close_lag3'] = current_features['close_lag2'].values
                current_features['close_lag2'] = current_features['close_lag1'].values
                current_features['close_lag1'] = predicted_price
            
            # Update price change features
            if 'price_change' in current_features.columns:
                prev_price = current_features['close_lag1'].values[0] if 'close_lag1' in current_features.columns else predicted_price
                current_features['price_change_5'] = current_features['price_change_2'].values
                current_features['price_change_2'] = current_features['price_change'].values
                current_features['price_change'] = (predicted_price - prev_price) / prev_price if prev_price > 0 else 0
        
        result = PredictionResult(
            stock_code=request.stock_code,
            stock_name=None,
            training_period=f"{request.start_date} to {request.end_date}",
            prediction_days=request.prediction_days,
            model_type=request.model_type,
            model_accuracy=float(val_r2),  # Use R2 as accuracy metric
            predictions=predictions,
            feature_importance=feature_importance,
            prediction_timestamp=datetime.now()
        )
        
        logger.info(f"Prediction completed: {len(predictions)} days predicted, "
                   f"model R2: {val_r2:.4f}")
        
        return result

