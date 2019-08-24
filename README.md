# Battalion Wars Model Viewer

This tool can view the 3d models of Battalion Wars and Battalion Wars 2.

It opens .res or .res.gz files (resource archive of BW1 or BW2 containing models, textures, sounds and more) and 
displays models. After opening an archive you will see a list of model names on the right that you can click to view the model.

Model->Export current as OBJ exports the current model in the OBJ format. Transformations will be backed into the 
vertex positions. Each node of the model (that contains geometry) will become a separate object in the obj file. 
Textures are also exported as .png but only the diffuse texture is used by the obj file.

Model->Export All as OBJ is similar to "Export current as OBJ" but it exports every model from the currently 
loaded archive into the chosen folder in a row. Each model is put into a folder named after the model. This process
takes some time, you can see the progress in the bar in the lower left corner of the program. With models you might
temporarily see messed up textures in the renderer, this is purely visual and has no effect on the actual exported files.

Textures->Export All Textures as PNG exports every texture in the currently loaded archive to the chosen folder. This
includes textures that are not used by any model. This is useful for exporting many UI-based textures.

Some model parts might appear offset. In such cases it's recommended to check ingame in Dolphin (using freeview
or just getting close to such an unit) what the actual position of the model parts is supposed to be and 
adjust it according to that.

Controls:

* W, A, S, D - horizontal movement 
* Q, E - Move upwards or downwards
* Holding shift while moving makes you go faster
* Right mouse button + mouse movement - rotates camera view
* R, T - rotates model in-place. Hold shift to rotate faster
* Arrow Key Up/Down - Select previous/next model in model list

Note for 3ds Max users: If you have trouble importing the exported obj files, try enabling the import option 
that says "Import as single mesh".

# Download
Check https://github.com/RenolY2/bw-model-viewer/releases for compiled releases

For anybody else who wants to run the editor from the source code, you need the following:
- Python 3.6.6 or newer
- PyQt5
- PyOpenGL

Once everything is installed, you can open the editor by running bw_model_viewer.py