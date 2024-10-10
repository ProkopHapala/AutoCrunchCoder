// renderer.js
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';

// Set up the scene, camera, and renderer
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer();
renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);

// Create a directional light for Phong shading
const light = new THREE.DirectionalLight(0xffffff, 1);
light.position.set(1, 1, 1).normalize();
scene.add(light);

// Set up OrbitControls for camera rotation
const controls = new OrbitControls(camera, renderer.domElement);

// Function to parse .xyz file
function parseXYZFile(fileContent) {
    console.log('Parsing .xyz file...');
    const lines = fileContent.split('\n');
    const numAtoms = parseInt(lines[0], 10);
    console.log(`Number of atoms: ${numAtoms}`);
    const atomPositions = [];

    for (let i = 2; i < 2 + numAtoms; i++) {
        const [symbol, x, y, z] = lines[i].trim().split(/\s+/);
        atomPositions.push({ symbol, x: parseFloat(x), y: parseFloat(y), z: parseFloat(z) });
    }

    console.log('Parsed atom positions:', atomPositions);
    return atomPositions;
}

// Function to generate bonds based on distance
function generateBonds(atomPositions) {
    console.log('Generating bonds...');
    const bonds = [];
    const bondThreshold = 2.0; // Angstroms

    for (let i = 0; i < atomPositions.length; i++) {
        for (let j = i + 1; j < atomPositions.length; j++) {
            const distance = new THREE.Vector3(atomPositions[i].x, atomPositions[i].y, atomPositions[i].z)
                .distanceTo(new THREE.Vector3(atomPositions[j].x, atomPositions[j].y, atomPositions[j].z));

            if (distance < bondThreshold) {
                bonds.push({ atom1: i, atom2: j });
            }
        }
    }

    console.log('Generated bonds:', bonds);
    return bonds;
}

// Function to render the molecule
function renderMolecule(atomPositions) {
    console.log('Rendering molecule...');

    // Convert atom positions to THREE.Vector3 objects
    const atomVectors = atomPositions.map(atom => new THREE.Vector3(atom.x, atom.y, atom.z));

    // Add atoms to the scene
    atomPositions.forEach((atom, index) => {
        const sphereGeometry = new THREE.SphereGeometry(0.3, 32, 32);
        const material = new THREE.MeshPhongMaterial({ color: atom.symbol === 'O' ? 0xff0000 : 0x0000ff });
        const sphere = new THREE.Mesh(sphereGeometry, material);
        sphere.position.set(atomVectors[index].x, atomVectors[index].y, atomVectors[index].z);
        sphere.userData = { symbol: atom.symbol, position: atomVectors[index] };
        scene.add(sphere);
    });

    // Generate bonds
    const bonds = generateBonds(atomPositions);

    // Add bonds to the scene
    bonds.forEach(pair => {
        const start = atomVectors[pair.atom1];
        const end = atomVectors[pair.atom2];
        const distance = start.distanceTo(end);

        const bondGeometry = new THREE.CylinderGeometry(0.1, 0.1, distance, 32);
        const bondMaterial = new THREE.MeshPhongMaterial({ color: 0x808080 });
        const bond = new THREE.Mesh(bondGeometry, bondMaterial);

        // Position the bond at the midpoint between the two atoms
        const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
        bond.position.set(midPoint.x, midPoint.y, midPoint.z);

        // Rotate the bond to align with the line between the two atoms
        const direction = new THREE.Vector3().subVectors(end, start).normalize();
        const quaternion = new THREE.Quaternion();
        quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
        bond.quaternion.copy(quaternion);

        scene.add(bond);
    });

    console.log('Molecule rendered.');
}

// Function to render axis arrows
function renderAxisArrows() {
    const axisHelper = new THREE.AxesHelper(5);
    scene.add(axisHelper);
}

// Handle file input
document.getElementById('fileInput').addEventListener('change', (event) => {
    console.log('File input changed.');
    const file = event.target.files[0];
    const reader = new FileReader();

    reader.onload = (e) => {
        console.log('File loaded.');
        const fileContent = e.target.result;
        const atomPositions = parseXYZFile(fileContent);
        renderMolecule(atomPositions);
    };

    reader.readAsText(file);
});

// Position the camera
camera.position.z = 5;

// Render axis arrows
renderAxisArrows();

// Initial hardcoded H2O molecule
const initialAtomPositions = [
    { symbol: 'O', x: 0, y: 0, z: 0 },
    { symbol: 'H', x: 0.9584, y: 0, z: 0.0 },
    { symbol: 'H', x: -0.2396, y: 0.9266, z: 0.0 }
];
renderMolecule(initialAtomPositions);

// Mouse picking and selection
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const selectedAtoms = [];

function onMouseClick(event) {
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(scene.children, true);

    console.log('Mouse coordinates:', mouse);
    console.log('Intersected objects:', intersects);

    if (intersects.length > 0) {
        const selectedAtom = intersects[0].object;
        console.log('Selected atom:', selectedAtom.userData);
        if (selectedAtom.userData && selectedAtom.userData.symbol) {
            selectedAtoms.push(selectedAtom.userData);
            updateSelectionList();
        }
    }
}

function updateSelectionList() {
    const selectionList = document.getElementById('selectionList');
    selectionList.innerHTML = '';
    selectedAtoms.forEach(atom => {
        const li = document.createElement('li');
        li.textContent = `Type: ${atom.symbol}, Position: (${atom.position.x.toFixed(2)}, ${atom.position.y.toFixed(2)}, ${atom.position.z.toFixed(2)})`;
        selectionList.appendChild(li);
    });
}

document.addEventListener('click', onMouseClick);

// Render the scene
function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}
animate();
