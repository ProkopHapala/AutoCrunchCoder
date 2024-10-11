// renderer.js
import { setupScene } from './sceneSetup.js';
import { MoleculeRenderer } from './moleculeRenderer.js';
import { SelectionManager } from './selectionManager.js';
import { renderAxisArrows } from './utility.js';
import { Molecule } from './molecule.js';

// Set up the scene, camera, and renderer
const { scene, camera, renderer, controls } = setupScene();

// Create molecule renderer
const moleculeRenderer = new MoleculeRenderer(scene);

// Create selection manager
const selectionManager = new SelectionManager(scene, camera);

// Handle file input
document.getElementById('fileInput').addEventListener('change', (event) => {
    console.log('File input changed.');
    const file = event.target.files[0];
    const reader = new FileReader();

    reader.onload = (e) => {
        console.log('File loaded.');
        const fileContent = e.target.result;
        const molecule = Molecule.parseXYZFile(fileContent);
        moleculeRenderer.renderMolecule(molecule);
    };

    reader.readAsText(file);
});

// Position the camera
camera.position.z = 5;

// Render axis arrows
renderAxisArrows(scene);

// Initial hardcoded H2O molecule
const initialAtomPositions = [
    { symbol: 'O', x: 0, y: 0, z: 0 },
    { symbol: 'H', x: 0.9584, y: 0, z: 0.0 },
    { symbol: 'H', x: -0.2396, y: 0.9266, z: 0.0 }
];
const initialMolecule = new Molecule(initialAtomPositions);
moleculeRenderer.renderMolecule(initialMolecule);

// Add mouse click event listener
document.addEventListener('click', (event) => selectionManager.onMouseClick(event));

// Render the scene
function animate() {
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}
animate();
