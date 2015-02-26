#!/usr/bin/env python2
# sva, the state vector analyzer

import os
import sys
import fileinput
import numpy

SPECTROGRAM_HEIGHT = 20
MAX_WIDTH = 56

BASE_SYMBOLS = [str(n) for n in range(0, 10)] + \
               [chr(n) for n in range(ord('a'), ord('z') + 1)] + \
               [chr(n) for n in range(ord('A'), ord('Z') + 1)] + \
               [chr(n) for n in range(ord('!'), ord('/') + 1)] + \
               [chr(n) for n in range(ord(':'), ord('@') + 1)]


def main():
    global MAX_WIDTH

    if len(sys.argv) == 2 and sys.argv[1] in ['-h', '--help']:
        print "usage: %s [fann_training_file]" % sys.argv[0]
        print "(without training file, training data is read via stdin)"
        sys.exit(0)

    stty = os.popen('stty size').read()
    if stty:
        _, cols = map(int, stty.split())
        MAX_WIDTH = cols

    states = []
    value_history = []
    vector_width = 0

    fi = fileinput.input()

    try:
        first_line = fi.readline()
    except:
        error("error: error reading training file '%s'" % fi.filename())
        sys.exit(1)

    fname = fi.filename()
    if '.train' not in fname:
        error("warning: file extension is not '.train'")

    try:
        num_states, vector_width, _ = map(int, first_line.split())
    except:
        error("error: '%s' does not appear to be a FANN training file" % fname)
        sys.exit(1)

    value_history = [[] for _ in range(num_states)]

    # go through rest of lines
    for line in fi:
        if fileinput.filelineno() % 2 == 1:
            # toss FANN's header on first line, and thereafter, every
            # other line to ignore output data
            continue

        bits = line.split()

        if len(bits) != vector_width:
            warn = "warning: %d bits in input " % len(bits) + \
                   "vector (expected %d)" % vector_width
            error(warn)

        states.append(map(int, bits))

        for bit_pos, val in enumerate(bits):
            value_history[bit_pos].append(int(val))

    print "read %d %d-bit state vectors" % (len(states), vector_width)

    commands = {('state', 'statenum'): "display a state vector",
                ('fft', 'bitnum'): "do Fourier analysis on a bit",
                ('table',): "show base %d table" % len(BASE_SYMBOLS),
                ('help',): "show this message",
                ('quit',): "exit this shell"}

    # start shell

    while True:
        try:
            cmd = raw_input("> ").strip().split()
        except (EOFError, KeyboardInterrupt):
            print
            return

        if len(cmd) == 0:
            continue

        if cmd[0] in ['s', 'state']:
            if len(cmd) > 1:
                state_num = int(cmd[1])
            else:
                state_num = int(raw_input('state (0-%d)? ' % (len(states) - 1)))

            if state_num not in range(len(states)):
                error("error: there is no state %d" % state_num)
                continue

            print_state(state_num, states[state_num])

        elif cmd[0] in ['f', 'fft']:
            if len(cmd) > 1:
                bit = int(cmd[1])
            else:
                bit = int(raw_input('bit (0-%d)? ' % (vector_width - 1)))

            if bit not in range(vector_width):
                error("error: there is no bit %d" % bit)
                continue

            print_spectrogram(value_history[bit])

        elif cmd[0] in ['t', 'table']:
            print_table()

        elif cmd[0] in ['h', 'help', '?']:
            for command, desc in commands.items():
                command_form = map(lambda s: '[' + s + ']', command[1:])
                s = command[0] + ' ' + ' '.join(command_form)

                print pad(s, MAX_WIDTH / 3) + desc

        elif cmd[0] in ['q', 'quit']:
            return

        else:
            error("unknown command: %s" % cmd[0])
            print "commands: %s" % ', '.join(map(lambda x: x[0], commands))


def print_table():
    col = 0
    for n in range(10, len(BASE_SYMBOLS)):
        s = "%s: %d" % (to_base(n, len(BASE_SYMBOLS)), n)

        if col + len(s) + 1 > MAX_WIDTH:
            print
            print s,
            col = len(s) + 1
        else:
            print s,
            col += len(s) + 1

    print
    print "base 10 digits have been omitted"


def shrink_magnitudes(mags):
    new_mags = []
    while len(mags) > MAX_WIDTH:
        for i in range(1, len(mags), 2):
            new_mags.append((i, avg(mags[i][1], mags[i - 1][1])))

        mags = new_mags
        new_mags = []

    return mags


def print_state(state_num, bits):
    print "showing state %d, one nibble at at time" % state_num

    col = 0
    for start in range(0, len(bits), 4):
        s = ''.join(map(str, bits[start:start + 4]))
        s += (4 - len(s)) * '_'

        if col + len(s) + 1 > MAX_WIDTH:
            print
            print s,
            col = len(s) + 1
        else:
            print s,
            col += len(s) + 1

    print


def print_spectrogram(bit_history):
    z = numpy.fft.rfft(map(lambda x: -1 if x == 0 else 1, bit_history))

    # remove zero-frequency component
    z[0] = 0

    magnitudes = list(enumerate(map(abs, z)))

    initial_width = len(magnitudes)
    horiz_scale = 1

    while len(magnitudes) > MAX_WIDTH:
        magnitudes = shrink_magnitudes(magnitudes)
        horiz_scale = initial_width / len(magnitudes)

    max_ = reduce(lambda a, b: a if a[1] > b[1] else b, magnitudes)[1]

    vertical_scale = max(1, int(max_ / SPECTROGRAM_HEIGHT))

    for row in range(int(max_), 1, -vertical_scale):
        for _, m in magnitudes:
            if m >= row:
                sys.stdout.write('#')
            else:
                sys.stdout.write(' ')

        print

    # print frequency values in large base
    # note: users multiply these values by horiz_scale
    for n in range(len(magnitudes)):
        sys.stdout.write(to_base(n, len(BASE_SYMBOLS)))

    print

    # show arrow to maximum frequency
    freqs_with_max = []
    for freq, mag in magnitudes:
        if mag == max_:
            freqs_with_max.append(freq)
            sys.stdout.write('^')
        else:
            sys.stdout.write(' ')

    print

    print "scale: %dx" % horiz_scale

    if len(freqs_with_max) > 1:
        s = "frequencies "
    else:
        s = "frequency "

    freqs_with_max = map(str, freqs_with_max)
    print s + "with maximum magnitude: %s" % ', '.join(freqs_with_max)


def to_base(int_, base):
    return BASE_SYMBOLS[int_]


def avg(a, b):
    return (a + b) / 2


def pad(str_, width):
    return str_ + (width - len(str_)) * ' '

def error(str_):
    sys.stderr.write(str_ + '\n')


if __name__ == '__main__':
    main()
