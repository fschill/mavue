import wave
import struct
import sys, os

input_file = open(sys.argv[1])

output_file = sys.argv[2]

data_csv = input_file.readlines()
data_parsed = [[int(pl.strip()) for pl in l.split(",")[0:-2]] for l in data_csv]

channels = dict()

#sort by channel ([0]) and strip time stamp [1]
for block in data_parsed:
    channels[block[0]] = []

for block in data_parsed:
    channels[block[0]].append(block[100:])

print "found channels: ", channels.keys(), len(channels[0]), len(channels[1])

wav_output = wave.open(output_file, 'w')
wav_output.setparams((2, 2, 22050, 0, 'NONE', 'not compressed'))

values = []


for i in range(0, min(len(channels[0]),len(channels[1]))):
    for s in range(0, len(channels[0][i])):
            packed_value = struct.pack('h', channels[0][i][s])
            values.append(packed_value)
            packed_value = struct.pack('h', channels[1][i][s])
            values.append(packed_value)
print "length:", len(values)
value_str = ''.join(values)
wav_output.writeframes(value_str)

wav_output.close()