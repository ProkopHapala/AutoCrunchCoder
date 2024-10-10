// selectionManager.js
import * as THREE from 'three';

export class SelectionManager {
    constructor(scene, camera) {
        this.scene = scene;
        this.camera = camera;
        this.raycaster = new THREE.Raycaster();
        this.mouse = new THREE.Vector2();
        this.selectedAtoms = new Set();
        this.selectionInput = document.getElementById('selectionInput');
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
                const atomIndex = this.scene.children.indexOf(selectedAtom);
                if (this.selectedAtoms.has(atomIndex)) {
                    this.selectedAtoms.delete(atomIndex);
                } else {
                    this.selectedAtoms.add(atomIndex);
                }
                this.updateSelectionInput();
            }
        }
    }

    updateSelectionInput() {
        const selectedIndexes = Array.from(this.selectedAtoms).join(', ');
        this.selectionInput.value = selectedIndexes;
    }
}
