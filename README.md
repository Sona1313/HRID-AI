# HRID-AI

HRID-AI is a comprehensive project focused on heart-related intelligent diagnostics. It leverages deep learning and IoT for cardiac monitoring and prediction of critical parameters such as Ejection Fraction (EF) and Left Ventricular Ejection Fraction (LVEF) using data from wearable devices.

## Features

- **EF Prediction:** Predict cardiac ejection fraction with pre-trained machine learning models using data from the sensor and control units
- **LVEF Prediction Using CNN:** Utilize Convolutional Neural Networks for predicting LVEF, with Jupyter Notebook examples and saved model files.
- **Cardiac Monitor (ESP32):** Acquire and transmit physiological signals from an ESP32 microcontroller, using MQTT for data publishing.
- **Web and App Integration:** User interfaces provided via HTML, JavaScript, and Python scripts for data interaction and visualization.
- **PCB and Hardware** PCB Gerber Files of both the Sensor and Control Units.

## File Structure

| File/Folder                     | Description                                     |
|---------------------------------|-------------------------------------------------|
| `EF Prediction`                 | Kaggle notebook for EF prediction               |
| `LVEF Pediction using CNN`      | CNN-based LVEF prediction notebook (v2)         |
| `README.md`                     | Project overview and setup instructions         |
| `app.js`                        | JavaScript logic for web interface              |
| `app.py`                        | Python backend application script               |
| `cardiac_monitor_esp32.ino`     | ESP32 firmware for data acquisition             |
| `final_cardiac_ef_model.keras`  | Pre-trained Keras EF prediction model           |
| `index.html`                    | Main webpage interface                          |
| `lvef-prediction-using-cnn.ipynb`| Jupyter Notebook for CNN-based LVEF prediction |
| `model_loader.py`               | Utility to load and use trained Keras models    |
| `SU_Gerber_arduino-nano_PCB_hrid-steth_2025-09-20.zip` |	Gerber files for Sensor Unit PCB |
| `CU_Gerber_PCB_hridPCB_hrid_2025-09-20.zip`	| Control Unit PCB Gerber files |
 
## Getting Started

### Requirements

- Python 3.8+
- Keras, TensorFlow, Flask (for backend)
- JavaScript (for frontend)
- ESP32 Microcontroller (for IoT module)
- MQTT Broker (for real-time data transmission)
