# ml_signal_optimizer.py
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os

class MLSignalOptimizer:
    """
    Machine learning model for predicting optimal traffic signal timing
    based on traffic density, weather conditions, and time of day.
    """
    
    def __init__(self, model_path=None):
        """
        Initialize the ML signal optimizer.
        
        Args:
            model_path: Path to a pre-trained model file. If None, a new model will be created.
        """
        if model_path and os.path.exists(model_path):
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(f"{os.path.splitext(model_path)[0]}_scaler.pkl")
            self.is_trained = True
        else:
            self.model = RandomForestRegressor(
                n_estimators=100, 
                max_depth=15,
                min_samples_split=5,
                random_state=42
            )
            self.scaler = StandardScaler()
            self.is_trained = False
    
    def preprocess_data(self, data):
        """
        Preprocess the input data for training or prediction.
        
        Args:
            data: DataFrame containing features for the model
            
        Returns:
            X: Processed feature matrix
            y: Target values (if 'optimal_green_time' is in data)
        """
        # Features to use in the model
        feature_cols = [
            'traffic_density', 'queue_length', 'waiting_time',
            'rainfall_intensity', 'visibility', 
            'hour_of_day', 'is_weekend',
            'junction_complexity'
        ]
        
        # Ensure all required columns exist
        for col in feature_cols:
            if col not in data.columns:
                raise ValueError(f"Required column '{col}' not found in input data")
        
        # Create time-based features
        if 'timestamp' in data.columns:
            data['hour_of_day'] = data['timestamp'].dt.hour
            data['is_weekend'] = data['timestamp'].dt.dayofweek >= 5
        
        # Extract features
        X = data[feature_cols].copy()
        
        # Handle missing values
        X.fillna(X.mean(), inplace=True)
        
        # Scale the features
        if not self.is_trained:
            X_scaled = self.scaler.fit_transform(X)
        else:
            X_scaled = self.scaler.transform(X)
        
        # Return features and target if available
        if 'optimal_green_time' in data.columns:
            y = data['optimal_green_time']
            return X_scaled, y
        else:
            return X_scaled
    
    def train(self, training_data, test_size=0.2):
        """
        Train the ML model on historical data.
        
        Args:
            training_data: DataFrame containing features and optimal signal timing
            test_size: Portion of data to use for testing
            
        Returns:
            Dictionary with model performance metrics
        """
        X, y = self.preprocess_data(training_data)
        
        # Split data into training and testing sets
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42
        )
        
        # Train the model
        self.model.fit(X_train, y_train)
        
        # Evaluate on test set
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        self.is_trained = True
        
        return {
            'mse': mse,
            'rmse': np.sqrt(mse),
            'r2': r2,
            'feature_importance': dict(zip(
                training_data.columns, 
                self.model.feature_importances_
            ))
        }
    
    def predict_optimal_timing(self, current_conditions):
        """
        Predict optimal signal timing based on current conditions.
        
        Args:
            current_conditions: DataFrame with current traffic and weather data
            
        Returns:
            DataFrame with predicted optimal green times
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        X = self.preprocess_data(current_conditions)
        predictions = self.model.predict(X)
        
        # Create output DataFrame
        results = current_conditions.copy()
        results['predicted_green_time'] = predictions
        
        # Ensure predictions are within reasonable bounds (5-120 seconds)
        results['predicted_green_time'] = results['predicted_green_time'].clip(5, 120)
        
        return results
    
    def save_model(self, model_path):
        """
        Save the trained model to disk.
        
        Args:
            model_path: Path where the model should be saved
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model")
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Save model and scaler
        joblib.dump(self.model, model_path)
        scaler_path = f"{os.path.splitext(model_path)[0]}_scaler.pkl"
        joblib.dump(self.scaler, scaler_path)
        
        print(f"Model saved to {model_path}")
        print(f"Scaler saved to {scaler_path}")


def generate_sample_training_data(n_samples=1000):
    """
    Generate synthetic data for testing and demonstration purposes.
    
    Args:
        n_samples: Number of samples to generate
        
    Returns:
        DataFrame with synthetic training data
    """
    np.random.seed(42)
    
    # Create timestamps spanning a week
    timestamps = pd.date_range(
        start='2023-01-01', 
        periods=n_samples, 
        freq='15min'
    )
    
    # Generate features with realistic correlations
    hour_of_day = timestamps.hour
    is_weekend = timestamps.dayofweek >= 5
    
    # Traffic typically heavier during weekday rush hours
    base_traffic = np.random.normal(loc=50, scale=15, size=n_samples)
    rush_hour_boost = (
        ((hour_of_day >= 7) & (hour_of_day <= 9) | 
         (hour_of_day >= 16) & (hour_of_day <= 18)) & 
        ~is_weekend
    ).astype(int) * 30
    weekend_reduction = is_weekend.astype(int) * -15
    
    traffic_density = base_traffic + rush_hour_boost + weekend_reduction
    traffic_density = np.clip(traffic_density, 5, 100)
    
    # Generate correlated features
    queue_length = traffic_density * 0.5 + np.random.normal(loc=0, scale=5, size=n_samples)
    queue_length = np.clip(queue_length, 0, 50)
    
    waiting_time = traffic_density * 0.3 + np.random.normal(loc=10, scale=3, size=n_samples)
    waiting_time = np.clip(waiting_time, 0, 60)
    
    # Weather data - some correlation with traffic
    rainfall_intensity = np.random.exponential(scale=0.5, size=n_samples)
    visibility = 100 - rainfall_intensity * 10 + np.random.normal(loc=0, scale=5, size=n_samples)
    visibility = np.clip(visibility, 20, 100)
    
    # Junction complexity (static for each junction)
    junction_ids = np.random.randint(1, 10, size=n_samples)
    junction_complexity = {i: np.random.uniform(1, 5) for i in range(1, 10)}
    junction_complexity_values = [junction_complexity[i] for i in junction_ids]
    
    # Optimal green time (target)
    # Formula: base time + traffic adjustment + weather adjustment
    base_time = 20
    traffic_factor = 0.3
    rain_factor = 5
    visibility_factor = -0.1
    
    optimal_green_time = (
        base_time + 
        traffic_factor * traffic_density + 
        rain_factor * rainfall_intensity +
        visibility_factor * (100 - visibility)
    )
    
    # Add some noise to the target
    optimal_green_time += np.random.normal(loc=0, scale=3, size=n_samples)
    optimal_green_time = np.clip(optimal_green_time, 10, 90)
    
    # Create DataFrame
    data = pd.DataFrame({
        'timestamp': timestamps,
        'traffic_density': traffic_density,
        'queue_length': queue_length,
        'waiting_time': waiting_time,
        'rainfall_intensity': rainfall_intensity,
        'visibility': visibility,
        'junction_id': junction_ids,
        'junction_complexity': junction_complexity_values,
        'hour_of_day': hour_of_day,
        'is_weekend': is_weekend,
        'optimal_green_time': optimal_green_time
    })
    
    return data


if __name__ == "__main__":
    # Generate sample data
    print("Generating sample training data...")
    data = generate_sample_training_data(2000)
    
    # Create and train the model
    print("Training the ML signal timing optimizer...")
    optimizer = MLSignalOptimizer()
    metrics = optimizer.train(data)
    
    print("\nModel Performance:")
    print(f"RMSE: {metrics['rmse']:.2f} seconds")
    print(f"R² Score: {metrics['r2']:.4f}")
    
    print("\nTop 3 most important features:")
    sorted_features = sorted(
        metrics['feature_importance'].items(), 
        key=lambda x: x[1], 
        reverse=True
    )[:3]
    for feature, importance in sorted_features:
        print(f"- {feature}: {importance:.4f}")
    
    # Save the model
    model_path = "../models/signal_optimizer.pkl"
    optimizer.save_model(model_path)
    
    # Make some predictions
    print("\nPredicting optimal signal timing for new conditions...")
    test_data = generate_sample_training_data(5)
    # Remove the target column to simulate prediction scenario
    test_data = test_data.drop('optimal_green_time', axis=1)
    
    predictions = optimizer.predict_optimal_timing(test_data)
    
    print("\nSample Predictions:")
    for i, (_, row) in enumerate(predictions.iloc[:5].iterrows()):
        print(f"Scenario {i+1}:")
        print(f"  Traffic Density: {row['traffic_density']:.1f}")
        print(f"  Rainfall: {row['rainfall_intensity']:.2f} mm/h")
        print(f"  Time: {row['timestamp'].strftime('%H:%M')} ({'Weekend' if row['is_weekend'] else 'Weekday'})")
        print(f"  Predicted Green Time: {row['predicted_green_time']:.1f} seconds\n")