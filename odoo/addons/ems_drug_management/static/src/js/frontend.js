// Form validation functions
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    // Clear previous error messages
    const errorMessages = form.querySelectorAll('.error-message');
    errorMessages.forEach(el => el.remove());
    
    // Check required fields
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            showError(field, 'This field is required');
        } else if (field.type === 'email' && !validateEmail(field.value)) {
            isValid = false;
            showError(field, 'Please enter a valid email address');
        } else if (field.dataset.type === 'number' && !validateNumber(field.value)) {
            isValid = false;
            showError(field, 'Please enter a valid number');
        } else if (field.dataset.type === 'date' && !validateDate(field.value)) {
            isValid = false;
            showError(field, 'Please enter a valid date');
        }
    });
    
    return isValid;
}

function showError(field, message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message text-danger mt-1';
    errorDiv.innerText = message;
    field.parentNode.appendChild(errorDiv);
    field.classList.add('is-invalid');
}

function validateEmail(email) {
    const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
    return re.test(String(email).toLowerCase());
}

function validateNumber(value) {
    return !isNaN(parseFloat(value)) && isFinite(value);
}

function validateDate(value) {
    return !isNaN(Date.parse(value));
}

// QR Code generation functions
function generateQRCode(elementId, data, width = 200, height = 200) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Clear previous QR code
    element.innerHTML = '';
    
    // Create new QR code
    new QRCode(element, {
        text: data,
        width: width,
        height: height,
        colorDark: "#000000",
        colorLight: "#ffffff",
        correctLevel: QRCode.CorrectLevel.H
    });
}

function generateDrugQRCode(drugData) {
    // Format: DRUG|LOT|EXP|QTY
    const qrData = `DRUG|${drugData.name}|${drugData.lot}|${drugData.expiry}|${drugData.quantity}`;
    generateQRCode('drugQRCode', qrData);
    
    // Show print button
    const printBtn = document.getElementById('printQRCode');
    if (printBtn) {
        printBtn.style.display = 'inline-block';
    }
}

function generatePouchQRCode(pouchData) {
    // Format: POUCH|ID|STATION|DATE
    const qrData = `POUCH|${pouchData.id}|${pouchData.station}|${pouchData.date}`;
    generateQRCode('pouchQRCode', qrData);
    
    // Show print button
    const printBtn = document.getElementById('printQRCode');
    if (printBtn) {
        printBtn.style.display = 'inline-block';
    }
}

function printQRCode() {
    const qrCodeContainer = document.getElementById('qrCodeContainer');
    if (!qrCodeContainer) return;
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write('<html><head><title>Print QR Code</title>');
    printWindow.document.write('<style>body { text-align: center; } .qr-container { margin: 20px auto; }</style>');
    printWindow.document.write('</head><body>');
    printWindow.document.write('<div class="qr-container">');
    printWindow.document.write(qrCodeContainer.innerHTML);
    printWindow.document.write('</div>');
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
    printWindow.close();
}

// Data persistence using localStorage
const DataStore = {
    // Save data to localStorage
    save: function(key, data) {
        try {
            localStorage.setItem(key, JSON.stringify(data));
            return true;
        } catch (e) {
            console.error('Error saving data:', e);
            return false;
        }
    },
    
    // Get data from localStorage
    get: function(key) {
        try {
            const data = localStorage.getItem(key);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('Error retrieving data:', e);
            return null;
        }
    },
    
    // Remove data from localStorage
    remove: function(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            console.error('Error removing data:', e);
            return false;
        }
    },
    
    // Clear all data from localStorage
    clear: function() {
        try {
            localStorage.clear();
            return true;
        } catch (e) {
            console.error('Error clearing data:', e);
            return false;
        }
    }
};

// Inventory management functions
const InventoryManager = {
    // Get all inventory data
    getAllInventory: function() {
        return DataStore.get('inventory') || {};
    },
    
    // Get station inventory
    getStationInventory: function(station) {
        const inventory = this.getAllInventory();
        return inventory[station] || { float: {}, pouch: {} };
    },
    
    // Add inventory to station
    addInventory: function(station, type, drug, lot, quantity, expiry) {
        const inventory = this.getAllInventory();
        
        if (!inventory[station]) {
            inventory[station] = { float: {}, pouch: {} };
        }
        
        if (!inventory[station][type][drug]) {
            inventory[station][type][drug] = [];
        }
        
        // Check if lot already exists
        const existingLotIndex = inventory[station][type][drug].findIndex(item => item.lot === lot);
        
        if (existingLotIndex >= 0) {
            // Update existing lot
            inventory[station][type][drug][existingLotIndex].quantity += parseInt(quantity);
            inventory[station][type][drug][existingLotIndex].expiry = expiry;
        } else {
            // Add new lot
            inventory[station][type][drug].push({
                lot: lot,
                quantity: parseInt(quantity),
                expiry: expiry
            });
        }
        
        return DataStore.save('inventory', inventory);
    },
    
    // Transfer inventory between stations
    transferInventory: function(fromStation, toStation, type, drug, lot, quantity) {
        const inventory = this.getAllInventory();
        
        if (!inventory[fromStation] || !inventory[fromStation][type][drug]) {
            return false;
        }
        
        // Find the lot in the source station
        const lotIndex = inventory[fromStation][type][drug].findIndex(item => item.lot === lot);
        
        if (lotIndex < 0) {
            return false;
        }
        
        const lotItem = inventory[fromStation][type][drug][lotIndex];
        
        // Check if there's enough quantity
        if (lotItem.quantity < parseInt(quantity)) {
            return false;
        }
        
        // Reduce quantity from source
        lotItem.quantity -= parseInt(quantity);
        
        // Remove lot if quantity is 0
        if (lotItem.quantity <= 0) {
            inventory[fromStation][type][drug].splice(lotIndex, 1);
        }
        
        // Add to destination
        if (!inventory[toStation]) {
            inventory[toStation] = { float: {}, pouch: {} };
        }
        
        if (!inventory[toStation][type][drug]) {
            inventory[toStation][type][drug] = [];
        }
        
        // Check if lot already exists in destination
        const destLotIndex = inventory[toStation][type][drug].findIndex(item => item.lot === lot);
        
        if (destLotIndex >= 0) {
            // Update existing lot
            inventory[toStation][type][drug][destLotIndex].quantity += parseInt(quantity);
        } else {
            // Add new lot
            inventory[toStation][type][drug].push({
                lot: lot,
                quantity: parseInt(quantity),
                expiry: lotItem.expiry
            });
        }
        
        return DataStore.save('inventory', inventory);
    }
};

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize sidebar toggle
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarCollapse && sidebar) {
        sidebarCollapse.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
    
    // Initialize form validation
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(form.id)) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });
    
    // Initialize QR code generation buttons
    const generateDrugQRBtn = document.getElementById('generateDrugQR');
    if (generateDrugQRBtn) {
        generateDrugQRBtn.addEventListener('click', function() {
            const drugName = document.getElementById('drugName').value;
            const lotNumber = document.getElementById('lotNumber').value;
            const expiryDate = document.getElementById('expiryDate').value;
            const quantity = document.getElementById('quantity').value;
            
            if (drugName && lotNumber && expiryDate && quantity) {
                generateDrugQRCode({
                    name: drugName,
                    lot: lotNumber,
                    expiry: expiryDate,
                    quantity: quantity
                });
            } else {
                alert('Please fill in all fields to generate QR code');
            }
        });
    }
    
    const generatePouchQRBtn = document.getElementById('generatePouchQR');
    if (generatePouchQRBtn) {
        generatePouchQRBtn.addEventListener('click', function() {
            const pouchId = document.getElementById('pouchId').value;
            const station = document.getElementById('station').value;
            const date = new Date().toISOString().split('T')[0];
            
            if (pouchId && station) {
                generatePouchQRCode({
                    id: pouchId,
                    station: station,
                    date: date
                });
            } else {
                alert('Please fill in all fields to generate QR code');
            }
        });
    }
    
    const printQRBtn = document.getElementById('printQRCode');
    if (printQRBtn) {
        printQRBtn.addEventListener('click', printQRCode);
    }
    
    // Load initial data
    initializeData();
});

// Initialize sample data if none exists
function initializeData() {
    // Check if inventory data exists
    if (!DataStore.get('inventory')) {
        // Create sample inventory data
        const sampleInventory = {
            'AJAX': {
                float: {
                    'Morphine': [
                        { lot: 'M2345', quantity: 76, expiry: '2026-05-15' }
                    ],
                    'Fentanyl': [
                        { lot: 'F1023', quantity: 54, expiry: '2026-03-20' }
                    ],
                    'Midazolam': [
                        { lot: 'M5561', quantity: 83, expiry: '2026-06-10' }
                    ],
                    'Ketamine': [
                        { lot: 'K8712', quantity: 67, expiry: '2026-04-25' }
                    ],
                    'Hydromorphone': [
                        { lot: 'H9901', quantity: 49, expiry: '2026-07-05' }
                    ]
                },
                pouch: {
                    'Morphine': [
                        { lot: 'M2345', quantity: 12, expiry: '2026-05-15' }
                    ],
                    'Fentanyl': [
                        { lot: 'F1023', quantity: 15, expiry: '2026-03-20' }
                    ],
                    'Midazolam': [
                        { lot: 'M5561', quantity: 11, expiry: '2026-06-10' }
                    ],
                    'Ketamine': [
                        { lot: 'K8712', quantity: 21, expiry: '2026-04-25' }
                    ],
                    'Hydromorphone': [
                        { lot: 'H9901', quantity: 24, expiry: '2026-07-05' }
                    ]
                }
            },
            'WHITBY': {
                float: {
                    'Morphine': [
                        { lot: 'M2345', quantity: 65, expiry: '2026-05-15' }
                    ],
                    'Fentanyl': [
                        { lot: 'F1023', quantity: 42, expiry: '2026-03-20' }
                    ],
                    'Midazolam': [
                        { lot: 'M5561', quantity: 79, expiry: '2026-06-10' }
                    ],
                    'Ketamine': [
                        { lot: 'K8712', quantity: 88, expiry: '2026-04-25' }
                    ],
                    'Hydromorphone': [
                        { lot: 'H9901', quantity: 58, expiry: '2026-07-05' }
                    ]
                },
                pouch: {
                    'Morphine': [
                        { lot: 'M2345', quantity: 20, expiry: '2026-05-15' }
                    ],
                    'Fentanyl': [
                        { lot: 'F1023', quantity: 13, expiry: '2026-03-20' }
                    ],
                    'Midazolam': [
                        { lot: 'M5561', quantity: 24, expiry: '2026-06-10' }
                    ],
                    'Ketamine': [
                        { lot: 'K8712', quantity: 27, expiry: '2026-04-25' }
                    ],
                    'Hydromorphone': [
                        { lot: 'H9901', quantity: 18, expiry: '2026-07-05' }
                    ]
                }
            }
        };
        
        DataStore.save('inventory', sampleInventory);
    }
}
