import tensorflow as tf  # or torch, depending on your framework
import numpy as np
import json

class CardiacCNNModel:
    def __init__(self, model_path):
        self.model = tf.keras.models.load_model(model_path)
        self.class_names = ['Normal', 'Abnormal']  # Adjust based on your classes
    
    def preprocess_data(self, ecg_data):
        """Preprocess ECG data for model prediction"""
        # Add your preprocessing logic here
        processed_data = np.array(ecg_data).reshape(1, -1, 1)
        return processed_data
    
    def predict(self, ecg_data):
        """Make prediction on ECG data"""
        processed_data = self.preprocess_data(ecg_data)
        prediction = self.model.predict(processed_data)
        predicted_class = self.class_names[np.argmax(prediction)]
        confidence = np.max(prediction)
        
        return {
            'prediction': predicted_class,
            'confidence': float(confidence),
            'timestamp': ecg_data.get('timestamp', '')
        }