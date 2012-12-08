import kivy
from kivy.app import App
from kivy.base import EventLoop
from kivy.factory import Factory
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.button import Button
from kivy.clock import Clock
import random
from kivy.graphics import Rectangle, Color, Callback, Rotate, PushMatrix, PopMatrix, Translate, Quad
from kivy.properties import NumericProperty, StringProperty, ObjectProperty, BooleanProperty
from kivy.lang import Builder
from kivyparticle.engine import *
from kivy.input.motionevent import MotionEvent
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition

def random_variance(base, variance):
    return base + variance * (random.random() * 2.0 - 1.0)

class DebugPanel(Widget):
    fps = StringProperty(None)

    def update_fps(self,dt):
        self.fps = str(int(Clock.get_fps()))
        Clock.schedule_once(self.update_fps)

class RunningGame(Screen):
    foreground = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(RunningGame, self).__init__(**kwargs)
        
    def start(self):
        self.player_character = PlayerCharacter(game = self)
        self.foreground = ScrollingForeground(game = self)
        self.midground = ScrollingMidground()
        self.background = ScrollingBackground()
        self.landing_fx = ParticleEffects(game = self)
        self.life_count = LivesDisplay()
        self.score = ScoreDisplay()
        self.confined_enemy = ConfinedEnemy()
        self.coin = Coin()
        self.add_widget(self.background)
        self.add_widget(self.midground)
        self.add_widget(self.foreground)
        self.add_widget(self.score)
        self.add_widget(self.life_count)
        self.add_widget(self.confined_enemy)
        self.add_widget(self.coin)
        self.add_widget(self.player_character)
        self.add_widget(self.landing_fx)

    # def on_touch_down(self, touch):
    #     pass

    def on_touch_up(self, touch):
        if 'swipe' not in touch.ud:
            # touch is not a swipe, for now lets make this mean junp
            self.player_character.isJumping = True
        else:
            if touch.ud['swipe'] == 'up':
                self.player_character.isJumping = True
            elif touch.ud['swipe'] == 'right':
                self.landing_fx.fire_forward(.1)
            elif touch.ud['swipe'] == 'down':
                self.player_character.down_dash = True

    def on_touch_move(self, touch):
        if touch.y > touch.oy and abs(touch.y - touch.oy) > 20 and abs(touch.y - touch.oy) > abs(touch.x - touch.ox):
            touch.ud['swipe'] = 'up'
        elif touch.y < touch.oy and abs(touch.y - touch.oy) > 20 and abs(touch.y - touch.oy) > abs(touch.x - touch.ox):
            touch.ud['swipe'] = 'down'
        elif touch.x > touch.ox and abs(touch.x - touch.ox) > 20 and abs(touch.x - touch.ox) > abs(touch.y - touch.oy):
            touch.ud['swipe'] = 'right'
        elif touch.x < touch.ox and abs(touch.x - touch.ox) > 20 and abs(touch.x - touch.ox) > abs(touch.y - touch.oy):
            touch.ud['swipe'] = 'left'

    def add_confined_enemy(enemy):
        self.add_widget(enemy)


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
    down_dash = BooleanProperty(False)
    down_dash_active = BooleanProperty(False)
    down_dash_counter = NumericProperty(0)
    dash_landed = BooleanProperty(False)
    dash_land_counter = NumericProperty(0)

    game = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PlayerCharacter, self).__init__(**kwargs)
        self.texture = 'media/art/characters/char1-idle1.png'
        self.x = Window.width *.2
        self.y = Window.height *.5
        self.size = (82, 150)
        self.size_hint = (None, None)
        self.render_dict = dict()
        Clock.schedule_once(self._update)
        Clock.schedule_once(self.update_anim_frame_counter, .25)


    def _update(self, dt):
        self._advance_time(dt)
        self._render()
        Clock.schedule_once(self._update)

    def _check_collision(self):
        # print "checking collision: ", len(self.game.foreground.platforms)
        for each in self.game.foreground.platforms:
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
        

    def die(self):
        self.y = Window.height *.5
        self.y_velocity = 0

        if self.parent.parent.life_count.lives > 0:
            self.parent.parent.life_count.decrease_lives()

        if self.parent.parent.life_count.lives == 0:
            print 'game over'   

    def _advance_time(self, dt):
        landed = False
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
            self.parent.parent.landing_fx.emit_dust(.1)
            
        if not self.isOnGround:
            self.y_velocity -= gravity * dt

        self.y += self.y_velocity * dt

        if self.y < 0 - self.size[0]:
            self.die()

        #Animation Code:

        if self.y_velocity > 0:
            if self.anim_frame_counter == 0 or self.anim_frame_counter == 2:
                self.texture = 'media/art/characters/char1-jump1.png'
            if self.anim_frame_counter == 1 or self.anim_frame_counter == 3:
                self.texture = 'media/art/characters/char1-jump1-2.png'

        if self.y_velocity < 0:
            if self.down_dash == False:
                if self.anim_frame_counter == 0 or self.anim_frame_counter == 2:
                    self.texture = 'media/art/characters/char1-jump2.png'
                if self.anim_frame_counter == 1 or self.anim_frame_counter == 3:
                    self.texture = 'media/art/characters/char1-jump2-2.png'
            if self.down_dash == True:
                self.texture = 'media/art/characters/char1-downdash_fall.png'
                self.down_dash_active = True

        if self.y_velocity == 0:
            self.down_dash = False
            if self.down_dash_active == True:
                self.texture = 'media/art/characters/char1-downdash_land1.png'
                self.down_dash_counter += 1
                if self.down_dash_counter > 15:
                    self.down_dash_active = False
                    self.down_dash_counter =0
            if self.down_dash_active == False:
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
                self.render_dict['rect'].points = points=(-self.size[0] * 0.5, -self.size[1] * 0.5,
                        self.size[0] * 0.5, -self.size[1] * 0.5, self.size[0] * 0.5, self.size[1] * 0.5,
                         -self.size[0] * 0.5, self.size[1] * 0.5)

class ScoreDisplay(Widget):
    score = NumericProperty(0)

    def __init__(self, **kwargs):
        super(ScoreDisplay, self).__init__(**kwargs)
        self.size_hint = (.3,.1)
        self.pos = (Window.width * .72, Window.height * .89)
        Clock.schedule_once(self.update_score)

    def update_score(self, dt):
        Clock.schedule_interval(self.increase_score, 1)

    def increase_score(self, dt):
        self.score += 1

class LivesDisplay(Widget):
    lives = NumericProperty(3)

    def __init__(self, **kwargs):
        super(LivesDisplay, self).__init__(**kwargs)
        self.size_hint = (.3,.1)
        self.pos = (0, Window.height * .89)

    def increase_lives(self):
        self.lives += 1

    def decrease_lives(self):
        self.lives -= 1

class Enemy(object):
    x, y = -500, -500
    texture = None
    size = (0, 0)

class ConfinedEnemy(Widget):
    speed = NumericProperty(200)
    texture = StringProperty(None)

    def __init__(self, **kwargs):
        super(ConfinedEnemy, self).__init__(**kwargs)
        self.enemies = list()
        self.enemies_dict = dict()
        # Clock.schedule_once(self._init_enemies)
        # Clock.schedule_once(self._update, timeout=2)

    def _create_enemy(self, plat_y, plat_x, plat_size):
        enemy = Enemy()
        print 'created enemy at: ', enemy.x
        enemy.texture = 'media/art/characters/testcharacter.png'
        texture = Image(source = 'media/art/characters/testcharacter.png')
        enemy.size = texture.texture_size
        enemy.min = plat_x - plat_size / 2
        enemy.max = plat_x + plat_size / 2
        enemy.y = plat_y
        enemy.x = plat_x
        enemy.test = True
        enemy.left = True
        enemy.right = False
        self.enemies.append(enemy)

    def _advance_time(self, dt):
        for enemy in self.enemies:
            enemy.min -= self.speed * dt
            enemy.max -= self.speed * dt

            if enemy.left == True:
                enemy.x -= self.speed * dt * 1.5

            if enemy.right == True:
                enemy.x += self.speed * dt * .5
            
            if enemy.x < enemy.min:
                enemy.right = True
                enemy.left = False

            if enemy.x > enemy.max:
                enemy.left = True
                enemy.right = False

            if enemy.x < -100:
                self.enemies.pop(self.enemies.index(enemy))

    def _render(self):
        for enemy in self.enemies:
            if enemy not in self.enemies_dict:
                self.enemies_dict[enemy] = dict()
                with self.canvas:
                    PushMatrix()
                    self.enemies_dict[enemy]['translate'] = Translate()
                    self.enemies_dict[enemy]['Quad'] = Quad(source=enemy.texture, points=(-enemy.size[0] * 0.5, -enemy.size[1] * 0.5, 
                        enemy.size[0] * 0.5,  -enemy.size[1] * 0.5, enemy.size[0] * 0.5,  enemy.size[1] * 0.5, 
                        -enemy.size[0] * 0.5,  enemy.size[1] * 0.5))    
                    self.enemies_dict[enemy]['translate'].xy = (enemy.x, enemy.y)
                    PopMatrix()

            else:           
                self.enemies_dict[enemy]['translate'].xy = (enemy.x, enemy.y)

class ScoringObject(object):
    x, y = -500, -500
    texture = None
    size = (0, 0)

class Coin(Widget):
    speed = NumericProperty(200)
    texture = StringProperty(None)

    def __init__(self, **kwargs):
        super(Coin, self).__init__(**kwargs)
        self.coins = list()
        self.coins_dict = dict()

    def _create_coin(self, plat_y, plat_x, plat_size):
        coin = ScoringObject()
        coin.texture = 'media/art/characters/char3-idle1.png'
        texture = Image(source = 'media/art/characters/char3-idle1.png')
        coin.size = texture.texture_size
        coin.y = plat_y
        coin.x = plat_x
        print 'created coin at: ', coin.x
        self.coins.append(coin)

    def _advance_time(self, dt):
        for coin in self.coins:
            coin.x -= self.speed * dt
            if coin.x < -100:
                self.coins.pop(self.coins.index(coin))

    def _render(self):
        for coin in self.coins:
            if coin not in self.coins_dict:
                self.coins_dict[coin] = dict()
                with self.canvas:
                    PushMatrix()
                    self.coins_dict[coin]['translate'] = Translate()
                    self.coins_dict[coin]['Quad'] = Quad(source=coin.texture, points=(-coin.size[0] * 0.5, -coin.size[1] * 0.5, 
                        coin.size[0] * 0.5,  -coin.size[1] * 0.5, coin.size[0] * 0.5,  coin.size[1] * 0.5, 
                        -coin.size[0] * 0.5,  coin.size[1] * 0.5))    
                    self.coins_dict[coin]['translate'].xy = (coin.x, coin.y)
                    PopMatrix()

            else:           
                self.coins_dict[coin]['translate'].xy = (coin.x, coin.y)


class Platform(object):
    x, y = -500, -500
    texture = None
    size = (0, 0)
    spacing = 0

class ScrollingForeground(Widget):
    speed = NumericProperty(200)
    current_platform_x = NumericProperty(0)

    game = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScrollingForeground, self).__init__(**kwargs)
        self.listofelements = list()
        self.listofelements.append('media/art/platforms/platform3.png')
        self.listofelements.append('media/art/platforms/platform2.png')
        self.listofelements.append('media/art/platforms/platform1.png')
        self.platforms = list()
        self.platforms_dict = dict()
        Clock.schedule_once(self._init_platforms)
        # Clock.schedule_once(self.startup_platform)
        Clock.schedule_once(self._update)
        #Clock.schedule_interval(self._increase_platform_speed, 1.0)

    # def startup_platform(self, dt):
    #     platform = Platform()
    #     platform.y = 0
    #     platform.x = 0
    #     platform.texture = self.listofelements[2]
    #     texture = Image(source = self.listofelements[2])
    #     platform.size = texture.texture.size
    #     self.platforms.append(platform)
    #     self._render()
    #     Clock.schedule_once(self._init_platforms, timeout=2)
    #     Clock.schedule_once(self._update, timeout=1)

    # def _increase_platform_speed(self, dt):
    #     self.speed += 10

    def _init_platforms(self, dt):
        platformxspace = Window.width * 2
        numplats = 0
        while platformxspace > 0:
            platform = self._create_platform()
            self.platforms.append(platform)
            platformxspace -= platform.size[0]
            numplats += 1         

    def _create_platform(self):
        max_jump_distance = ((3*self.game.player_character.jump_velocity)/self.game.player_character.gravity)*self.speed
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
        print platform.size[0]

        # platform.confined_enemy = random.randint(0,4)
        # if platform.confined_enemy == 3:
        if platform.size[0] > 200:
            platform.enemy = self.parent.parent.confined_enemy._create_enemy(plat_y = platform.y + platform.size[1]*1.25, plat_x = platform.x, plat_size = platform.size[0])
            print 'created enemy'
        if platform.size[0] < 200:
            platform.coin = self.parent.parent.coin._create_coin(plat_y = platform.y + platform.size[1]*1.25, plat_x = platform.x, plat_size = platform.size[0])
        return platform

    def _update(self, dt):
        self._advance_time(dt)
        self._render()
        self.parent.parent.confined_enemy._advance_time(dt)
        self.parent.parent.confined_enemy._render()
        self.parent.parent.coin._advance_time(dt)
        self.parent.parent.coin._render()
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
                        platform.size[0] * 0.5, -platform.size[1] * 0.5, platform.size[0] * 0.5, platform.size[1] * 0.5,
                        -platform.size[0] * 0.5, platform.size[1] * 0.5))
                    self.platforms_dict[platform]['translate'].xy = (platform.x, platform.y)
                    PopMatrix()

            else:
                self.platforms_dict[platform]['translate'].xy = (platform.x, platform.y)

class ParticleEffects(Widget):
    landing_dust = ObjectProperty(ParticleSystem)
    shoot_fire = ObjectProperty(ParticleSystem)
    game = ObjectProperty(None)

    def emit_dust(self, dt, name = 'ParticleEffects/templates/jellyfish.pex'):
        with self.canvas:
            self.landing_dust = ParticleSystem(name)
            self.landing_dust.emitter_x = self.game.player_character.x
            self.landing_dust.emitter_y = self.game.player_character.y - self.game.player_character.size[1]*.35
            self.landing_dust.start(duration = .3)
            Clock.schedule_once(self.landing_dust.stop, timeout = .3)

    def fire_forward(self, dt, name = 'ParticleEffects/templates/shoot_spell.pex'):
        with self.canvas:
            self.shoot_fire = ParticleSystem(name)
            self.shoot_fire.emitter_x = self.game.player_character.x + self.game.player_character.size[0]*.5
            self.shoot_fire.emitter_y = self.game.player_character.y
            self.shoot_fire.start(duration = 1)
            Clock.schedule_once(self.shoot_fire.stop, timeout = 1)

class ScrollImage(object):
    x, y = -500, -500
    texture = None
    size = (0, 0)
    spacing = 0

class ScrollingMidground(Widget):
    current_midground_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super(ScrollingMidground, self).__init__(**kwargs)
        self.midelements = list()
        self.midelements.append('media/art/midground_objects/testarch.png')
        # self.midelements.append('media/art/midground_objects/testground1.png')
        # self.midelements.append('media/art/midground_objects/testground2.png')
        self.midelements.append('media/art/midground_objects/testhill.png')
        self.midelements.append('media/art/midground_objects/testhill2.png')
        self.midelements.append('media/art/midground_objects/testhouse.png')
        self.midgrounds = list()
        self.midground_dict = dict()
        Clock.schedule_once(self._init_midground)
        Clock.schedule_once(self._update_midground)

    def _init_midground(self,dt):
        midgroundxspace = Window.width * 2
        num_mid_objects = 0
        while midgroundxspace > 0:
            midground = self._create_midground()
            self.midgrounds.append(midground)
            midgroundxspace -= midground.size[0]
            num_mid_objects += 1

    def _create_midground(self):
        midground = ScrollImage()
        rand_midground = random.randint(0, 3)
        midground.texture = self.midelements[rand_midground]
        texture = Image(source = self.midelements[rand_midground])
        midground.spacing = random.randint(0, 500)
        midground.size = texture.texture.size
        midground.speed = midground.size[0]*.25
        midground.y = 0 + midground.size[1]*.5
        midground.x = self.current_midground_x + midground.spacing
        self.current_midground_x += midground.size[0] + midground.spacing
        return midground

    def _render_midground(self):
        for midground in self.midgrounds:
            if midground not in self.midground_dict:
                self.midground_dict[midground] = dict()
                with self.canvas:
                    PushMatrix()
                    self.midground_dict[midground]['translate'] = Translate()
                    self.midground_dict[midground]['Quad'] = Quad(source=midground.texture, points=(-midground.size[0] * 0.5, -midground.size[1] * 0.5,
                        midground.size[0] * 0.5, -midground.size[1] * 0.5, midground.size[0] * 0.5, midground.size[1] * 0.5,
                        -midground.size[0] * 0.5, midground.size[1] * 0.5))
                    self.midground_dict[midground]['translate'].xy = (midground.x, midground.y)
                    PopMatrix()
            else:
                self.midground_dict[midground]['translate'].xy = (midground.x, midground.y)

    def _update_midground(self, dt):
        self._advance_time(dt)
        self._render_midground()
        Clock.schedule_once(self._update_midground)

    def _advance_time(self, dt):
        for midground in self.midgrounds:
            midground.x -= midground.speed * dt
            # print midground.speed
            if midground.x < -midground.size[0]:
                self.current_midground_x -= midground.size[0] + midground.spacing
                self.midgrounds.pop(self.midgrounds.index(midground))
                midground = self._create_midground()
                self.midgrounds.append(midground)

class ScrollingBackground(Widget):
    speed = NumericProperty(50)
    current_background_x = NumericProperty(0)

    def __init__(self, **kwargs):
        super(ScrollingBackground, self).__init__(**kwargs)
        self.backelements = list()
        # self.backelements.append('media/art/midground_objects/testarch.png')
        self.backelements.append('media/art/midground_objects/testground1.png')
        self.backelements.append('media/art/midground_objects/testground2.png')
        # self.backelements.append('media/art/midground_objects/testhill.png')
        # self.backelements.append('media/art/midground_objects/testhill2.png')
        # self.backelements.append('media/art/midground_objects/testhouse.png')
        self.backgrounds = list()
        self.background_dict = dict()
        Clock.schedule_once(self._init_background)
        Clock.schedule_once(self._update_background)

    def _init_background(self,dt):
        backgroundxspace = Window.width * 2
        num_back_objects = 0
        while backgroundxspace > 0:
            background = self._create_background()
            self.backgrounds.append(background)
            backgroundxspace -= background.size[0]
            num_back_objects += 1

    def _create_background(self):
        background = ScrollImage()
        rand_background = random.randint(0, 1)
        background.texture = self.backelements[rand_background]
        texture = Image(source = self.backelements[rand_background])
        background.spacing = 0
        background.size = texture.texture.size
        background.speed = background.size[0]*.1
        background.y = 0 + background.size[1]*.5
        background.x = self.current_background_x + background.spacing
        self.current_background_x += background.size[0] + background.spacing
        return background

    def _render_background(self):
        for background in self.backgrounds:
            if background not in self.background_dict:
                self.background_dict[background] = dict()
                with self.canvas:
                    PushMatrix()
                    self.background_dict[background]['translate'] = Translate()
                    self.background_dict[background]['Quad'] = Quad(source=background.texture, points=(-background.size[0] * 0.5, -background.size[1] * 0.5, 
                        background.size[0] * 0.5,  -background.size[1] * 0.5, background.size[0] * 0.5,  background.size[1] * 0.5, 
                        -background.size[0] * 0.5,  background.size[1] * 0.5))    
                    self.background_dict[background]['translate'].xy = (background.x, background.y)
                    PopMatrix()
            else:           
                self.background_dict[background]['translate'].xy = (background.x, background.y)

    def _update_background(self, dt):
        self._advance_time(dt)
        self._render_background()
        Clock.schedule_once(self._update_background)

    def _advance_time(self, dt):
        for background in self.backgrounds:
            background.x -= self.speed * dt
            if background.x < -background.size[0]:
                self.current_background_x -= background.size[0] + background.spacing
                self.backgrounds.pop(self.backgrounds.index(background))
                background = self._create_background()
                self.backgrounds.append(background)

# class ImageButton(Image):
# state = StringProperty('normal')
# background_normal = StringProperty(None)
# background_down = StringProperty(None)

# def __init__(self, **kwargs):
# super(ImageButton, self).__init__(**kwargs)

# def on_touch_down(self, touch):
# if self.collide_point(*touch.pos):
# touch.grab(self)
# self.state = 'down'
# else:
# return False

# def on_touch_up(self, touch):
# if touch.grab_current is self:
# self.state = 'normal'
# touch.ungrab(self)

# def on_state(self, instance, value):
# if value == 'normal':
# self.source = self.background_normal
# elif value == 'down':
# if self.background_down is not None:
# self.source = self.background_down

class MenuScreen(Screen):
    foreground = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(MenuScreen, self).__init__(**kwargs)

    def button_callback(self, btn_id):
        if btn_id == 'quit':
            Window.close()
        elif btn_id == 'new':
            self.manager.current = 'game'
            self.manager.get_screen('game').start()


Factory.register('RunningGame', RunningGame)
Factory.register('DebugPanel', DebugPanel)
Factory.register('ScrollingMidground', ScrollingMidground)
Factory.register('ScrollingBackground', ScrollingBackground)
Factory.register('ScoreDisplay', ScoreDisplay)
Factory.register('LivesDisplay', LivesDisplay)


class RunningGameApp(App):
    def build(self):
        sm = ScreenManager(transition = FadeTransition())
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(RunningGame(name='game'))
        return sm

if __name__ == '__main__':
    RunningGameApp().run()