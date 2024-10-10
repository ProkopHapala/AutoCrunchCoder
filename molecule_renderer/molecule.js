// molecule.js
import * as THREE from 'three';
import { ELEMENTS } from './elements.js';

// Function to create the element dictionary
function elementDict(ELEMENTS) {
    const dic = {};
    for (const elem of ELEMENTS) {
        dic[elem[1]] = elem;
    }
    return dic;
}

// Create the ELEMENT_DICT
const ELEMENT_DICT = elementDict(ELEMENTS);

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
        const bondFactor = 1.2; // Bond factor for covalent radii

        for (let i = 0; i < this.atomPositions.length; i++) {
            for (let j = i + 1; j < this.atomPositions.length; j++) {
                const atom1 = this.atomPositions[i];
                const atom2 = this.atomPositions[j];
                const radius1 = ELEMENT_DICT[atom1.symbol][6]; // Covalent radius of atom1
                const radius2 = ELEMENT_DICT[atom2.symbol][6]; // Covalent radius of atom2

                
                const bondThreshold = bondFactor * (radius1 + radius2);

                const distance = this.atomVectors[i].distanceTo(this.atomVectors[j]);

                console.log( `try bond [${i},${j}] `, distance, radius1 + radius2, radius1, radius2 );

                if (distance < bondThreshold) {
                    bonds.push({ atom1: i, atom2: j });
                }
            }
        }

        console.log('Generated bonds:', bonds);
        return bonds;
    }
}
