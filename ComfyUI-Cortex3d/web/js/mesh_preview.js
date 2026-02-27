/**
 * CortexMeshPreview — Three.js 离屏网格预览器
 * 支持 OBJ / GLB 拖入画布实时预览。
 */

let _scene, _camera, _renderer, _controls, _mesh;

export const CortexMeshPreview = {
    init(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        loadThreeJs().then(() => _initScene(canvas));
    },
    loadUrl(url) {
        if (!_scene) return;
        _loadFromUrl(url);
    },
};
window.CortexMeshPreview = CortexMeshPreview;

// ── Three.js 动态加载 ────────────────────────────────────────────────────────
async function loadThreeJs() {
    if (window.THREE) return;
    await loadScript("https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js");
}

function loadScript(src) {
    return new Promise((resolve, reject) => {
        if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
        const s = document.createElement("script");
        s.src  = src;
        s.onload  = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
    });
}

// ── 场景初始化 ───────────────────────────────────────────────────────────────
function _initScene(canvas) {
    const THREE = window.THREE;
    _scene    = new THREE.Scene();
    _scene.background = new THREE.Color(0x1a1a2e);

    _camera   = new THREE.PerspectiveCamera(45, canvas.width / canvas.height, 0.01, 1000);
    _camera.position.set(0, 1.5, 3);

    _renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    _renderer.setSize(canvas.width, canvas.height);
    _renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // 环境光 + 方向光
    _scene.add(new THREE.AmbientLight(0xffffff, 0.5));
    const dir = new THREE.DirectionalLight(0xffffff, 1.2);
    dir.position.set(3, 5, 5);
    _scene.add(dir);

    // 网格地面
    const grid = new THREE.GridHelper(4, 20, 0x444466, 0x222244);
    _scene.add(grid);

    _setupOrbitControls(canvas);
    _animate();
    _setupDropZone(canvas);
}

// ── 轨道控制（简版，不依赖 OrbitControls.js）────────────────────────────────
function _setupOrbitControls(canvas) {
    let isDragging = false, lastX = 0, lastY = 0;
    let theta = 0, phi = Math.PI / 4, radius = 3;
    const target = window.THREE ? new window.THREE.Vector3() : null;

    canvas.addEventListener("mousedown", e => { isDragging = true; lastX = e.clientX; lastY = e.clientY; });
    canvas.addEventListener("mouseup",   () => { isDragging = false; });
    canvas.addEventListener("mousemove", e => {
        if (!isDragging || !_camera) return;
        theta -= (e.clientX - lastX) * 0.01;
        phi   -= (e.clientY - lastY) * 0.01;
        phi    = Math.max(0.05, Math.min(Math.PI - 0.05, phi));
        lastX  = e.clientX; lastY = e.clientY;
        _updateCamera(theta, phi, radius, target);
    });
    canvas.addEventListener("wheel", e => {
        radius = Math.max(0.5, radius + e.deltaY * 0.005);
        _updateCamera(theta, phi, radius, target);
    });
}

function _updateCamera(theta, phi, radius, target) {
    if (!_camera || !window.THREE) return;
    const t = target || new window.THREE.Vector3();
    _camera.position.set(
        t.x + radius * Math.sin(phi) * Math.sin(theta),
        t.y + radius * Math.cos(phi),
        t.z + radius * Math.sin(phi) * Math.cos(theta),
    );
    _camera.lookAt(t);
}

// ── 动画循环 ─────────────────────────────────────────────────────────────────
function _animate() {
    requestAnimationFrame(_animate);
    if (_mesh) _mesh.rotation.y += 0.003;
    if (_renderer && _scene && _camera) _renderer.render(_scene, _camera);
}

// ── 拖放加载 OBJ / GLB ───────────────────────────────────────────────────────
function _setupDropZone(canvas) {
    canvas.addEventListener("dragover", e => { e.preventDefault(); canvas.style.outline = "2px solid #7c5cbf"; });
    canvas.addEventListener("dragleave", () => { canvas.style.outline = ""; });
    canvas.addEventListener("drop", e => {
        e.preventDefault(); canvas.style.outline = "";
        const file = e.dataTransfer.files[0];
        if (!file) return;
        const url = URL.createObjectURL(file);
        _loadFromUrl(url, file.name);
    });
}

async function _loadFromUrl(url, name = "") {
    if (!window.THREE || !_scene) return;
    const THREE = window.THREE;
    const ext = (name || url).split(".").pop().toLowerCase();

    // 清除旧网格
    if (_mesh) { _scene.remove(_mesh); _mesh = null; }

    try {
        let geometry;
        if (ext === "obj") {
            geometry = await _parseObjSimple(url);
        } else if (ext === "glb" || ext === "gltf") {
            geometry = await _loadGlbSimple(url);
        } else {
            document.getElementById("cortex3d-info").textContent = `不支持格式: ${ext}`;
            return;
        }
        const mat  = new THREE.MeshStandardMaterial({ color: 0x9c7cbf, roughness: 0.5, metalness: 0.2 });
        _mesh = new THREE.Mesh(geometry, mat);
        // 居中并缩放
        geometry.computeBoundingBox();
        const box    = geometry.boundingBox;
        const center = new THREE.Vector3(); box.getCenter(center);
        const size   = new THREE.Vector3(); box.getSize(size);
        const maxDim = Math.max(size.x, size.y, size.z);
        _mesh.position.sub(center);
        _mesh.scale.setScalar(2 / maxDim);
        _scene.add(_mesh);
        document.getElementById("cortex3d-info").textContent = `已加载: ${name || url.split("/").pop()}`;
    } catch (err) {
        document.getElementById("cortex3d-info").textContent = `加载失败: ${err.message}`;
    }
}

async function _parseObjSimple(url) {
    const THREE = window.THREE;
    const text  = await (await fetch(url)).text();
    const verts = [], faces = [], positions = [];
    for (const line of text.split("\n")) {
        const parts = line.trim().split(/\s+/);
        if (parts[0] === "v") verts.push(+parts[1], +parts[2], +parts[3]);
        if (parts[0] === "f") {
            const idx = parts.slice(1).map(p => (+p.split("/")[0] - 1) * 3);
            for (let i = 1; i < idx.length - 1; i++) {
                [idx[0], idx[i], idx[i + 1]].forEach(k => {
                    positions.push(verts[k], verts[k + 1], verts[k + 2]);
                });
            }
        }
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geo.computeVertexNormals();
    return geo;
}

async function _loadGlbSimple(url) {
    // GLB 加载需要 GLTFLoader；动态注入
    await loadScript("https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/loaders/GLTFLoader.js");
    return new Promise((resolve, reject) => {
        const loader = new window.THREE.GLTFLoader();
        loader.load(url, gltf => {
            let geo = null;
            gltf.scene.traverse(c => {
                if (!geo && c.isMesh) geo = c.geometry.clone();
            });
            geo ? resolve(geo) : reject(new Error("GLB 中未找到 Mesh"));
        }, undefined, reject);
    });
}
