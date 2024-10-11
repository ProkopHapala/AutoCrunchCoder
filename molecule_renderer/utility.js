// utility.js
import * as THREE from 'three';

export function renderAxisArrows(scene) {
    const axisHelper = new THREE.AxesHelper(5);
    scene.add(axisHelper);
}
