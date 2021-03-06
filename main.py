import kivy
from kivy.app import App
from kivy.base import EventLoop
from kivy.factory import Factory
from kivy.animation import Animation
from kivy.uix.widget import Widget
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.graphics import Rectangle, Color, Callback, Rotate, PushMatrix, PopMatrix, Translate, Quad
from kivy.properties import NumericProperty, StringProperty, ObjectProperty, BooleanProperty, ListProperty
from kivy.lang import Builder
from kivyparticle.engine import *
from kivy.input.motionevent import MotionEvent
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.network.urlrequest import UrlRequest
from kivy.core.audio import SoundLoader
from functools import partial
import random
import os
import urllib
from engine import ArtContainer


def random_variance(base, variance):
    return base + variance * (random.random() * 2.0 - 1.0)

class DebugPanel(Widget):
    fps = StringProperty(None)
    start = True

    def update_fps(self,dt):
        self.fps = str(int(Clock.get_fps()))
        Clock.schedule_once(self.update_fps)
        if self.start: Clock.schedule_once(self.log_fps)
        self.start = False

    def log_fps(self,dt):
        log.add_datapoint('fps', float(self.fps))
        Clock.schedule_once(self.log_fps, 7.5)

class Logger(object):
    active_log = {}
    active_log_raw_items = {}

    server_url = 'http://sleepy-anchorage-4701.herokuapp.com/log?'
    headers = {'Content-type': 'application/x-www-form-urlencoded',
          'Accept': 'text/plain',}

    def log_event(self, event_name):
        try:
            self.active_log[event_name] += 1
        except KeyError:
            self.active_log[event_name] = 1

    def record_data(self, key, val):
        self.active_log[key] = val

    def add_datapoint(self, key, val):
        # keeps a running average of val
        try:
            self.active_log_raw_items[key].append(val)
        except KeyError:
            self.active_log_raw_items[key] = [val,]

    def send_to_logs(self):
        for k in self.active_log_raw_items.keys():
            self.active_log[k] = sum(self.active_log_raw_items[k])/float(len(self.active_log_raw_items[k]))

        params = urllib.urlencode(self.active_log)
        print 'sending request:', params
        req = UrlRequest(self.server_url + params, method='GET')

    def clear(self):
        self.active_log = {}


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
        self.particle_effects = ParticleEffects(game=self)
        self.life_count = LivesDisplay()
        self.score = ScoreDisplay(game = self)
        self.confined_enemy = ConfinedEnemy(game = self)
        self.goldcoin = WorldObject(game = self)
        self.sound_fx = SoundController(game = self)
        self.add_widget(self.background)
        self.add_widget(self.midground)
        self.add_widget(self.foreground)
        self.add_widget(self.goldcoin)
        self.add_widget(self.confined_enemy)
        self.add_widget(self.player_character)
        self.add_widget(self.particle_effects)
        self.add_widget(self.score)
        self.add_widget(self.life_count)
        

    def stop(self, *largs):
        self.player_character.stop = True
        for w in [self.player_character, self.foreground, self.midground, self.background, 
                    self.particle_effects, self.life_count ,self.score, self.confined_enemy, self.goldcoin]:
            self.remove_widget(w)
            w = None

    def on_touch_up(self, touch):
        if 'swipe' not in touch.ud:
            # touch is not a swipe, for now lets make this mean junp
            self.player_character.exec_move("jump1")
        else:
            if touch.ud['swipe'] == 'up':
                self.player_character.exec_move("jump1")
            elif touch.ud['swipe'] == 'right':
                if not self.player_character.is_dropping and self.player_character.is_dashing == False:
                    if self.player_character.dash_set:
                        self.player_character.exec_move("dash")
                    if not self.player_character.dash_set and self.player_character.jump_dash == False:
                        self.player_character.exec_move("dash")
                        self.player_character.jump_dash = True
            elif touch.ud['swipe'] == 'down':
                self.player_character.drop_plat = True
                self.player_character.exec_move("drop")
            # elif touch.ud['swipe'] == 'left':
            #     self.stop()

            
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

    collectible_directory = 'media/art/collectibles'
    char_directory = 'media/art/characters/'
    conf_enemy_dir = 'media/art/characters'
    active_animation = StringProperty(None)
    active_texture_index = 0
    
    def __init__(self, char_name, initial_state, game=None):
        super(AnimationController, self).__init__()
        self._read_animations_from_file(char_name)
        self.active_animation = initial_state
        Clock.schedule_once(self._next_frame)

    def _read_animations_from_file(self, char_name):
        # parse animations.txt file
        if char_name == 'char1':
            search_dir = os.path.join(self.char_directory, char_name)
            self.active_dir = self.char_directory
        elif char_name == 'goldcoin':
            search_dir = os.path.join(self.collectible_directory, char_name)
            self.active_dir = self.collectible_directory
        elif char_name == 'redcoin':
            search_dir = os.path.join(self.collectible_directory, char_name)
            self.active_dir = self.collectible_directory
        elif char_name == 'bluecoin':
            search_dir = os.path.join(self.collectible_directory, char_name)
            self.active_dir = self.collectible_directory
        elif char_name == 'mechaspiderturtle':
            search_dir = os.path.join(self.conf_enemy_dir, char_name)
            self.active_dir = self.conf_enemy_dir


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
                    txtr = CoreImage(os.path.join(self.active_dir, char_name, t[0])).texture
                    attrs.append((txtr, txtr.size, float(t[1])))
            if anim_name is not None: self.animations[anim_name] = attrs
        # print self.animations

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

class SoundController(object):

    sound_dir = 'media/sounds/'


    def __init__(self, game=None):
        super(SoundController, self).__init__()
        self.sound_dict = {}
        for f in os.listdir(self.sound_dir):
            if os.path.splitext(os.path.basename(f))[1] != '.wav': continue
            self.sound_dict[os.path.splitext(os.path.basename(f))[0]] = SoundLoader.load(os.path.join(self.sound_dir, os.path.basename(f)))

    def play(self, sound_name):
        if sound_name in self.sound_dict:
            self.sound_dict[sound_name].play()
        else:
            print "sound",sound_name,"not found in", self.sound_dir



class PlayerCharacter(Widget):
    isRendered = BooleanProperty(False)
    y_velocity = NumericProperty(0)
    oyv = 0
    is_on_ground = BooleanProperty(False)
    jump_num = NumericProperty(0)
    max_jumps = NumericProperty(2)
    jump_velocity = NumericProperty(250)
    is_jumping = BooleanProperty(False)
    landed = BooleanProperty(False)
    drop_plat = BooleanProperty(False)
    current_plat_height = NumericProperty(0)
    dash_time_count = NumericProperty(0)
    jump_dash = BooleanProperty(False)
    dash_set = BooleanProperty(False)
    stop = BooleanProperty(False)

    drop_velocity = NumericProperty(-500)
    is_dropping = BooleanProperty(False)

    gravity = NumericProperty(300)

    is_dashing = False
    has_emitted_dash_particles = False

    offensive_move = BooleanProperty(False)

    game = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(PlayerCharacter, self).__init__(**kwargs)
        self.x = Window.width * .2
        self.y = Window.height * .5
        self.size = (82, 150)
        self.size_hint = (None, None)
        self.collided_platform = ObjectProperty(None)
        self.render_dict = dict()
        self.animation_controller = AnimationController('char1', 'walk')
        Clock.schedule_once(self._update)

    def _update(self, dt):
        self._advance_time(dt)
        self._render()
        if not self.stop: Clock.schedule_once(self._update)

    def _check_collision(self):
        if self.is_jumping: return False
        for each in self.game.foreground.platforms:
            if (self.center_x >= each.x) and (self.center_x <= each.x + each.size[0]):
                tile_idx = int((self.center_x - each.x)/each.tile_size[0])
                if tile_idx < 0 or tile_idx >= each.r: continue
                for h in each.platform_heights[tile_idx]:
                     if abs(self.y - (each.y + h)) < 10:
                        self.y = each.y + h
                        self.current_plat_height = h
                        for enemy in each.enemies:
                            enemy.attack_command = True
                        return True
        return False

    def exec_move(self, move_name, *largs):
        # move-specific code that is NOT animation related goes here (for example, physics)
        if move_name == 'jump1':
            if self.jump_num >= self.max_jumps: return
            self.jump_num += 1
            self.is_jumping = True
            self.offensive_move = False
            
            self.y_velocity += self.jump_velocity
            log.log_event('jump1')
        elif move_name == 'drop':
            # you can only drop from a jump
            if self.jump_num == 0: return
            if self.is_dashing: return
            anim = Animation(global_speed = .3 * self.game.score.global_speed_multiplier, duration = .2)
            anim.start(self.game)
            self.is_jumping = False
            self.is_dropping = True
            self.offensive_move = True
            self.y_velocity = self.drop_velocity
            # self.game.sound_fx.play('sword_draw')
            self.game.sound_fx.play('media/sounds/sword_draw.wav')
            log.log_event('drop')
        elif move_name == 'drop-land':
            # get the game clock running back at normal speed again
            anim = Animation(global_speed = 1 * self.game.score.global_speed_multiplier, duration = .5)
            anim.start(self.game)
            # self.is_dropping = False
            self.landed = True
            self.is_jumping = False
            self.offensive_move = False
            Clock.schedule_once(partial(self.exec_move, 'walk'), .3)
        elif move_name == 'dash':
            anim = Animation(global_speed = 3 * self.game.score.global_speed_multiplier, duration = .1)
            anim.start(self.game)
            self.is_dashing = True
            self.offensive_move = True
            # self.is_jumping = False
            # self.game.sound_fx.play('sword_draw')
            self.game.sound_fx.play('media/sounds/sword_draw.wav')
            Clock.schedule_once(partial(self.exec_move, 'dash-end'), .28)
            log.log_event('dash')
        elif move_name == 'dash-end':
            anim = Animation(global_speed = 1 * self.game.score.global_speed_multiplier, duration = .1)
            anim.start(self.game)
            self.offensive_move = True
            self.drop_plat = False
            self.is_dashing = False
            # as of now dash-end does not have an animation associated with it
            if self.is_dropping or self.is_jumping:
                self.exec_move('jump2')
            else:
                self.exec_move('walk')
            return
        
        elif move_name == 'walk':
            
            self.is_dropping = False
            self.drop_plat = False
            self.is_jumping = False
            self.offensive_move = False

        elif move_name == 'drop_platform':
            
            self.is_dropping = False
            self.is_jumping = False
            self.y = self.y - 5
            self.y_velocity = self.drop_velocity
            self.exec_move('jump2')
            log.log_event('drop_platform')

        self.animation_controller.set_animation(move_name)

    def on_y_velocity(self, instance, value):
        # watches for the point where player hits the apex of his parabola so that we can change animations
        # if character is not jumping, we don't care about y_velocity and who likes running extra python code? not my crappy tablet!
        # if self.jump_num == 0: return
        # but if velocity used to be positive and now it's negative, execute the jump2 move
        if self.oyv > 0 and value <= 0:
            self.is_jumping = False
            if not self.is_dashing: self.exec_move('jump2')
        self.oyv = value

    def die(self):
        self.y = Window.height *.5
        self.y_velocity = 0
        self.jump_num = 1
        self.is_dropping = False
        self.is_dashing = False
        self.dash_time_count = 0
        self.game.global_speed = 1
        self.exec_move('jump2')
        self.game.score.global_speed_multiplier = 1
        self.game.score.score_multiplier = 1
        # self.game.sound_fx.play('player_death')
        self.game.sound_fx.play('media/sounds/player_death.wav')

        self.game.life_count.decrease_lives()
        if self.game.life_count.lives == 0:
            self.lose()

    def lose(self):


        Clock.schedule_once(self.game.stop, .5)
        self.game.manager.get_screen('replay').game_score = self.game.score.score
        self.game.manager.current = 'replay'

    def _advance_time(self, dt):
        is_on_ground = self._check_collision()
        self.dash_set = is_on_ground

        # player was falling down and landed:
        if is_on_ground and self.y_velocity < 0:
            self.jump_dash = False
            self.y_velocity = 0
            self.jump_num = 0
            self.is_jumping = False
            if self.is_dropping:
                self.exec_move('drop-land')
            else:
                self.exec_move('walk')

        if is_on_ground and 17 <= self.texture.id <= 20 and self.drop_plat == True and self.current_plat_height > 150:
            self.exec_move('drop_platform')

        # player is in the air and not actively jumping
        if not is_on_ground:
            for each in self.game.foreground.platforms:
                for enemy in each.enemies:
                    enemy.attack_command = False
            if not self.is_jumping and not self.is_dropping and not self.is_dashing: self.exec_move('jump2')
            self.y_velocity -= self.gravity * dt

        if self.is_dashing:
            self.y_velocity = 0
            
        self.oy = self.y
        self.ox = self.x
        self.y += self.y_velocity * dt

        if self.y < 0 - self.size[0]:
            log.log_event('fell_off')
            self.die()

        # if self.is_dashing == True:
        #     self.dash_time_count += 1
        #     if self.dash_time_count == 28:
        #         self.dash_time_count = 0
        #         self.is_dashing = False

        #Animation Code:
        self.texture, self.size = self.animation_controller.get_frame()

        if self.is_dashing == True and not self.has_emitted_dash_particles:
            self.game.particle_effects.emit_dash_particles(dt, emit_x=self.x, emit_y=self.y)
            self.has_emitted_dash_particles = True
        if not self.is_dashing and self.has_emitted_dash_particles:
            self.has_emitted_dash_particles = False
        if self.landed == True:
            if self.game.particle_effects.dust_plume_emitting == True:
                self.game.particle_effects.stop_dust_plume(dt)
            self.game.particle_effects.emit_dust_plume(dt, emit_x=self.x, emit_y=self.y)
            self.landed = False
    
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
    game = ObjectProperty(None)
    sound_count = NumericProperty(1)
    global_speed_multiplier = NumericProperty(1)
    score_multiplier = NumericProperty(1)

    def __init__(self, **kwargs):
        super(ScoreDisplay, self).__init__(**kwargs)
        self.size_hint = (.3,.1)
        self.pos = (Window.width * .72, Window.height * .89)
        Clock.schedule_once(self.update_score)

    def update_score(self, dt):
        Clock.schedule_interval(self.increase_score, 1)

    def increase_score(self, dt):
        self.score += 1

    def coin_collected(self, coin_type):
        log.log_event('coin_collected')
        if coin_type == 'redcoin':
            if self.global_speed_multiplier < 2:
                self.global_speed_multiplier += .2
                self.game.global_speed = 1 * self.global_speed_multiplier
                self.score_multiplier += .4
                # self.game.sound_fx.play('red_coin_pickup')
                self.game.sound_fx.play('media/sounds/red_coin_pickup.wav')
        if coin_type == 'bluecoin':
            if self.global_speed_multiplier > .6:
                self.global_speed_multiplier -= .2
                self.game.global_speed = 1 * self.global_speed_multiplier
                self.score_multiplier -= .4
                # self.game.sound_fx.play('blue_coin_pickup')
                self.game.sound_fx.play('media/sounds/blue_coin_pickup.wav')
        if coin_type == 'goldcoin':
            self.score += int(10 * self.score_multiplier)
            if self.sound_count == 1:
                # self.game.sound_fx.play('coin_pickup_1')
                self.game.sound_fx.play('media/sounds/coin_pickup_1.wav')
                self.sound_count = 2
                return
            if self.sound_count == 2:
                # self.game.sound_fx.play('coin_pickup_2')
                self.game.sound_fx.play('media/sounds/coin_pickup_2.wav')
                self.sound_count = 1
                return

class LivesDisplay(Widget):
    lives = NumericProperty(1)

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
    active = False
    outside_range = False

class ConfinedEnemy(Widget):
    speed = NumericProperty(200)
    texture = StringProperty(None)
    speed_multiplier = NumericProperty(1)
    game = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(ConfinedEnemy, self).__init__(**kwargs)
        self.enemies = list()
        self.enemies_dict = dict()

    def create_enemy(self, plat_y, plat_x, plat_size):
        enemy = Enemy()
        enemy.test = True
        enemy.move_left = True
        enemy.move_right = False
        enemy.right = enemy.x + enemy.size[0] * .5
        enemy.top = enemy.y + enemy.size[1] * .5
        enemy.killed = False
        enemy.killed_player = False
        enemy.check_health = True
        enemy.active = True
        enemy.outside_range = False
        enemy.attack_command = False
        enemy.attack_multiplier = 1
        enemy.anim_num = random.randint(1,3)
        enemy.animation_controller = AnimationController('mechaspiderturtle', 'walkleft')
        enemy.texture = enemy.animation_controller.textures[enemy.animation_controller.active_texture_index]
        enemy.texture, enemy.size = enemy.animation_controller.get_frame()
        enemy.min = plat_x
        enemy.max = plat_x + plat_size
        enemy.y = plat_y + enemy.size[1]*.5
        enemy.x = plat_x
        enemy.right = enemy.x + enemy.size[0] * .5
        enemy.top = enemy.y + enemy.size[1] * .5
        self.enemies.append(enemy)

        return enemy

    def animate_con_enemy(self, enemy, plat_x, scroll_multiplier):
        if enemy.move_left == True:
            if enemy.anim_num == 1:
                enemy.x -= scroll_multiplier * enemy.attack_multiplier * 1.2
            if enemy.anim_num == 2:
                enemy.x -= scroll_multiplier * enemy.attack_multiplier * 1.5
            if enemy.anim_num == 3:
                enemy.x -= scroll_multiplier * enemy.attack_multiplier * 1.7
            if enemy.attack_command == True and self.game.player_character.x < enemy.x:
                move_name = 'walkattackleft'
                enemy.attack_multiplier = 1.75
            else:
                move_name = 'walkleft'
                enemy.attack_multiplier = 1
        if enemy.move_right == True:
            if enemy.anim_num == 1:
                enemy.x += scroll_multiplier * enemy.attack_multiplier * .3
            if enemy.anim_num == 2:
                enemy.x += scroll_multiplier * enemy.attack_multiplier * .5
            if enemy.anim_num == 3:
                enemy.x += scroll_multiplier * enemy.attack_multiplier * .7
            if enemy.attack_command == True and self.game.player_character.x > enemy.x:
                move_name = 'walkattackright'
                enemy.attack_multiplier = 1.75
            else:
                move_name = 'walkright'
                enemy.attack_multiplier = 1
        if enemy.x < enemy.min:
            enemy.move_right = True
            enemy.move_left = False
        if enemy.x > enemy.max:
            enemy.move_left = True
            enemy.move_right = False
        if enemy.x < -100:
            enemy.outside_range = True
            enemy.active = False
        enemy.animation_controller.set_animation(move_name)
        return enemy

    def _advance_time(self, dt):
        for enemy in self.enemies:
            #logic for player killed by enemy
            if self.game.player_character.collide_widget(enemy) and not self.game.player_character.offensive_move and not enemy.killed and not enemy.killed_player:
                if  enemy.x - self.game.player_character.x < 105 and enemy.x - self.game.player_character.x > -25:
                    if self.game.player_character.y - enemy.y < 45 and self.game.player_character.y - enemy.y > 0 \
                    or enemy.y - self.game.player_character.y < 100 and enemy.y - self.game.player_character.y > 0:
                        log.log_event('player_killed_by_enemy')
                        enemy.killed_player = True
                        self.game.player_character.y = self.game.player_character.y - 10
                        self.game.player_character.y_velocity -= self.game.player_character.jump_velocity * .5
                        self.game.player_character.exec_move('jump2')
                        self.play_killed_sound(2)
            #logic for enemy killed by player
            if self.game.player_character.collide_widget(enemy) and enemy.check_health and not enemy.killed:
                if self.game.player_character.offensive_move:
                    if self.game.player_character.animation_controller.active_animation == 'drop':
                        if enemy.x - self.game.player_character.x < 145 and enemy.x - self.game.player_character.x > 65:
                            if self.game.player_character.y - enemy.y < 40 and self.game.player_character.y - enemy.y > -60:
                                self.game.particle_effects.confined_enemy_explosion(dt, emit_x=enemy.x, emit_y=enemy.y)
                                self.kill_enemy(enemy)
                    elif self.game.player_character.animation_controller.active_animation == 'drop-land':
                        if enemy.x - self.game.player_character.x < 135 and enemy.x - self.game.player_character.x > 90:
                            if self.game.player_character.y - enemy.y < 40 and self.game.player_character.y - enemy.y > -60:
                                self.game.particle_effects.confined_enemy_explosion(dt, emit_x=enemy.x, emit_y=enemy.y)
                                self.kill_enemy(enemy)
                    elif self.game.player_character.animation_controller.active_animation == 'dash':
                        if enemy.x - self.game.player_character.x < 170 and enemy.x - self.game.player_character.x > 90:
                            if self.game.player_character.y - enemy.y < 40 and self.game.player_character.y - enemy.y > -60:
                                self.game.particle_effects.confined_enemy_explosion(dt, emit_x=enemy.x, emit_y=enemy.y)
                                self.kill_enemy(enemy)
                    # else:
                    #     self.game.player_character.offensive_move = False
                        
            if enemy.outside_range == True:
                self.enemies.pop(self.enemies.index(enemy))
                # print 'ENEMY REMOVED'

            elif enemy.killed == False:
                self.enemies_dict[enemy]['translate'].xy = (enemy.x, enemy.y)
                enemy.texture, enemy.size = enemy.animation_controller.get_frame()
                self.enemies_dict[enemy]['Quad'].texture = enemy.texture

    def kill_enemy(self, enemy):
        enemy.killed = True
        enemy.check_health = False
        # self.game.particle_effects.confined_enemy_explosion(dt, emit_x=enemy.x, emit_y=enemy.y)
        self.game.sound_fx.play('robot_explosion')
        self.enemies_dict[enemy]['translate'].xy = (-100, enemy.y)
        self.play_killed_sound(1)
        log.log_event('enemy_killed')
        return enemy
        # print 'enemy killed'

    def play_killed_sound(self, hit_sound):
        if hit_sound == 1:
            # self.game.sound_fx.play('sword_hit1')
            self.game.sound_fx.play('media/sounds/sword_hit1.wav')
            return
        if hit_sound == 2:
            # self.game.sound_fx.play('sword_hit2')
            self.game.sound_fx.play('media/sounds/sword_hit2.wav')
            return

    def _render(self, dt):
        for enemy in self.enemies:
            if enemy not in self.enemies_dict:
                self.enemies_dict[enemy] = dict()
                with self.canvas:
                    PushMatrix()
                    self.enemies_dict[enemy]['translate'] = Translate()
                    self.enemies_dict[enemy]['Quad'] = Quad(texture=enemy.texture, points=(-enemy.size[0] * 0.5, -enemy.size[1] * 0.5,
                        enemy.size[0] * 0.5, -enemy.size[1] * 0.5, enemy.size[0] * 0.5, enemy.size[1] * 0.5,
                        -enemy.size[0] * 0.5, enemy.size[1] * 0.5))
                    self.enemies_dict[enemy]['translate'].xy = (enemy.x, enemy.y)
                    PopMatrix()

class ScoringObject(object):
    x, y = -500, -500
    texture = None
    size = (0, 0)
    active = False
    outside_range = False

class WorldObject(Widget):
    speed = NumericProperty(200)
    texture = StringProperty(None)
    game = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(WorldObject, self).__init__(**kwargs)
        self.world_objects = list()
        self.world_objects_dict = dict()

    def create_world_object(self, obj_type, plat_y, plat_x):
        world_object = ScoringObject()
        world_object.collected = False
        world_object._check_collision = True
        world_object.active = True
        world_object.outside_range = False
        world_object.type = obj_type

        if world_object.type == 'goldcoin':
            world_object.animation_controller = AnimationController('goldcoin', 'resting')

        elif world_object.type == 'redcoin':
            world_object.animation_controller = AnimationController('redcoin', 'resting')

        elif world_object.type == 'bluecoin':
            world_object.animation_controller = AnimationController('bluecoin', 'resting')
            
        world_object.texture = world_object.animation_controller.textures[world_object.animation_controller.active_texture_index]
        world_object.texture, world_object.size = world_object.animation_controller.get_frame()
        world_object.y = plat_y + world_object.size[1]*2
        world_object.x = plat_x
        world_object.right = world_object.x + world_object.size[0] * .5
        world_object.top = world_object.y + world_object.size[1] * .5
        self.game.goldcoin.world_objects.append(world_object)
            
        return world_object

    def _advance_time(self, dt):
        for world_object in self.world_objects:
            # controls world object
            if self.game.player_character.collide_widget(world_object) and world_object._check_collision:
                if world_object.x - self.game.player_character.x < 92 and world_object.x - self.game.player_character.x > -5:
                    if self.game.player_character.y - world_object.y < 10 and self.game.player_character.y - world_object.y > -150:
                        world_object.collected = True
                        world_object._check_collision = False
                        self.world_objects_dict[world_object]['translate'].xy = (-201, world_object.y)
                        self.game.score.coin_collected(world_object.type)
            if world_object.x < -200:
                self.world_objects.pop(self.world_objects.index(world_object))
            elif world_object.collected == False:
                self.world_objects_dict[world_object]['translate'].xy = (world_object.x, world_object.y)
                world_object.texture, world_object.size = world_object.animation_controller.get_frame()
                self.world_objects_dict[world_object]['Quad'].texture = world_object.texture

    def _render(self):
        for world_object in self.world_objects:
            if world_object not in self.world_objects_dict:
                self.world_objects_dict[world_object] = dict()
                with self.canvas:
                    PushMatrix()
                    self.world_objects_dict[world_object]['translate'] = Translate()
                    self.world_objects_dict[world_object]['Quad'] = Quad(texture=world_object.texture, points=(-world_object.size[0] * 0.5, -world_object.size[1] * 0.5, 
                        world_object.size[0] * 0.5,  -world_object.size[1] * 0.5, world_object.size[0] * 0.5,  world_object.size[1] * 0.5, 
                        -world_object.size[0] * 0.5,  world_object.size[1] * 0.5))    
                    self.world_objects_dict[world_object]['translate'].xy = (world_object.x, world_object.y)
                    PopMatrix()

class Platform(object):
    x, y = -500, -500
    is_partially_off_screen = True
    end_height = 0
    line = 0
    earth = False
    # if Platform is an orphan, it will NOT spawn new platforms after it is on the screen.
    orphan = False
    walkable_textures = ['scaffolding-cplat-left-1.png', 'scaffolding-cplat-right-1.png', 'scaffolding-cplat-right-2.png', 
            'scaffolding-mplatnopost-1.png', 'scaffolding-mplatwithpost-left-1.png', 'scaffolding-mplatwithpost-right-1.png', 
            'platform1.png', 'platform2.png', 'platform3.png']

    def __init__(self, texture_sources, tile_size = (64,64), tiles_per_level = 1, platform_type = None):
        # takes a dictionary in the form {(r,c): filename.png} and converts it into a platform. If tile_per_level = n is provided,
        # assumes that every nth tile can be walked upon (1 is default, so you don't have to touch it if you're just making single-sprite platforms
        self.tile_size = tile_size
        self.platform_type = platform_type
        # turn filepaths into textures
        self.textures = {x: art_container.get(texture_sources[x]) for x in texture_sources.keys()}
        self.texture_sources = texture_sources
        
        # get number of rows and columns
        self.r, self.c = [z+1 for z in reduce(lambda x, y : (max(x[0],y[0]), max(x[1],y[1])), texture_sources.keys())]
        
        self.size = (tile_size[0] * self.r, tile_size[1] * self.c)
        
        self.platform_heights = []
        for r in range(self.r):
            hs = []
            for c in range(self.c):
                if (r,c) in texture_sources.keys() and os.path.basename(texture_sources[(r,c)]) in self.walkable_textures: hs.append(tile_size[1] * (c+1))
            self.platform_heights.append(hs)
        # print self.platform_heights
        self.coins = list()
        goldcoin = ScoringObject()
        self.coins.append(goldcoin)
        self.enemies = list()
        enemy = Enemy()
        self.enemies.append(enemy)

class ScrollingForeground(Widget):
    speed = NumericProperty(200)
    speed_multiplier = NumericProperty(1)
    
    
    # size of tiles used for scaffolding
    tile_size = (64,64)

    lines = [
        # top line
        {'platform_type_ratio': .5,
        'platform_max_y_change': 200,
        'max_height': .9*Window.size[1],
        'min_height': .6*Window.size[1],
        'max_length': 10,
        'max_distance': 800,
        'min_distance': 100,
        'difficulty': 1,
        'up_prob': .2,
        'down_prob': .3},

        # base line
        {'platform_type_ratio': .25,
        'platform_max_y_change': 0,
        'max_height': .2*Window.size[1],
        'min_height': 0,
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
        Clock.schedule_once(partial(self._init_platform, 0, None))
        Clock.schedule_once(partial(self._init_platform, 1, None))
        self._create_initial_platforms(1)
        Clock.schedule_once(self._update)


    def _init_platform(self, line_num, last_height, *largs):
        if random.random() < self.lines[line_num]['platform_type_ratio']:
            if last_height is None: last_height = 0
            start_height = last_height + random.randint(-self.lines[line_num]['platform_max_y_change'], self.lines[line_num]['platform_max_y_change'])
            if start_height < self.lines[line_num]['min_height']: 
                # print "too small", self.lines[line_num]['min_height']
                start_height = self.lines[line_num]['min_height']
            if start_height > self.lines[line_num]['max_height']: start_height = self.lines[line_num]['max_height']
            self.platforms.append(self._create_scaffold(line_num, start_height = start_height))
        else:
            self.platforms.append(self._create_floating_platform(line_num, last_height = last_height))

    def _get_tile_name(self, prefix, position, corner=True):
        # position is 1-9 arranged like your numpad
        if corner:
            return prefix + ['cplat-left-3', None, 'cplat-right-3',
                    'cplat-left-2', 'fblock-1', 'cplat-right-2',
                    'cplat-left-1', 'mplatnopost-1', 'cplat-right-1', 
                    'mplatwithpost-right-4', 'mplatwithpost-left-4'][position-1] + '.png'
        else:
            return prefix + ['mplatwithpost-right-3', None, 'mplatwithpost-left-3',
                    'mplatwithpost-right-2', 'fblock-1', 'mplatwithpost-left-2',
                    'mplatwithpost-right-1', 'mplatnopost-1', 'mplatwithpost-left-1'][position-1] + '.png'

    def _create_scaffold(self, line, start_height = 0):
        # print "creating scaffold with start height", start_height
        prefix = 'media/art/platforms/scaffolding-'
        
        # first create list of heights so we know what to build
        h = int(start_height/self.tile_size[1]) + 1
        heights = []
        for x in range(int(self.lines[line]['max_length']*random.random())+1):
            heights.append(h)
            r = random.random()
            if r > 1 - self.lines[line]['up_prob'] and (h + 1)*self.tile_size[1] <= self.lines[line]['max_height']:
                # build an additional level in next column
                h += 1
            elif r < self.lines[line]['down_prob'] and (h - 1)*self.tile_size[1] >= self.lines[line]['min_height']:
                # go down a level
                h -= 1
            else:
                # stay at the same level
                pass
        # print "heights", heights, h

        # make 20% of the levels underneath the top level also walkable
        last_level = max(heights)
        walkable_levels = [last_level]
        for h in range(last_level, 0, -1):
            if last_level - h > 2 and h >= 2 and random.random() < .4: 
                last_level = h
                walkable_levels.append(h)
        # print "walk", walkable_levels

        # now actually build the scaffolding
        tile_dict = {}
        bridging = False
        for col_idx, h in enumerate(heights):
            #build a "bridge" if we are connecting two scaffolds of the same height
            if (col_idx != 0) and (col_idx != len(heights) - 1) and h == heights[col_idx-1] == heights[col_idx+1]:
                tile_dict[(2*col_idx, h-1)] = tile_dict[(2*col_idx + 1, h-1)] = self._get_tile_name(prefix, 8)
                if not bridging:
                    tile_dict[(2*col_idx, h-1)] = self._get_tile_name(prefix, 7, corner = False)
                    tile_dict[(2*col_idx, h-2)] = self._get_tile_name(prefix, 4, corner = False)
                    for i in range(h-2):
                        tile_dict[(2*col_idx, i)] = self._get_tile_name(prefix, 11, corner = True)
                    bridging = True
                continue
            elif bridging:
                # finish the bridge
                tile_dict[(2*col_idx - 1, h-1)] = self._get_tile_name(prefix, 9, corner = False)
                tile_dict[(2*col_idx - 1, h-2)] = self._get_tile_name(prefix, 6, corner = False)
                for i in range(h-2):
                    tile_dict[(2*col_idx - 1, i)] = self._get_tile_name(prefix, 10, corner = True)
                bridging = False
            for r in (0,1):
                for c in range(h):
                    t = (r + 2*col_idx, c)
                    corner = False
                    if r == 0:
                        if col_idx == 0:    
                            corner = True
                        if col_idx > 0 and c >= heights[col_idx - 1]:
                            tile_dict[(t[0]-1, t[1])] = self._get_tile_name(prefix, 10, corner = True)
                        if c + 1 in walkable_levels + [h]:
                            position = 7
                        elif c + 2 in walkable_levels + [h]:
                            position = 4 
                        else:
                            position = 1  
                    elif r == 1:
                        if col_idx == len(heights) - 1:
                            corner = True
                        if col_idx < len(heights) - 1 and c >= heights[col_idx + 1]:
                            tile_dict[(t[0]+1, t[1])] = self._get_tile_name(prefix, 11, corner = True)
                        if c + 1 in walkable_levels + [h]:
                            position = 9
                        elif c + 2 in walkable_levels + [h]:
                            position = 6 
                        else:
                            position = 3  
                    tile_dict[t] = self._get_tile_name(prefix, position, corner = corner)
        # print tile_dict

        platform = Platform(tile_dict, platform_type = 'scaffold')
        platform.x = Window.size[0]
        platform.y = 0
        platform.end_height = platform.y + heights[-1] * platform.tile_size[1]
        platform.line = line
        self.add_enemy(platform)
        self.add_coins(platform)
        # print 'tile dict',col_idx
        return platform

    def _signal_platform_on_screen(self, platform):
        # print "PLATFORM COMPLETE"
        if platform.orphan:
            return
        interval = random.triangular(self.lines[platform.line]['min_distance'], self.lines[platform.line]['max_distance'],
                    self.lines[platform.line]['min_distance'] + self.lines[platform.line]['difficulty']*(self.lines[platform.line]['max_distance']
                     - self.lines[platform.line]['min_distance'])) / (self.speed * self.speed_multiplier)

        Clock.schedule_once(partial(self._init_platform, platform.line, platform.end_height), interval)

    def _create_initial_platforms(self, line):
        src = {(0,0): 'media/art/platforms/platform1.png'}
        texture_size = art_container.get(src[(0,0)]).size
        for x in range(0, Window.size[0], texture_size[0] - 50):
            # print "creating initial platform at", x
            platform = Platform(src, tile_size = texture_size, platform_type = 'floating')
            platform.x = x
            platform.y = -texture_size[1]*0.5
            platform.end_height = platform.y + texture_size[1]
            platform.line = line
            platform.orphan = True
            self.platforms.append(platform)


    def _create_floating_platform(self, line, last_height = None):
        src = random.choice([{(0,0): 'media/art/platforms/platform1.png'},
            {(0,0): 'media/art/platforms/platform2.png'},
            {(0,0): 'media/art/platforms/platform3.png'}])
        texture_size = art_container.get(src[(0,0)]).size
        platform = Platform(src, tile_size = texture_size, platform_type = 'floating')
        platform.x = Window.size[0]
        if last_height is None:
            platform.y = -texture_size[1]*0.5
        else:
            y = last_height - texture_size[1] + random.randint(-self.lines[line]['platform_max_y_change'], self.lines[line]['platform_max_y_change'])
            if y < self.lines[line]['min_height'] - texture_size[1]*0.5: y = self.lines[line]['min_height'] - texture_size[1]*0.5
            if y > self.lines[line]['max_height'] - texture_size[1]*0.5: y = self.lines[line]['max_height'] - texture_size[1]*0.5
            platform.y = y
        platform.end_height = platform.y + texture_size[1]
        platform.line = line
        self.add_enemy(platform)
        self.add_coins(platform)
        return platform

    def add_enemy(self,platform):
        select_enemy = random.randint(1,2)
        if select_enemy == 1 and platform.size[0] > 200:
            confined_enemy = self.game.confined_enemy.create_enemy(plat_y = platform.y + platform.size[1], plat_x = platform.x + platform.size[0]*.5, plat_size = platform.size[0])
            platform.enemies.append(confined_enemy)
        return platform

    def add_coins(self,platform):
        select_coin = random.randint(1,12)
        if select_coin == 1 or select_coin == 9 or select_coin == 10 or select_coin == 12:
            for i in range(1, int(platform.size[0]/50)):
                plat_x = platform.x + 50 * i
                goldcoin = self.game.goldcoin.create_world_object(obj_type='goldcoin', plat_y = platform.y + platform.size[1], plat_x = plat_x)
                platform.coins.append(goldcoin)
        elif select_coin == 4 or select_coin == 8:
            if platform.y < Window.height*.65:
                parab_length = int(platform.size[0]/80)
                plat_x = platform.x
                for i in range(-parab_length+1,parab_length):
                    plat_x += 40
                    plat_y = platform.y + platform.size[1]*1.35 + (3*parab_length - (i*i))*4
                    goldcoin = self.game.goldcoin.create_world_object(obj_type='goldcoin', plat_y = plat_y, plat_x = plat_x)
                    platform.coins.append(goldcoin)
        elif select_coin == 2 or select_coin == 5 or select_coin == 7:
            goldcoin = self.game.goldcoin.create_world_object(obj_type='redcoin', plat_y = platform.y + platform.size[1], plat_x = platform.x + platform.size[0]*.5)
            platform.coins.append(goldcoin)
        elif select_coin == 3:
            goldcoin = self.game.goldcoin.create_world_object(obj_type='bluecoin', plat_y = platform.y + platform.size[1], plat_x = platform.x + platform.size[0]*.5)
            platform.coins.append(goldcoin)
        elif select_coin == 6 or select_coin == 11:
            parab_length = int(platform.size[0]/80)
            plat_x = platform.x + platform.size[0]*.9
            for i in range(-parab_length+1,0):
                plat_x += 40
                plat_y = platform.y + platform.size[1]*1.35 + (3*parab_length - (i*i))*5
                goldcoin = self.game.goldcoin.create_world_object(obj_type='goldcoin', plat_y = plat_y, plat_x = plat_x)
                platform.coins.append(goldcoin)
        platform.earth = True
        return platform

    def _update(self, dt):
        self._advance_time(dt)
        self._render()
        self.game.confined_enemy._render(dt)
        self.game.confined_enemy._advance_time(dt)
        self.game.goldcoin._render()
        self.game.goldcoin._advance_time(dt)
        Clock.schedule_once(self._update)

    def _advance_time(self, dt):
        for platform in self.platforms:
            scroll_multiplier = self.speed * self.speed_multiplier * dt
            platform.x -= scroll_multiplier
             # set goldcoin x to correspond with its platform
            for goldcoin in platform.coins:
                if goldcoin.active:
                    if goldcoin.x < -100:
                        goldcoin.outside_range = True
                        goldcoin.active = False
                    else:
                        goldcoin.x -= scroll_multiplier
                        # self.game.particle_effects.goldcoin_shimmer(dt, emit_x=goldcoin.x, emit_y=goldcoin.y)
            # set confined enemy x to correspond with its platform
            for enemy in platform.enemies:
                if enemy.active:
                    if enemy.x < -150:
                        enemy.outside_range = True
                        enemy.active = False
                    else:
                        enemy.min = platform.x
                        enemy.max = platform.x + platform.size[0]
                        enemy = self.game.confined_enemy.animate_con_enemy(enemy=enemy, plat_x=platform.x, scroll_multiplier=scroll_multiplier)

            if platform.x < -platform.size[0]*1.5:
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
    dust_plume = ObjectProperty(ParticleSystem)
    dust_plume_emitting = BooleanProperty(False)
    game = ObjectProperty(None)

    def emit_dust_plume(self, dt, emit_x, emit_y, name = 'ParticleEffects/game_effects/hhs-dirtplume.pex'):
        self.dust_plume = ParticleSystem(name)
        self.dust_plume.emitter_x = emit_x + 32
        self.dust_plume.emitter_y = emit_y
        self.dust_plume.start()
        self.dust_plume_emitting = True
        self.add_widget(self.dust_plume)
        Clock.schedule_once(self.stop_dust_plume, .9)

    def stop_dust_plume(self,dt):
        self.dust_plume_emitting = False
        self.dust_plume.stop(clear=True)
        self.remove_widget(self.dust_plume)
        

    def emit_dash_particles(self, dt, emit_x, emit_y, name = 'ParticleEffects/game_effects/hhs-dash.pex'):
        self.dash_particles = ParticleSystem(name)
        self.dash_particles.emitter_x = emit_x + 32
        self.dash_particles.emitter_y = emit_y
        self.dash_particles.start()
        self.add_widget(self.dash_particles)
        Clock.schedule_once(self.stop_dash_particles, .5)

    def stop_dash_particles(self,dt):
        self.dash_particles.stop(clear=True)
        self.remove_widget(self.dash_particles)

    def goldcoin_shimmer(self, dt, emit_x, emit_y, name = 'ParticleEffects/game_effects/hhs-coinpowerup1.pex'):
        return
        self.shimmer = ParticleSystem(name)
        self.shimmer.emitter_x = emit_x - 30
        self.shimmer.emitter_y = emit_y
        self.shimmer.start()
        self.add_widget(self.shimmer)
        Clock.schedule_once(self.stop_shimmer, .3)

    def stop_shimmer(self,dt):
        self.shimmer.stop(clear=True)
        self.remove_widget(self.shimmer)

    def confined_enemy_explosion(self,dt, emit_x, emit_y, name = 'ParticleEffects/game_effects/hhs-robotexplosion.pex'):
        self.explode = ParticleSystem(name)
        self.explode.emitter_x = emit_x
        self.explode.emitter_y = emit_y
        self.explode.start()
        self.add_widget(self.explode)
        Clock.schedule_once(self.stop_explosion, .5)

    def stop_explosion(self, dt):
        self.explode.stop(clear=True)
        self.remove_widget(self.explode)


class ScrollImage(object):
    x, y = -500, -500
    texture = None
    size = (0, 0)
    spacing = 0

class ScrollingMidground(Widget):
    current_midground_x = NumericProperty(0)
    speed_multiplier = NumericProperty(1)
    texture_keys = ['media/art/midground_objects/testarch.png',
                    'media/art/midground_objects/testhill.png',
                    'media/art/midground_objects/testhill2.png',
                    'media/art/midground_objects/testhouse.png',
                    'media/art/midground_objects/cherrytree1.png',
                    'media/art/midground_objects/tree1.png',]

    def __init__(self, **kwargs):
        super(ScrollingMidground, self).__init__(**kwargs)
        self.midelements = list()
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
        midground.texture_key = random.choice(self.texture_keys)
        midground.texture = art_container.get(midground.texture_key)
        midground.spacing = random.randint(0, 500)
        midground.size = midground.texture.size
        midground.speed = midground.size[0]*.25
        midground.y = midground.size[1]*.5
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
                    self.midground_dict[midground]['Quad'] = Quad(texture=midground.texture, points=(-midground.size[0] * 0.5, -midground.size[1] * 0.5,
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
    current_land_background_x = NumericProperty(0)
    current_sky_background_x = NumericProperty(0)
    texture_keys = ['media/art/background_objects/testground1.png',
                'media/art/background_objects/testground2.png',
                'media/art/background_objects/cloud1.png',
                'media/art/background_objects/cloud2.png',
                'media/art/background_objects/cloud3.png',
                'media/art/background_objects/cloud4.png',
                ]

    def __init__(self, **kwargs):
        super(ScrollingBackground, self).__init__(**kwargs)
        self.backelements = list()
        self.backgrounds = list()
        self.background_dict = dict()
        Clock.schedule_once(self._init_background)
        Clock.schedule_once(self._update_background)

    def _init_background(self,dt):
        backgroundxspace = Window.width * 2.5
        num_back_objects = 0
        while backgroundxspace > 0:
            background = self._create_background()
            self.backgrounds.append(background)
            if background.sky == False:
                backgroundxspace -= background.size[0]
            num_back_objects += 1

    def _create_background(self):
        background = ScrollImage()
        background.texture_key = random.choice(self.texture_keys)
        background.texture = art_container.get(background.texture_key)
        background.size = background.texture.size
        print "creating background", background.texture_key, background.size
        background.speed = background.size[0]*.1
        if 'testground' in background.texture_key:
            background.y = background.size[1]*.5
            background.spacing = -5
            background.x = self.current_land_background_x + background.spacing
            background.sky = False
            self.current_land_background_x += background.size[0] + background.spacing
        else:
            background.y = Window.height - background.size[1]*random.uniform(.2,2.5)
            background.spacing = random.uniform(10,20)
            background.x = self.current_sky_background_x + background.spacing
            background.sky = True
            self.current_sky_background_x += background.size[0] - background.spacing

        return background

    def _render_background(self):
        for background in self.backgrounds:
            if background not in self.background_dict:
                self.background_dict[background] = dict()
                with self.canvas:
                    PushMatrix()
                    self.background_dict[background]['translate'] = Translate()
                    self.background_dict[background]['Quad'] = Quad(texture=background.texture, points=(-background.size[0] * 0.5, -background.size[1] * 0.5, 
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
                if background.sky == False:
                    self.current_land_background_x -= background.size[0] + background.spacing
                elif background.sky == True:
                    self.current_sky_background_x -= background.size[0] - background.spacing
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

class GetNameInput(Widget):
    
    ok = BooleanProperty(False)
    text = StringProperty("Please enter your name.")

class ReplayScreen(Screen):
    foreground = ObjectProperty(None)
    hi_scores_list = ListProperty([("-", "0")]*5)
    game_score = 0

    def __init__(self, **kwargs):
        super(ReplayScreen, self).__init__(**kwargs)

    def on_transition_state(self, instance, value):
        if value != 'in':
            return
        log.record_data('game_score', self.game_score)

        self.hi_scores_from_file = []
        try:
            with open('hi_scores', 'r') as hi_score_file:
                for line in hi_score_file:
                    if line.strip() == '': continue
                    ls = [x.strip() for x in line.split(':')]
                    self.hi_scores_from_file.append([ls[0], float(ls[1])])
        except IOError:
            pass

        self.update_hi_score_display()
        

        # now test if the user's score is over min(self.hi_scores_from_file)
        if self.game_score >= min([float(t[1]) for t in self.hi_scores_list]) or len(self.hi_scores_from_file) == 0:
            self.get_name_widget = GetNameInput()
            popup = Popup(title='Congratulations!', content = self.get_name_widget, size_hint=(.4,.4))
            self.get_name_widget.bind(ok = popup.dismiss)
            popup.bind(on_dismiss = self.get_name_popup_closed)
            popup.open()
        else:
            log.send_to_logs()
    
    def get_name_popup_closed(self, *largs):
        print self.get_name_widget.text 
        log.record_data('player_name', self.get_name_widget.text)
        log.send_to_logs()

        if self.get_name_widget.text == "Please enter your name.": return

        if len(self.hi_scores_from_file) == 5:
            self.hi_scores_from_file = sorted([[self.get_name_widget.text, self.game_score]] + sorted(self.hi_scores_from_file, key=lambda t: t[1])[1:], key=lambda t: t[1], reverse=True)
        else:
            self.hi_scores_from_file = sorted([[self.get_name_widget.text, self.game_score]] + sorted(self.hi_scores_from_file, key=lambda t: t[1]), key=lambda t: t[1], reverse=True)
        
        self.update_hi_score_display()
        self.write_hi_scores_to_file()

    def update_hi_score_display(self):
        for idx, score in enumerate(sorted(self.hi_scores_from_file, key=lambda t: t[1], reverse=True)):
            self.hi_scores_list[idx] = (score[0], str(int(score[1])))

    def write_hi_scores_to_file(self):
        with open('hi_scores', 'w') as hi_score_file:
            for line in self.hi_scores_list:
                hi_score_file.write(line[0]+ ": " + str(line[1]) + '\n')

    def button_callback(self, btn_id):
        if btn_id == 'quit':
            Window.close()
        elif btn_id == 'new':
            log.clear()
            self.parent.remove_widget(self.manager.get_screen('game'))
            self.parent.add_widget(RunningGame(name='game'))
            self.manager.current = 'game'
            self.manager.get_screen('game').start()


Factory.register('RunningGame', RunningGame)
Factory.register('DebugPanel', DebugPanel)
Factory.register('ScrollingMidground', ScrollingMidground)
Factory.register('ScrollingBackground', ScrollingBackground)
Factory.register('ScoreDisplay', ScoreDisplay)
Factory.register('LivesDisplay', LivesDisplay)

log = Logger()
art_container = ArtContainer('media/art')

class RunningGameApp(App):
    def build(self):
        sm = ScreenManager(transition = FadeTransition())
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(RunningGame(name='game'))
        sm.add_widget(ReplayScreen(name='replay'))
        return sm

if __name__ == '__main__':
    RunningGameApp().run()