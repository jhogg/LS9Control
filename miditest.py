#!/usr/bin/python

from lib.pyportmidi import midi

midi.init()

for i in range(midi.get_count()):
   interface, name, is_input, is_output, is_opened = midi.get_device_info(i)
   print "%2i %s/%s/%s" % (i, interface, name, 'in' if is_input else 'out' )

print "Opem"
d = midi.Output(17)

print "Write"
#d.write([[[ 0x01, 0x02 ], 0]])
d.write_short(0xc0, 1)
d.close()

midi.quit()

