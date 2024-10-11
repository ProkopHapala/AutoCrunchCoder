// moleculeRenderer.js
import * as THREE from 'three';
import { Molecule } from './molecule.js';

export class MoleculeRenderer {
    constructor(scene) {
        this.scene = scene;
    }

    renderMolecule(molecule) {
        console.log('Rendering molecule...');
        const bonds = molecule.generateBonds();

        molecule.atomPositions.forEach((atom, index) => {
            const sphereGeometry = new THREE.SphereGeometry(0.3, 32, 32);
            const material = new THREE.MeshPhongMaterial({ color: atom.symbol === 'O' ? 0xff0000 : 0x0000ff });
            const sphere = new THREE.Mesh(sphereGeometry, material);
            sphere.position.set(molecule.atomVectors[index].x, molecule.atomVectors[index].y, molecule.atomVectors[index].z);
            sphere.userData = { symbol: atom.symbol, position: molecule.atomVectors[index] };
            this.scene.add(sphere);
        });

        bonds.forEach(pair => {
            const start = molecule.atomVectors[pair.atom1];
            const end = molecule.atomVectors[pair.atom2];
            const distance = start.distanceTo(end);

            const bondGeometry = new THREE.CylinderGeometry(0.1, 0.1, distance, 32);
            const bondMaterial = new THREE.MeshPhongMaterial({ color: 0x808080 });
            const bond = new THREE.Mesh(bondGeometry, bondMaterial);

            const midPoint = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
            bond.position.set(midPoint.x, midPoint.y, midPoint.z);

            const direction = new THREE.Vector3().subVectors(end, start).normalize();
            const quaternion = new THREE.Quaternion();
            quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction);
            bond.quaternion.copy(quaternion);

            this.scene.add(bond);
        });

        console.log('Molecule rendered.');
    }
}
