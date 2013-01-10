import kivy
from kivy.core.image import Image as CoreImage
import os


class ArtContainer():
    # This class just reads all the image files from a directory ONCE and stores them all as textures that can be instantly 
    # accessed using get(file_location). This will be super fast once the program is running, but if we want to optimize
    # for RAM usage and startup time, then we should extend this class to read atlases as well.
    def __init__(self, base_dir):
        self.textures = {}
        for (path, dirs, files) in os.walk(base_dir):
            for f in files:
                if f.endswith('.png'):
                    print os.path.join(path, f)
                    self.textures[os.path.join(path, f)] = CoreImage(os.path.join(path, f)).texture

    def get(self, key):
        return self.textures[key]