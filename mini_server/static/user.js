// User model management for ranging visualization
import * as THREE from 'three';
import { gSceneManager } from './scene.js';
import { dataPanel } from './panel.js';

/**
 * UserModelManager class
 * Handles loading and positioning of the user model in the scene
 * for visualizing ranging information
 */
class UserModelManager {
    constructor() {
        // Scale factor to adjust the distance visualization
        // [+] Higher values make the user appear further away
        // [+] Lower values make them appear closer
        // [+] 1 is exact scale, no adjustments
        this.scale = 2;

        // User model container
        this.model = null;
        
        // Default position values
        this.defaultDistance = 6.0;
        this.defaultHeight = 0.0;
        
        // Store original material properties for all loaded meshes
        this.originalMaterialProps = new Map();
        
        // Track if model is loaded
        this.isLoaded = false;
        
        // Distance line properties
        this.distanceLine = null;
        this.distanceLabel = null;
        this.firstPathPower = 0; // Default value, will be updated from ranging data
        
        // Animation properties
        this.targetPosition = new THREE.Vector3(this.defaultDistance, this.defaultHeight, this.defaultDistance);
        this.targetRotation = 0;
        this.animationDuration = 0.5; // Animation duration in seconds
        this.animationProgress = 0;
        this.isIdling = true;
        this.prevPosition = new THREE.Vector3(this.defaultDistance, this.defaultHeight, this.defaultDistance);
        this.prevRotation = 0;
        this.trueDistance = 0;
        
        // Create HTML overlay for the distance label
        this.createDistanceLabelOverlay();
        
        // Set up loader
        this.loader = gSceneManager.createGLTFLoader();
        
        // Load the model
        this.loadModel("user");
    }    
    
    /**
     * Create HTML overlay for distance label
     */
    createDistanceLabelOverlay() {
        // Create a container for the distance label
        const container = document.createElement('div');
        container.id = 'distance-label-container';
        container.style.position = 'absolute';
        container.style.top = '0';
        container.style.left = '0';
        container.style.pointerEvents = 'none';
        container.style.width = '100%';
        container.style.height = '100%';
        container.style.zIndex = '1000';
        document.body.appendChild(container);
        
        // Create the distance label element
        this.distanceLabel = document.createElement('div');
        this.distanceLabel.id = 'distance-label';
        this.distanceLabel.style.position = 'absolute';
        this.distanceLabel.style.padding = '5px 10px';
        this.distanceLabel.style.backgroundColor = 'rgba(0, 255, 0, 0.5)';
        this.distanceLabel.style.color = 'white';
        this.distanceLabel.style.borderRadius = '4px';
        this.distanceLabel.style.fontSize = '14px';
        this.distanceLabel.style.fontWeight = 'bold';
        this.distanceLabel.style.fontFamily = 'Arial, sans-serif';
        this.distanceLabel.style.transform = 'translate(-50%, -50%)';
        this.distanceLabel.style.textShadow = '1px 1px 2px rgba(0,0,0,0.5)';
        this.distanceLabel.style.visibility = 'hidden';
        container.appendChild(this.distanceLabel);
          // Set up renderer to update label position and animations after each frame render
        const originalRenderFunction = gSceneManager.renderer.render;
        let lastFrameTime = performance.now();
        
        gSceneManager.renderer.render = (scene, camera) => {
            // Calculate delta time for animation
            const currentTime = performance.now();
            const deltaTime = Math.min((currentTime - lastFrameTime) / 1000, 0.01); // Convert to seconds, cap at 100ms
            lastFrameTime = currentTime;
            
            // Update animation only when needed
            // if (this.isAnimating) {
            // }
            this.updateAnimation(deltaTime);
            
            // Render the scene
            originalRenderFunction.call(gSceneManager.renderer, scene, camera);
            
            // Update label position
            if (this.distanceLabel && this.distanceLabel.style.visibility === 'visible') {
                this.updateLabelPosition();
            }
        };
    }

      /**
     * Create a line between the origin and user model with a distance label
     */
    createDistanceLine() {
        // Don't create line if model isn't loaded
        if (!this.model) return;

        // Create line geometry
        const points = [];
        points.push(new THREE.Vector3(0, 1, 0)); // Origin with slight height offset
        points.push(new THREE.Vector3(
            this.model.position.x,
            1, // Keep line at constant height
            this.model.position.z
        ));
        
        const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);

        // Calculate opacity based on first path power value
        // Range from -100dBm (very weak) to 0dBm (very strong)
        const normalizedPower = Math.min(1, Math.max(0, (this.firstPathPower + 100) / 100));
        const opacity = 0.2 + normalizedPower * 0.8; // Scale to 0.2-1.0 range

        // Create line material with opacity based on firstPathPower
        const lineMaterial = new THREE.LineBasicMaterial({ 
            color: 0xff,
            linewidth: 40,
            transparent: true,
            opacity: opacity
        });

        if(this.model.visible === true) {
            // Reuse any existing line
            if (this.distanceLine) {
                this.distanceLine.geometry = lineGeometry;
                this.distanceLine.material = lineMaterial;
            } else {
                this.distanceLine = new THREE.Line(lineGeometry, lineMaterial);
                gSceneManager.scene.add(this.distanceLine);
            }

            // Update the HTML label with current distance
            if (this.distanceLabel) {
                this.distanceLabel.textContent = `${this.trueDistance.toFixed(3)}cm`;
                this.distanceLabel.style.backgroundColor = `rgba(0, 255, 0, ${opacity})`;
                this.distanceLabel.style.visibility = 'visible';
            }
        } else {
            // If model is not visible, hide the label and line
            if (this.distanceLine) {
                gSceneManager.scene.remove(this.distanceLine);
                this.distanceLine = null;
            }
            if (this.distanceLabel) {
                this.distanceLabel.style.visibility = 'hidden';
            }
        }
    }
    
    /**
     * Update the HTML label position to match the 3D world position
     */
    updateLabelPosition() {
        if (!this.distanceLabel || !this.model || !this.distanceLine) return;
        
        // Get midpoint of the line
        const midPoint = new THREE.Vector3(
            this.model.position.x / 2,
            0.5, // Slightly above the line
            this.model.position.z / 2
        );
        
        // Project 3D position to 2D screen coordinates
        const widthHalf = window.innerWidth / 2;
        const heightHalf = window.innerHeight / 2;
        
        // Clone the midpoint and project it
        const projected = midPoint.clone();
        projected.project(gSceneManager.camera);
        
        // Convert to screen coordinates
        const x = (projected.x * widthHalf) + widthHalf;
        const y = -(projected.y * heightHalf) + heightHalf;
        
        // Update label position
        this.distanceLabel.style.left = `${x}px`;
        this.distanceLabel.style.top = `${y}px`;
    }
    
    /**
     * Update the distance line based on first path power
     * @param {number} powerValue - First path power value in dBm
     */
    updateDistanceLineOpacity(powerValue) {
        
        // If line exists, update its opacity
        if (this.distanceLine) {
            // Calculate opacity based on first path power value
            // Range from -100dBm (very weak) to 0dBm (very strong)
            const normalizedPower = Math.min(1, Math.max(0, (powerValue + 100) / 100));
            const opacity = 0.2 + normalizedPower * 0.8; // Scale to 0.2-1.0 range
            
            // Update line opacity
            this.distanceLine.material.opacity = opacity;
            
            // Update label opacity if it exists
            if (this.distanceLabelMesh) {
                this.distanceLabelMesh.material.opacity = opacity;
            }
        }
    }

    loadModel(modelName) {
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.textContent = "Loading user model...";
        }

        // Initialize animation variables if they don't exist
        if (!window.animationModels) {
            window.animationModels = {};
            window.animationMixers = {};
            window.animations = {};
        }

        // Clean up previous model and its animations if it exists
        if (window.animationModels[modelName]) {
            scene.remove(window.animationModels[modelName]);
            if (window.animationMixers[modelName]) {
                window.animationMixers[modelName].stopAllAction();
            }
        }
        
        this.loader.load(
            '/static/business_male_4__low_poly_style.glb',
            (gltf) => {
                // Process the loaded model
                this.model = gltf.scene;
                
                // Store original material properties for later animations
                this.model.traverse(obj => {
                    if (obj.isMesh && obj.material) {
                        const materials = Array.isArray(obj.material) ? obj.material : [obj.material];
                        materials.forEach(mat => {
                            this.originalMaterialProps.set(mat, {
                                color: mat.color ? mat.color.clone() : null,
                                emissive: mat.emissive ? mat.emissive.clone() : null,
                                emissiveIntensity: mat.emissiveIntensity
                            });
                        });
                    }
                });
                
                // Scale the model appropriately (adjust as needed)
                this.model.scale.set(1.0, 1.0, 1.0);
                
                // Update model position
                this.model.position.set(this.defaultDistance, this.defaultHeight, this.defaultDistance);
                
                // Add to scene
                gSceneManager.scene.add(this.model);

                // Store the model reference
                window.animationModels[modelName] = gltf.scene;
                // Create animation mixer for this model
                window.animationMixers[modelName] = new THREE.AnimationMixer(gltf.scene);

                // Extract and store animations
                if (gltf.animations && gltf.animations.length > 0) {
                    window.animations[modelName] = {};

                    const originalClip = gltf.animations[0]; // Assuming "Take 001" is the first animation

                    // --- Create new animation clips based on time ranges ---
                    const clip_walk = this.extractAnimationClip(originalClip, 0.45, 3.14, "Walk");
                    window.animations[modelName][clip_walk.name] = clip_walk;

                    const clip_idle = this.extractAnimationClip(originalClip, 8.2, 16, "Idle");
                    window.animations[modelName][clip_idle.name] = clip_idle;

                    const clip_opendoor = this.extractAnimationClip(originalClip, 3.5, 7, "OpenDoor");  // do we even need this?
                    window.animations[modelName][clip_opendoor.name] = clip_opendoor;

                    // do we need a siting animation?

                    // const clip3 = this.extractAnimationClip(originalClip, 8, 20, "Random");
                    // window.animations[modelName][clip3.name] = clip3;

                    statusElement.textContent = `Model loaded with ${Object.keys(window.animations[modelName]).length} animations!`;
                    // console.log(`Found animations: ${gltf.animations.map(a => a.name).join(', ')}`);
                } else {
                    statusElement.textContent = 'Model loaded but no animations found.';
                }

                // Simplify the model geometry to improve performance
                this.model.traverse(node => {
                    if (node.isMesh) {
                        // Reduce polygon count if the mesh has a geometry with attributes
                        if (node.geometry && node.geometry.attributes && node.geometry.attributes.position) {
                            // Use THREE.BufferGeometryUtils to simplify if available
                            if (THREE.BufferGeometryUtils && THREE.BufferGeometryUtils.mergeVertices) {
                                // Merge vertices that are close to each other
                                node.geometry = THREE.BufferGeometryUtils.mergeVertices(node.geometry, 0.01);
                            }
                            
                            // Optimize the geometry
                            node.geometry.computeBoundingSphere();
                            node.geometry.computeBoundingBox();
                            
                            // Remove unused attributes to save memory
                            if (node.geometry.attributes.color && !node.material.vertexColors) {
                                delete node.geometry.attributes.color;
                            }
                        }
                        
                        // Optimize materials
                        if (node.material) {
                            // Disable unnecessary features
                            node.material.flatShading = true;
                            node.material.needsUpdate = true;
                            
                            // Reduce texture quality if textures exist
                            if (node.material.map) {
                                node.material.map.anisotropy = 1;
                                node.material.map.minFilter = THREE.LinearFilter;
                            }
                        }
                        
                        // Enable frustum culling
                        node.frustumCulled = true;
                    }
                });

                // Update status
                this.isLoaded = true;
            },
            (xhr) => {
                const percentComplete = (xhr.loaded / xhr.total) * 100;
                if (statusElement) {
                    statusElement.textContent = `Loading user model... ${Math.round(percentComplete)}%`;
                }
            },
            (error) => {
                console.error('Error loading user model:', error);
                if (statusElement) {
                    statusElement.textContent = "Error loading user model";
                }
            }
        );
    }

    // Function to properly extract a sub-clip from an animation
    extractAnimationClip(originalClip, startTime, endTime, name) {
        // Validate input times
        if (startTime < 0 || endTime > originalClip.duration || startTime >= endTime) {
            console.error("Invalid time range:", startTime, endTime, "Original duration:", originalClip.duration);
            return null;
        }

        // Create a new AnimationClip
        const newClip = new THREE.AnimationClip(
            name || `${originalClip.name}_${startTime}_${endTime}`, 
            endTime - startTime, // Duration is the difference between end and start
            []
        );

        // Process each track in the original clip
        originalClip.tracks.forEach(origTrack => {
            // We'll need to extract the keyframes in our time range
            const times = [];
            const values = [];
            
            // Find the indices of the keyframes within our time range
            let startIndex = -1;
            let endIndex = -1;
            
            for (let i = 0; i < origTrack.times.length; i++) {
                const time = origTrack.times[i];
                
                if (time >= startTime && startIndex === -1) {
                    startIndex = i;
                }
                
                if (time <= endTime) {
                    endIndex = i;
                } else {
                    break;
                }
            }
            
            // If we didn't find any keyframes in our range, handle edge cases
            if (startIndex === -1) {
                startIndex = 0;
            }
            if (endIndex === -1 || endIndex < startIndex) {
                endIndex = startIndex;
            }
            
            // Include one keyframe before and after our range if available
            if (startIndex > 0) startIndex--;
            if (endIndex < origTrack.times.length - 1) endIndex++;
            
            // Extract the times and values
            const valueSize = origTrack.getValueSize();
            
            for (let i = startIndex; i <= endIndex; i++) {
                const time = origTrack.times[i];
                const adjustedTime = Math.max(0, time - startTime); // Shift time to start from 0
                times.push(adjustedTime);
                
                // Extract the corresponding values
                for (let j = 0; j < valueSize; j++) {
                    values.push(origTrack.values[i * valueSize + j]);
                }
            }
            
            // Create a new track with the extracted data
            let newTrack;
            
            if (origTrack instanceof THREE.QuaternionKeyframeTrack) {
            newTrack = new THREE.QuaternionKeyframeTrack(
                origTrack.name,
                times,
                values
            );
            } else if (origTrack instanceof THREE.VectorKeyframeTrack) {
            newTrack = new THREE.VectorKeyframeTrack(
                origTrack.name,
                times,
                values
            );
            } else if (origTrack instanceof THREE.NumberKeyframeTrack) {
            newTrack = new THREE.NumberKeyframeTrack(
                origTrack.name,
                times,
                values
            );
            } else if (origTrack instanceof THREE.BooleanKeyframeTrack) {
            newTrack = new THREE.BooleanKeyframeTrack(
                origTrack.name,
                times,
                values
            );
            } else if (origTrack instanceof THREE.StringKeyframeTrack) {
            newTrack = new THREE.StringKeyframeTrack(
                origTrack.name,
                times,
                values
            );
            } else {
                console.warn("Unsupported track type:", origTrack);
                return;
            }
            
            newClip.tracks.push(newTrack);
        });
        
        return newClip;
    }

    playAnimation(modelName, animationName) {
        if (!window.currentAnimation) {
            window.currentAnimation = {
                modelName: null,
                animationName: null,
                mixer: null,
                action: null
            };
        }
        
        if (window.currentAnimation.animationName == animationName && window.currentAnimation.modelName == modelName && window.currentAnimation != null) return;
        // if (window.currentAnimation)
        if (!window.animationMixers[modelName] || !window.animations[modelName][animationName]) {
            console.error(`Animation ${animationName} not found`);
            return;
        }
        
        const mixer = window.animationMixers[modelName];
        const clip = window.animations[modelName][animationName];
        
        // Stop any currently playing animation on this model
        mixer.stopAllAction();
        
        // Create and play the new action
        const action = mixer.clipAction(clip);
        action.setLoop(THREE.LoopRepeat);
        action.setDuration(clip.duration);
        action.setEffectiveWeight(1.0);
        action.enabled = true;
        action.paused = false;
        action.reset();
        action.play();
        
        // Store the current animation for reference
        window.currentAnimation = {
            modelName: modelName,
            animationName: animationName,
            mixer: mixer,
            action: action
        };
    }

    // Function to stop all animations for a model
    stopAnimation(modelName) {
        if (window.currentAnimation == null) return;
        if (!window.animationMixers[modelName]) return;

        const mixer = window.animationMixers[modelName];
        const clip = window.animations[modelName][window.currentAnimation.animationName];
        const action = mixer.clipAction(clip);
        action.enabled = false;
        action.paused = true;
        
        mixer.stopAllAction();
        
        if (window.currentAnimation && window.currentAnimation.modelName === modelName) {
            window.currentAnimation = null;
        }
            
        const statusElement = document.getElementById('status');
        statusElement.textContent = `Switched to Idle animation for ${modelName}`;
    }


      /**
     * Update the user model's position based on ranging data
     * @param {object} UserPositionData - Data from the ranging API
     */
    updateFromUserPositionData(UserPositionData) {
        if (!this.model || !UserPositionData) return false;
        
        // Store current position and rotation as previous state for animation
        this.prevPosition.copy(this.model.position);
        this.prevRotation = this.model.rotation.y;
        
        // Set target position and rotation
        this.targetPosition.set((UserPositionData.y/100) * this.scale, this.defaultHeight, (UserPositionData.x/100) * this.scale)
        this.targetRotation = UserPositionData.TurnAngle;
        
        // Handle visibility
        if(UserPositionData.x === 0 && UserPositionData.y === 0) {
            this.model.visible = false;
        }
        else {
            this.model.visible = true;
        }
        
        const movementDistance = this.prevPosition.distanceTo(this.targetPosition);
        this.isIdling = (movementDistance <= 0.1);
        this.animationProgress = 0;

        if (this.isIdling) {
            this.playAnimation("user", "Idle");
            return true;
        }

        this.playAnimation("user", "Walk");
        return true;
    }
    
    /**
     * Update animation for smooth movement
     * @param {number} deltaTime - Time elapsed since last frame in seconds
     */
    updateAnimation(deltaTime) {
        if (!this.model) return;
        
        if (window.animationMixers && window.animationMixers["user"]) {
            window.animationMixers["user"].update(deltaTime);
        }
        
        // Update animation progress
        this.animationProgress += deltaTime / this.animationDuration;
        
        // Clamp progress to 0-1 range
        if (this.animationProgress > 1) {
            this.animationProgress = 1;
            // this.isAnimating = false;

            // Set final position and rotation
            this.model.position.copy(this.targetPosition);
            this.model.rotation.y = this.targetRotation;
            // this.stopAnimation('user');

            this.createDistanceLine();

        }
        else {
            // Use easing function for smoother animation (ease-out cubic)
            const t = 1 - Math.pow(1 - this.animationProgress, 3);
            
            if (window.currentAnimation && window.currentAnimation.action) {
                window.currentAnimation.animationName == "Walk" ? window.currentAnimation.action.timeScale = 4 : window.currentAnimation.action.timeScale = 1;
            }

            // Interpolate position
            const newX = this.prevPosition.x + (this.targetPosition.x - this.prevPosition.x) * t;
            const newZ = this.prevPosition.z + (this.targetPosition.z - this.prevPosition.z) * t;
            
            // Set interpolated position
            this.model.position.set(newX, this.defaultHeight, newZ);
            
            // Interpolate rotation (shortest path)
            const angleDiff = ((this.targetRotation - this.prevRotation) + Math.PI) % (Math.PI * 2) - Math.PI;
            const newRotation = this.prevRotation + angleDiff * t;
            
            this.model.rotation.y = newRotation;
            
            // Update the distance line during animation
            this.createDistanceLine();
        }
    }
}

// Create and export a single instance
export const UserModel = new UserModelManager();
let previousUserData = null;
async function fetchUserStatus() {
    try {
        const response = await fetch('/api/user');
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const userData = await response.json();
        
        // Update the user model with the fetched data
        UserModel.updateFromUserPositionData(userData);
        if(previousUserData)
        {
            for (const [key, value] of Object.entries(userData)) {
                if (previousUserData[key] !== value) {
                    // Log changed values to panel
                    dataPanel.addEntry('User', key, previousUserData[key].toFixed(3), value.toFixed(3));
                }
            }
        }
        // Update previous data
        previousUserData = {...userData};
        return userData; // Return the data for promise chaining
    } catch (error) {
        if (error instanceof TypeError && error.message.includes("Failed to fetch")) return null;
        console.error("Error fetching user status:", error);
        return null;
    }
}

// Poll the server for user data updates
setInterval(fetchUserStatus, ( 288 ) );
