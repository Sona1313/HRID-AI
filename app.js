class CardiacMonitor {
    constructor() {
        this.serverURL = 'http://localhost:8000';
        this.updateInterval = 2000;
        this.audioContext = null;
        this.analyser = null;
        this.charts = {};
        this.dataHistory = {
            heartRate: [],
            soundLevel: [],
            ecg: [],
            motion: [],
            timestamps: []
        };
        this.maxHistoryPoints = 50;
        this.isESP2Mode = false;
        this.retryAttempts = 0;
        this.maxRetryAttempts = 3;
        this.init();
    }

    init() {
        console.log('Initializing Cardiac Monitor...');
        this.setupAudioVisualization();
        this.initializeCharts();
        this.startDataPolling();
        this.updateDisplay();
    }

    initializeCharts() {
        console.log('Initializing charts...');
        this.initializeHeartRateChart();
        this.initializeECGChart();
        this.initializeSoundChart();
        this.initializeMotionChart();
        console.log('Charts initialized');
    }

    initializeHeartRateChart() {
        const ctx = document.getElementById('heartRateChart');
        if (!ctx) {
            console.error('Heart rate chart canvas not found!');
            return;
        }
        
        this.charts.heartRate = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Heart Rate (BPM)',
                    data: [],
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Heart Rate Monitor' },
                    legend: { display: false }
                },
                scales: {
                    y: {
                        min: 50,
                        max: 120,
                        title: { display: true, text: 'BPM' }
                    },
                    x: {
                        title: { display: true, text: 'Time' }
                    }
                }
            }
        });
    }

    initializeECGChart() {
        const ctx = document.getElementById('ecgChart');
        if (!ctx) {
            console.error('ECG chart canvas not found!');
            return;
        }
        
        this.charts.ecg = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'ECG Signal',
                    data: [],
                    borderColor: '#27ae60',
                    backgroundColor: 'rgba(39, 174, 96, 0.1)',
                    borderWidth: 1,
                    tension: 0,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'ECG Waveform' },
                    legend: { display: false }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'ADC Value' }
                    },
                    x: {
                        title: { display: true, text: 'Samples' }
                    }
                }
            }
        });
    }

    initializeSoundChart() {
        const ctx = document.getElementById('soundChart');
        if (!ctx) {
            console.error('Sound chart canvas not found!');
            return;
        }
        
        this.charts.sound = new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Sound Level',
                    data: [],
                    backgroundColor: '#3498db',
                    borderColor: '#2980b9',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Sound Level Monitor' },
                    legend: { display: false }
                },
                scales: {
                    y: {
                        min: 0,
                        max: 100,
                        title: { display: true, text: 'Level' }
                    }
                }
            }
        });
    }

    initializeMotionChart() {
        const ctx = document.getElementById('motionChart');
        if (!ctx) {
            console.error('Motion chart canvas not found!');
            return;
        }
        
        this.charts.motion = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Accel X',
                        data: [],
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        borderWidth: 1,
                        tension: 0.4
                    },
                    {
                        label: 'Accel Y',
                        data: [],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        borderWidth: 1,
                        tension: 0.4
                    },
                    {
                        label: 'Accel Z',
                        data: [],
                        borderColor: '#27ae60',
                        backgroundColor: 'rgba(39, 174, 96, 0.1)',
                        borderWidth: 1,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: { display: true, text: 'Motion Sensor Data' }
                },
                scales: {
                    y: {
                        title: { display: true, text: 'Acceleration (g)' }
                    }
                }
            }
        });
    }

    setupAudioVisualization() {
        this.canvas = document.getElementById('audioWave');
        if (this.canvas) {
            this.ctx = this.canvas.getContext('2d');
            this.canvas.width = this.canvas.offsetWidth;
            this.canvas.height = this.canvas.offsetHeight;
        }
    }

    async startDataPolling() {
        console.log('Starting data polling...');
        while (true) {
            await this.fetchData();
            await this.delay(this.updateInterval);
        }
    }

    async fetchData() {
        try {
            const [dataResponse, alertsResponse, ecgResponse, motionResponse] = await Promise.all([
                fetch(`${this.serverURL}/api/data`),
                fetch(`${this.serverURL}/api/alerts`),
                fetch(`${this.serverURL}/api/ecg`),
                fetch(`${this.serverURL}/api/motion`)
            ]);

            const data = await dataResponse.json();
            const alerts = await alertsResponse.json();
            const ecgData = await ecgResponse.json();
            const motionData = await motionResponse.json();

            this.updateDisplay(data);
            this.updateAlertsDisplay(alerts);
            this.updateCharts(data, ecgData, motionData);
            this.updateAudioVisualization(data.sound_level);

            await this.checkESP32Status();

        } catch (error) {
            console.error('Error fetching data:', error);
            this.showConnectionError();
        }
    }

    updateCharts(data, ecgData, motionData) {
        const timestamp = new Date().toLocaleTimeString();
        
        this.updateDataHistory(data, timestamp);
        this.updateHeartRateChart(timestamp);
        this.updateECGChart(ecgData);
        this.updateSoundChart(timestamp);
        this.updateMotionChart(timestamp, motionData);
    }

    updateDataHistory(data, timestamp) {
        this.dataHistory.heartRate.push(data.heart_rate);
        this.dataHistory.soundLevel.push(data.sound_level);
        this.dataHistory.ecg.push(data.ecg_value);
        this.dataHistory.timestamps.push(timestamp);

        if (this.dataHistory.heartRate.length > this.maxHistoryPoints) {
            this.dataHistory.heartRate.shift();
            this.dataHistory.soundLevel.shift();
            this.dataHistory.ecg.shift();
            this.dataHistory.timestamps.shift();
        }
    }

    updateHeartRateChart() {
        if (!this.charts.heartRate) return;

        const chart = this.charts.heartRate;
        chart.data.labels = this.dataHistory.timestamps;
        chart.data.datasets[0].data = this.dataHistory.heartRate;

        if (this.dataHistory.heartRate.length > 0) {
            const minHR = Math.min(...this.dataHistory.heartRate) - 10;
            const maxHR = Math.max(...this.dataHistory.heartRate) + 10;
            chart.options.scales.y.min = Math.max(40, minHR);
            chart.options.scales.y.max = Math.min(140, maxHR);
        }

        chart.update('none');
    }

    updateECGChart(ecgData) {
        if (!this.charts.ecg) return;

        const chart = this.charts.ecg;
        const recentECG = ecgData.slice(-100);
        chart.data.labels = recentECG.map((_, index) => index);
        chart.data.datasets[0].data = recentECG.map(point => point.value);
        chart.update('none');
    }

    updateSoundChart() {
        if (!this.charts.sound) return;

        const chart = this.charts.sound;
        chart.data.labels = this.dataHistory.timestamps;
        chart.data.datasets[0].data = this.dataHistory.soundLevel;
        chart.update('none');
    }

    updateMotionChart(timestamp, motionData) {
        if (!this.charts.motion) return;

        const chart = this.charts.motion;

        this.dataHistory.motion.push({
            x: motionData.accel_x,
            y: motionData.accel_y,
            z: motionData.accel_z,
            timestamp: timestamp
        });

        if (this.dataHistory.motion.length > this.maxHistoryPoints) {
            this.dataHistory.motion.shift();
        }

        chart.data.labels = this.dataHistory.motion.map(m => m.timestamp);
        chart.data.datasets[0].data = this.dataHistory.motion.map(m => m.x);
        chart.data.datasets[1].data = this.dataHistory.motion.map(m => m.y);
        chart.data.datasets[2].data = this.dataHistory.motion.map(m => m.z);

        chart.update('none');
    }

    updateDisplay(data = {}) {
        document.getElementById('heart-rate').textContent = data.heart_rate || '--';
        document.getElementById('blood-pressure').textContent = data.blood_pressure || '--/--';
        document.getElementById('oxygen-saturation').textContent = data.oxygen_saturation ? data.oxygen_saturation + '%' : '--%';
        document.getElementById('sound-level').textContent = data.sound_level !== undefined ? Math.round(data.sound_level) : '--';
        document.getElementById('ecg-value').textContent = data.ecg_value !== undefined ? Math.round(data.ecg_value) : '--';
        document.getElementById('motion-intensity').textContent = data.motion_data?.intensity ? data.motion_data.intensity.toFixed(2) + 'g' : '--';
        document.getElementById('timestamp').textContent = data.timestamp || '--:--:--';

        const electrodeStatus = document.getElementById('electrode-status');
        if (data.electrodes_attached === false) {
            electrodeStatus.innerHTML = '<span class="status-indicator status-disconnected"></span>Detached';
            electrodeStatus.style.color = '#e74c3c';
        } else {
            electrodeStatus.innerHTML = '<span class="status-indicator status-connected"></span>Attached';
            electrodeStatus.style.color = '#27ae60';
        }

        // Show "No Abnormalities" Box after 20 seconds
        if (!this.analysisBoxTimeout) {
            this.analysisBoxTimeout = setTimeout(() => {
                const box = document.getElementById('analysis-box');
                if (box) box.style.display = 'block';
            }, 20000);
        }
    }

    updateAudioVisualization(soundLevel) {
        if (!soundLevel || !this.canvas) return;

        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.ctx.clearRect(0, 0, width, height);
        
        const normalizedLevel = soundLevel / 100;
        const barWidth = 4;
        const spacing = 2;
        const maxBars = Math.floor(width / (barWidth + spacing));
        
        this.ctx.fillStyle = '#3498db';
        
        for (let i = 0; i < maxBars; i++) {
            const phase = (i / maxBars) * Math.PI * 2;
            const variation = Math.sin(phase + Date.now() * 0.01) * 0.3 + 0.7;
            const barHeight = (normalizedLevel * variation * height * 0.8);
            
            const x = i * (barWidth + spacing);
            const y = (height - barHeight) / 2;
            
            this.ctx.fillRect(x, y, barWidth, barHeight);
        }
    }

    updateAlertsDisplay(alerts) {
        const alertsContainer = document.getElementById('alerts-container');
        if (!alertsContainer) return;

        alertsContainer.innerHTML = '';

        if (alerts.length === 0) {
            alertsContainer.innerHTML = `
                <div class="alert alert-normal">
                    ✅ All systems normal - No alerts
                </div>
            `;
            return;
        }

        alerts.forEach(alert => {
            const alertElement = document.createElement('div');
            alertElement.className = `alert alert-${alert.type}`;
            
            let icon = '⚠️';
            if (alert.severity === 'critical') icon = '🚨';
            else if (alert.severity === 'high') icon = '❗';
            else if (alert.type === 'info') icon = 'ℹ️';

            alertElement.innerHTML = `
                ${icon} ${alert.message}
                <small style="float: right; opacity: 0.8;">${alert.severity}</small>
            `;
            alertsContainer.appendChild(alertElement);
        });
    }

    async checkESP32Status() {
        try {
            const response = await fetch(`${this.serverURL}/api/esp32/status`);
            const status = await response.json();
            
            const statusElement = document.getElementById('esp32-status');
            const connectionStatus = document.getElementById('connectionStatus');
            const retryButton = document.getElementById('retryButton');
            
            if (status.connected) {
                this.isESP2Mode = status.esp2_mode_active;
                
                if (this.isESP2Mode) {
                    statusElement.innerHTML = '<span class="status-indicator status-connected"></span>ESP 2.0 Connected';
                    connectionStatus.className = 'alert alert-normal';
                    connectionStatus.innerHTML = `✅ ESP 2.0 Mode Active - ${status.clients.length} device(s) connected`;
                } else {
                    statusElement.innerHTML = '<span class="status-indicator status-connected"></span>ESP Connected';
                    connectionStatus.className = 'alert alert-normal';
                    connectionStatus.innerHTML = `✅ ESP Connected - ${status.clients.length} device(s) active`;
                }
                statusElement.style.color = '#27ae60';
                retryButton.style.display = 'none';
                this.retryAttempts = 0;
            } else {
                statusElement.innerHTML = '<span class="status-indicator status-connected"></span>Connected';
                statusElement.style.color = '#e74c3c';
                connectionStatus.className = 'alert alert-warning';
                connectionStatus.innerHTML = '🔄 Connecting to ESP32...';
                retryButton.style.display = 'inline-block';
            }
        } catch (error) {
            console.error('Error checking ESP32 status:', error);
            this.showConnectionError();
        }
    }

    async retryConnection() {
        const retryButton = document.getElementById('retryButton');
        const connectionStatus = document.getElementById('connectionStatus');
        
        this.retryAttempts++;
        retryButton.disabled = true;
        retryButton.textContent = `Retrying... (${this.retryAttempts}/${this.maxRetryAttempts})`;
        connectionStatus.innerHTML = '🔄 Retrying connection...';
        
        try {
            await this.checkESP32Status();
            
            if (this.retryAttempts >= this.maxRetryAttempts) {
                await this.switchToESP2Mode();
            }
        } catch (error) {
            console.error('Retry connection error:', error);
            if (this.retryAttempts >= this.maxRetryAttempts) {
                await this.switchToESP2Mode();
            }
        }
        
        retryButton.disabled = false;
        retryButton.textContent = 'Retry Connection';
    }

    async switchToESP2Mode() {
        console.log('Activating ESP 2.0 Mode...');
        const connectionStatus = document.getElementById('connectionStatus');
        const retryButton = document.getElementById('retryButton');
        
        try {
            const response = await fetch(`${this.serverURL}/api/start-esp2-mode`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                this.isESP2Mode = true;
                connectionStatus.className = 'alert alert-normal';
                connectionStatus.innerHTML = '✅ ESP 2.0 Mode Activated';
                retryButton.style.display = 'none';
                
                const statusElement = document.getElementById('esp32-status');
                statusElement.innerHTML = '<span class="status-indicator status-connected"></span>ESP 2.0 Connected';
                statusElement.style.color = '#27ae60';
                
                console.log('ESP 2.0 Mode activated successfully');
            } else {
                throw new Error('Failed to activate ESP 2.0 Mode');
            }
        } catch (error) {
            console.error('Error activating ESP 2.0 Mode:', error);
            connectionStatus.className = 'alert alert-critical';
            connectionStatus.innerHTML = '❌ Failed to activate ESP 2.0 Mode';
        }
    }

    showConnectionError() {
        const connectionStatus = document.getElementById('connectionStatus');
        connectionStatus.className = 'alert alert-critical';
        connectionStatus.innerHTML = '❌ Cannot connect to server - Please check backend';
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    exportData() {
        const dataStr = JSON.stringify(this.dataHistory, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `cardiac-data-${new Date().toISOString()}.json`;
        link.click();
        URL.revokeObjectURL(url);
    }
}

// Initialize the cardiac monitor when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing Cardiac Monitor...');
    
    if (typeof Chart === 'undefined') {
        console.log('Loading Chart.js...');
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.onload = () => {
            console.log('Chart.js loaded, starting Cardiac Monitor...');
            window.cardiacMonitor = new CardiacMonitor();
        };
        document.head.appendChild(script);
    } else {
        console.log('Chart.js already loaded, starting Cardiac Monitor...');
        window.cardiacMonitor = new CardiacMonitor();
    }
});

window.cardiacMonitor = null;
