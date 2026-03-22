// Dashboard Controller
const DashboardController = {
    // Element references
    elements: {
        tempValue: null,
        co2Value: null,
        humidityValue: null,
        alertBox: null,
        historyContent: null,
        datetimePicker: null,
        fetchButton: null,
        alertModal: null,
        modalText: null,
        modalClose: null
    },

    // Initialize the dashboard
    init() {
        this.cacheElements();
        this.bindEvents();
        this.setDefaultDateTime();
        this.startLiveSimulation();
    },

    // Cache DOM elements
    cacheElements() {
        this.elements.tempValue = document.getElementById('temp-value');
        this.elements.co2Value = document.getElementById('co2-value');
        this.elements.humidityValue = document.getElementById('humidity-value');
        this.elements.alertBox = document.getElementById('alert-box');
        this.elements.historyContent = document.getElementById('history-content');
        this.elements.datetimePicker = document.getElementById('datetime-picker');
        this.elements.fetchButton = document.getElementById('fetch-history-btn');
        this.elements.alertModal = document.getElementById('alert-modal');
        this.elements.modalText = document.getElementById('modal-text');
        this.elements.modalClose = document.getElementById('modal-close');
    },

    // Bind event listeners
    bindEvents() {
        this.elements.fetchButton.addEventListener('click', () => {
            const selectedDateTime = this.elements.datetimePicker.value;
            if (selectedDateTime) {
                fetchHistory(selectedDateTime);
            } else {
                this.showHistoryMessage('Please select a date and time.');
            }
        });

        // Allow Enter key to fetch history
        this.elements.datetimePicker.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.elements.fetchButton.click();
            }
        });

        // Close modal
        this.elements.modalClose.addEventListener('click', () => {
            this.hideModal();
        });
    },

    // Set default datetime to current time
    setDefaultDateTime() {
        const now = new Date();
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        this.elements.datetimePicker.value = now.toISOString().slice(0, 16);
    },

    // Update display values with animation
    updateDisplay(element, value) {
        element.style.opacity = '0';
        setTimeout(() => {
            element.textContent = value;
            element.style.opacity = '1';
        }, 150);
    },

    // Show message in history content
    showHistoryMessage(message) {
        this.elements.historyContent.textContent = message;
    },

    // Show modal with message
    showModal(message) {
        this.elements.modalText.textContent = message;
        this.elements.alertModal.classList.add('show');
    },

    hideModal() {
        this.elements.alertModal.classList.remove('show');
    },

    // Simulate live sensor readings
    startLiveSimulation() {
        setInterval(() => {
            const temp = 20 + Math.floor(Math.random() * 20);   // 20–40°C
            const co2 = 600 + Math.floor(Math.random() * 800);  // 600–1400 ppm
            const hum = 25 + Math.floor(Math.random() * 60);    // 25–85%
            updateValues(temp, co2, hum);
        }, 4000);
    }
};

/**
 * Updates the dashboard values with real-time data
 */
function updateValues(temp, co2, hum) {
    DashboardController.updateDisplay(DashboardController.elements.tempValue, `${temp}°C`);
    DashboardController.updateDisplay(DashboardController.elements.co2Value, `${co2} ppm`);
    DashboardController.updateDisplay(DashboardController.elements.humidityValue, `${hum}%`);
    checkForAnomalies(temp, co2, hum);
}

/**
 * Checks for anomalies in the sensor data and triggers alerts
 */
function checkForAnomalies(temp, co2, hum) {
    let alertMessage = [];

    if (temp < 15 || temp > 30) alertMessage.push(`Temperature anomaly: ${temp}°C`);
    if (co2 > 1000) alertMessage.push(`High CO₂ detected: ${co2} ppm`);
    if (hum < 30 || hum > 70) alertMessage.push(`Humidity out of range: ${hum}%`);

    if (alertMessage.length > 0) {
        DashboardController.elements.alertBox.classList.add('active');
        DashboardController.elements.alertBox.querySelector('.alert-text').textContent = alertMessage.join(' | ');
        DashboardController.showModal(alertMessage.join('\n'));
    } else {
        DashboardController.elements.alertBox.classList.remove('active');
        DashboardController.elements.alertBox.querySelector('.alert-text').textContent = 'Environment Normal';
    }
}

/**
 * Fetches random historical data (simulated)
 */
function fetchHistory(dateTime) {
    const formattedDate = new Date(dateTime).toLocaleString();
    DashboardController.showHistoryMessage(`Fetching data for ${formattedDate}...`);

    setTimeout(() => {
        const data = {
            temperature: 18 + Math.floor(Math.random() * 15),
            co2: 700 + Math.floor(Math.random() * 500),
            humidity: 35 + Math.floor(Math.random() * 40),
            timestamp: dateTime
        };

        displayHistoryData(data);
    }, 1000);
}

/**
 * Displays historical data in the history box
 */
function displayHistoryData(data) {
    const content = `
        <div style="display: grid; gap: 0.8rem;">
            <div><strong>Temperature:</strong> ${data.temperature}°C</div>
            <div><strong>CO₂:</strong> ${data.co2} ppm</div>
            <div><strong>Humidity:</strong> ${data.humidity}%</div>
            <div><strong>Timestamp:</strong> ${new Date(data.timestamp).toLocaleString()}</div>
        </div>
    `;
    DashboardController.elements.historyContent.innerHTML = content;
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => DashboardController.init());
