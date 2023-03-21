#!/usr/bin/env python

import glob
import os
import re
import signal
import time
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
  'zeiss': [7,9,7,7,7,7,5,4,0],
}


start_message="""
This is Laura's custom Piano HAT program.  Can you find all easter eggs?

Press Ctrl+C to exit
"""

# Settings and vars for the piano
NOTE_OFFSET = -9
FILETYPES = ['*.wav', '*.ogg']
samples = []
files = []
octaves = 0
opmode_index = 0


def turn_off_leds():
    for led in range(16):
       pianohat.set_led(led, False)


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
    octaves = len(files) // 12
    samples = [pygame.mixer.Sound(sample) for sample in files]


# Pressing 'instrument' will cycle through the modes. All modes
# keep their state.
def handle_instrument(channel, pressed):
    global opmodes, opmode_index
    if pressed:
        opmode_index += 1
        opmode_index %= len(opmodes)
        print('Selecting Opmode {}'.format(opmodes[opmode_index].name))
        opmodes[opmode_index].activate()


class PianoMode:
    auto_led = True

    def activate(self):
        pianohat.on_note(self.handle_note)
        pianohat.on_octave_up(self.handle_octave_up)
        pianohat.on_octave_down(self.handle_octave_down)
        for x in range(16):
            pianohat.set_led(x, False)
        pianohat.auto_leds(self.auto_led)

    def handle_note(self, channel, pressed):
        pass

    def handle_octave_up(self, channel, pressed):
        pass

    def handle_octave_down(self, channel, pressed):
        pass


class SimplePianoMode(PianoMode):
    auto_led = True

    def __init__(self, name="Piano", starting_octave=0):
        self.name = name
        if starting_octave >= 0 and starting_octave < octaves:
            self.octave = starting_octave
        else:
            print('Impossible starting octave. Initializing with 0.')
            self.octave = 0

    def handle_note(self, channel, pressed):
        note_index = channel + (12 * self.octave) + NOTE_OFFSET
        if note_index >= 0 and note_index < len(samples) and pressed:
            print('Playing Sound {}'.format(files[note_index]))
            samples[note_index].play(loops=0)

    def handle_octave_up(self, channel, pressed):
        if pressed and self.octave < octaves:
            self.octave += 1
            print('Selecting Octave {}'.format(self.octave))

    def handle_octave_down(self, channel, pressed):
        if pressed and self.octave > 0:
            self.octave -= 1
            print('Selecting Octave {}'.format(self.octave))


class MelodyMode(PianoMode):
    auto_led = False

    def __init__(self, name="Melody", melody='alle_meine_entchen',
                 easter_egg=None, octave=4, transpose=0):
        self.name = name
        self.melody = melodies[melody]
        if easter_egg:
            self.play_on_success = os.path.join(BANK, easter_egg)
        else:
            self.play_on_success = None
        # use 'octave' to bring the samples to a reasonable range and
        # use 'transpose' to transpose as necessary.
        self.note_offset = 12*octave + transpose + NOTE_OFFSET

    def _success(self):
        if self.play_on_success:
            pygame.mixer.music.load(self.play_on_success)
            pygame.mixer.music.play()
            self._music_running = True
        turn_off_leds()
        for led in range(13):
            pianohat.set_led(led, True)
            time.sleep(0.1)
        turn_off_leds()
        time.sleep(2.0)

    def _next(self):
        pianohat.set_led(self._current_note(), False)
        time.sleep(0.1)
        self.note += 1
        if self.note == len(self.melody):
            self._success()
            self.note = 0
        print('Advancing to note {} of {}'.format(self.note, len(self.melody)))
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
            print('Wrong key pressed')
            return
        if pressed:
            note_index = self.note_offset + channel
            print('Playing Sound {}'.format(files[note_index]))
            samples[note_index].play(loops=0)
            self._next()

    def handle_octave_up(self, channel, pressed):
        if self.play_on_success and pressed:
            pygame.mixer.music.unpause()
            self._music_running = True

    def handle_octave_down(self, channel, pressed):
        if self.play_on_success and pressed:
            if self._music_running:
                pygame.mixer.music.pause()
                self._music_running = False
            else:
                pygame.mixer.music.stop()


print(start_message)
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.mixer.init()
pygame.mixer.set_num_channels(16)
turn_off_leds()
load_samples()
opmodes = [SimplePianoMode(starting_octave=4),
           MelodyMode(name='Alle meine Entchen', melody='alle_meine_entchen'),
           MelodyMode(name='Zeiss-Sprung', melody='zeiss', transpose=6, easter_egg='mysterious.ogg')]
# Register instrument button handling as this is a global key, independent of the mode class.
pianohat.on_instrument(handle_instrument)
# opmode_index is 0 by default.
opmodes[opmode_index].activate()
try:
    signal.pause()
except KeyboardInterrupt:
    turn_off_leds()
    exit()
