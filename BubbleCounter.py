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

__version__ = '0.2'

import sys

from math     import sqrt
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
                 dataFormat='S32_LE', dataFrequency=8000, listenTime=1000, 
                 minTimeBetweenBubbles=150, debug=False):
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

        listenTime: The time in ms that is listened to before each line of 
            output. A sensible value would be 30000 or 60000, as your beer/wine
            has just about finished fermenting when it drops to about 2 bubbles 
            per minute.

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

        if type(inputFile) == str:
            self.inputFile = open(inputFile, 'rb')
            self.openedFiles.append(self.inputFile)
        else:
            self.inputFile = inputFile

        if type(outputFile) == str:
            self.outputFile = open(outputFile, 'wb')
            self.openedFiles.append(self.outputFile)
        else:
            self.outputFile = outputFile

        # 2) Initialize input data parser
        # Convert arecord's data format name into struct.pack format, 
        # then create a reader that can read the data.
        (self.dataFormat, self.dataSize) = BubbleCounter.FORMATS[dataFormat]
        self.dataFrequency = dataFrequency 
        self.dataReader    = lambda : self.inputFile.read(self.dataSize)

        # 3) Initialize stuff to do with the bubble counter.
        # In future we should stick a high pass filter in this section
        self.listenTime               = listenTime
        self.minTimeBetweenBubbles    = minTimeBetweenBubbles
        self.samplesPerPeriod         = (dataFrequency * listenTime) / 1000
        self.minSamplesBetweenBubbles = (dataFrequency * minTimeBetweenBubbles) / 1000

        # 4) Misc
        self.debug = debug

        if debug:
            for i in self.__dict__.keys():
                print i, self.__dict__[i]
            

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
        totalSampleCount = periodSum = lastPeriodMean = 0
        periodVarianceSum = lastPeriodStdDev = 0
        lastBubble = periodBubbleCount = 0

        try:
            # iterate through data in the stream until we reach the end
            for rawData in iter(self.dataReader, ''):
                # This unpack may fail at the end of a broken stream
                sampleValue = unpack(self.dataFormat, rawData)[0]
                # Use the absolute value because the average of all points of 
                # a wave are at 0.0, which isn't very useful.
                sampleAbs        = abs(sampleValue)
                totalSampleCount = totalSampleCount + 1

                # gather stats for this time period
                sampleVariance    = (sampleAbs-lastPeriodMean)**2
                periodSum         = periodSum + sampleAbs
                periodVarianceSum = periodVarianceSum + sampleVariance

                # bubbles are two standard deviations from the mean
                if sqrt(sampleVariance) > lastPeriodStdDev * 2.0:
                    # This is a bubble, let's elongate it
                    nextBubbleMinSampleCount = lastBubble + self.minSamplesBetweenBubbles
                    lastBubble               = totalSampleCount

                    # record it only if there's enough of a gap between the bubbles
                    if totalSampleCount > nextBubbleMinSampleCount:
                        periodBubbleCount = periodBubbleCount + 1

                # We've reached the end of this time period
                if totalSampleCount % self.samplesPerPeriod == 0:
                    self.outputFile.write('{count}\n'.format(count=periodBubbleCount))
                    # we're a stream tool, remember to flush the output buffer!
                    self.outputFile.flush()
                    # Save this period's stats
                    lastPeriodMean    = periodSum / self.samplesPerPeriod
                    lastPeriodStdDev  = sqrt(periodVarianceSum / self.samplesPerPeriod)

                    periodSum         = 0
                    periodVarianceSum = 0
                    periodBubbleCount = 0


        except IOError:
            pass
        except KeyboardInterrupt:
            pass
        except struct.error:
            # broken stream
            pass

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
                      dest='dataFormat',
                      default='S32_LE',
                      choices=formats,
                      help='The format of the RAW data, must be one of {f}. Defaults to S32_LE.'.format(f=', '.join(formats)))

    parser.add_option('-q', '--frequency',
                      dest='dataFrequency',
                      default=8000,
                      type=int,
                      help='The frequency of the RAW data. Defaults to 8000 (8KHZ).')

    parser.add_option('-t', '--time',
                      dest='listenTime',
                      type=int,
                      default=10000,
                      help='The number of ms to listen for before outputting a value. Defaults to 10000. Depends on the data frequency, not real time.')

    parser.add_option('-m', '--min-bubble-gap',
                      dest='minTimeBetweenBubbles',
                      type=int,
                      default=250,
                      help='The minimum amount of time between two bubbles.')

    parser.add_option('-d', '--debug',
                      dest='debug',
                      action='store_true',
                      default=False,
                      help='Enables debug mode, which spews noise to stdout.')

    (options, args) = parser.parse_args()

    bubbler = BubbleCounter(**vars(options))
    bubbler.start()

if __name__ == '__main__':
    main()
