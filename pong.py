# DeadmanXXXII's Classic Pong - Mobile Neon Edition
# Optimized for touch controls on Android/iOS

import os, json, base64
from random import randint, choice

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty, BooleanProperty, StringProperty
from kivy.vector import Vector

Window.clearcolor = (0, 0, 0, 1)

SETTINGS_FILE = "pong_settings.json"
HIGHSCORE_FILE = "pong_highscore.json"

# Color themes
COLOR_THEMES = {
    'Neon Red': {'player': (1, 0, 0), 'ai': (1, 0, 0.4), 'ball': (1, 0.2, 0.2)},
    'Cyan/Magenta': {'player': (0, 1, 1), 'ai': (1, 0, 1), 'ball': (1, 1, 1)},
    'Green/Yellow': {'player': (0, 1, 0), 'ai': (1, 1, 0), 'ball': (1, 1, 1)},
    'Purple/Orange': {'player': (0.6, 0, 1), 'ai': (1, 0.4, 0), 'ball': (1, 1, 1)},
    'Blue/Pink': {'player': (0, 0.4, 1), 'ai': (1, 0.4, 0.8), 'ball': (1, 1, 1)}
}

# ------------------------- Helper: save/load -------------------------
def load_settings():
    default = {
        "difficulty": "Normal", 
        "sound_enabled": True, 
        "music_volume": 0.5, 
        "sfx_volume": 0.7,
        "color_theme": "Neon Red"
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f: 
                parsed = json.load(f)
            for k in default: 
                parsed.setdefault(k, default[k])
            return parsed
        except: 
            return default
    return default

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w") as f: 
            json.dump(settings, f)
    except: 
        pass

def load_highscore():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f: 
                return json.load(f).get("high_score", 0)
        except: 
            return 0
    return 0

def save_highscore(score):
    try:
        with open(HIGHSCORE_FILE, "w") as f: 
            json.dump({"high_score": score}, f)
    except: 
        pass

# ------------------------- Sample Audio (base64) -------------------------
hit_wav_b64 = (
    "UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YRAAAAD/AAD//wAA//8AAP//"
    "AAD//wAA//8AAP//AAD//wAA//8AAP//AAD//wAA"
)
over_wav_b64 = (
    "UklGRjQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAAA//8AAP//AAD//wAA"
)

def create_sample_audio():
    for name, b64 in [("hit.wav", hit_wav_b64), ("over.wav", over_wav_b64)]:
        if not os.path.exists(name):
            with open(name, "wb") as f: 
                f.write(base64.b64decode(b64))

# ------------------------- Game objects -------------------------
class PongBall(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    velocity = ReferenceListProperty(velocity_x, velocity_y)
    
    def move(self): 
        self.pos = Vector(*self.velocity) + self.pos

class PongPaddle(Widget):
    score = NumericProperty(0)
    
    def bounce_ball(self, ball, sfx=None, sfx_vol=1.0):
        if self.collide_widget(ball):
            ball.velocity_x *= -1.1
            ball.velocity_y += randint(-3, 3)
            self.score += 1
            if sfx:
                sfx.volume = sfx_vol
                sfx.play()

# ------------------------- Main Game Widget -------------------------
class PongGame(Widget):
    ball = ObjectProperty(None)
    player = ObjectProperty(None)
    computer = ObjectProperty(None)
    difficulty = StringProperty("Normal")
    sound_enabled = BooleanProperty(True)
    music_volume = NumericProperty(0.5)
    sfx_volume = NumericProperty(0.7)
    high_score = NumericProperty(0)
    color_theme = StringProperty("Neon Red")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        create_sample_audio()
        self.sfx_hit = SoundLoader.load("hit.wav")
        self.sfx_over = SoundLoader.load("over.wav")
        
        # Try to load music if it exists
        self.music = None
        if os.path.exists("8-bit-loop-music-290770.mp3"):
            self.music = SoundLoader.load("8-bit-loop-music-290770.mp3")
        
        self.high_score = load_highscore()
        self.apply_sound_settings()
        self.game_over = False
        self.restart_button = None
        self.win_label = None

    def apply_sound_settings(self):
        if self.music:
            self.music.volume = self.music_volume if self.sound_enabled else 0.0
            self.music.loop = True
            if self.sound_enabled: 
                self.music.play()
            else: 
                self.music.stop()

    def serve_ball(self, vel=(4, 0)):
        self.ball.center = self.center
        self.ball.velocity = vel
        self.game_over = False
        if self.restart_button: 
            self.remove_widget(self.restart_button)
        if self.win_label: 
            self.remove_widget(self.win_label)

    def update(self, dt):
        if self.game_over: 
            return
            
        self.ball.move()
        
        # Bounce off top/bottom
        if self.ball.y < 0 or self.ball.top > self.height: 
            self.ball.velocity_y *= -1
            
        # Paddle collisions
        self.player.bounce_ball(self.ball, self.sfx_hit if self.sound_enabled else None, self.sfx_volume)
        self.computer.bounce_ball(self.ball, self.sfx_hit if self.sound_enabled else None, self.sfx_volume)
        
        # AI movement
        ai_speed = {"Easy": 2, "Normal": 3, "Hard": 4, "Insane": 6}.get(self.difficulty, 3)
        if self.computer.center_y < self.ball.y: 
            self.computer.center_y += ai_speed
        elif self.computer.center_y > self.ball.y: 
            self.computer.center_y -= ai_speed
            
        # Out of bounds
        if self.ball.x < self.x: 
            self.computer.score += 1
            self.serve_ball((4, 0))
        if self.ball.right > self.width: 
            self.player.score += 1
            self.serve_ball((-4, 0))
            
        # Get current color theme
        colors = COLOR_THEMES.get(self.color_theme, COLOR_THEMES['Neon Red'])
        
        # Neon glow drawing
        self.canvas.after.clear()
        with self.canvas.after:
            # Ball glow
            Color(*colors['ball'], 0.4)
            Line(rectangle=(self.ball.x-2, self.ball.y-2, self.ball.width+4, self.ball.height+4), width=2)
            
            # Player paddle glow
            Color(*colors['player'], 0.5)
            Line(rectangle=(self.player.x-2, self.player.y-2, self.player.width+4, self.player.height+4), width=3)
            
            # AI paddle glow
            Color(*colors['ai'], 0.5)
            Line(rectangle=(self.computer.x-2, self.computer.y-2, self.computer.width+4, self.computer.height+4), width=3)
            
        # Check win condition
        if self.player.score >= 10 or self.computer.score >= 10: 
            self.end_game()
            
        # Draw title with current colors
        for c in list(self.children):
            if hasattr(c, "neon_title") and c.neon_title: 
                self.remove_widget(c)
                
        player_color = '#{:02x}{:02x}{:02x}'.format(int(colors['player'][0]*255), int(colors['player'][1]*255), int(colors['player'][2]*255))
        ai_color = '#{:02x}{:02x}{:02x}'.format(int(colors['ai'][0]*255), int(colors['ai'][1]*255), int(colors['ai'][2]*255))
        
        neon = Label(
            text=f"[b][color={player_color}]DeadmanXXXII's[/color] [color={ai_color}]Classic Pong[/color][/b]",
            markup=True, font_size="16sp", size_hint=(None, None), size=(340, 40),
            pos=(self.center_x-170, self.height-56), halign="center", valign="middle"
        )
        neon.neon_title = True
        self.add_widget(neon)

    def end_game(self):
        self.game_over = True
        if self.sound_enabled and self.sfx_over: 
            self.sfx_over.play()
            
        if self.player.score > self.high_score:
            self.high_score = self.player.score
            save_highscore(self.high_score)
            
        winner = "You Win!" if self.player.score > self.computer.score else "You Lose"
        self.win_label = Label(
            text=f"{winner}\nScore: {self.player.score}\nHigh: {self.high_score}",
            font_size="20sp", halign="center", valign="middle",
            size_hint=(None, None), size=(300, 120), 
            pos=(self.center_x-150, self.center_y-20)
        )
        self.add_widget(self.win_label)
        
        self.restart_button = Button(
            text="Restart", size_hint=(0.4, 0.12),
            pos_hint={'center_x': 0.5, 'center_y': 0.25}
        )
        self.restart_button.bind(on_press=self.restart_game)
        self.add_widget(self.restart_button)
        self.apply_sound_settings()

    def restart_game(self, *args):
        self.player.score = 0
        self.computer.score = 0
        self.serve_ball()
        self.apply_sound_settings()

    def on_touch_move(self, touch):
        # Touch control for player paddle - works anywhere on left half
        if not self.game_over and touch.x < self.width / 2: 
            self.player.center_y = touch.y
            
    def on_touch_down(self, touch):
        # Also respond to initial touch
        if not self.game_over and touch.x < self.width / 2: 
            self.player.center_y = touch.y
            
    def stop_music(self):
        if self.music: 
            self.music.stop()

# ------------------------- Screens -------------------------
class MenuScreen(Screen):
    def on_pre_enter(self, *a):
        self.clear_widgets()
        layout = BoxLayout(orientation='vertical', spacing=12, padding=40)
        
        title = Label(
            text="[b][color=#FF0000]DeadmanXXXII's[/color]\n[color=#FF0066]Classic Pong[/color][/b]",
            font_size='36sp', markup=True, halign='center'
        )
        title.size_hint = (1, 0.4)
        
        start_btn = Button(text="Start Game", size_hint=(1, 0.13))
        settings_btn = Button(text="Settings", size_hint=(1, 0.13))
        quit_btn = Button(text="Quit", size_hint=(1, 0.13))
        
        start_btn.bind(on_press=lambda x: self.manager.current='game')
        settings_btn.bind(on_press=lambda x: self.manager.current='settings')
        quit_btn.bind(on_press=lambda x: App.get_running_app().stop())
        
        layout.add_widget(title)
        layout.add_widget(start_btn)
        layout.add_widget(settings_btn)
        layout.add_widget(quit_btn)
        self.add_widget(layout)

class SettingsScreen(Screen):
    def on_pre_enter(self, *a):
        self.clear_widgets()
        app = App.get_running_app()
        settings = load_settings()
        
        outer = BoxLayout(orientation='vertical', padding=30, spacing=12)
        title = Label(text="Settings", font_size='28sp', size_hint=(1, 0.15))
        
        # Difficulty
        diff_label = Label(text=f"Difficulty: {settings.get('difficulty', 'Normal')}", size_hint=(1, 0.1))
        diff_btn = Button(text="Change Difficulty", size_hint=(1, 0.12))
        diff_btn.bind(on_press=lambda x: self.change_diff(diff_label))
        
        # Color Theme
        color_label = Label(text=f"Theme: {settings.get('color_theme', 'Neon Red')}", size_hint=(1, 0.1))
        color_btn = Button(text="Change Color Theme", size_hint=(1, 0.12))
        color_btn.bind(on_press=lambda x: self.change_color(color_label))
        
        # Sound
        sound_label = Label(text=f"Sound: {'On' if settings.get('sound_enabled', True) else 'Off'}", size_hint=(1, 0.1))
        sound_btn = Button(text="Toggle Sound", size_hint=(1, 0.12))
        sound_btn.bind(on_press=lambda x: self.toggle_sound(sound_label))
        
        # Back
        back_btn = Button(text="Back", size_hint=(1, 0.12))
        back_btn.bind(on_press=lambda x: setattr(self.manager, 'current', 'menu'))
        
        outer.add_widget(title)
        outer.add_widget(diff_label)
        outer.add_widget(diff_btn)
        outer.add_widget(color_label)
        outer.add_widget(color_btn)
        outer.add_widget(sound_label)
        outer.add_widget(sound_btn)
        outer.add_widget(back_btn)
        self.add_widget(outer)
        
    def change_diff(self, label):
        settings = load_settings()
        diffs = ["Easy", "Normal", "Hard", "Insane"]
        idx = diffs.index(settings.get('difficulty', 'Normal')) if settings.get('difficulty') in diffs else 1
        new_diff = diffs[(idx + 1) % len(diffs)]
        settings['difficulty'] = new_diff
        label.text = f"Difficulty: {new_diff}"
        save_settings(settings)
        
    def change_color(self, label):
        settings = load_settings()
        themes = list(COLOR_THEMES.keys())
        idx = themes.index(settings.get('color_theme', 'Neon Red')) if settings.get('color_theme') in themes else 0
        new_theme = themes[(idx + 1) % len(themes)]
        settings['color_theme'] = new_theme
        label.text = f"Theme: {new_theme}"
        save_settings(settings)
        
    def toggle_sound(self, label):
        settings = load_settings()
        settings['sound_enabled'] = not settings.get('sound_enabled', True)
        label.text = f"Sound: {'On' if settings['sound_enabled'] else 'Off'}"
        save_settings(settings)

class GameScreen(Screen):
    def on_pre_enter(self, *a):
        settings = load_settings()
        self.clear_widgets()
        self.game = PongGame()
        self.game.difficulty = settings.get("difficulty", "Normal")
        self.game.sound_enabled = settings.get("sound_enabled", True)
        self.game.music_volume = settings.get("music_volume", 0.5)
        self.game.sfx_volume = settings.get("sfx_volume", 0.7)
        self.game.color_theme = settings.get("color_theme", "Neon Red")
        self.game.high_score = load_highscore()
        self.add_widget(self.game)
        Clock.schedule_interval(self.game.update, 1.0/60.0)
        self.game.serve_ball()
        
    def on_leave(self, *a):
        Clock.unschedule(self.game.update)
        self.game.stop_music()

# ------------------------- App -------------------------
class NeonPongApp(App):
    difficulty = StringProperty("Normal")
    sound_enabled = BooleanProperty(True)
    color_theme = StringProperty("Neon Red")
    
    def build(self):
        # Load settings
        settings = load_settings()
        self.difficulty = settings.get("difficulty", "Normal")
        self.sound_enabled = settings.get("sound_enabled", True)
        self.color_theme = settings.get("color_theme", "Neon Red")
        
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(MenuScreen(name='menu'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(GameScreen(name='game'))
        return sm

if __name__ == "__main__":
    NeonPongApp().run()

