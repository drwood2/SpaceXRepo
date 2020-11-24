# !/usr/local/bin/python3
import socket
import sys
import argparse

# CONNNECTION VARIABLES
# HOST and PORT are arbitrary values can be used for debugging connections
# Provide HOST and PORT as arguments for instrument's address/port and use
# included "echo_server.py" script to echo back commands.

HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 10000  # Port to listen on (non-privileged ports are > 1023)
BUFFER = 1024  # Return size for read_<CONNECTION TYPE>

# SYNTAX
# COMMENTs are ignored
# LINEBREAK allows breaking excessive line lengths across multiple lines

COMMENT = "//"
LINEBREAK = "\\"

# CONNECTION TYPES

# Currently scpiCMD supports connections via TCP. Additional connection methods
# should be added here

INTERFACE_TYPES = ["TCP"]

# Keyword requirements for TCP sockets. Program will throw errors if command
# file is missing this data
CONNECTION_REQUIREMENTS_TCP = ["ADDRESS", "PORT"]
CONNECTION_OPTIONS_TCP = ["DEBUG", "OUTPUT"]


# connect_TCP	:Sets up a TCP/IP connection to the provided address/port.
# param Address 	:IP address for connection
# param port   	:Port for connection
# return	s	  	:A socket instance for the given address/port
def connect_TCP(address, port, message):
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  s.connect((address, port))
  print("opened connection on Address,Port", address, port)
  # Return number of sent bytes
  bytesSent = s.sendall(message.encode("utf_8"))
  data = s.recv(1024).decode("utf_8")
  print('received "%s"' % data)
  return bytesSent, data
  # ADD exception handler
  # ADD higher level exception handler to determine which unit is failing


# For each connection type there is a corresponding transmission function.
# Each interface shall alow users to transmit commands,
# and to receive query responses
# Additional functions should be added here


# parse_Input	:Reads input file and converts to a list of commands/pragmas
# NOTE 			:Review input commandFile and the README for structure details
# CMDFile		:Raw input text file
# return CMDList	:List of commands and pragmas in original order
def parse_input(CMDFile):
  with open(CMDFile) as CMDS:

    # number of lines in command file
    numLines = len(CMDS.readlines())
    CMDS.seek(0)

    lineNum = 0
    line = ""

    CMDList = []
    activeInstrument = ""
    modifiers = []
    for i in range(numLines):
      # print("i is ",i)
      line += CMDS.readline()
      # print(line)
      line = line.strip("\n")
      line = line.strip(" ")
      lineNum += 1
      if len(line) == 0:
        line = ""
        continue
      if line.startswith(COMMENT):
        line = ""
        continue
      if LINEBREAK in line:
        line = line.replace("\\", "")

        continue

      line = line.strip(";")
      line = line.split(";")
      for cmd in line:
        # initializations
        cmd = cmd.split()
        if len(cmd) == 0:
          continue

        # This indicates a pragma
        if (cmd[0].startswith("#")):
          # This is not actually a command, but a command modifier
          # Pragma will modify next command line
          cmd[0] = cmd[0].strip("#")

          if len(cmd) == 1:
            modifiers.append(cmd[0])

          else:
            if (cmd[0] == "START"):
              activeInstrument = cmd[1]
            elif (cmd[0] == "END"):
              activeInstrument = ""

            # In this case it is an instrument initialization, debug declaration, etc.
            else:
              CMDList.append(parsedPragma(lineNum, activeInstrument, cmd))

        # If not a pragma, an instrument command
        else:
          CMDList.append(
              parsedInstrCMD(lineNum, activeInstrument, cmd, modifiers))
          modifiers = []

      # Modifiers only apply for a single line

      line = ""

    return CMDList


# SCPI commands to instrument
# lineNum 	:The location of the commnd inside the CMD file
# instru 	:The instrument command is being sent to
# cmd  		:SCPI Command being sent to instrument
# cmdMods 	:Pragmas which are modifying SCPI command
class parsedInstrCMD():

  def __init__(self, lineNum, instru, cmd, cmdMods):
    self.lineNum = lineNum
    self.instru = instru
    self.cmd = cmd
    self.cmdMods = cmdMods


# Standalone Pragmas which are not just modifying SCPI commands
# lineNum 	:Location of #Pragma command
# instru 	:Instrument being modified, if there is one
# cmd 		:The #Pragma command itself
class parsedPragma():

  def __init__(self, lineNum, instru, cmd):
    self.lineNum = lineNum
    self.instru = instru
    self.cmd = cmd


# PROCESS PARSED DATA


# process_parsed_pragma	:Converts parsed and organized Pragmas into a dict
# 						:this  structure would readily convert to .JSON
# CMD 					:Parsed CMD file
# connections 			:A dict of TCP (and other) connections
# outputFiles			:A dict of the output files logging data
# return 				:Error check, 0 for normal, -1 for error
def process_parsed_pragma(CMD, connections, outputFiles):
  if (CMD.cmd[0] == "OUTPUT"):
    outputFiles[CMD.cmd[1]] = "ALL"
    return 0

  # create a new connection for INSTRUMENT CMD.instru
  # Of type INTERFACE

  if (CMD.cmd[0] == "INTERFACE"):
    connections[CMD.instru] = {"INTERFACE": CMD.cmd[1]}
    return 0

  # else we are populating an existent connection
  if (connections.get(CMD.instru) is not None):
    connections[CMD.instru][CMD.cmd[0]] = CMD.cmd[1]
    # we also need to open DEBUG output files
    # Record which socket file belongs to.
    if (CMD.cmd[0] == "DEBUG"):
      connections[CMD.instru]["DEBUG"] = CMD.cmd[1]
      outputFiles[CMD.cmd[1]] = CMD.instru

  else:
    print("ERROR: No Instrument selected for connection " + "declared on line ",
          CMD.lineNum)
    return -1


def main(args):
  # Interpreter has converted provided CMDS file
  CMDList = parse_input(args.cmdsfile)

  connections = {}
  outputFiles = {}
  commands = {}

  # First loop through pragmas to initialize interfaces, files, etc.
  for CMD in CMDList:
    if isinstance(CMD, parsedPragma):
      if (args.debug_mode):
        print("{PRAGMA}")
        print(CMD.lineNum)
        print(CMD.instru)
        print(CMD.cmd)
      # INTERFACE AND FILE LISTING
      if (process_parsed_pragma(CMD, connections, outputFiles) == -1):
        return -1

  for connection in connections:
    print("connection is ", connection)
    # Verify a connection type is present
    if (connections[connection].get("INTERFACE") is not None):
      # Verify connection type is a supported method
      if (connections[connection].get("INTERFACE") in INTERFACE_TYPES):
        # Check if connection is TCP (include other methods below)
        if (connections[connection]["INTERFACE"] == "TCP"):
          # Error check for address,port,
          for item in CONNECTION_REQUIREMENTS_TCP:
            if connections[connection].get(item) is None:
              print("ERROR: Missing ", item, " from ", connection)
              return -1
          #Verify connections work
          address = connections[CMD.instru]["ADDRESS"]
          port = int(connections[CMD.instru]["PORT"])
          connect_TCP(address, port," ")

        else:
          print("ERROR: Connection type ", connections[connection]["INTERFACE"],
                " not recognized")
          return -1

    else:
      print(
          "Connection ", connection, " does not include a supported " +
          "interface(or it does not contain an interface)")

  for file in outputFiles:
    filename = "outputFiles/"+file
    if (args.debug_mode):
      print("File: ", file, " opened")

    outputFiles[file] = open(filename, "w")

  # After initialization, commands are ready to be processed
  for CMD in CMDList:
    if isinstance(CMD, parsedInstrCMD):
      if connections[CMD.instru]["INTERFACE"] == "TCP":
        address = connections[CMD.instru]["ADDRESS"]
        port = int(connections[CMD.instru]["PORT"])

        #Ignore true commands, replace address/port with address and port 
        #for a local echo server
        if args.loopback_mode:
          address = HOST
          port = PORT


      message = ""
      for word in CMD.cmd:
        message += word
        message += " "

      # Recombining SCPI Command
      message = message.strip()

      # check if DEBUG pragma is active. If so, store everything to file
      if (args.debug_mode):
        print("TX'd |", message, "|")
      if (connections[CMD.instru].get("DEBUG") is not None):
        outputPointer = outputFiles[connections[CMD.instru]["DEBUG"]]
        outputPointer.write("SEND line: " + str(CMD.lineNum) + "\n")
        outputPointer.write(message)
        outputPointer.write("\n")

      if(args.verify_mode):
      	print("Skipping actual transmission")
      else:
        bytesSent, data = connect_TCP(address, port, message)
        if (args.debug_mode):
          print("TX'D ", bytesSent, " bytes, RX'D |", data, "|")
  
          if (connections[CMD.instru].get("DEBUG") is not None):
            outputPointer = outputFiles[connections[CMD.instru]["DEBUG"]]
  
            outputPointer.write("RECV:\n")
            outputPointer.write(data)
            outputPointer.write("\n")
          for file in outputFiles:
            if file in CMD.cmdMods:
              if (args.debug_mode):
                print("Output DATA: |", data, "|")
              outputFiles[file].write(data)
            outputFiles[file].write("\n")

  # Close files recording data
  for file in outputFiles:
    outputFiles[file].close()

  if(args.verify_mode):
    print("VERIFIED")


if __name__ == "__main__":
  parser = argparse.ArgumentParser(description="SCPI Sequencer")

  parser.add_argument(
      "--cmdsfile",
      dest="cmdsfile",
      type=str,
      default=None,
      help="file containing SCPI Commands")
  parser.add_argument(
      "--debug",
      dest="debug_mode",
      type=bool,
      default=False,
      help="T/F arg, showing intermediate result print statements")
  parser.add_argument(
      "--verify",
      dest="verify_mode",
      type=bool,
      default=False,
      help="Verifies syntax without sending commands")
  parser.add_argument(
      "--loopback",
      dest="loopback_mode",
      type=bool,
      default=False,
      help="Use echo_server.py in /Debug tools to verify commands")

  args = parser.parse_args()
  # execute only if run as a script
  # otherwise other scripts may use these functions for API calls
  if (main(args) == -1):
    print("Sequencer Failed")
  else:
    print("Sequencer Complete")
