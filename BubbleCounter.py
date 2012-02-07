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

__version__ = '0.1a'

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
                 dataFormat='S32_LE', dataFrequency=8000, sampleTime=1000, 
                 minTimeBetweenBubbles=50, debug=False):
        """Creates a bubble counter.

        inputFile: The file to read from. This should be a RAW file containing
            data in the format specified by sampleFormat.

        outputFile: The file to write the bubble counts to. The output will be
            one line for each samplePeriod, each containing the number of 
            bubbles detected within this period.

        dataFormat: The format of the data held in the RAW file or stream. This
            should be one of the string keys held in BubbleCounter.FORMATS

        dataFrequency: The number of samples of input data per second. For 
            example, set this to 8000 for an 8KHZ audio stream.

        sampleTime: The time in ms that the data is sampled for before 
            each line of output. A sensible value would be 30000 or 60000, as 
            your beer/wine/mead has just about finished fermenting when it 
            drops to about 2 bubbles per minute.

        minTimeBetweenBubbles: The minimum time between two detections that
            will be considered a new bubble (ms). Does a gurgling noise count
            as a bunch of discrete bubbles, or is it one big continuous one? 
            This setting lets you decide. The default of 100ms ought to filter
            out false positives.
        """

        # 1) Initialize IO buffers.
        # We need to maintain a list of which files we've actually opened
        # so that we can close them in the destructor. 
        self.openedFiles  = []

        if type(inputFile) == string:
            self.inputFile = open(inputFile, 'rb')
            self.openedFiles.append(self.inputFile)
        else:
            self.inputFile = inputFile

        if type(outputFile) == string:
            self.outputFile = open(outputFile, 'wb')
            self.openedFiles.append(self.outputFile)
        else:
            self.outputFile = outputFile

        # 2) Initialize input data parser
        # Convert arecord's data format name into struct.pack format, 
        # then create a reader that can read the data.
        (self.dataFormat, self.dataSize) = BubbleCounter.FORMATS[sampleFormat]
        self.dataFrequency = dataFrequency 
        self.dataFormat    = dataFormat
        self.dataReader    = lambda : self.inputFile.read(self.dataSize)

        # 3) Initialize stuff to do with the bubble counter.
        # In future we should stick a high pass filter in this section

        self.sampleTime            = sampleTime
        self.minTimeBetweenBubbles = minTimeBetweenBubbles

        # 4) Misc
        self.debug = debug

    def __del__(self):
        """Destructor.
        Just closes any files that we opened earlier.
        """
        for f in self.openedFiles:
            if not f.closed:
                f.close()

    def start(self):
        """Start the bubble counting process.
        This will continue until interrupted or the end of the input
        file or stream is reached.
        """

        # Initialize loop variables 
        # counter, sampleSum, sampleMean, sampleMax,
        # lastBubble, bubbleCount) = (0 for i in range(6))

        sampleMean = sampleCount = 0

        # iterate through the data until we reach the end
        for rawData in iter(self.dataReader, ''):
            try:
                # This unpack may fail at the end of a broken stream
                sampleValue    = unpack(structFormat, sample)[0]
                # Use the absolute value because the average of all points of 
                # a wave are at 0.0, which isn't very useful.
                sampleAbs      = abs(sampleValue)
                sampleVariance = (sampleAbs-sampleMean)**2
                sampleSum      = sampleSum + abs(sampleValue)
                sampleCount    = sampleCount + 1

                sampleSum = sampleSum + sampleAbs
            sampleMax = sampleMax if sampleMax > absSample else absSample

            if counter > lastBubble + (sampleCount / maxBubbles):
                if absSample > 2**31*0.75: # todo: proper threshold check here
                    lastBubble  = counter
                    bubbleCount = bubbleCount + 1

            if counter % sampleCount == 0:
                outputFile.write('{count}\n'.format(count=bubbleCount))
                outputFile.flush()
                sampleMean  = sampleSum / sampleCount
                sampleSum   = 0
                bubbleCount = 0

def main():
    """Main entry point into the app"""

    parser = OptionParser(usage   = __doc__,
                          version ='%prog {0}'.format(__version__))

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

    parser.add_option('-m', '--max-bubbles',
                      dest='maxBubbles',
                      type=int,
                      default=5,
                      help='The maximum number of bubbles to count in the given sample period. Defaults to 5, which at default values can count up to 5 bubbles per second. In reality, if your fermenter is producing this level of CO2 then the bubbles are too damn long to count.')

    parser.add_option('-d', '--debug',
                      dest='debug',
                      action='store_true',
                      default=False,
                      help='Enables debug mode, which spews noise to stdout.')

    (options, args) = parser.parse_args()

    bubbles = BubbleCounter(**vars(options))
    bubbles.count()

if __name__ == '__main__':
    main()
