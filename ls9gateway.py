#!/usr/bin/python

import sys, time, socket
import yaml

from lib.pyportmidi import midi

class BadUri(Exception):
    def __init__(self, uri, msg = ''):
        print "BadURI %s %s" % (uri, msg)
        self._uri = uri
        self._msg = msg

class DataObject(object): pass
        
# ---------------------------------------------------------------------------------------

class LS9_Console(object):
    
    def __init__(self, config = {}):
        
        self.midi_channel = int(config.get('midi_channel', 1)) - 1
        
        self._route = {}
        self._route['channel'] = LS9_Channel(self)
        self._route['mix']     = LS9_Mix(self)
        self._route['matrix']  = LS9_Matrix(self)
        self._route['mutegroup']  = LS9_MuteGroup(self)
        
        self._midi = []
    
    def queue_midi(self, mididata):
        #print "Queue midi", mididata
        self._midi.extend(mididata)
    
    def handle_message(self, uri, data = None):
        
        uri_text = '/' + '/'.join(uri)

        try:
            if len(uri) != 3:
                raise BadUri(uri_text, 'Too short')
            
            if not uri[0] in self._route:
                raise BadUri(uri_text, 'Unknown route %s' % uri[0])
            
            channel = int(uri[1])
            fn = self._route[uri[0]].__getattribute__(uri[2])
            
            if fn:
                fn(channel)
            else:
                raise BadUri(uri_text, 'Unknown Method %s' % uri[2])

        except Exception, e:
            print e

class LS9_GenericDevice(object):
    
    def _check_index(self, idx):
        if (idx < 1) or (idx > self._max_index):
            raise IndexOutOfRange()
    
    def nrpn(self, addr, value):
        mc = self._console.midi_channel
        addr_h, addr_l = addr / 128, addr % 128
        value_h, value_l = value / 128, value % 128
        m = [ [0xb0 | mc, 98, addr_l] , [0xb0 | mc, 99, addr_h],
              [0xb0 | mc, 38, value_h], [0xb0 | mc,  6, value_l] ]
        
        return m

class LS9_Channel(LS9_GenericDevice):
    """ Implement NRPN Channel Control"""
    
    def __init__(self, console):
        self._console = console
        self._max_index = 64
        
    def mute(self, channel):
        self._check_index(channel)
        if channel > 48: channel += 8
        self._console.queue_midi(self.nrpn(0x05B6 + channel -1, 0))
    
    def unmute(self, channel):
        self._check_index(channel)
        if channel > 48: channel += 8
        self._console.queue_midi(self.nrpn(0x05B6 + channel -1, 127))

class LS9_Mix(LS9_GenericDevice):
    
    def __init__(self, console):
        self._console = console
        self._max_index = 16
    
    def mute(self, channel):
        self._check_index(channel)
        self._console.queue_midi(self.nrpn(0x0616 + channel -1, 0))
    
    def unmute(self, channel):
        self._check_index(channel)
        self._console.queue_midi(self.nrpn(0x0616 + channel -1, 127))

class LS9_Matrix(LS9_GenericDevice):
    
    def __init__(self, console):
        self._console = console
        self._max_index = 8
    
    def mute(self, channel):
        self._check_index(channel)
        channel += 4
        self._console.queue_midi(self.nrpn(0x0626 + channel -1, 0))
    
    def unmute(self, channel):
        self._check_index(channel)
        channel += 4
        self._console.queue_midi(self.nrpn(0x0626 + channel -1, 127))

class LS9_MuteGroup(LS9_GenericDevice):
    
    def __init__(self, console):
        self._console = console
        self._max_index = 6
    
    def mute(self, idx):
        self._check_index(idx)
        self._console.queue_midi(self.nrpn(0x3a5a + idx -1, 127))
    
    def unmute(self, idx):
        self._check_index(idx)
        self._console.queue_midi(self.nrpn(0x3a5a + idx -1, 0))

# ---------------------------------------------------------------------------------------

class MidiInterface(object):
    
    def __init__(self):
        self._devices = {}
        midi.init()
        for i in range(midi.get_count()):
            interface, name, is_input, is_output, is_opened = midi.get_device_info(i)
            key = '%s/%s/%s' % (interface.lower(), name.replace(' ','_').lower(), 'in' if is_input else 'out')
            print "%2i %s/%s/%s = %s" % (i, interface, name, 'in' if is_input else 'out', key )
            self._devices[key] = i
        
    def close():
        midi.quit()
        
    def get_output(self, name):
        return midi.Output(self._devices[name])
            
# ---------------------------------------------------------------------------------------

class URIExpander(object):
	
    def __init__(self):
        self._tags = {}

    def loadtags(self, taglist):
        for td in taglist:
            klass = td.get('class', None)
            index = td.get('index', None)
            name = td.get('name', None)
            tags = td.get('tags', [])
            
            if not klass or not index:
                print 'Bad tag data: %s' % str(td)
                continue
                
            if name:
                tags.append('name:%s' % name)
            
            for tag in tags:
                tag = tag.replace(' ', '_').lower()
                key = (klass.lower(),tag)
                if not key in self._tags:  self._tags[key] = set()
                self._tags[key].update([index])
                    
        for k,v in self._tags.iteritems():  print k,v
        
    def parse(self, uri, tags = {}):
		
        final = []
        self._result = []
        parts = uri.split('/')
		
        for idx,part in enumerate(parts):
			
            if idx == 0 and len(part) == 0:		# Skip initial blank
                continue
			
            if len(final) == 0:					# We never expand first entry
                final.append([part])
                continue
			
            if part[0] == '[' and part[-1] ==']':
                final.append(self._expand_tags(final[0][0], part))
            elif ('-' in part) or (',' in part):
                final.append(self._expand_value(part))
            else:
                final.append([part])
		
        print final
		
        self._flatten_iter(final, [])
        return self._result
	
    def _expand_tags(self, root, args):
        result_incl = set()
        result_excl = set()
        for tag in args[1:-1].split(','):
            t = result_excl if tag[0] == '!' else result_incl
            key = (root.lower(), tag.replace(' ','_').replace('!','').lower())
            print key
            if key in self._tags:
                t.update(self._tags[key])
            else:
                raise BadUri('', 'Unknown tag/class: %s' % str(key))    
        result_incl.difference_update(result_excl)
        return sorted(result_incl)
        
    def _expand_value(self, args):
		result_incl = set()
		result_excl = set()
		for part in args.split(','):
			t = result_excl if part[0] == '!' else result_incl
			x = part.replace('!','').split('-')
			t.update(range(int(x[0]), int(x[-1])+1))
		result_incl.difference_update(result_excl)
		return sorted(result_incl)
	
    def _flatten_iter(self, final, partial=[]):
		parts = final[0]
		for p in parts:
			partial_next = list(partial)
			partial_next.append(str(p))
			if len (final) > 1:
				self._flatten_iter(final[1:], partial_next)
			else:
				self._result.append(partial_next)

# ---------------------------------------------------------------------------------------

class Application(object):
    
    def __init__(self):
        pass
        
    def run(self):

        print "LS9 OSC Gateway"
        print "v 0.10  (c) 2016, Jay Hogg\n"
    
        # --- Parse command line options
        options = DataObject()
        options.config = 'config.yaml'
    
        # --- Load Configuration
        print "Loading Configuration"
        config = yaml.load(open(options.config, 'r'))
        
        print "Configuring MIDI"
        self._midiif = MidiInterface()
        self._md = self._midiif.get_output(config['midi']['interface'])
        
        print "Load Tag data"
        self._parser = URIExpander()
        self._parser.loadtags(config.get('tags', []))
        
        print "Creating Console"
        self._console = LS9_Console(config['console'])
        
        if True:
            self.ListenMode()
        else:
            self.TestMode()

        # Midi Cleanup
        self._md.close()    
        self._midiif.close()
        
        
    def TestMode(self):

        print "Running in TEST mode"
        
        test = [
    #        '/channel/12/mute',
            '/channel/35-38/mute',
    #       '/channel/35/unmute',
    #       '/channel/1-18,22,31-42/unmute',
    #       '/channel/1-18,22,31-42,!35,!12-14/unmute',
        ]
    
        for uri in test:
            print 'Test URI ', uri
            for path in self._parser.parse(uri):
                print path
                self._console.handle_message(path, {})

        self.update_console()
        
    def ListenMode(self):
    
        print "Running in LISTEN mode"

        listen_addr = ('localhost', 55000)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(listen_addr)

        while True:
            data, address = sock.recvfrom(4096)
            print data
            sys.stdout.flush()
    
            for uri in data.split('|'):
                try:
                    for path in self._parser.parse(uri):
                        print path
                        self._console.handle_message(path, {})
                except Exception, e:
                    print e
                    
            self.update_console()
            
    def update_console(self):
        for mc in self._console._midi:
            #print mc
            self._md.write_short(mc[0], mc[1], mc[2])
            time.sleep(0.005)
        self._console._midi = []    # FIXME
        
if __name__ == '__main__':
    Application().run()

