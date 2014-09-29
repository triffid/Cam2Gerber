#!/usr/bin/env python
#
# Script to parse an Eagle-CAD CAM file, to produce Windows command lines
# that are executed to produce Gerber plots and/or an Excellon drill file.
#
# Parameters:
# -c<path of the .cam file> -b<path of the .brd file> [-e<path of the eaglecon.exe file>]
#
# Sample parameters:
# -c"C:\Users\MyPie\Documents\eagle\PulseOx\Seeed_Gerber_Generator_4-layer_1-2-15-16.cam" -b"C:\Users\MyPie\repos\tonkalib\designs\BandpassFilter\results\o1ul2wxq\schema.brd"
#
# -------------------------------------------------------------------------
# The MIT License (MIT)
# 
# Copyright (c) 2014 MetaMorph (http://metamorphsoftware.com)
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#
from subprocess import call
from unicodedata import normalize
import re
import os
import sys
from optparse import OptionParser

#----------------------------------------------
r"""
Cam2Gerber
==========

**Cam2Gerber** contains a Python script for EAGLE PCB software, to run a ".cam" file from a Windows command line,
producing Gerber files.

Parameters
----------
 -c<path of the .cam file>
 -b<path of the .brd file>
 -e<path of the eaglecon.exe file> (defaults to "C:\Program Files (x86)\EAGLE-6.5.0\bin\eaglecon.exe")

Outputs
-------
The outputs are extended Gerber files and/or Excellon drill files, as specified by the ".cam" file.

Background
----------
EAGLE software  is used for designing printed circuit boards.  It can produce Gerber files and Excellon drill files,
used to make printed circuit boards, in two ways:

1. EAGLE's PCB layout editor includes a CAM GUI that lets users configure the mapping of EAGLE CAD layers to Gerber
files and Excellon drill files, save or load settings in ".cam" files, and run a single job that produces multiple
output files for PCB manufacturing.

2. EAGLE has a Windows command that can generate a single output file at a time. It doesn't use a ".cam" file; instead,
everything is specified by parameters.

The Problem
-----------
Sometimes you may want an easy way to produce all the output for a board automatically, without needing a person to
click through a CAM GUI.  Method (1), using the CAM GUI, needs human intervention to click through the GUI.  Method (2),
 generating each output file with a separate windows command having detailed parameters, is complex, not well explained,
 and not easy to maintain.

The Solution
------------
The **Cam2Gerber** Python script takes a ".cam" file as input to specify what outputs are needed, and then executes the
Windows commands needed to make that output.  It allows a board's output files to be generated from a script, without
human intervention.  It also allows users to customize the outputs via a modified ".cam" file, instead of changing
complicated command-line parameters.

Limitations
-----------
The Python script currently only supports the output of Extended Gerber (RS-274X) files and Excellon drill files.  It
was written for EAGLE version 6.5.0 and Python version 2.7.5.

"""
#----------------------------------------------

g_warningCount = 0
g_errorCount = 0

def warning( args ):
    """
     Print a warning message to stdout, and increment a global warning-message counter.

     args -- A string containing the message to print.
    """
    global g_warningCount
    g_warningCount += 1
    sys.stdout.write("*** Warning: ")
    print( args )

def error( args ):
    """
     Print an error message to stdout, and increment a global error-message counter.

     args -- A string containing the message to print.
    """
    global g_errorCount
    g_errorCount += 1
    sys.stdout.write("*** Error: ")
    print( args )

#----------------------------------------------


# Global camfile object
class CamFile:

    def __init__(self, camFilePath ):
        """ Initializes the CamFile class with the CAM file's path. """
        if not os.path.exists( camFilePath ):
            error( 'Unable to open the CAM file path "{0}"'.format( camFilePath ))
        else:
            handle = open(camFilePath, 'r')
            self.allLines = handle.readlines()
            handle.close()
            self.lineIndex = 0
            self.maxLines = len(self.allLines)

    def getNextLine(self):
        """ Returns the next line from the CAM file, with trailing whitespace trimmed. """
        result = None
        if self.lineIndex < self.maxLines:
            result = self.allLines[self.lineIndex].rstrip()
            self.lineIndex += 1
        self.currentLineString = result
        return result

    def isLinePrefix(self,prefix):
        """ Check if the current line starts with a prefix string. """
        result = False
        if( prefix == self.currentLineString[:len(prefix)]):
            result = True
        return result

    def getKeyEqValue(self, key):
        """ Check if a line starts with <key>=<value>, and if so
         advances to the next CAM line and return the value string.
        """
        value = None
        pattern = key + "="
        if self.isLinePrefix(pattern):
            value = self.currentLineString[len(pattern):]
            self.getNextLine()
        return value

    def eof(self):
        " Return True if all CAM file lines have been processed."
        return self.lineIndex >= self.maxLines

    def skipBlankLine(self):
        """ Skip the current CAM file line if it is blank. """
        result = False
        if not self.currentLineString:
            self.getNextLine()
            result = True
        return result

    def getKeyLangEqQuotedVal(self, key):
        """ If the current line matches <key>[<languageCode>]="<value>",
        then return a tuple with the languageCode and value, and
        advance to the next line
        """
        result = []
        pattern = key + r'\[(.+)\]="(.*)"'
        match = re.match( pattern, self.currentLineString )
        if match:
            result.append( match.group(1) )
            result.append( match.group(2) )
            self.getNextLine()
        return result

    def getMultipleKeyLangEqQuotedVal(self, key):
        """ Match one or more lines matching <key>[<languageCode>]="<value>",
        and if found, advance past them and return a dictionary with
        languageCodes as keys mapping to the values.
        """
        matchingDone = False
        resultDict = {}
        while not matchingDone:
            parts = self.getKeyLangEqQuotedVal(key)
            if parts:
                resultDict[parts[0]] = parts[1]
            else:
                matchingDone = True
        return resultDict

    def getValInSqBrackets(self):
        """ Check if the line starts with text in square brackets, and if so,
        advance to the next line and return the string found in the brackets.
        """
        result = None
        pattern = r'\[(.+)\]'
        match = re.match( pattern, self.currentLineString )
        if match:
            result = match.group(1)
            self.getNextLine()
        return result

    def getKeyEqQuotedVal(self,key):
        """ Check if a line starts with <key>="<value>", and if so
         advance to the next line and return the value.
        """
        result = None
        pattern = key + r'="(.*)"'
        match = re.match( pattern, self.currentLineString )
        if match:
            result = match.group(1)
            self.getNextLine()
        return result

    # generic parse of cam name/value pair
    def getKeyValuePairs(self,key):
        """ Checks if there are one or more lines of:
         - <key>[<languageCode]="<value>",
         or a single line of:
         - <key>="<value">,
         or a single line of:
         - <key>=<value>
         and advances past these lines.

         In the first case, a dictionary is returned mapping
         languages to values.  In the second and third case,
         the value string is returned.
        """
        result = self.getMultipleKeyLangEqQuotedVal(key)
        if not result:
            result = self.getKeyEqQuotedVal(key)
        if not result:
            result = self.getKeyEqValue(key)
        return result

#---------------------------------------

def newParseCam( camFilePath ):
    """ Parses a CAM file using the CamFile class, returning a dictionary with
    a description of the CAM job and sections describing each output file to be generated.
    """
    done = False
    cam = CamFile(camFilePath)
    bigResult = {}
    if not cam.maxLines:
        done = True
        error( "Unable to open '{0}'.".format( camFilePath ))
    if not done:
        cam.getNextLine()
        val = cam.getValInSqBrackets()
        if not ('CAM Processor Job' == val):
            done = True
            error( "File '{0}' was not a CAM processor job.".format( camFilePath ))
    if not done:
        bigResult['Description'] = cam.getMultipleKeyLangEqQuotedVal('Description')

    if not done:
        sectionList = []
        maybeSection = True
        while maybeSection:
            sectionValue = cam.getKeyEqValue('Section')
            if None != sectionValue:
                sectionList.append(sectionValue)
            else:
                maybeSection = False
        if len(sectionList) == 0:
            done = True
            error( "No sections found in the CAM file.")
    if not done:
        bigResult['Sections'] = []
    # parse multiple sections
    while (not done) and (not cam.eof()):
        sectionResults = {}
        done = not cam.skipBlankLine()
        if not done:
            thisSection = cam.getValInSqBrackets()
            if not (thisSection and thisSection in sectionList):
                done = True
                warning("Section not found.")
            else:
                sectionResults['tag'] = thisSection
        if not done:
            sectionResults['name'] = cam.getKeyValuePairs('Name')
            sectionResults['prompt'] = cam.getKeyValuePairs('Prompt')
            sectionResults['device'] = cam.getKeyValuePairs('Device')
            if not sectionResults['device']:
                done = True
                error("Device specification not found.")
        if not done:
            sectionResults['wheel'] = cam.getKeyValuePairs('Wheel')
            sectionResults['rack'] = cam.getKeyValuePairs('Rack')
            sectionResults['scale'] = cam.getKeyValuePairs('Scale')
            sectionResults['output'] = cam.getKeyValuePairs('Output')
            if not sectionResults['output']:
                done = True
                error( "Output file name not found.")
        if not done:
            sectionResults['flags'] = cam.getKeyValuePairs('Flags')
            if not sectionResults['flags']:
                done = True
                error("Flags not found.")
        if not done:
            sectionResults['emulate'] = cam.getKeyValuePairs('Emulate')
            if not sectionResults['emulate']:
                done = True
                error("Emulate not found.")
        if not done:
            sectionResults['offset'] = cam.getKeyValuePairs('Offset')
            if not sectionResults['offset']:
                done = True
                error("Offset not found.")
        if not done:
            sectionResults['sheet'] = cam.getKeyValuePairs('Sheet')
            sectionResults['tolerance'] = cam.getKeyValuePairs('Tolerance')
            sectionResults['pen'] = cam.getKeyValuePairs('Pen')
            sectionResults['page'] = cam.getKeyValuePairs('Page')

            sectionResults['layers'] = cam.getKeyValuePairs('Layers')
            if not sectionResults['layers']:
                done = True
                error( "Layers not found" )
        if not done:
            sectionResults['colors'] = cam.getKeyValuePairs('Colors')
        if not done:
            # Add section info to results
            bigResult['Sections'].append( sectionResults )
    return bigResult

#----------------------------------------------

def getOutputName( nameTemplate, boardPath ):
    """ Returns a file name string without CAM-name placeholders, from a file name string that may contain them.

     nameTemplate is a string possibly containing placeholders, such as "%N.cmp".
     boardPath is the path to the Eagle ".brd" file.
    """
    result = None
    if( nameTemplate and boardPath):
        replacementDict = {}
        replacementDict['%N'] = os.path.splitext(os.path.basename(boardPath))[0]
        replacementDict['%E'] = os.path.splitext(os.path.basename(boardPath))[1][1:]
        replacementDict['%P'] = os.path.dirname(boardPath)
        replacementDict['%H'] = os.path.expanduser('~')
        replacementDict['%%'] = '%'

        #do the replacements here in one pass
        rep = dict((re.escape(k), v) for k, v in replacementDict.iteritems())
        pattern = re.compile("|".join(rep.keys()))
        result = pattern.sub(lambda m: rep[re.escape(m.group(0))], nameTemplate)
    return result

#----------------------------------------------
g_boardLayerNumberToNameMap = {}

def getBoardLayerNumberToNameMap(boardPath):
    """ Returns a map of an Eagle board's layer numbers to layer names. """
    if g_boardLayerNumberToNameMap:
        # TODO: We might check that the board path hasn't changed before returning the previous map.
        return g_boardLayerNumberToNameMap
    if not os.path.exists( boardPath ):
        error( 'Unable to open the board file "{0}".'.format( boardPath ))
        return g_boardLayerNumberToNameMap
    # TODO: We should ideally parse the board file as XML instead of using regular expressions to find layers.
    pattern = r'<layer number="([0-9]+)" name="([^"]+)"'
    handle = open(boardPath, 'r')
    allLines = handle.readlines()
    for line in allLines:
        match = re.match( pattern, line )
        if match:
            g_boardLayerNumberToNameMap[ match.group(1) ] = match.group(2)
    return g_boardLayerNumberToNameMap



#----------------------------------------------

def getValidLayers( layerString, boardPath, sectionName):
    """ Generate a string with a space-separated list of board layers that are
    both in the board and in the layerString input.
    """
    validList = []
    boardLayerNumberToNameMap = getBoardLayerNumberToNameMap( boardPath )
    layerList = layerString.split()
    for layer in layerList:
        if (layer in boardLayerNumberToNameMap) or (layer in boardLayerNumberToNameMap.values()):
            validList.append(layer)
        else:
            warning("Eagle layer {0} in the CAM tab named '{1}' is not a layer listed in the board file.".format( layer, sectionName ))
    validLayerString = " ".join( validList )
    return " " + validLayerString
#----------------------------------------------


# Convert CAM-file flag parameter to CAM-processor options:
def getFlagString( camSection ):
    """ Convert a space-separated string of zeroes and ones from a CAM-file flag value to
    a sequence of CAM-processor parameters, for parameters different from defaults.

    Here are the flag CAM-Processor parameters in sequence, from the Eagle manual:
    -m- Mirror output
    -r- Rotate output 90 degrees
    -u- Rotate output 180 degrees
    -c+ Positive coordinates
    -q- Quick plot
    -O+ Optimize pen movement
    -f+ Fill pads

    A trailing '+" means the option's default is on, and '-' means it's off.
    """
    resultString = ''
    defaultValue = ' 0 0 0 1 0 1 1'.split()
    flagLetters = 'm r u c q O f'.split()
    rawFlagList = camSection['flags'].split()
    for index, value in enumerate( rawFlagList ):
        if value != defaultValue[index]:
            resultString += ' -' + flagLetters[index] + ('+' if '1' == value else '-')
    return resultString
#----------------------------------------------
def getOffsets( camSection ):
    """  Convert a CAM string containing a number, a linear-units string, a space, another
    number, and another linear-units string, to a tuple of two floats representing inches. """
    units = {
        'mil': (1/1000.0),
        'cm': (1/25.4),
        'mm': (1/25.4),
        'inch': 1.0
    }
    xResult = 0
    yResult = 0
    pattern = r'^([-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)(\S+)\s([-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)(\S+)$'
    match = re.match( pattern, camSection['offset'] )
    if match:
        xResult = float(match.group(1)) * float( units.get( match.group(5), 0 ))
        yResult = float(match.group(6)) * float( units.get( match.group(10), 0 ))
    return (xResult, yResult)

#----------------------------------------------

def getEagleCommandFromCamSection( camSection, boardPath, eaglePath ):
    """Produce a Windows command to run Eagle to generate a CAM output file.

    camSection is a dictionary containing parameter info.
    boardpath is the path to the Eagle board file.
    eaglePath is the path to the eaglecon.exe file.
    """
    outputName = getOutputName( camSection['output'], boardPath )
    wheelName = getOutputName( camSection['wheel'], boardPath )
    inName = camSection['name']
    if isinstance( inName, dict ) and ('en' in inName):
        sectionName = inName['en']
    else:
        sectionName = str(inName)
    validLayers = getValidLayers( camSection['layers'], boardPath, sectionName)
    flagString = getFlagString( camSection )

    xFlag = ''
    yFlag = ''
    xOffset, yOffset = getOffsets( camSection )
    if xOffset:
        xFlag = ' -x'+ str(xOffset)
    if yOffset:
        yFlag = ' -y' + str(yOffset)

    commandString = ( '"' + eaglePath + '"' + flagString + ' -X -d"' + camSection['device'] + '" -o"' + outputName +
                      (('" -W"' + wheelName) if wheelName else '') +
    '"' + xFlag + yFlag +
    ' "' + boardPath + '" ' + validLayers)
    return commandString



#----------------------------------------------

def main():
    """ Main routine that parses the .cam file, generates Windows commands, and executes them,
    to produce extended Gerber files and/or Excellon drill files.
    """
    parser = OptionParser()
    parser.add_option("-c", "--cam", dest="camFile",
                help="path of the (.cam) CAM job file", metavar="FILE")
    parser.add_option("-b", "--board", dest="boardFile", metavar="FILE",
                default=r".\schema.brd",
                help="path of the (.brd) board file")
    parser.add_option("-e", "--eagle", dest="eagleFile", metavar="FILE",
                default=r"C:\Program Files (x86)\EAGLE-6.5.0\bin\eaglecon.exe",
                help="path of the 'eaglecon.exe' file")

    (options, args) = parser.parse_args()
    myCamPath = options.camFile
    if not myCamPath:
        error( 'The path of the CAM file must be specified with the -c parameter.')
    myBoard = options.boardFile
    if not os.path.exists(myBoard):
        error( 'The board file path "{0}" does not exist.'.format(myBoard))
    myEaglePath = options.eagleFile
    if not os.path.exists(myEaglePath):
        error( 'The file "{0}" does not exist.  Please specify the "eaglecon.exe" path using the -e parameter.'.format(myEaglePath))

    if( not g_errorCount ):
        parseResult = newParseCam(myCamPath)

    expectedDevices = ["EXCELLON", "GERBER_RS274X", "GERBER_RS274X_25" ]

    if 'Sections' in parseResult:
        for camSection in parseResult['Sections']:
            eagleCommand = getEagleCommandFromCamSection( camSection, myBoard, myEaglePath )
            print( eagleCommand )
            if not camSection['device'] in expectedDevices:
                warning( 'Device "{0}" is not supported, and the generated command line may be missing parameters. Only "GERBER_RS274X", "GERBER_RS274X_25", and "EXCELLON" are supported.'.format( camSection['device'] ))
            returnCode = call(eagleCommand, shell=True)
            print "return code: " + str(returnCode)
            if returnCode < 0:
                warning("Eagle CAD return code = {0}.".format(returnCode) )
            # call('DIR /A-D /OD /TW "' + os.path.dirname(myBoard) + '"', shell=True)
        print( '*** CAM job completed with {0} warnings and {1} errors. ***'.format( g_warningCount, g_errorCount ))
    else:
        print( '*** CAM job did not run. ***')
    if g_warningCount + g_errorCount == 0:
        return 0
    else:
        return -1




# Run the main program ************************************

main()

#----------------------------------------------
