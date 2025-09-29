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
        fetchButton: null
    },

    // Initialize the dashboard
    init() {
        this.cacheElements();
        this.bindEvents();
        this.setDefaultDateTime();
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
    }
};

/**
 * Updates the dashboard values with real-time data
 * @param {number} temp - Temperature in Celsius
 * @param {number} co2 - CO2 level in ppm
 * @param {number} hum - Humidity percentage
 */
function updateValues(temp, co2, hum) {
    // Validate inputs
    if (temp === null || temp === undefined) {
        DashboardController.updateDisplay(
            DashboardController.elements.tempValue, 
            'No data'
        );
    } else {
        DashboardController.updateDisplay(
            DashboardController.elements.tempValue, 
            `${temp}°C`
        );
    }

    if (co2 === null || co2 === undefined) {
        DashboardController.updateDisplay(
            DashboardController.elements.co2Value, 
            'No data'
        );
    } else {
        DashboardController.updateDisplay(
            DashboardController.elements.co2Value, 
            `${co2} ppm`
        );
    }

    if (hum === null || hum === undefined) {
        DashboardController.updateDisplay(
            DashboardController.elements.humidityValue, 
            'No data'
        );
    } else {
        DashboardController.updateDisplay(
            DashboardController.elements.humidityValue, 
            `${hum}%`
        );
    }

    // Check for anomalies
    checkForAnomalies(temp, co2, hum);
}

/**
 * Checks for anomalies in the sensor data and triggers alerts
 * @param {number} temp - Temperature in Celsius
 * @param {number} co2 - CO2 level in ppm
 * @param {number} hum - Humidity percentage
 */
function checkForAnomalies(temp, co2, hum) {
    let hasAnomaly = false;

    // Define threshold values
    const thresholds = {
        temp: { min: 15, max: 30 },
        co2: { max: 1000 },
        humidity: { min: 30, max: 70 }
    };

    // Check temperature
    if (temp !== null && temp !== undefined) {
        if (temp < thresholds.temp.min || temp > thresholds.temp.max) {
            hasAnomaly = true;
        }
    }

    // Check CO2
    if (co2 !== null && co2 !== undefined) {
        if (co2 > thresholds.co2.max) {
            hasAnomaly = true;
        }
    }

    // Check humidity
    if (hum !== null && hum !== undefined) {
        if (hum < thresholds.humidity.min || hum > thresholds.humidity.max) {
            hasAnomaly = true;
        }
    }

    // Show or hide alert box
    if (hasAnomaly) {
        showAlert();
    } else {
        hideAlert();
    }
}

/**
 * Shows the alert box
 */
function showAlert() {
    DashboardController.elements.alertBox.classList.add('active');
}

/**
 * Hides the alert box
 */
function hideAlert() {
    DashboardController.elements.alertBox.classList.remove('active');
}

/**
 * Fetches historical data for the specified date and time
 * @param {string} dateTime - The selected date and time in ISO format
 */
function fetchHistory(dateTime) {
    // Log the request to console (placeholder for API call)
    console.log(`Fetching history for: ${dateTime}`);
    
    // Format the datetime for display
    const formattedDate = new Date(dateTime).toLocaleString();
    
    // Update the history content to show loading state
    DashboardController.showHistoryMessage(`Loading data for ${formattedDate}...`);
    
    // Simulate API call delay
    setTimeout(() => {
        // This is where the actual API call would be made
        // For now, just update the display
        DashboardController.showHistoryMessage(
            `History data for ${formattedDate} will be displayed here once connected to backend.`
        );
    }, 500);
    
    // Placeholder for future API integration
    // Example of what the actual implementation might look like:
    /*
    fetch(`/api/history?datetime=${dateTime}`)
        .then(response => response.json())
        .then(data => {
            displayHistoryData(data);
        })
        .catch(error => {
            console.error('Error fetching history:', error);
            DashboardController.showHistoryMessage('Error loading history data.');
        });
    */
}

/**
 * Displays historical data in the history box
 * @param {Object} data - Historical data from the API
 */
function displayHistoryData(data) {
    // This function will be implemented when backend is connected
    // It will format and display the historical data
    if (data && data.temperature !== undefined && data.co2 !== undefined && data.humidity !== undefined) {
        const content = `
            <div style="display: grid; gap: 1rem;">
                <div><strong>Temperature:</strong> ${data.temperature}°C</div>
                <div><strong>CO₂:</strong> ${data.co2} ppm</div>
                <div><strong>Humidity:</strong> ${data.humidity}%</div>
                <div><strong>Timestamp:</strong> ${new Date(data.timestamp).toLocaleString()}</div>
            </div>
        `;
        DashboardController.elements.historyContent.innerHTML = content;
    } else {
        DashboardController.showHistoryMessage('No data available for the selected time.');
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    DashboardController.init();
    
    // Example: Test the updateValues function after 2 seconds
    // Remove this in production
    /*
    setTimeout(() => {
        updateValues(22.5, 450, 55);
    }, 2000);
    */
});