#!/usr/bin/python
"""BubbleCounter by Gaz Davidson 2012.

Takes WAV data from stdin or a file and counts the bubbles heard during 
a given period, then outputs these numbers to stdout or a file.

To use, tape a microphone to the airlock on your fermenter, then pipe
RAW sample data into this script using arecord. This will give you a 
rough measurement of the carbon dioxide being released as you ferment
your beer or wine. 

See bubbler.sh for an example script.
"""

import sys

from optparse import OptionParser
from struct   import unpack

class BubbleCounter(object):
    """Bubble counting class."""

    FORMATS = {'S8':         ('b',  1),
               'S16_LE':     ('<h', 2),
               'S16_BE':     ('>h', 2),
               'S32_LE':     ('<l', 4),
               'S32_BE':     ('>l', 4),
               'FLOAT_LE':   ('<f', 4),
               'FLOAT_BE':   ('>f', 4),
               'FLOAT64_LE': ('<d', 8),
               'FLOAT64_BE': ('>d', 8)}

    def __init__(self, inputFile=sys.stdin, outputFile=sys.stdout, 
                 sampleFormat='S32_LE', sampleCount='8000'):

        (structFormat, sampleSize) = BubbleCounter.FORMATS[sampleFormat]
        sampleCount = int(sampleCount)

        reader = lambda : inputFile.read(sampleSize)

        for sample in iter(reader, ''):
            # abort if the sample data is the wrong length
            if len(sample) != sampleSize:
                break

            print unpack(structFormat, sample)[0]

def main():
    """Main entry point into the app"""

    parser = OptionParser(usage   = __doc__,
                          version ='%prog 1.0')

    parser.add_option('-i', '--input',
                      dest='inputFile',
                      default=sys.stdin,
                      help='The file to read the RAW data from. Defaults to stdin')

    parser.add_option('-o', '--output',
                      dest='outputFile',
                      default=sys.stdout,
                      help='The file to write the bubble count to. Defaults to stdout')

    formats = BubbleCounter.FORMATS.keys()
    formats.sort()

    parser.add_option('-f', '--format',
                      dest='sampleFormat',
                      default='S32_LE',
                      choices=formats,
                      help='The format of the RAW data, must be one of {f}. Defaults to S32_LE.'.format(f=', '.join(formats)))

    parser.add_option('-c', '--count',
                      dest='sampleCount',
                      type=int,
                      default=8000,
                      help='The number of samples to read before outputting a value. Defaults to 8000.')

    (options, args) = parser.parse_args()

    bubbles = BubbleCounter(**vars(options))

if __name__ == '__main__':
    main()
