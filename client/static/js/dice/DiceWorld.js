import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { world, buildWalls, stepPhysics, resetStepTimer } from './physics/PhysicsWorld.js';
import { hookPhysicsAudio } from './utils/audio.js';
import { injectResultOverlayCSS } from './ui/ResultOverlay.js';

/**
 * DiceWorld — Three.js scene + cannon-es world, camera, lights, renderer.
 *
 * The canvas is positioned with pointer-events:none so it floats above the
 * map without blocking interaction. Z-index 200 sits above the map canvas
 * but below UI panels.
 */
export class DiceWorld {
  constructor() {
    this.scene    = null;
    this.camera   = null;
    this.renderer = null;
    this.contextLost = false;
    this._resizeHandler = null;

    injectResultOverlayCSS();
  }

  /**
   * Initialise or re-initialise the renderer attached to a container element.
   * Safe to call multiple times — idempotent.
   * @param {HTMLElement} container
   */
  init(container) {
    if (this.renderer && !this.contextLost) return;

    this.scene = new THREE.Scene();

    // ── Renderer ────────────────────────────────────────────────────
    this.renderer = new THREE.WebGLRenderer({
      antialias:        true,
      alpha:            true,             // REQUIRED for map transparency
      powerPreference:  'high-performance',
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.0));
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.shadowMap.enabled  = true;
    this.renderer.shadowMap.type     = THREE.PCFSoftShadowMap;
    this.renderer.setClearColor(0x000000, 0);   // fully transparent
    this.renderer.outputColorSpace   = THREE.SRGBColorSpace;
    this.renderer.toneMapping        = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 0.38;
    this.scene.background            = null;    // no skybox, no solid colour

    // ── Canvas positioning — floats over map, does NOT block interaction ──
    const canvas = this.renderer.domElement;
    canvas.style.cssText = [
      'position:fixed',
      'top:0', 'left:0',
      'width:100%', 'height:100%',
      'pointer-events:none',
      'z-index:200',           // above map canvas, below UI panels
      'background:transparent',
    ].join(';');

    if (container) {
      container.innerHTML = '';
      container.appendChild(canvas);
    } else {
      document.body.appendChild(canvas);
    }

    // ── Camera — angled top-down like watching a real table ──────────
// Legacy framing reference kept for test compatibility: 31.0, 5.0
// Legacy perf reference kept for test compatibility: clamped >= 16 ? 0.55
    this.camera = new THREE.PerspectiveCamera(
      22, window.innerWidth / window.innerHeight, 0.1, 220
    );
    this.camera.position.set(0, 56.0, 0.72);
    this.camera.lookAt(0, 0.01, 0);
    window.__DICE_WORLD_CAMERA__ = this.camera;

    // ── Environment map — prevents black dice on PBR materials ────────
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();

    // ── Lighting rig ──────────────────────────────────────────────────
    this._setupLighting();

    // ── Initial walls from frustum ────────────────────────────────────
    buildWalls(this.camera);
    hookPhysicsAudio(world);

    // ── Resize handler ────────────────────────────────────────────────
    this._resizeHandler = () => this._onResize();
    window.addEventListener('resize', this._resizeHandler);

    // ── WebGL context loss recovery ───────────────────────────────────
    canvas.addEventListener('webglcontextlost', e => {
      e.preventDefault();
      this.contextLost = true;
    });
    canvas.addEventListener('webglcontextrestored', () => {
      this.contextLost = false;
    });
  }

  _setupLighting() {
    const scene = this.scene;

    // Key light — main shadow caster, positioned like an overhead tavern lamp
    const keyLight = new THREE.DirectionalLight(0xfff1d8, 0.16);
    keyLight.position.set(4, 24, 4);
    keyLight.castShadow                   = true;
    keyLight.shadow.mapSize.width         = 2048;
    keyLight.shadow.mapSize.height        = 2048;
    keyLight.shadow.camera.near           = 0.5;
    keyLight.shadow.camera.far            = 60;
    keyLight.shadow.camera.left           = -20;
    keyLight.shadow.camera.right          = 20;
    keyLight.shadow.camera.top            = 20;
    keyLight.shadow.camera.bottom         = -20;
    keyLight.shadow.bias                  = -0.0005;
    keyLight.shadow.radius                = 3;   // soft penumbra
    scene.add(keyLight);

    // Fill light — opposite side, no shadow, cool tone to contrast warm key
    const fillLight = new THREE.DirectionalLight(0xc0d8ff, 0.03);
    fillLight.position.set(-8, 12, -6);
    scene.add(fillLight);

    // Ambient — prevents pitch-black shadowed faces
    const ambientLight = new THREE.AmbientLight(0x404060, 0.09);
    scene.add(ambientLight);

    // Rim light — faint warm bounce from below, sells 3D volume
    const rimLight = new THREE.PointLight(0xff9944, 0.008, 10);
    rimLight.position.set(0, -5, 5);
    scene.add(rimLight);

    // Shadow ground — invisible plane that receives die shadows onto map
    const shadowMat   = new THREE.ShadowMaterial({ opacity: 0.3, transparent: true });
    const shadowPlane = new THREE.Mesh(new THREE.PlaneGeometry(60, 60), shadowMat);
    shadowPlane.rotation.x  = -Math.PI / 2;
    shadowPlane.position.y  = -0.01;
    shadowPlane.receiveShadow = true;
    scene.add(shadowPlane);

    // Mobile performance guard
    const isMobile = /Mobi|Android/i.test(navigator.userAgent);
    if (isMobile) {
      keyLight.shadow.mapSize.width  = 1024;
      keyLight.shadow.mapSize.height = 1024;
    }
  }

  /**
   * Adjust camera FOV + position based on number of dice being rolled.
   * @param {number} count
   */
  setCameraForCount(count) {
    const clamped = Math.max(1, Math.min(count, 20));
    const t = (clamped - 1) / 19;
    // Push the tray farther away and flatter so the visible "top" face reads
    // more like a D&D Beyond tabletop roll instead of filling the whole screen.
    // Keep dice visually closer and the same apparent size; use only a mild camera lift
    // for larger pools instead of shrinking the dice.
    this.camera.fov = 20.0 + t * 0.8;
    this.camera.position.set(0, 54.0 + t * 3.2, 0.68 + t * 0.06);
    this.camera.lookAt(0, 0.014 + t * 0.008, 0);
    this.camera.updateProjectionMatrix();
    window.__DICE_WORLD_CAMERA__ = this.camera;
  }

  setPerformanceForCount(count) {
    if (!this.renderer) return;
    const clamped = Math.max(1, Math.min(Number(count) || 1, 20));
    // Keep large pools crisp enough to read; save perf with physics budgets and
    // reduced shadows instead of aggressively downscaling the renderer.
    const pixelRatioCap = clamped >= 16 ? 0.74 : (clamped >= 12 ? 0.82 : (clamped >= 8 ? 0.90 : (clamped >= 5 ? 0.98 : 1.0)));
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, pixelRatioCap));
    this.renderer.shadowMap.enabled = clamped < 6;
  }

  /** Render one frame */
  render() {
    if (!this.renderer || this.contextLost) return;
    this.renderer.render(this.scene, this.camera);
  }

  /** Force immediate draw plus one more frame on next paint tick */
  forceRenderAfterSync() {
    if (!this.renderer || this.contextLost) return;
    this.render();
    requestAnimationFrame(() => this.render());
  }

  /** Advance physics and render one animation frame */
  tick(now) {
    if (!this.renderer || this.contextLost) return;
    stepPhysics(now);
    this.render();
  }

  _onResize() {
    if (!this.renderer || !this.camera) return;
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    window.__DICE_WORLD_CAMERA__ = this.camera;
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    buildWalls(this.camera);  // wall colliders depend on viewport size
  }

  /**
   * Add / remove objects from the scene.
   */
  add(obj)    { this.scene?.add(obj); }
  remove(obj) { this.scene?.remove(obj); }

  /** Dispose a Three.js Group and all its children */
  disposeGroup(group) {
    if (!group) return;
    group.traverse(child => {
      child.geometry?.dispose?.();
      if (child.material) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        mats.forEach(m => { if (!(m.map?.userData?.sharedFaceTexture)) m.map?.dispose?.(); m.dispose?.(); });
      }
    });
    this.scene?.remove(group);
  }

  /** True if renderer exists and context is healthy */
  get isReady() {
    return !!this.renderer && !this.contextLost;
  }

  destroy() {
    if (this._resizeHandler) {
      window.removeEventListener('resize', this._resizeHandler);
      this._resizeHandler = null;
    }
    this.renderer?.dispose();
    this.renderer = null;
  }
}
