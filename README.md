# Battalion Wars 2 Model Viewer

Opens .res or .res.gz files (resource archive of BW2 containing models, textures, sounds and more) and displays models. 
After opening an archive you will see a list of model names on the right that you can click to view the model.

Model->Export OBJ exports the current model in the OBJ format. Transformations will be backed into the vertex positions. 
Each node of the model (that contains geometry) will become a separate object in the obj file. Textures are also exported as .png
but only the diffuse texture is used by the obj file.

Controls:

* W, A, S, D - horizontal movement 
* Q, E - Move upwards or downwards
* Holding shift while moving makes you go faster
* Right mouse button + mouse movement - rotates camera view
* R, T - rotates model in-place. Hold shift to rotate faster

Note for 3ds Max users: If you have trouble importing the exported obj files, try enabling the import option that says "Import as single mesh".
