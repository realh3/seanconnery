#!/usr/bin/python
import sys, socket, string, os, re, subprocess, pprint, commands

HOST  = '127.0.0.1'
PORT  = 6667
NICK  = 'Lyle'
IDENT = 'seanconnery'
REALNAME = 'seanconnery'
CHANNEL = '#realh3'
RCVCNT = 0
SCRIPT_PATH = '/opt/sean/'
DEBUG = True
COMMANDS = []
LOADING = False

class ARG(object):
    NOOP = 0
    SEND_MSG = 1
    SEND_WHO = 2

def load_data():

    f = open('sean.dat', 'r')
    for line in f:
        addCmd(*line.strip().split(' '))
    f.close()

    for cmd in COMMANDS:
        print "CMD: " + str(cmd)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
def connect():
    global s
    s.connect((HOST, PORT))

def sendmsg(msg):
    global s
    if DEBUG:
        print '-> {0}'.format(msg)
    s.send(msg + "\r\n")

def recvmsg(msg):
    global RCVCNT
    RCVCNT += 1
    lines = msg.split('\n')
    if lines[-1] == '':
        lines.pop()

    if DEBUG:
        for line in lines:
            print '<- {0}'.format(line)
    msg = ' '.join(lines)
    bang_pos = msg.find('!')
    at_pos   = msg.find('@', bang_pos + 1)
    prv_pos  = msg.find('PRIVMSG ')
    msg_pos  = msg.find(' :', prv_pos)
    if bang_pos == -1 or at_pos == -1 or prv_pos == -1:
        return (None, None, None)

    who  = msg[1: bang_pos]
    chan = msg[prv_pos + len('PRIVMSG '):msg_pos]
    if chan == NICK:
        chan = who
    msg = msg[msg_pos + 2:]

    return (who, chan, msg)

def sendchan(chan, msg):
    sendmsg('PRIVMSG {0} :{1}'.format(chan, msg))

def addCmd(trigger, script, args=ARG.NOOP):
    command = { 'trigger': trigger,
            'script': script,
            'args': int(args)
          }

    COMMANDS.append(command)

def update_file():
    f = open('sean.dat', 'w')
    for cmd in COMMANDS:
        f.write("{0} {1} {2}\n".format(cmd['trigger'], cmd['script'], cmd['args']))
    f.close()

def parsemsg(chan, who, msg):
    global DEBUG, NICK
    if chan == who and msg.find('newNick') == 0:
        args = msg.split()[1:]
        if len(args) is not 1:
            sendchan(who, 'error. syntax: newNick <new nick>')
            return

        NICK = args[0]  
        sendmsg('NICK {0}'.format(NICK))

        return
    if chan == who and msg.find('addCmd') == 0:
        args = msg.split()[1:]
        if len(args) < 2 or len(args) > 3:
            sendchan(who, 'error. syntax: regex scriptname args_param')
            return  
        addCmd(*args)
        update_file()

        sendchan(who, 'command added successfully.')
        return

    if chan == who and msg.find('rmCmd') == 0:
        cmd = msg.split()
        if len(cmd) == 2:
            for c in COMMANDS:
                if c['trigger'] == cmd[1]:
                    COMMANDS.remove(c)
                    update_file()

                    sendchan(who, "removed")
                    return
        sendchan(who, "cmd not found")
        return
 
    if chan == who and msg.find('DEBUG') == 0:
        DEBUG = not DEBUG
        sendchan(who, 'toggling debug')
        return

    if chan == who and msg.find('listCmds') == 0:
        print str(COMMANDS)
        return

    if chan == who and msg.find('echo') == 0:
        msg = ' '.join(msg.split()[1:])
        sendchan(CHANNEL, msg)
        return

    if chan == who and msg.find('action') == 0:
        msg = ' '.join(msg.split()[1:])
        sendchan(CHANNEL, "/me " + msg)
        return

    for command in COMMANDS[:]:
        match = re.search(command['trigger'], msg, re.I)
        if match == None:
            continue

        # we found a match
        cmd = [ os.path.join(SCRIPT_PATH, command['script']) ]
        args = command.get('args', ARG.NOOP)
        if args & ARG.SEND_WHO:
            cmd.append(who)
        if args & ARG.SEND_MSG:
            cmd.append(re.escape(msg))

        print 'running -> ' + ' '.join(cmd)
        out = commands.getstatusoutput(' '.join(cmd))
        if out[0] != 0 or out[0] == 1:
                return
        else:
                out = out[1]
        if len(out):
            for line in out.strip().split("\n"):
               sendchan(chan, line.strip())
            return

connect()

while True:
    line = s.recv(500).strip()
    who, chan, msg = recvmsg(line)
    if RCVCNT == 2:
        sendmsg('USER {0} {1} blah :{2}'.format(IDENT, HOST, REALNAME)) 
        sendmsg('NICK {0}'.format(NICK))
        load_data()
        continue
    if line.find('MOTD File is missing') != -1:
        sendmsg('JOIN {0}'.format(CHANNEL))
        continue

    if line.find('PING') != -1:
        sendmsg('PONG {0}'.format(line.split()[1]))
        continue

    # now we get into the real stuff
    if chan and who and msg:
        parsemsg(chan, who, msg)    
