// Door status management for car model
import * as THREE from 'three';
import { CarModel } from './car.js';

// Map to keep track of previous door states to detect changes
var previousDoorStates = {
    "FrontLeft": ["close", "lock"],
    "FrontRight": ["close", "lock"],
    "RearLeft": ["close", "lock"],
    "RearRight": ["close", "lock"],
    "Trunk": ["close", "lock"]
};

// Map door names from the API to the door names used in CarModel
const doorNameMapping = {
    "FrontLeft": "frontLeft",
    "FrontRight": "frontRight",
    "RearLeft": "rearLeft",
    "RearRight": "rearRight"
    // "Trunk" is not implemented in the car model yet
};

// Map lock status to color
function getDoorLockColor(lockStatus) {
    switch (lockStatus) {
        case 'unlock': return { r: 0.0, g: 1.0, b: 0.0 };  // Green for unlocked
        case 'lock': return { r: 1.0, g: 0.0, b: 0.0 };    // Red for locked
        default: return { r: 0.5, g: 0.5, b: 0.5 };        // Gray for unknown
    }
}

// Import dataPanel from panel.js
import { dataPanel } from './panel.js';

// Update door models based on door states from the server
function updateDoorStatus(doorStates) {
    // Loop through each door in the received states
    for (const [doorName, state] of Object.entries(doorStates)) {
        // Skip if this door isn't in our mapping (like Trunk which isn't in the model)
        if (!doorNameMapping[doorName]) continue;
        
        const modelDoorName = doorNameMapping[doorName];
        const [openStatus, lockStatus] = state;
        const [prevOpenStatus, prevLockStatus] = previousDoorStates[doorName];
          // Check if open/close status has changed
        if (openStatus !== prevOpenStatus) {
            console.log(`${doorName} open status changed: ${prevOpenStatus} -> ${openStatus}`);
            // True for open, false for close
            animateDoorMovement(modelDoorName, openStatus === 'open');
            
            // Log to data panel
            dataPanel.addEntry('Door', `${doorName} Position`, prevOpenStatus, openStatus);
        }
        
        // Check if lock status has changed
        if (lockStatus !== prevLockStatus) {
            console.log(`${doorName} lock status changed: ${prevLockStatus} -> ${lockStatus}`);
            // Apply color based on lock status
            if (CarModel.carParts && CarModel.carParts.doors && CarModel.carParts.doors[modelDoorName]) {
                const doorModel = CarModel.carParts.doors[modelDoorName].model;
                if (doorModel) {
                    animateDoorColor(doorModel, getDoorLockColor(lockStatus));
                }
            }
            
            // Log to data panel
            dataPanel.addEntry('Door', `${doorName} Lock`, prevLockStatus, lockStatus);
        }
        
        // Update previous state
        previousDoorStates[doorName] = state;
    }
}

// Function to fetch door status from server
async function fetchDoorStatus() {
    try {
        const response = await fetch('/api/door');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const doorData = await response.json();
        updateDoorStatus(doorData);
    } catch (error) {
        if (error instanceof TypeError && error.message.includes("Failed to fetch")) return;
        console.error("Error fetching door status:", error);
    }
}

// Animate door opening/closing
function animateDoorMovement(doorName, open) {
    const door = CarModel.carParts.doors[doorName];
    if (!door.model) return;

    // Store the current position and angle before animation
    const currentPos = door.model.position.clone();
    const currentAngle = door.angle;

    // Define target angle based on door position
    // Since car is facing north (positive X) and east is positive Z:
    // - Left doors (negative Z side) should open counterclockwise (positive angle)
    // - Right doors (positive Z side) should open clockwise (negative angle)
    let targetAngle = 0;
    if (open) {
        if (doorName.includes('Right')) {
            // Right doors open counterclockwise (negative angle)
            targetAngle = Math.PI / 3; // ex: 90 degrees
        } else {
            // Left doors open clockwise (positive angle)
            targetAngle = -Math.PI / 3; // ex: -90 degrees
        }
    }

    // Calculate the base position (position when closed)
    // If we're already open, we need to figure out what the closed position would be
    let basePosition;
    if (currentAngle !== 0) {
        // Calculate vector from hinge to current position
        const currentVector = new THREE.Vector3().subVectors(currentPos, door.hingePoint);
        // Un-rotate this vector to get the original offset
        currentVector.applyAxisAngle(new THREE.Vector3(0, 1, 0), -currentAngle);
        // The base position is the hinge point plus this un-rotated vector
        basePosition = new THREE.Vector3().addVectors(door.hingePoint, currentVector);
    } else {
        // If we're already closed, the current position is the base position
        basePosition = currentPos.clone();
    }

    // Store the vector from hinge to base position
    const baseOffset = new THREE.Vector3().subVectors(basePosition, door.hingePoint);
    
    // Animate the door
    gsap.to(door, {
        angle: targetAngle,
        duration: 1,
        onUpdate: () => {
            // Start from the hinge point
            door.model.position.copy(door.hingePoint);

            // Apply the rotated offset
            const rotatedOffset = baseOffset.clone();
            rotatedOffset.applyAxisAngle(new THREE.Vector3(0, 1, 0), door.angle);
            door.model.position.add(rotatedOffset);

            // Update the door's rotation
            // We need to adjust the rotation based on the initial orientation
            // Since we already have the model rotated 90 degrees on Y (Math.PI/2)
            door.model.rotation.y = Math.PI / 2 + door.angle;
        },
        onComplete: () => {
            // Update the door's open state
            door.open = open;
        }
    });
}

// Animate the color of a specific door model
function animateDoorColor(doorModel, color) {
    if (!doorModel) return;
    
    // Collect all meshes from the door model
    const meshes = [];
    doorModel.traverse(obj => {
        if (obj.isMesh && obj.material) meshes.push(obj);
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
                duration: 0.2, // Duration for fade out
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
}

// Poll the server for door status updates (once per second is sufficient for door status)
setInterval(fetchDoorStatus, ( 288 * 2 ) );
