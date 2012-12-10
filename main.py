import kivy
from kivy.app import App
from kivy.base import EventLoop
from kivy.factory import Factory
from kivy.animation import Animation
from kivy.uix.widget import Widget
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import Rectangle, Color, Callback, Rotate, PushMatrix, PopMatrix, Translate, Quad
from kivy.properties import NumericProperty, StringProperty, ObjectProperty, BooleanProperty
from kivy.lang import Builder
from kivyparticle.engine import *
from kivy.input.motionevent import MotionEvent
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
import functools
import random
import os

def random_variance(base, variance):
    return base + variance * (random.random() * 2.0 - 1.0)

class DebugPanel(Widget):
    fps = StringProperty(None)

    def update_fps(self,dt):
        self.fps = str(int(Clock.get_fps()))
        Clock.schedule_once(self.update_fps)

class RunningGame(Screen):
    foreground = ObjectProperty(None)
    global_speed = NumericProperty(1)

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


    def on_touch_up(self, touch):
        if 'swipe' not in touch.ud:
            # touch is not a swipe, for now lets make this mean junp
            self.player_character.exec_move("jump1")
        else:
            if touch.ud['swipe'] == 'up':
                self.player_character.exec_move("jump1")
            elif touch.ud['swipe'] == 'right':
                self.player_character.sword_dash = True
                self.player_character.offensive_move = True
            elif touch.ud['swipe'] == 'down':
                self.player_character.exec_move("drop")
                self.player_character.offensive_move = True

    def on_touch_move(self, touch):
        if touch.y > touch.oy and abs(touch.y - touch.oy) > 20 and abs(touch.y - touch.oy) > abs(touch.x - touch.ox):
            touch.ud['swipe'] = 'up'
        elif touch.y < touch.oy and abs(touch.y - touch.oy) > 20 and abs(touch.y - touch.oy) > abs(touch.x - touch.ox):
            touch.ud['swipe'] = 'down'
        elif touch.x > touch.ox and abs(touch.x - touch.ox) > 20 and abs(touch.x - touch.ox) > abs(touch.y - touch.oy):
            touch.ud['swipe'] = 'right'
        elif touch.x < touch.ox and abs(touch.x - touch.ox) > 20 and abs(touch.x - touch.ox) > abs(touch.y - touch.oy):
            touch.ud['swipe'] = 'left'

    def on_global_speed(self, instance, value):
        for obj in [self.foreground, self.midground, self.background]:
            obj.speed_multiplier = value

    def add_confined_enemy(enemy):
        self.add_widget(enemy)

class AnimationController(Widget):

    char_directory = 'media/art/characters/'
    active_animation = StringProperty(None)
    active_texture_index = 0
    
    def __init__(self, char_name, initial_state, game=None):
        super(AnimationController, self).__init__()
        self._read_animations_from_file(char_name)
        self.active_animation = initial_state
        Clock.schedule_once(self._next_frame)

    def _read_animations_from_file(self, char_name):
        # parse animations.txt file
        search_dir = os.path.join(self.char_directory, char_name)
        self.animations = {}
        anim_name = None
        with open(os.path.join(search_dir, 'animations.txt'), 'r') as anim_file:
            for line in anim_file:
                if line.strip() == "": continue
                if line[0] not in [" ", "\t"]:
                    # unindented lines are animations like "walk:" or "jump:"
                    if anim_name is not None: self.animations[anim_name] = attrs
                    anim_name = line.strip(" :\n\t")
                    attrs = []
                else:
                    t = [x.strip() for x in line.split(":")]
                    txtr = CoreImage(os.path.join(self.char_directory, char_name, t[0])).texture
                    attrs.append((txtr, txtr.size, float(t[1])))
            if anim_name is not None: self.animations[anim_name] = attrs
        print self.animations

    def _next_frame(self,dt):
        self.active_texture_index = self.active_texture_index + 1 if self.active_texture_index < len(self.textures) - 1 else 0
        Clock.schedule_once(self._next_frame, self.textures[self.active_texture_index][2])

    def get_frame(self):
        # returns a tuple containing the active texture and the (x,y) size of the texture
        return self.textures[self.active_texture_index][0:2]

    def on_active_animation(self,instance,value):
        self.active_texture_index = 0
        self.textures = self.animations[value]

    def set_animation(self, anim_name):
        # if custom code exists to run when the current animation stops, run it.
        if self.active_animation+"_stop" in dir(self):
            getattr(self, self.active_animation+"_stop")()
        self.active_animation = anim_name
        
        # if custom code exists to run when the new animation starts, run it.
        if anim_name+"_start" in dir(self):
            getattr(self, anim_name+"_start")()

    def jump1_start(self):
        print "started jumping!"

    def jump1_stop(self):
        print "stopped jumping!"

    def walk_start(self):
        print "started walking!"

    def walk_stop(self):
        print "stopped walking!"

class PlayerCharacter(Widget):
    isRendered = BooleanProperty(False)
    y_velocity = NumericProperty(0)
    oyv = 0

    jump_num = NumericProperty(0)
    max_jumps = NumericProperty(2)
    jump_velocity = NumericProperty(250)
    is_jumping = BooleanProperty(False)

    drop_velocity = NumericProperty(-400)
    is_dropping = BooleanProperty(False)

    gravity = NumericProperty(300)
    down_dash = BooleanProperty(False)
    down_dash_active = BooleanProperty(False)
    down_dash_landed = BooleanProperty(False)
    down_dash_counter = NumericProperty(0)
    dash_landed = BooleanProperty(False)
    dash_land_counter = NumericProperty(0)
    sword_dash = BooleanProperty(False)
    sword_dash_counter = NumericProperty(0)
    offensive_move = BooleanProperty(False)

    game = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PlayerCharacter, self).__init__(**kwargs)
        self.x = Window.width *.2
        self.y = Window.height * .2
        self.size = (82, 150)
        self.size_hint = (None, None)
        self.render_dict = dict()
        self.animation_controller = AnimationController('char1', 'walk')
        Clock.schedule_once(self._update)


    def _update(self, dt):
        self._advance_time(dt)
        self._render()
        Clock.schedule_once(self._update)

    def _check_collision(self):
        if self.is_jumping: return False
        for each in self.game.foreground.platforms:
            if (self.center_x >= each.x) and (self.center_x <= each.x + each.size[0]):
                tile_idx = int((self.center_x - each.x)/each.tile_size[0])
                if tile_idx < 0 or tile_idx >= each.r: continue
                for h in each.platform_heights[tile_idx]:
                     if abs(self.y - (each.y + h)) < 10:
                        self.y = each.y + h
                        return True
        return False


    def exec_move(self, move_name, *largs):
        # move-specific code that is NOT animation related goes here (for example, physics)
        if move_name == 'jump1':
            if self.jump_num >= self.max_jumps: return
            self.jump_num += 1
            self.is_jumping = True
            self.y_velocity += self.jump_velocity
        elif move_name == 'drop':
            # you can only drop from a jump
            if self.jump_num == 0: return
            anim = Animation(global_speed = 0, duration = .2)
            anim.start(self.game)
            self.is_dropping = True
            self.y_velocity = self.drop_velocity
        elif move_name == 'drop-land':
            # get the game clock running back at normal speed again
            anim = Animation(global_speed = 1, duration = .5)
            anim.start(self.game)
            self.is_dropping = False
            Clock.schedule_once(functools.partial(self.exec_move, 'walk'), .3)


        self.animation_controller.set_animation(move_name)

    def on_y_velocity(self, instance, value):
        # watches for the point where player hits the apex of his parabola so that we can change animations
        # if character is not jumping, we don't care about y_velocity and who likes running extra python code? not my crappy tablet!
        if self.jump_num == 0: return
        # but if velocity used to be positive and now it's negative, execute the jump2 move
        if self.oyv > 0 and value <= 0:
            self.is_jumping = False
            self.exec_move('jump2')
        self.oyv = value

    def die(self):
        self.y = Window.height *.5
        self.y_velocity = 0
        self.game.global_speed = 1
        # self.down_dash_active = False

        if self.parent.parent.life_count.lives > 0:
            self.parent.parent.life_count.decrease_lives()

        if self.parent.parent.life_count.lives == 0:
            self.parent.parent.manager.current = 'replay'

    def _advance_time(self, dt):
        is_on_ground = self._check_collision()

        # player was falling down and landed:
        if is_on_ground and self.y_velocity < 0:
            self.y_velocity = 0
            self.jump_num = 0
            self.is_jumping = False
            if self.is_dropping:
                self.exec_move('drop-land')
            else:
                self.exec_move('walk')

        # player is in the air and not actively jumping
        if not is_on_ground:
            self.y_velocity -= self.gravity * dt

        self.oy = self.y
        self.ox = self.x
        self.y += self.y_velocity * dt

        if self.y < 0 - self.size[0]:
            self.die()

        #Animation Code:
        self.texture, self.size = self.animation_controller.get_frame()
    
    def _render(self):
        if not self.isRendered:
            with self.canvas:
                PushMatrix()
                self.render_dict['translate'] = Translate()
                self.render_dict['rect'] = Quad(texture=self.texture, points=(0, 0, self.size[0], 0, self.size[0], self.size[1], 0, self.size[1], ))
                self.render_dict['translate'].xy = (self.x, self.y)
                PopMatrix()
            self.isRendered = True

        else:
            self.render_dict['translate'].xy = (self.x, self.y)
            self.render_dict['rect'].texture = self.texture
            self.render_dict['rect'].points = points=( 0, 0, self.size[0], 0, self.size[0], self.size[1], 0, self.size[1],)

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

    def coin_collected(self):
        self.score += 10
        # print 'SCORED'

class LivesDisplay(Widget):
    lives = NumericProperty(5)

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

    def create_enemy(self, plat_y, plat_x, plat_size):
        enemy = Enemy()
        print 'created enemy at: ', enemy.x
        enemy.texture = 'media/art/characters/testcharacter.png'
        texture = Image(source = 'media/art/characters/testcharacter.png')
        enemy.size = texture.texture_size
        enemy.bbox = enemy.size
        enemy.min = plat_x - plat_size / 2
        enemy.max = plat_x + plat_size / 2
        enemy.y = plat_y
        enemy.x = plat_x
        enemy.test = True
        enemy.move_left = True
        enemy.move_right = False
        enemy.right = enemy.x + enemy.size[0] * .5
        # enemy.left = enemy.x - enemy.size[0] * .5
        enemy.top = enemy.y + enemy.size[1] * .5
        # enemy.bottom = enemy.y - enemy.size[1] *.5
        enemy.killed = False
        enemy.killed_player = False
        enemy.check_health = True
        print 'enemy size',enemy.size
        self.enemies.append(enemy)

    def _advance_time(self, dt):
        for enemy in self.enemies:
            enemy.min -= self.speed * dt
            enemy.max -= self.speed * dt

            if enemy.move_left == True:
                enemy.x -= self.speed * dt * 1.5

            if enemy.move_right == True:
                enemy.x += self.speed * dt * .5
            
            if enemy.x < enemy.min:
                enemy.move_right = True
                enemy.move_left = False

            if enemy.x > enemy.max:
                enemy.move_left = True
                enemy.move_right = False

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
            if self.parent.parent.player_character.collide_widget(enemy) == True and self.parent.parent.player_character.offensive_move == False and enemy.killed == False and abs(enemy.x - self.parent.parent.player_character.x) < 50 and abs(enemy.y - self.parent.parent.player_character.y) < 100 and enemy.killed_player == False:
                self.parent.parent.player_character.die()
                enemy.killed_player = True
            if self.parent.parent.player_character.collide_widget(enemy) == True and self.parent.parent.player_character.offensive_move == True and enemy.check_health == True and self.parent.parent.player_character.x - enemy.x < 60 and abs(enemy.y - self.parent.parent.player_character.y) < 150:
                enemy.killed = True
                enemy.check_health = False
                self.enemies_dict[enemy]['translate'].xy = (-100, enemy.y)
                print 'enemy killed'

            elif enemy.killed == False:           
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

    def create_coin(self, plat_y, plat_x, plat_size):
        coin = ScoringObject()
        coin.texture = 'media/art/collectibles/goldcoin1.png'
        texture = Image(source = 'media/art/collectibles/goldcoin1.png')
        coin.size = texture.texture_size
        coin.bbox = coin.size
        coin.y = plat_y
        coin.x = plat_x
        coin.right = coin.x + coin.size[0] * .5
        # coin.left = coin.x - coin.size[0] * .5
        coin.top = coin.y + coin.size[1] * .5
        # coin.bottom = coin.y - coin.size[1] *.5
        coin.collected = False
        coin._check_collision = True

        print 'coin size ', coin.size
        self.parent.parent.coin.coins.append(coin)

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

            if self.parent.parent.player_character.collide_widget(coin) == True and coin._check_collision == True and abs(coin.x - self.parent.parent.player_character.x) < 45 and abs(coin.y - self.parent.parent.player_character.y) < 70:
                coin.collected = True
                coin._check_collision = False
                self.coins_dict[coin]['translate'].xy = (-100, coin.y)
                self.parent.parent.score.coin_collected()


            elif coin.collected == False:       
                self.coins_dict[coin]['translate'].xy = (coin.x, coin.y)

class Platform(object):
    x, y = -500, -500
    is_partially_off_screen = True
    end_height = 0
    line = 0

    def __init__(self, texture_sources, tile_size = (64,64), tiles_per_level = 1, platform_type = None):
        # takes a dictionary in the form {(r,c): filename.png} and converts it into a platform. If tile_per_level = n is provided,
        # assumes that every nth tile can be walked upon (1 is default, so you don't have to touch it if you're just making single-sprite platforms
        self.tile_size = tile_size
        self.platform_type = platform_type
        # turn filepaths into textures
        self.textures = {x: CoreImage(texture_sources[x]).texture for x in texture_sources.keys()}
        self.texture_sources = texture_sources
        
        # get number of rows and columns
        self.r, self.c = [z+1 for z in reduce(lambda x, y : (max(x[0],y[0]), max(x[1],y[1])), texture_sources.keys())]
        
        self.size = (tile_size[0] * self.r, tile_size[1] * self.c)
        
        self.platform_heights = []
        for r in range(self.r):
            hs = []
            for c in range(tiles_per_level - 1, self.c, tiles_per_level):
                if (r,c) in texture_sources.keys(): hs.append(tile_size[1] * (c+1))
            self.platform_heights.append(hs)
        print self.platform_heights

class ScrollingForeground(Widget):
    speed = NumericProperty(200)
    speed_multiplier = NumericProperty(1)
    initial_platforms = NumericProperty(0)
    current_platform_x = NumericProperty(0)
    
    # # 25% is scaffolds, 75% floating
    # platform_type_ratio = .25

    # # maximum distance to go up or down between floating platforms
    # platform_max_y_change = 256


    # # maximum length of a scaffold
    # max_length = 6

    # size of tiles used for scaffolding
    tile_size = (64,64)

    # # range in distance between platforms
    # max_distance = 300
    # min_distance = 20

    # # difficulty on a scale from 0 to 1. This effects the skewness of the distribution of distances between platforms
    # # (0 means all distances are min_distance, 1 means all distances are max distance)
    # difficulty = .5

    lines = [
        # top line
        {'platform_type_ratio': 1,
        'platform_max_y_change': 200,
        'max_height': 3,
        'max_length': 6,
        'max_distance': 700,
        'min_distance': 100,
        'difficulty': 1,
        'up_prob': .2,
        'down_prob': .3},

        # base line
        {'platform_type_ratio': .2,
        'platform_max_y_change': 0,
        'max_height': 1,
        'max_length': 3,
        'max_distance': 200,
        'min_distance': 20,
        'difficulty': 0.6,
        'up_prob': .1,
        'down_prob': .4},
    ]

    game = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ScrollingForeground, self).__init__(**kwargs)
        self.platforms = list()
        self.platforms_dict = dict()
        Clock.schedule_once(functools.partial(self._init_platform, 0, None))
        Clock.schedule_once(functools.partial(self._init_platform, 1, None))
        Clock.schedule_once(self._update)


    def _init_platform(self, line_num, last_height, *largs):
        if random.random() < self.lines[line_num]['platform_type_ratio']:
            start_height = 1 if last_height is None else int(last_height / self.tile_size[1]) + random.randint(-1,1)
            if start_height < 1: start_height = 1
            if start_height > self.lines[line_num]['max_height']: start_height = self.lines[line_num]['max_height']
            self.platforms.append(self._create_scaffold(line_num, start_height = start_height, max_height = self.lines[line_num]['max_height'], max_length = self.lines[line_num]['max_length']))
        else:
            self.platforms.append(self._create_floating_platform(line_num, last_height = last_height))

    def _get_tile_name(self, prefix, position, corner=True):
        # position is 1-9 arranged like your numpad
        if corner:
            return prefix + ['cplat-left-3', None, 'cplat-right-3',
                    'cplat-left-2', 'fblock-1', 'cplat-right-2',
                    'cplat-left-1', 'mplatnopost-1', 'cplat-right-1'][position-1] + '.png'
        else:
            return prefix + ['mplatwithpost-right-3', None, 'mplatwithpost-left-3',
                    'mplatwithpost-right-2', 'fblock-1', 'mplatwithpost-left-2',
                    'mplatwithpost-right-1', 'mplatnopost-1', 'mplatwithpost-left-1'][position-1] + '.png'

    def _create_scaffold(self, line, start_height = 1, max_height = 3, max_length = 5):
        prefix = 'media/art/platforms/scaffolding-'
        
        # first create list of heights so we know what to build
        h = start_height
        heights = []
        for x in range(int(max_length*random.random())+1):
            heights.append(h)
            r = random.random()
            if r > .75 and h + 1 <= max_height:
                # build an additional level in next column
                h += 1
            elif r < .25 and h - 1 >= 1:
                # go down a level
                h -= 1
            else:
                # stay at the same level
                pass

        # now actually build the scaffolding
        tile_dict = {}
        for col_idx, h in enumerate(heights):
            #build a "bridge" if we are connecting two scaffolds of the same height
            if (col_idx != 0) and (col_idx != len(heights) - 1) and h == heights[col_idx-1] == heights[col_idx+1]:
                tile_dict[(2*col_idx, 3*h-1)] = tile_dict[(2*col_idx + 1, 3*h-1)] = self._get_tile_name(prefix, 8)
                continue
            for r in (0,1):
                for c in range(3*h):
                    t = (r + 2*col_idx, c)

                    corner = False
                    if r == 0:
                        if col_idx == 0:
                            corner = True

                        if c % 3 == 0:
                            position = 1
                        elif c % 3 == 1:
                            position = 4
                        elif c % 3 == 2:
                            position = 7
                    elif r == 1:
                        if col_idx == len(heights) - 1:
                            corner = True

                        if c % 3 == 0:
                            position = 3
                        elif c % 3 == 1:
                            position = 6
                        elif c % 3 == 2:
                            position = 9
                    tile_dict[t] = self._get_tile_name(prefix, position, corner = corner)

        platform = Platform(tile_dict, tiles_per_level = 3, platform_type = 'scaffold')
        platform.x = Window.size[0]
        platform.y = 0
        platform.end_height = platform.y + heights[-1] * platform.tile_size[1]
        platform.line = line
        return platform

    def _signal_platform_on_screen(self, platform):
        print "PLATFORM COMPLETE"
        interval = random.triangular(self.lines[platform.line]['min_distance'], self.lines[platform.line]['max_distance'],
                    self.lines[platform.line]['min_distance'] + self.lines[platform.line]['difficulty']*(self.lines[platform.line]['max_distance']
                     - self.lines[platform.line]['min_distance'])) / (self.speed * self.speed_multiplier)

        Clock.schedule_once(functools.partial(self._init_platform, platform.line, platform.end_height), interval)

    def _create_floating_platform(self, line, last_height = None):
        if self.initial_platforms < 2:
            src = {(0,0): 'media/art/platforms/platform1.png'}
            texture_size = CoreImage(src[(0,0)]).texture.size
            platform = Platform(src, tile_size = texture_size, platform_type = 'floating')
            platform.x = self.current_platform_x
            self.current_platform_x += platform.size[0]
            self.initial_platforms += 1
            platform.y = -texture_size[1]*0.5
            platform.end_height = platform.y + texture_size[1]
            platform.line = line
            return platform
        else:
            src = random.choice([{(0,0): 'media/art/platforms/platform1.png'},
                {(0,0): 'media/art/platforms/platform2.png'},
                {(0,0): 'media/art/platforms/platform3.png'}])
            texture_size = CoreImage(src[(0,0)]).texture.size
            platform = Platform(src, tile_size = texture_size, platform_type = 'floating')
            platform.x = Window.size[0]
            if last_height is None:
                platform.y = -texture_size[1]*0.5
            else:
                y = last_height - texture_size[1] + random.randint(-self.lines[line]['platform_max_y_change'], self.lines[line]['platform_max_y_change'])
                if y < -texture_size[1]*0.5: y = -texture_size[1]*0.5
                if y > Window.size[1] - texture_size[1] - 150: y = Window.size[1] - texture_size[1] - 150
                platform.y = y
            platform.end_height = platform.y + texture_size[1]
            platform.line = line
            if platform.size[0] > 200:
                platform.enemy = self.parent.parent.confined_enemy.create_enemy(plat_y = platform.y + platform.size[1]*1.75, plat_x = platform.x + platform.size[0]*.5, plat_size = platform.size[0])
            if platform.size[0] < 200:
                platform.coin = self.parent.parent.coin.create_coin(plat_y = platform.y + platform.size[1]*1.25, plat_x = platform.x  + platform.size[0]*.5, plat_size = platform.size[0])
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
            platform.x -= (self.speed * self.speed_multiplier) * dt
            if platform.x < -platform.size[0]:
                self.platforms.pop(self.platforms.index(platform))
            elif platform.is_partially_off_screen and platform.x + platform.size[0] < Window.size[0]:
                self._signal_platform_on_screen(platform)
                platform.is_partially_off_screen = False

    def _render(self):
        for line_num in range(len(self.lines)):
            for platform in self.platforms:
                if platform.line != line_num: continue
                if platform not in self.platforms_dict:
                    xs = platform.tile_size[0]
                    ys = platform.tile_size[1]
                    self.platforms_dict[platform] = dict()
                    with self.canvas:
                        PushMatrix()
                        self.platforms_dict[platform]['translate'] = Translate()
                        for t in platform.textures.keys():
                            self.platforms_dict[platform]['Quad'] = Quad(points=(xs * t[0], ys * t[1],
                                        xs * t[0] + xs, ys * t[1],
                                        xs * t[0] + xs, ys * t[1] + ys,
                                        xs * t[0], ys * t[1] + ys,),
                                    texture=platform.textures[t])

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
    speed_multiplier = NumericProperty(1)

    def __init__(self, **kwargs):
        super(ScrollingMidground, self).__init__(**kwargs)
        self.midelements = list()
        self.midelements.append('media/art/midground_objects/testarch.png')
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
            midground.x -= midground.speed * self.speed_multiplier * dt
            if midground.x < -midground.size[0]:
                self.current_midground_x -= midground.size[0] + midground.spacing
                self.midgrounds.pop(self.midgrounds.index(midground))
                midground = self._create_midground()
                self.midgrounds.append(midground)

class ScrollingBackground(Widget):
    speed = NumericProperty(50)
    speed_multiplier = NumericProperty(1)
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
            background.x -= self.speed * self.speed_multiplier * dt
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

class ReplayScreen(Screen):
    foreground = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ReplayScreen, self).__init__(**kwargs)

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
        sm.add_widget(ReplayScreen(name='replay'))
        return sm

if __name__ == '__main__':
    RunningGameApp().run()