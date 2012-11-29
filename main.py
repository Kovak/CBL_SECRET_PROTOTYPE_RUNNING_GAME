import kivy
from kivy.app import App
from kivy.factory import Factory
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.clock import Clock
import random
from kivy.graphics import Rectangle, Color, Callback, Rotate, PushMatrix, PopMatrix, Translate, Quad
from kivy.properties import NumericProperty, StringProperty, ObjectProperty, BooleanProperty

def random_variance(base, variance):
    return base + variance * (random.random() * 2.0 - 1.0)

class DebugPanel(Widget):
    fps = StringProperty(None)

    def update_fps(self,dt):
        self.fps = str(int(Clock.get_fps()))
        Clock.schedule_once(self.update_fps)

class RunningGame(Widget):
    foreground = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(RunningGame, self).__init__(**kwargs)
        self.player_character = PlayerCharacter(parent = self)
        
        self.foreground = ScrollingForeground()
        self.add_widget(self.foreground)
        self.add_widget(self.player_character)
        button = Button(text='Jump', pos=(Window.width * .2, 500))
        button.bind(on_press = self.jump_button_callback)
        self.add_widget(button)

    def jump_button_callback(self, instance):   
        self.player_character.isJumping = True

class PlayerCharacter(Widget):
    texture = StringProperty(None)
    isRendered = BooleanProperty(False)
    isOnGround = BooleanProperty(False)
    y_velocity = NumericProperty(0)
    isJumping = BooleanProperty(False)
    isMidJump = BooleanProperty(False)
    numJumps = NumericProperty(2)
    anim_frame_counter = NumericProperty(0)
    gravity = NumericProperty(300)
    jump_velocity = NumericProperty(250)

    def __init__(self, parent, **kwargs):
        super(PlayerCharacter, self).__init__(**kwargs)
        self.texture = 'media/art/characters/char1-idle1.png'
        self.x = Window.width *.2
        self.y = Window.height *.5
        self.size = (82, 150)
        self.render_dict = dict()
        Clock.schedule_once(self._update)
        Clock.schedule_once(self.update_anim_frame_counter, .25)

    def _update(self, dt):
        self._advance_time(dt)
        self._render()
        Clock.schedule_once(self._update)

    def _check_collision(self):
        for each in self.parent.foreground.platforms:
            if self.x >= each.x - each.size[0] * .5 and self.x <= each.x + each.size[0] * .5:
                if each.y + each.size[1]*.5 >= self.y - self.size[1] *.5 and each.y + each.size[1]*.5 - 10 < self.y - self.size[1] *.5:
                    self.isOnGround = True
                    self.y = each.y + each.size[1]*.5 + self.size[1] *.5 
                    return

        self.isOnGround = False

    def _set_jumping(self, dt):
        self.isMidJump = False

    def update_anim_frame_counter(self, dt):
        if self.anim_frame_counter <= 3:
            self.anim_frame_counter += 1
        if self.anim_frame_counter > 3:
            self.anim_frame_counter = 0
        Clock.schedule_once(self.update_anim_frame_counter, .20)
                    
    def _advance_time(self, dt):
        gravity = self.gravity
        self._check_collision()
        if self.isOnGround and not self.isMidJump:
            self.y_velocity -= self.y_velocity
            self.numJumps = 2

        if self.isJumping:
            if self.numJumps > 0:
                print 'jumping', self.numJumps
                self.isOnGround = False
                self.y_velocity += self.jump_velocity
                self.isMidJump = True
                self.numJumps -= 1
            self.isJumping = False
            Clock.schedule_once(self._set_jumping, .25)
            
        if not self.isOnGround:
            self.y_velocity -= gravity * dt

        self.y += self.y_velocity * dt

        if self.y < 0 - self.size[0]:
            self.y = Window.height *.5
            self.y_velocity = 0

        #Animation Code:

        if self.y_velocity > 0:
            if self.anim_frame_counter == 0 or self.anim_frame_counter == 2:
                self.texture = 'media/art/characters/char1-jump1.png'
            if self.anim_frame_counter == 1 or self.anim_frame_counter == 3:
                self.texture = 'media/art/characters/char1-jump1-2.png'

        if self.y_velocity < 0:
            if self.anim_frame_counter == 0 or self.anim_frame_counter == 2:
                self.texture = 'media/art/characters/char1-jump2.png'
            if self.anim_frame_counter == 1 or self.anim_frame_counter == 3:
                self.texture = 'media/art/characters/char1-jump2-2.png'
        if self.y_velocity == 0:
            if self.anim_frame_counter == 0:
                self.texture = 'media/art/characters/char1-idle1.png'
            if self.anim_frame_counter == 1:
                self.texture = 'media/art/characters/char1-step1.png'
            if self.anim_frame_counter == 2:
                self.texture = 'media/art/characters/char1-idle2.png'
            if self.anim_frame_counter == 3:
                self.texture = 'media/art/characters/char1-step2.png'       
        
    def _render(self):
            if not self.isRendered:
                with self.canvas:
                    PushMatrix()
                    self.render_dict['translate'] = Translate()
                    self.render_dict['rect'] = Quad(source=self.texture, points=(-self.size[0] * 0.5, -self.size[1] * 0.5, 
                        self.size[0] * 0.5,  -self.size[1] * 0.5, self.size[0] * 0.5, self.size[1] * 0.5, 
                         -self.size[0] * 0.5, self.size[1] * 0.5))    
                    self.render_dict['translate'].xy = (self.x, self.y)
                    PopMatrix()
                self.isRendered = True

            else:
                self.render_dict['translate'].xy = (self.x, self.y)
                self.render_dict['rect'].source = self.texture

class Platform(object):
    x, y = -500, -500
    texture = None
    size = (0, 0)
    spacing = 0

class ScrollingForeground(Widget):
    speed = NumericProperty(200)
    current_platform_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super(ScrollingForeground, self).__init__(**kwargs)
        self.listofelements = list()
        self.listofelements.append('media/art/platforms/platform3.png')
        self.listofelements.append('media/art/platforms/platform2.png')
        self.listofelements.append('media/art/platforms/platform1.png')
        self.platforms = list()
        self.platforms_dict = dict()
        Clock.schedule_once(self._init_platforms)
        Clock.schedule_once(self._update)
        #Clock.schedule_interval(self._increase_platform_speed, 1.0)

    def _increase_platform_speed(self, dt):
        self.speed += 10

    def _init_platforms(self, dt):
        platformxspace = Window.width * 2
        numplats = 0
        while platformxspace > 0:
            platform = self._create_platform()
            self.platforms.append(platform)
            platformxspace -= platform.size[0]
            numplats += 1         

    def _create_platform(self):
            max_jump_distance = ((3*self.parent.player_character.jump_velocity)/self.parent.player_character.gravity)*self.speed
            platform = Platform()
            randPlatform = random.randint(0, 2)
            platform.spacing = random.randint(0, max_jump_distance)
            platform.y = 0
            platform.x = self.current_platform_x + platform.spacing
            print 'created platform at: ', platform.x
            platform.texture = self.listofelements[randPlatform]
            texture = Image(source = self.listofelements[randPlatform])
            platform.size = texture.texture_size
            self.current_platform_x += platform.size[0] + platform.spacing
            return platform

    def _update(self, dt):
        self._advance_time(dt)
        self._render()
        Clock.schedule_once(self._update)

    def _advance_time(self, dt):
        for platform in self.platforms:
            platform.x -= self.speed * dt
            if platform.x < -platform.size[0]:
                self.current_platform_x -= platform.size[0] + platform.spacing
                self.platforms.pop(self.platforms.index(platform))
                platform = self._create_platform()
                self.platforms.append(platform)

    def _render(self):
        for platform in self.platforms:
            if platform not in self.platforms_dict:
                self.platforms_dict[platform] = dict()
                with self.canvas:
                    PushMatrix()
                    self.platforms_dict[platform]['translate'] = Translate()
                    self.platforms_dict[platform]['Quad'] = Quad(source=platform.texture, points=(-platform.size[0] * 0.5, -platform.size[1] * 0.5, 
                        platform.size[0] * 0.5,  -platform.size[1] * 0.5, platform.size[0] * 0.5,  platform.size[1] * 0.5, 
                        -platform.size[0] * 0.5,  platform.size[1] * 0.5))    
                    self.platforms_dict[platform]['translate'].xy = (platform.x, platform.y)
                    PopMatrix()

            else:           
                self.platforms_dict[platform]['translate'].xy = (platform.x, platform.y)


Factory.register('RunningGame', RunningGame)
Factory.register('DebugPanel', DebugPanel)

class RunningGameApp(App):
    def build(self):
        pass

if __name__ == '__main__':
    RunningGameApp().run()