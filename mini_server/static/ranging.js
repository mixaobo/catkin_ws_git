// Ranging data management
import { dataPanel } from './panel.js';
import { UserModel } from './user.js';

// Keep track of previous ranging data to detect changes
let previousRangingData = null;

// Function to fetch ranging data from server
async function fetchRangingStatus() {
    try {
        const response = await fetch('/api/ranging');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const rangingData = await response.json();
        UserModel.firstPathPower = rangingData["FirstPathPower"]
        UserModel.trueDistance = rangingData["Distance"]
        
        // Check if we have previous data to compare
        if (previousRangingData) {
            // Compare with previous data and log changes
            for (const [key, value] of Object.entries(rangingData)) {
                if (previousRangingData[key] !== value) {
                    // Log changed values to panel
                    dataPanel.addEntry('Ranging', key, previousRangingData[key], value);
                }
            }
        } else {
            // First time data received, log all values
            for (const [key, value] of Object.entries(rangingData)) {
                dataPanel.addEntry('Ranging', key, 'Initial', value);
            }
        }        
        // Update previous data
        previousRangingData = {...rangingData};
        return rangingData; // Return the data for promise chaining
    } catch (error) {
        if (error instanceof TypeError && error.message.includes("Failed to fetch")) return null;
        console.error("Error fetching ranging status:", error);
        return null;
    }
}


// Poll the server for ranging status updates
setInterval(fetchRangingStatus, ( 288 ) );
