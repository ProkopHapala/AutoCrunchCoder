// selectionManager.js
import * as THREE from 'three';

export class SelectionManager {
    constructor(scene, camera) {
        this.scene = scene;
        this.camera = camera;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.selectedAtoms = [];
    }

    onMouseClick(event) {
        this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
        this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

        this.raycaster.setFromCamera(this.mouse, this.camera);
        const intersects = this.raycaster.intersectObjects(this.scene.children, true);

        console.log('Mouse coordinates:', this.mouse);
        console.log('Intersected objects:', intersects);

        if (intersects.length > 0) {
            const selectedAtom = intersects[0].object;
            console.log('Selected atom:', selectedAtom.userData);
            if (selectedAtom.userData && selectedAtom.userData.symbol) {
                this.selectedAtoms.push(selectedAtom.userData);
                this.updateSelectionList();
            }
        }
    }

    updateSelectionList() {
        const selectionList = document.getElementById('selectionList');
        selectionList.innerHTML = '';
        this.selectedAtoms.forEach(atom => {
            const li = document.createElement('li');
            li.textContent = `Type: ${atom.symbol}, Position: (${atom.position.x.toFixed(2)}, ${atom.position.y.toFixed(2)}, ${atom.position.z.toFixed(2)})`;
            selectionList.appendChild(li);
        });
    }
}
