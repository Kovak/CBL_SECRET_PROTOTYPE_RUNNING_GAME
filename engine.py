import kivy
from kivy.core.image import Image as CoreImage
import pygame
import os
import re

class ArtContainer():
    # This class just reads all the image files from a directory ONCE and stores them all as textures that can be instantly 
    # accessed using get(file_location). This will be super fast once the program is running, but if we want to optimize
    # for RAM usage and startup time, then we should extend this class to read atlases as well.

    # filenames that match these REs should be imported with pygame.image.load instead of CoreImage.texture
    pygame_res = [re.compile(r'scaffolding-*'),]

    def __init__(self, base_dir):
        self.textures = {}
        for (path, dirs, files) in os.walk(base_dir):
            for f in files:
                if f.endswith('.png'):
                    # if the filename matches at least one of the items in pygame_res, store it as a pygame texture,
                    # otherwise store it as a kivy texture
                    print f
                    if reduce(lambda x,y: x is not None or y is not None,[r.match(f) for r in self.pygame_res]):
                        self.textures[os.path.join(path, f)] = pygame.image.load(os.path.join(path, f))
                        print 'pygame'
                    else:
                        self.textures[os.path.join(path, f)] = CoreImage(os.path.join(path, f)).texture
                        print 'kivy'

    def get(self, key):
        return self.textures[key]