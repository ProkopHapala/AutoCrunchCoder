# molecule_renderer

Standalone web-based 3D molecule viewer using Three.js. No Python dependency for rendering — `server.py` is just a convenience static file server. Atoms are rendered as spheres, bonds as cylinders positioned and rotated from the two atom vectors.

## Files

- `moleculeRenderer.js` — `MoleculeRenderer` class: `renderMolecule()` creates sphere meshes for atoms and cylinder meshes for bonds; positions/rotates bonds from the two atom position vectors.
- `molecule.js` — `Molecule` class: atom symbols, positions, and automatic bond generation by distance threshold.
- `sceneSetup.js` — Camera, lights, and Three.js renderer configuration.
- `selectionManager.js` — Click/selection handling for individual atoms.
- `utility.js` — Shared utility functions.
- `server.py` — Minimal `http.server` static file server for local preview.
- `index.html` — Entry point: loads Three.js and renderer modules.

Open `index.html` in a browser (or run `python server.py`) to use the viewer.
