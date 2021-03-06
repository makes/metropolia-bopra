import json
import pandas as pd
import numpy as np
from datetime import timedelta

def LoadJSON(filename):
    with open(filename, "r") as fd:
        return json.load(fd)
    return None

def Info(json):
    data = json['ZOLL']['FullDisclosure'][0]['FullDisclosureRecord']
    print(data['PatientInfo'])

def LoadWaveform(json, channel=1, discard_by_status=True, hide_starttime=False):
    data = json['ZOLL']['FullDisclosure'][0]['FullDisclosureRecord']
    wave_records = []
    for item in data:
        for key in item:
            if key == "ContinWaveRec":
                wave_records.append(item['ContinWaveRec'])

    values = []
    bad_value = []
    timeindex = []
    starttime = ""
    currenttime = None
    discarded_samples = 0
    samplecount = 0
    sampletime = None
    waveform_name = None
    wavetype = None
    min_val = None
    max_val = None
    for wave_rec in wave_records:
        try:
            if not starttime and wave_rec['Waveform'][channel]['WaveRec']['FrameSize'] != 0:
                starttime = wave_rec['StdHdr']['DevDateTime']
                currenttime = pd.to_datetime(starttime)
        except IndexError:
            print(f'No such channel: {str(channel)}')
            return None, 0
        if not wavetype:
            wavetype = wave_rec['Waveform'][channel]['WaveRec']['WaveType']
        if not waveform_name:
            waveform_name = wave_rec['Waveform'][channel]['WaveRec']['WaveTypeVar']
        if not sampletime:
            sampletime = wave_rec['Waveform'][channel]['WaveRec']['SampleTime']
        if sampletime != wave_rec['Waveform'][channel]['WaveRec']['SampleTime']:
            print("Variable sampling rate detected") # this should not happen
        samples = wave_rec['Waveform'][channel]['WaveRec']['UnpackedSamples']
        samplestatus = wave_rec['Waveform'][channel]['WaveRec']['SampleStatus']
        for sample, status in zip(samples, samplestatus):
            timeindex.append(currenttime)
            samplecount = samplecount + 1
            currenttime = currenttime + timedelta(microseconds=8000)
            if status > 0: status = 1
            bad_value.append(status)
            if status == 0 or discard_by_status == False:
                values.append(sample)
                if min_val is None or min_val > sample: min_val = sample
                if max_val is None or max_val < sample: max_val = sample
            else: # discard if SampleStatus is not 0
                values.append(np.nan)
                discarded_samples = discarded_samples + 1

    samplerate = int(1E6 / sampletime) # SampleTime = 8000 μs
    duration = len(values) / samplerate

    print("Channel {}: {}".format(channel, waveform_name))
    print("WaveType:  {}".format(wavetype))
    if not hide_starttime:
        print("Start:         {}".format(starttime))
    print("Duration:      {: >10} s".format(duration))
    print("Total samples: {: >10}      Discarded:   {: >5}".format(samplecount, discarded_samples))
    print("Sample rate:   {: >10} 1/s  Sample time: {: >5} μs".format(samplerate, sampletime))
    if min_val is not None:
        print("Min:           {: >10}      Max:         {: >5}".format(min_val, max_val))
    print("")

    df = pd.DataFrame()
    df['Time'] = timeindex
    df['Waveform'] = values
    df['BadSignal'] = bad_value
    df.set_index('Time', inplace=True)
    return df, samplerate