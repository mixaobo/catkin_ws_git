/**
 * Connection Status Management
 * This file handles connection status updates from the server and manages visual representations
 * including car model color changes and BLE circle animations.
 */
import { CarModel } from './car.js';
import * as THREE from 'three';

// -----------------------------------------
// Constants and Variables
// -----------------------------------------

// Connection status record
var pre_Connection = {
    "VehicleStatus": "Sleep", 
    "BleStatus": "Disconnected",
    "UwbStatus": "NA"
};

// BLE Circle properties and object
let bleCircleObj = null;
const bleCircleRadius = 4.0;    // meter
const bleCircleMaxRadius = 8.0;
const bleCircleMinRadius = 1.0;
const bleCircleColor = 0x00ffff; // Blue color

// Uwb Circle properties and object
let UwbCircleObj = null;
const UwbCircleRadius = 2.0;    // meter
const UwbCircleMaxRadius = 4.0;
const UwbCircleMinRadius = 1.0;
const UwbCircleColor = 0x00ff00; // Blue color

// -----------------------------------------
// Utility Functions - Status to Visual Mapping
// -----------------------------------------

function getUwbColor(status) {
    switch (status) {
        case 'NA': return { r: 1.0, g: 0.41, b: 0.71 };       // pink
        case 'Ranging': return { r: 0.0, g: 1.0, b: 0.0 };     // green
        case 'CPD': return { r: 1.0, g: 1.0, b: 0.0 };         // yellow
        case 'Mixed': return { r: 0.5, g: 0.0, b: 0.5 };       // purple
        default: return { r: 0.5, g: 0.5, b: 0.5 };            // gray
    }
}

function getBleColor(status) {
    switch (status) {
        case 'Connected': return { r: 0.0, g: 0.0, b: 1.0 };   // blue
        case 'Disconnected': return { r: 1.0, g: 0.0, b: 0.0 }; // red
        default: return { r: 0.5, g: 0.5, b: 0.5 };            // gray
    }
}

function getVehicleBrightness(status) {
    return status === 'Awake' ? 1.5 : 0.15;
}

// Animation functions moved from CarModel.js
function animateCarModelColor(color) {
    // Collect all meshes from the car body and doors
    const meshes = [];
    
    // Collect meshes from body
    if (CarModel.carParts.body) {
        CarModel.carParts.body.traverse(obj => {
            if (obj.isMesh && obj.material) meshes.push(obj);
        });
        // Collect meshes from doors
    }
    else
    {
        return false;
    }

    Object.values(CarModel.carParts.doors).forEach(door => {
        if (door.model) {
            door.model.traverse(obj => {
                if (obj.isMesh && obj.material) meshes.push(obj);
            });
        }
        else
        {
            return false;
        }
    });
    
    
    // Create an object to track animation progress
    const colorObj = { 
        progress: 0,
        r: color.r,
        g: color.g,
        b: color.b
    };
    
    // Animate fade in
    gsap.to(colorObj, {
        progress: 1,
        duration: 0.2, // Duration for fade in
        ease: "power2.out",
        onUpdate: () => {
            // Update each mesh's material color based on interpolation
            meshes.forEach(mesh => {
                const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                materials.forEach(mat => {
                    const orig = CarModel.originalMaterialProps.get(mat);
                    
                    // Interpolate between original color and target color
                    if (mat.color && orig && orig.color) {
                        mat.color.r = orig.color.r * (1 - colorObj.progress) + colorObj.r * colorObj.progress;
                        mat.color.g = orig.color.g * (1 - colorObj.progress) + colorObj.g * colorObj.progress;
                        mat.color.b = orig.color.b * (1 - colorObj.progress) + colorObj.b * colorObj.progress;
                    }
                    
                    // Interpolate emissive color
                    if (mat.emissive && orig && orig.emissive) {
                        mat.emissive.r = orig.emissive.r * (1 - colorObj.progress) + colorObj.r * colorObj.progress;
                        mat.emissive.g = orig.emissive.g * (1 - colorObj.progress) + colorObj.g * colorObj.progress;
                        mat.emissive.b = orig.emissive.b * (1 - colorObj.progress) + colorObj.b * colorObj.progress;
                    }
                    
                    mat.needsUpdate = true;
                });
            });
        },
        onComplete: () => {
            // After reaching full color, start fade out back to original
            gsap.to(colorObj, {
                progress: 0,
                duration: 0.2, // Duration for fade out (slightly longer than fade in)
                ease: "power2.in",
                onUpdate: () => {
                    // Update each mesh's material color based on interpolation
                    meshes.forEach(mesh => {
                        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                        materials.forEach(mat => {
                            const orig = CarModel.originalMaterialProps.get(mat);
                            
                            // Interpolate between target color and original color
                            if (mat.color && orig && orig.color) {
                                mat.color.r = orig.color.r * (1 - colorObj.progress) + colorObj.r * colorObj.progress;
                                mat.color.g = orig.color.g * (1 - colorObj.progress) + colorObj.g * colorObj.progress;
                                mat.color.b = orig.color.b * (1 - colorObj.progress) + colorObj.b * colorObj.progress;
                                mat.color.multiplyScalar(CarModel.currentBrightness);
                            }
                            
                            // Interpolate emissive color
                            if (mat.emissive && orig && orig.emissive) {
                                mat.emissive.r = orig.emissive.r * (1 - colorObj.progress) + colorObj.r * colorObj.progress;
                                mat.emissive.g = orig.emissive.g * (1 - colorObj.progress) + colorObj.g * colorObj.progress;
                                mat.emissive.b = orig.emissive.b * (1 - colorObj.progress) + colorObj.b * colorObj.progress;
                                mat.emissive.multiplyScalar(CarModel.currentBrightness);
                            }
                            
                            mat.needsUpdate = true;
                        });
                    });
                }
            });
        }
    });
    return true;
}

function animateCarModelFade(to) {
    const meshes = [];
    // Collect all meshes from body and doors
    if (CarModel.carParts.body) {
        CarModel.carParts.body.traverse(obj => {
            if (obj.isMesh && obj.material) meshes.push(obj);
        });
    }
    else
    {
        return false;
    }

    Object.values(CarModel.carParts.doors).forEach(door => {
        if (door.model) {
            door.model.traverse(obj => {
                if (obj.isMesh && obj.material) meshes.push(obj);
            });
        }
        else
        {
            return false;
        }
    });

    // Animate brightness, starting from the current brightness level
    const obj = { brightness: CarModel.currentBrightness };
    gsap.to(obj, {
        brightness: to,
        duration: 0.5,
        onUpdate: () => {
            meshes.forEach(mesh => {
                const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
                materials.forEach(mat => {
                    const orig = CarModel.originalMaterialProps.get(mat);
                    if (mat.color && orig && orig.color) {
                        mat.color.copy(orig.color).multiplyScalar(obj.brightness);
                    }
                    if (mat.emissive && orig && orig.emissive) {
                        mat.emissive.copy(orig.emissive).multiplyScalar(obj.brightness);
                    }
                    mat.needsUpdate = true;
                });
            });
        },onComplete: () => {
            // Update the current brightness level
            CarModel.currentBrightness = to;
        }
    });
    return true;
}
var pre_Connection = {
            "VehicleStatus" : "NA", 
            "BleStatus" : "Disconnected",
            "UwbStatus": "NA"
        };
// Import dataPanel from panel.js
import { dataPanel } from './panel.js';

// Update UI elements (implement these functions as needed)
function updateConnectionUI(connection) {
    /*Check for Ble status changed*/
    // Animate the BLE circle when status changes
    
    if(pre_Connection.BleStatus != connection.BleStatus) {
        console.log("BLE Status Changed: " + connection.BleStatus);
        const appliedSts = animateCarModelColor(getBleColor(connection.BleStatus));
        
        // Log to data panel
        dataPanel.addEntry('Connection', 'BLE Status', pre_Connection.BleStatus, connection.BleStatus);
        
        if (connection.BleStatus === "Connected") {
            console.log("BLE connected - showing active region circle");
            bleCircleObj = showCircle(bleCircleObj, bleCircleRadius, bleCircleMaxRadius, bleCircleMinRadius, bleCircleColor);
        } else {
            console.log("BLE disconnected - hiding active region circle");
            hideCircle(bleCircleObj, bleCircleMaxRadius, bleCircleMinRadius);
            bleCircleObj = null; // Clear the circle object
        }
        
        if(appliedSts){
            pre_Connection.BleStatus = connection.BleStatus;
        }
    }
    /*Check for Uwb status changed*/
    else if(pre_Connection.UwbStatus != connection.UwbStatus) {
        console.log("UWB Status Changed: " + connection.UwbStatus);
        // Log to data panel
        dataPanel.addEntry('Connection', 'UWB Status', pre_Connection.UwbStatus, connection.UwbStatus);
        const appliedSts = animateCarModelColor(getUwbColor(connection.UwbStatus));
        if (connection.UwbStatus === "Ranging" || connection.UwbStatus === "Mixed") {
            console.log("Uwb Ranging - showing active region circle");
            UwbCircleObj = showCircle(UwbCircleObj, UwbCircleRadius, UwbCircleMaxRadius, UwbCircleMinRadius, UwbCircleColor);
        } else {
            console.log("Uwb NotRanging - hiding active region circle");
            hideCircle(UwbCircleObj, UwbCircleMaxRadius, UwbCircleMinRadius);
            UwbCircleObj = null; // Clear the circle object
        }
        if(appliedSts){
            pre_Connection.UwbStatus = connection.UwbStatus;
        }
    }
    /*No change*/
    else{
        /*Do nothing*/
    }    /*Check for vehicle status change*/
    if(pre_Connection.VehicleStatus != connection.VehicleStatus) {
        // console.log("Vehicle Status Changed: " + connection.VehicleStatus);
        const appliedSts = animateCarModelFade(getVehicleBrightness(connection.VehicleStatus));
        
        // Log to data panel
        dataPanel.addEntry('Connection', 'Vehicle Status', pre_Connection.VehicleStatus, connection.VehicleStatus);
        if(appliedSts){
            pre_Connection.VehicleStatus = connection.VehicleStatus;
        }
    }
}

// Initialize BLE circle based on current status
function initializeCircles() {
    fetchConnectionStatus().then(() => {
        if (pre_Connection.BleStatus === "Connected") {
            bleCircleObj = showCircle(bleCircleObj, bleCircleRadius, bleCircleMaxRadius, bleCircleMinRadius, bleCircleColor);
        }
        if (pre_Connection.UwbStatus === "Ranging" || pre_Connection.UwbStatus === "Mixed") {
            bleCircleObj = showCircle(UwbCircleObj, UwbCircleRadius, UwbCircleMaxRadius, UwbCircleMinRadius, UwbCircleColor);
        }
    });
}

// Initialize when page loads
initializeCircles();

// Create a BLE circle underneath the car
function createCircle(CircleObj, CircleRadius, CircleObjColor) {
    if (CircleObj) {
        console.warn("BLE circle already exists, removing old one.");
        // Remove existing circle if it exists
        CarModel.scene.remove(CircleObj);
    }
    
    console.log("Creating BLE circle with radius:", CircleRadius, "and color:", CircleObjColor);
    // Create a new circle geometry
    const geometry = new THREE.CircleGeometry(CircleRadius, 64);
    const material = new THREE.MeshBasicMaterial({
        color: CircleObjColor,
        transparent: true,
        opacity: 0.0, // Start invisible
        side: THREE.DoubleSide
    });

    // Create mesh
    CircleObj = new THREE.Mesh(geometry, material);
    
    // Position the circle below the car, facing up
    CircleObj.position.y = 0.01; // Slightly above the ground to prevent z-fighting
    CircleObj.rotation.x = -Math.PI / 2; // Rotate to face up
    
    // Add to scene
    CarModel.scene.add(CircleObj);
    
    return CircleObj;
}

// Animate the connection circle to show (expand and fade in)
function showCircle(CircleObj, CircleRadius, CircleMaxRadius, CircleMinRadius, CircleObjColor) {
    if (!CircleObj) {
        CircleObj = createCircle(CircleObj, CircleRadius, CircleObjColor);
    }
    
    // Animation parameters
    const animParams = { 
        radius: CircleMinRadius, 
        opacity: 0 
    };
    
    // Animation timeline for coordinated animations
    const timeline = gsap.timeline();
    
    // First expand and fade in
    timeline.to(animParams, {
        radius: CircleMaxRadius,
        opacity: 0.6,
        duration: 0.8,
        ease: "power2.out",
        onUpdate: () => {
            // Update the circle geometry and material
            if (CircleObj) {
                // Update geometry (create a new one with current radius)
                const newGeometry = new THREE.CircleGeometry(animParams.radius, 64);
                CircleObj.geometry.dispose();
                CircleObj.geometry = newGeometry;
                
                // Update opacity
                CircleObj.material.opacity = animParams.opacity;
            }
        }
    });
    
    // Then pulsate by slightly contracting and re-expanding
    timeline.to(animParams, {
        radius: CircleMaxRadius * 0.8,
        duration: 0.5,
        ease: "power1.inOut",
        onUpdate: () => {
            if (CircleObj) {
                const newGeometry = new THREE.CircleGeometry(animParams.radius, 64);
                CircleObj.geometry.dispose();
                CircleObj.geometry = newGeometry;
            }
        }
    });
    
    timeline.to(animParams, {
        radius: CircleMaxRadius,
        duration: 0.5,
        ease: "power1.inOut",
        onUpdate: () => {
            if (CircleObj) {
                const newGeometry = new THREE.CircleGeometry(animParams.radius, 64);
                CircleObj.geometry.dispose();
                CircleObj.geometry = newGeometry;
            }
        }
    });
    
    return CircleObj;
}

// Animate the BLE circle to hide (contract and fade out)
function hideCircle(CircleObj, CircleMaxRadius, CircleMinRadius) {
    if (!CircleObj) return;
    
    // Animation parameters
    const animParams = { 
        radius: CircleObj.geometry.parameters.radius || CircleMaxRadius, 
        opacity: CircleObj.material.opacity || 0.6
    };
    
    // Animate contraction and fade out
    gsap.to(animParams, {
        radius: CircleMinRadius,
        opacity: 0,
        duration: 0.6,
        ease: "power2.in",
        onUpdate: () => {
            // Update the circle geometry and material
            if (CircleObj) {
                // Update geometry
                const newGeometry = new THREE.CircleGeometry(animParams.radius, 64);
                CircleObj.geometry.dispose();
                CircleObj.geometry = newGeometry;
                
                // Update opacity
                CircleObj.material.opacity = animParams.opacity;
            }
        },
        onComplete: () => {
            // Remove the circle from scene when animation completes
            if (CircleObj) {
                CarModel.scene.remove(CircleObj);
                CircleObj.geometry.dispose();
                CircleObj.material.dispose();
                CircleObj = null;
            }
        }
    });
}

// Function to fetch door status from server
async function fetchConnectionStatus() {
    try {
        const response = await fetch('/api/connection');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const connectionData = await response.json();
        updateConnectionUI(connectionData);
        return connectionData; // Return the data for promise chaining
    } catch (error) {
        if (error instanceof TypeError && error.message.includes("Failed to fetch")) return null;
        console.error("Error fetching connection status:", error);
        return null;
    }
}

// Poll the server for connection status updates (once per second is sufficient for door status)
setInterval(fetchConnectionStatus, ( 288 * 2 ) );
