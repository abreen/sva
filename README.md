`sva` is a small shell-like program that provides tools to analyze
a `.train` file obtained by the FANN library in ASC. `sva` reads a
training file for a list of bit vectors corresponding to the values
of the bits ASC has determined are excited.

`sva` currently allows you to view any particular excited bit
vector state and run the Fourier transform on the values of a
particular bit over the entire trace.

This program is written in Python 2 and requires the `numpy` library.
