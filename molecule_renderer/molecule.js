// molecule.js
import * as THREE from 'three';

export class Molecule {
    constructor(atomPositions) {
        this.atomPositions = atomPositions;
        this.atomVectors = atomPositions.map(atom => new THREE.Vector3(atom.x, atom.y, atom.z));
    }

    static parseXYZFile(fileContent) {
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
        return new Molecule(atomPositions);
    }

    generateBonds() {
        console.log('Generating bonds...');
        const bonds = [];
        const bondThreshold = 2.0; // Angstroms

        for (let i = 0; i < this.atomPositions.length; i++) {
            for (let j = i + 1; j < this.atomPositions.length; j++) {
                const distance = this.atomVectors[i].distanceTo(this.atomVectors[j]);

                if (distance < bondThreshold) {
                    bonds.push({ atom1: i, atom2: j });
                }
            }
        }

        console.log('Generated bonds:', bonds);
        return bonds;
    }
}
