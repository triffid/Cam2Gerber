Cam2Gerber
----------

**Cam2Gerber** contains a Python script for EAGLE PCB software, to run a ".cam" file from a Windows command line, producing Gerber files.

###Background
EAGLE software  is used for designing printed circuit boards.  It can produce Gerber files and Excellon drill files, used to make printed circuit boards, in two ways:

1. EAGLE's PCB layout editor includes a CAM GUI that lets users configure the mapping of EAGLE CAD layers to Gerber files and Excellon drill files, save or load settings in ".cam" files, and run a single job that produces multiple output files for PCB manufacturing.

2. EAGLE has a Windows command that can generate a single output file at a time. It doesn't use a ".cam" file; instead, everything is specified by parameters.

###The Problem
Sometimes you may want an easy way to produce all the output for a board automatically, without needing a person to click through a CAM GUI.  Method (1), using the CAM GUI, needs human intervention to click through the GUI.  Method (2), generating each output file with a separate windows command having detailed parameters, is complex, not well explained, and not easy to maintain.

###The Solution
The **Cam2Gerber** Python script takes a ".cam" file as input to specify what outputs are needed, and then executes the Windows commands needed to make that output.  It allows a board's output files to be generated from a script, without human intervention.  It also allows users to customize the outputs via a modified ".cam" file, instead of changing complicated command-line parameters.

###Limitations
The Python script currently only supports the output of Extended Gerber (RS-274X) files and Excellon drill files.  It was written for EAGLE version 6.5.0 and Python version 2.7.5.
