# LS9Control
An OSC-like gateway for basic Yamaha LS9 control via qLab.

This was developed one evening to assist in running a hogh school musical group on an LS9 where you
don't really have usable mute groups.  The focus was on mute control for inputs and mixes, but is
easily extendable for other areas that are accessible via NRPN.

Just implementing basic channel control didn't meet the needs because of the number of channels in play, 
so a tag system with expansion was also implemented, which is what makes this usable.

/channel/1/mute               - Mute channel 1
/channel/1/unmute             - Unmute channel 1
/channel/1-10/mute            - Mute channels 1-10
/channel/[headset]/unmute     - Unmute all headsets
/channel/[name:mike]/unmute   - Unmute Mike
/channel/[headset,!mike]/unmute - Unmute all headsets except Mike

It understands:
/channel     mute/unmute
/mix         mute/unmute
/matrix      mute/unmute
/mutegroup   mute/unmute

# Python 2.7

This was developed using Python 2.7 and PortMidi.  The relevent PortMidi pieces (and sources) are 
included in this repo due to the complexities of building it.

If you don't have PyYaml, you will need to install it with either:
pip install pyyaml
or sudo easy_install pyyaml

# Configure the console

Enable the LS9 to receive Midi, channel 1, and enable NRPN control.

# Configure the program

The configuration files is a YAML file.  The only required sections are "console" and "midi" with an empty "tags" section.   When the program runs, it will dump all known midi device names.

See the example file for how names and tags work.

Start the program.

# To use in qLab

This uses raw UDP messages, not OSC, to keep things simple.


- In qLab OSC Configuration, create an entry for LS9, localhost, port 55000

- Create an OSC cue, set the message type to 'Raw UDP String'
- Enter: /channel/1-32/mute
- Click "send"
 


