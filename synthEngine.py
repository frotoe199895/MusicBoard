import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
import time
import pygame
from enum import Enum
from threading import Thread
import random

sample_rate = 44100
size = -16
channels = 1
# https://stackoverflow.com/questions/18273722/pygame-sound-delay
buffersize = 512
pygame.mixer.pre_init(int(sample_rate/2), size, channels, buffersize)
pygame.mixer.init()
pygame.mixer.set_num_channels(100)


# https://en.wikipedia.org/wiki/MIDI_tuning_standard
def midi(midiKey):
    # midi key 69 --> A4
    # midi key 70 --> A#4
    # midi key 71 --> B4
    freq = (440) * (2**((midiKey-69)/12))
    return freq


# https://docs.python.org/3/library/enum.html
class Wave(Enum):
    SAW = 0
    SINE = 1
    SQUARE = 2
    TRIANGLE = 3
    NOISE = 4


def playArray(array, repeat=False):
    scaledArray = 0.5 * array * 32768
    scaledArray = scaledArray.astype(np.int16)
    pySound = pygame.sndarray.make_sound(scaledArray)

   # pySound = Array2PySound(array)
    k = -1 if repeat else 0
    pyChannel = pySound.play(k)
    return pySound, pyChannel


def Array2PySound(array):
    scaledArray = 0.5 * array * 32768
    scaledArray = scaledArray.astype(np.int16)
    pySound = pygame.mixer.Sound(scaledArray)
    return pySound


def noise(array):
    out = []
    random.seed()
    for i in array:
        out.append(2 * random.random() - 1)
    return np.array(out)


class synth:
    def __init__(self, oscillators=2):

        self.sources = []
        for i in range(oscillators):
            self.sources.append(oscillator())
        self.adsr = Envelope()
        self.ffilter = Filter()
        self.sustains = {}
        self.vol = 1

    def getToneData(self, freq, dur):
        tone = 0
        for osc in self.sources:
            tone += osc.getToneData(freq, dur)
        tone /= np.amax(tone)
        tone = self.ffilter.run(tone)
        return self.vol * tone

    def draw(self, freq):
        # plt.hold(True)

        for source in self.sources:
            source.plot(freq)

        y = self.getToneData(freq, 3/freq)
        t = np.linspace(0, 3/freq, y.size)
        plt.plot(t, y)

        # plt.hold(False)
        plt.ylim(-1, 1)
        plt.show()

    def play(self, freq):
        if str(freq) not in self.sustains:
            self.sustains[str(freq)] = None

        if self.sustains[str(freq)] is None:
            # get tone data of the synth at this frequency for 5 waves
            tone = self.getToneData(freq, 300/freq)
            pySound, pyChannel = playArray(tone, True)
            self.adsr.start(pySound)
            self.sustains[str(freq)] = pySound
            return pySound
        else:
            print("Frequency: " + str(freq) + " has not been released!")

    def release(self, freq):
        self.adsr.release(self.sustains[str(freq)])
        self.sustains[str(freq)].stop()
        self.sustains[str(freq)] = None


class oscillator:
    def __init__(self, form=Wave.SINE, scale=1, fine=0, shift=0):
        self.form = form
        self.scale = scale
        self.fine = 0
        self.shift = 0

    def getToneData(self, freq, dur):
        t = np.linspace(0, dur, dur * sample_rate, False)
        theta = 2 * np.pi * (freq + self.fine) * t + self.shift
        waveforms = {
                Wave.SINE: np.sin(theta),
                Wave.SAW: signal.sawtooth(theta, 0),
                Wave.SQUARE: signal.square(theta),
                Wave.TRIANGLE: signal.sawtooth(theta, 0.5),
                Wave.NOISE: noise(theta)
                }
        return self.scale * waveforms.get(self.form)

    def play(self, freq, dur):
        tone = self.getToneData(freq, dur)
        pySound, pyChannel = playArray(tone)
        return pySound

    def plot(self, freq):
        y = self.getToneData(freq, 3/freq)
        t = np.linspace(0, 3/freq, y.size)
        plt.plot(t, y)

class lfo:
    def __init__(self, form=Wave.SINE, freq=10):
        self.osc = oscillator()
        self.osc.form = form
        self.freq = freq
    def getData(self, dur):
        o

class Envelope:
    def __init__(self):
        self.Adur = 0.05
        self.Dval = 0.5
        self.Ddur = 0.2
        self.Sval = 1
        self.Rdur = 0.3
        self.enabled = False
        self.sustains = {}

    def start(self, sound):
        if self.enabled:
            # http://sebastiandahlgren.se/2014/06/27/running-a-method-as-a-background-thread-in-python/
            thread = Thread(target=self.__start__, args=(sound,))
            thread.daemon = True
            thread.start()

    def __start__(self, sound):
        sound.set_volume(0)
        start = time.time()
        elapsed = 2
        while elapsed < self.Adur:
            time.sleep(1/sample_rate)
            sound.set_volume(self.Dval * elapsed/self.Adur)
            elapsed = time.time() - start

        start = time.time()
        elapsed = 0
        while elapsed < self.Ddur:
            time.sleep(1/sample_rate)
            sound.set_volume(
                    self.Dval + (self.Sval-self.Dval)*elapsed/self.Ddur)
            elapsed = time.time() - start

        sound.set_volume(self.Sval)

    def release(self, sound):
        if self.enabled:
            thread = Thread(target=self.__release__, args=(sound,))
            thread.daemon = True
            thread.start()

    def __release__(self, sound):
        start = time.time()
        elapsed = 0
        while elapsed < self.Rdur:
            time.sleep(1/sample_rate)
            sound.set_volume(self.Sval-self.Sval*elapsed/self.Rdur)
            elapsed = time.time() - start
        sound.stop()


class Filter:
    def __init__(self, mode='band', cuttoff=400, width=1000, repeats=4, mix=1):
        self.mode = mode
        self.cuttoff = cuttoff
        self.width = width
        self.mix = mix
        self.enabled = True
        self.repeats = repeats

    def draw(self):
        b, a = self.__createButter__()
        angularFreq, response = signal.freqz(b, a)
        realFreq = sample_rate * angularFreq/ (2*np.pi)

        plt.semilogx(realFreq, abs(response))
        ticks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
        labels = ["20", "50", "100", "200", "500", "1k", "2k", "5k", "10k"]
        plt.xticks(ticks, labels)

        plt.xlim([20, 20000])
        plt.show()

    def run(self,  inputSignal):
        b, a = self.__createButter__()
        outputSignal = signal.filtfilt(b, a, inputSignal)
        return self.mix * outputSignal + (1-self.mix) * inputSignal

    def __createButter__(self):
        # https://dsp.stackexchange.com/questions/49460/apply-low-pass-butterworth-filter-in-python
        if self.mode == ('low' or 'high'):
            normalizedCuttoff = self.cuttoff / (sample_rate / 2)  # Normalize the frequency
            butter = signal.butter(1 + self.repeats, normalizedCuttoff, btype=self.mode)
        elif self.mode == 'band':
            low = self.cuttoff / (sample_rate / 2)
            high = (self.cuttoff + self.width) / (sample_rate / 2)
            butter = signal.butter(1 + self.repeats, [low, high], btype=self.mode)

        return butter

if __name__ == "__main__":

    mySynth = synth(3)
    mySynth.sources[0].form = Wave.SAW
    mySynth.sources[1].form = Wave.SINE
    mySynth.sources[2].form = Wave.NOISE

    mySynth.sources[0].scale = 0.5
    mySynth.sources[1].scale = 0.5
    mySynth.sources[2].scale = 1

    mySynth.sources[1].shift = np.pi/2

    mySynth.ffilter.draw()
    mySynth.ffilter.mix = 0
    mySynth.draw(440)
    mySynth.ffilter.mix = 1
    mySynth.draw(440)

    mySynth.adsr.Adur = 0.1
    mySynth.adsr.Ddur = 0.3
    mySynth.adsr.Dval = 0.75
    mySynth.adsr.Sval = 0.5
    mySynth.adsr.Rdur = 2.0
    mySynth.useAdsr = True

    mySynth2 = synth(4)
    mySynth2.sources[0].form = Wave.SINE
    mySynth2.sources[1].form = Wave.SINE
    mySynth2.sources[2].form = Wave.SQUARE
    mySynth2.sources[3].form = Wave.NOISE
    mySynth2.sources[3].scale = 0.3

    mySynth2.vol = 0

    mySynth2.adsr.Adur = 0.1
    mySynth2.adsr.Ddur = 0.0
    mySynth2.adsr.Dval = 1.0
    mySynth2.adsr.Sval = 1.0
    mySynth2.adsr.Rdur = 0.2
    mySynth2.useAdsr = True

    def myK(k):
        mySynth2.play(midi(k))
        time.sleep(0.100)
        mySynth2.release(midi(k))
        time.sleep(0.25)

    def Achord():
        mySynth.play(midi(69))
        mySynth.play(midi(73))
        mySynth.play(midi(76))

    def AchordRel():
        mySynth.release(midi(69))
        mySynth.release(midi(73))
        mySynth.release(midi(76))

    def Bmchord():
        mySynth.play(midi(71))
        mySynth.play(midi(74))
        mySynth.play(midi(78))

    def BmchordRel():
        mySynth.release(midi(71))
        mySynth.release(midi(74))
        mySynth.release(midi(78))

    def Dchord():
        mySynth.play(midi(69))
        mySynth.play(midi(74))
        mySynth.play(midi(78))

    def DchordRel():
        mySynth.release(midi(69))
        mySynth.release(midi(74))
        mySynth.release(midi(78))

    def Fsmchord():
        mySynth.play(midi(69))
        mySynth.play(midi(73))
        mySynth.play(midi(78))

    def FsmchordRel():
        mySynth.release(midi(69))
        mySynth.release(midi(73))
        mySynth.release(midi(78))

    def Gchord():
        mySynth.play(midi(71))
        mySynth.play(midi(74))
        mySynth.play(midi(79))

    def GchordRel():
        mySynth.release(midi(71))
        mySynth.release(midi(74))
        mySynth.release(midi(79))

    while True:
        Dchord()
        myK(69)
        myK(74)
        myK(78)
        myK(81)
        myK(86)
        myK(90)
        myK(86)
        myK(81)
        myK(78)
        time.sleep(1)
        DchordRel()
        time.sleep(1)
        Achord()
        myK(69)
        myK(73)
        myK(76)
        myK(81)
        myK(85)
        myK(81)
        myK(76)
        myK(73)
        AchordRel()
        time.sleep(1)
        Bmchord()
        myK(71)
        myK(74)
        myK(78)
        myK(83)
        myK(86)
        myK(83)
        myK(78)
        myK(74)
        BmchordRel()
        time.sleep(1)
        Fsmchord()
        myK(66)
        myK(69)
        myK(73)
        myK(78)
        myK(81)
        myK(78)
        myK(73)
        myK(69)
        FsmchordRel()
        time.sleep(1)
