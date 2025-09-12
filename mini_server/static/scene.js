import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

/**
 * Shared Scene Manager
 * Handles the common THREE.js elements like scene, renderer, camera, and controls
 * that can be reused across different components
 */
class SceneManager {
    constructor() {
        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color("rgb(255, 255, 255)");

        // Camera setup
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 70);

        // Renderer setup
        this.renderer = new THREE.WebGLRenderer({ antialias: true });
        this.renderer.setSize(window.innerWidth, window.innerHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.shadowMap.enabled = true;
        document.body.appendChild(this.renderer.domElement);

        // Controls setup
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = true;
        this.controls.dampingFactor = 0.05;
        this.controls.enableZoom = true;
        this.controls.enablePan = false;

        // Setup lighting
        this.setupLights();

        // Grid helper
        const gridHelper = new THREE.GridHelper(20, 20);
        this.scene.add(gridHelper);

        const axisHelper = new THREE.AxesHelper(20);
        this.scene.add(axisHelper);
        
        // Setup window resize handling
        window.addEventListener('resize', this.onWindowResize.bind(this));
        
        // Animation loop reference
        this.animationId = null;
        
        // Start animation loop
        this.startAnimationLoop();
    }

    setupLights() {
        // Add ambient light
        const ambientLight = new THREE.AmbientLight(0xffffff, 2);
        this.scene.add(ambientLight);

        // Add directional light
        const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
        directionalLight.position.set(5, 10, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        this.scene.add(directionalLight);
    }
    
    onWindowResize() {
        // Update camera aspect ratio and projection matrix
        this.camera.aspect = window.innerWidth / window.innerHeight;
        this.camera.updateProjectionMatrix();
        
        // Update renderer size
        this.renderer.setSize(window.innerWidth, window.innerHeight);
    }
    
    startAnimationLoop() {
        // Bind the animation function to this instance
        const animate = () => {
            this.animationId = requestAnimationFrame(animate);
            
            // Update controls
            this.controls.update();
            
            // Render scene with camera
            this.renderer.render(this.scene, this.camera);
            // console.log("Scene rendered")
        };
        
        // Start the animation loop
        animate();
    }
    
    stopAnimationLoop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }
    
    /**
     * Create a GLTF loader with DRACO decompression support
     * @returns {GLTFLoader} - Configured GLTF loader
     */
    createGLTFLoader() {
        const loader = new GLTFLoader();
        const dracoLoader = new DRACOLoader();
        dracoLoader.setDecoderPath('https://cdn.jsdelivr.net/npm/three@0.159.0/examples/jsm/libs/draco/');
        loader.setDRACOLoader(dracoLoader);
        return loader;
    }
}

// Create and export a single instance
export const gSceneManager = new SceneManager();
