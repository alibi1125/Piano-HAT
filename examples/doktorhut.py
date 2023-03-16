#!/usr/bin/env python

import glob
import os
import re
import signal
from sys import exit

try:
    import pygame
except ImportError:
    exit("This script requires the pygame module\nInstall with: sudo pip install pygame")

import pianohat


# Soundbank path
BANK = os.path.join(os.path.dirname(__file__), "sounds")


# A little dictionary of melodies, to be used by MelodyMode.
melodies = {
  'alle_meine_entchen': [0,2,4,5,7,7,9,9,9,9,7,9,9,9,9,7,5,5,5,5,4,4,2,2,2,2,0],
  'twinkle_twinkle': [0,0,7,7,9,9,7,5,5,4,4,2,2,0],
  'zeiss': [5,5,7,5,5,5,5,4,2,0],
}


print("""
This is Laura's custom Piano HAT program.  Can you find all easter eggs?
""")

# Settings and vars for the piano
NOTE_OFFSET = -9
FILETYPES = ['*.wav', '*.ogg']
samples = []
files = []
octaves = 0
opmode_index = 0


def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s)]


def load_samples():
    global samples, files, octaves
    files = []
    base_path = os.path.join(BANK, 'piano')
    print('Loading samples from {}'.format(base_path))
    for filetype in FILETYPES:
        files.extend(glob.glob(os.path.join(base_path, filetype)))
    files.sort(key=natural_sort_key)
    octaves = len(files) / 12
    samples = [pygame.mixer.Sound(sample) for sample in files]


# Pressing 'instrument' will cycle through the modes. All modes will
# keep their state.
def handle_instrument(channel, pressed):
    global opmodes, opmode_index
    if pressed:
        opmode_index += 1
        opmode_index %= len(opmodes)
        print('Selecting opmode {}'.format(opmodes[opmode_index].name))
        opmodes[opmode_index].activate()


class PianoMode:
    auto_led = True

    def activate():
        pianohat.on_note(self.handle_note)
        pianohat.on_octave_up(self.handle_octave_up)
        pianohat.on_octave_down(self.handle_octave_down)
        for x in range(16):
            pianohat.set_led(x, False)
        pianohat.auto_leds(self.auto_led)

    def handle_note(channel, pressed):
        pass

    def handle_octave_up(channel, pressed):
        pass

    def handle_octave_down(channel, pressed):
        pass


class SimplePianoMode(PianoMode):
    auto_led = True

    def __init__(self, name="Piano", starting_octave=octaves/2):
        self.name = name
        if starting_octave >= 0 and starting_octave < octaves:
            self.octave = starting_octave
        else:
            print("Impossible starting octave. Initializing with 0.")
            self.octave = 0

    def handle_note(self, channel, pressed):
        note_index = channel + (12 * self.octave) + NOTE_OFFSET
        if note_index >= 0 and note_index < len(samples) and pressed:
            print('Playing Sound {}'.format(files[note_index]))
            samples[note_index].play(loops=0)

    def handle_octave_up(self, channel, pressed):
        if pressed and self.octave < octaves:
            self.octave += 1
            print('Selected Octave {}'.format(octave))

    def handle_octave_down(self, channel, pressed):
        if pressed and self.octave > 0:
            self.octave -= 1
            print('Selected Octave {}'.format(octave))


class MelodyMode(PianoMode):
    auto_led = False
    fadein = 1000

    def __init__(self, name="Melody", melody='alle_meine_entchen',
                 easter_egg=None, octave=4, transpose=0):
        self.name = name
        self.melody = melodies[melody]
        self.play_on_success = easter_egg
        # use 'octave' to bring the samples to a reasonable range and
        # use 'transpose' to transpose as necessary.
        self.note_offset = 12*octave + transpose + NOTE_OFFSET

    def _start_music(self):
        pygame.mixer.music.load(os.path.join(BANK, self.play_on_success))
        pygame.mixer.music.play(fade_ms=fadein)
        self._music_running = True

    def _next(self):
        pianohat.set_led(self._current_note(), False)
        time.sleep(0.1)
        self.note += 1
        self.note %= len(melody)
        if self.note == 0 and self.play_on_success:
            self._start_music()
        pianohat.set_led(self._current_note(), True)

    def _current_note(self):
        return self.melody[self.note]

    def activate(self):
        super().activate()
        # 'activate' is called when changing modes. We assume that we
        # want to reset the melody on switching modes.
        self.note = 0
        pianohat.set_led(self._current_note(), True)

    def handle_note(self, channel, pressed):
        if not channel == self._current_note():
            return
        note_index = self.note_offset + channel
        if pressed:
            print('Playing Sound {}'.format(files[note_index]))
            samples[note_index].play(loops=0)
            self._next()

    def handle_octave_up(self, channel, pressed):
        if self.play_on_success and pressed:
            pygame.mixer.music.unpause()

    def handle_octave_down(self, channel, pressed):
        if self.play_on_success and pressed:
            if self._music_running:
                pygame.mixer.music.pause()
            else:
                pygame.mixer.music.stop()


pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.init()
pygame.mixer.set_num_channels(16)

load_samples()
signal.pause()
opmodes = [SimplePianoMode(),
           MelodyMode(name='Alle meine Entchen', melody='alle_meine_entchen'),
           MelodyMode(name='Zeiss-Sprung', melody='zeiss', easter_egg='./sounds/mystery.mp3')]
pianohat.on_instrument(handle_instrument)
# opmode_index is 0 by default.
opmodes[opmode_index].activate()
