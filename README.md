# Installation

- Install Blender (I am using 4.3.2)
- Install relevant plugins: AutoCam ([https://renderrides.gitbook.io/autocam/welcome/installation](https://renderrides.gitbook.io/autocam/welcome/installation)) and Stop Motion OBJ ([https://github.com/neverhood311/Stop-motion-OBJ](https://github.com/neverhood311/Stop-motion-OBJ))
- AutoCam provides an easy way to generate camera trajectories for rendering. Stop Motion OBJ allows to assemble dynamic objects from a sequence of ply (point cloud) files.
- Note that for the latter, downloading the release zip directly is not the zip that is needed for the add-on! Download links are behind paywall but it is possible to assemble the add-on for free from the source code → just needed to zip and upload the src folder which contains the init python file at the top level, Blender knows how to handle that.
- Check the details on how to use them here: [https://renderrides.gitbook.io/autocam](https://renderrides.gitbook.io/autocam) [https://github.com/neverhood311/Stop-motion-OBJ/wiki](https://github.com/neverhood311/Stop-motion-OBJ/wiki)
- Rendering point clouds: [https://blender.stackexchange.com/questions/310858/how-to-visualize-point-cloud-colors-in-blender-4-0-after-ply-data-import](https://blender.stackexchange.com/questions/310858/how-to-visualize-point-cloud-colors-in-blender-4-0-after-ply-data-import)
- Note that I have already put an example for a camera trajectory with AutoCam there, imported a 4D sequence with Stop Motion OBJ, and hooked up the ply rendering! Please install the plugins to make sure everything is functional but the instructions are mostly so you know how to do it and can add additional sequences. You may get by in this project without doing this yourself and just using what I have already provided.

# Running python code with Blender

Add a line like `alias blender='/Applications/Blender.app/Contents/MacOS/Blender'` to your ~/.zshrc so you can just call commands as `blender ...`

- Example: `blender --factory-startup --background ./marss26.blend --python ./blender_camera_horizontal_poc.py`

# More data and underlying plys
We have more data available and I can provide the ply files for the already imported sequences.