""" Code calculating the Venous Wave Pulse Velocity (vWPV): 
1 - ECG MONITORING FOR THRESHOLD SETTINGS (initial 10 s)
    a - Acquisition of 10 seconds of ECG signal (500 Hz)
    b - Set threshold for R-wave detection
        Threshold = average + 15% total amplitude OR threshold + 20% total amplitude (depending on the number of peaks, which should not exceed an excessive 1 per second or so)

2 - RESPIRATORY SIGNAL (50 Hz)
    a - Acquisition of 5 seconds of signal for threshold imposition 
    b - Identification of the expiratory phase when the signal passes from above to below the threshold 
        (the transition is considered as such only if 5 samples are found consecutively above threshold, followed by 5 samples below threshold. 
        So the threshold crossing is more resistant to noise)
    
3 - ECG SIGNAL (500 Hz)
    a - Acquisition of the ECG signal 
    b - Detection of R-wave when signal exceeds threshold 

4 - TRIGGER
    After detecting the expiratory phase and the R wave, the inflation trigger is sent by opening the valve. 
    The trigger can be delayed by updating the delay parameter. 

5 - DOPPLER SIGNAL (15KHz)
    a - Acquisition of 1s of signal immediately after sending the inflation trigger 
    b - Identification of the footprint --> calculation of the latency between sending the trigger and the start of the peak on the doppler signal

"""

from turtle import delay
import numpy as np
import matplotlib.pyplot as plt
import time
import os

from numpy.core.function_base import linspace
import ADS1256new
import RPi.GPIO as GPIO
import config
from multiprocessing import Process

import math 
import statsmodels.api as sm 
from scipy.signal import find_peaks 
from scipy import convolve 


def ADC_reading():
    """"This function reads the value on the input pin of the ADC. 
    It considers the first bit (MSB) as the sign bit, 1 = negative."""
    ADC.ADS1256_WaitDRDY() #it waits untill ADC is ready 
    buf = config.spi_readbytes(3)

    read = (buf[0]<<16) & 0xff0000
    read |= (buf[1]<<8) & 0xff00
    read |= (buf[2]) & 0xff
    
    
    if (read & 0x800000): # mask to check the MSB (negative number)
       read = -(0xffffff - read + 0x000001)

    return (read * 5.0 / 0x7fffff)

def ADC_configuration(codice_segnale):
    """ This function configures and initialises ADS1256 for acquisition of desired signal (breath, ecg, doppler)
    
    INPUT: 
    - signal_code: "R" = Respiratory Signal, "E" = ECG, "D" = Doppler"""
    ADC.ADS1256_reset()

    if codice_segnale=="R": #RESPIRATORY SIGNAL
        gain = ADS1256new.ADS1256_GAIN_E['ADS1256_GAIN_1']
        drate = ADS1256new.ADS1256_DRATE_E['ADS1256_50SPS']
        channel = 7
    elif codice_segnale=="E": #ECG 
        gain = ADS1256new.ADS1256_GAIN_E['ADS1256_GAIN_1']
        drate = ADS1256new.ADS1256_DRATE_E['ADS1256_500SPS']
        channel = 4
    elif codice_segnale=="D": #DOPPLER
        gain = ADS1256new.ADS1256_GAIN_E['ADS1256_GAIN_1']
        drate = ADS1256new.ADS1256_DRATE_E['ADS1256_15000SPS']
        channel = 2

    ADC.ADS1256_init(gain,drate,channel) 
    ADC.ADS1256_WriteCmd(ADS1256new.CMD['CMD_SYNC']) 
    ADC.ADS1256_WriteCmd(ADS1256new.CMD['CMD_WAKEUP'])
    ADC.ADS1256_WaitDRDY()
    
    config.digital_write(config.CS_PIN, GPIO.LOW) 
    config.spi_writebyte([ADS1256new.CMD['CMD_RDATAC']]) 
    return 0

def trigger():
    """Function that triggers the cuff inflation process.
    The output pin on Raspberry Pi drives a relay which powers the valve.
    The energized valve opens the compressor-cuff way, this allows inflation."""
    
    print('trigger')
    #inflation
    GPIO.output(16,True) 
    time.sleep(0.2)
    #deflation
    GPIO.output(16, False) 

    time.sleep(5) 

def isoutlier(x,w_size):
    """It identifies as outliers values that differ by more than 3*standard dev from the mean.
    Mean and standard dev are calculated locally on a moving window of size w_size
    
    INPUT: 
        - x: Signal in which outliers are to be identified
        - w_size: Size of the moving window 

    OUTPUT: 
        - outlier: Boolean vector of the same size as x. Where 1 = outlier
    """

    outlier = []
    
    for i in range(0, int(len(x)/w_size)+1):
        window = x[(i*w_size):((i+1)*w_size)]
        m = np.mean(window)
        dev = np.std(window)

        for j in window:
            if j>=m+3*dev or j<=m-3*dev:
                outlier.append(True)
            else: 
                outlier.append(False)
    
    return outlier


def window_rms(a, window_size):
    """Function that calculates window RMS of a function 

    INPUT:
    - a: signal on which to calculate the window RMS
    - window_size: size of the movable window 

    OUTPUT: 
    - rms: vector of the same size as a, where each element is calculated as the rms value of the windowed signal, with window centred on the sample of interest
    """
    
    a2 = [pow(aa,2) for aa in a]
    window = np.ones(int(window_size)) / float(window_size)  # creo array di lunghezza pari
    rms = (np.sqrt(np.convolve(a2, window,'same')))
    return rms 


def vPWV_TD_percentage( x, fs ):
    """This function computes the time-domain envelope of the Doppler-shift signal and it identifies the footprint of the profile as the 5% of the peak amplitude.
    
    INPUT: 
    - x = vector of length 1 sec
    - fs = sampling frequency [Hz]

    OUTPUT:
    - latency = scalar [sec]
    - v = velocitogram profile [normalized units]
    """

    #PARAMETRI 
    span = 0.1 #Length of window for signal smoothing. As this value increases, the smoothing increases.
    bs = 0.1 * fs;  # initial time when no spike should appear (100 ms)
    MPW = 0.1 * fs; # min peak witdh 
    th = 5; # percentage of peak amplitude

    #ESTRAZIONE DELL'INVILUPPO 
    dx = np.diff(x)
    v = window_rms( dx, fs/100); 
    v1 = np.zeros(len(v)+2)
    v1[0:len(v)]=v
    v1[-2]=v[-1]
    v1[-1]=v[-1] 
    v = v1

    #SMOOTHING AND NORMALIZATION
    points = np.arange(0, len(v), 1)
    smooth = sm.nonparametric.lowess(v, points, frac=span, it=0, is_sorted=True)
    v = smooth[:, 1]
    v = v - np.amin(v)
    v = v / np.amax(v)

    # PEAK FINDING 
    [peaks, property] = find_peaks(v[int(bs):], width=math.floor(MPW))

    if peaks.size == 0:
        peak = np.argmax(v[int(bs):])
    else:
        peak = int(peaks[0])
    
    peak = int(peak + bs)
    
    #VALLEY FINDING 
    valley =  np.argmin(v[int(bs/2):int(peak)])
    valley = int(bs/2)+valley

    #5% OF THE AMPLITUDE
    H = (v[peak] - v[valley]) / 100 * th + v[valley]
    percentage = np.argmin(abs(v[valley:peak] - H))
    percentage = valley + percentage

    # transform in seconds
    latency = percentage / fs

    return latency,v

# ------------------------------------ MAIN -----------------------------------------

def initialization():
    """ Initialisation function to be called only once at the start of the measurement process 
    - Sets the input and output pins
    - Sets the global variables useful for the measurement
    - Monitors 10 s of ECG and sets the threshold to find the R wave
    
    OUTPUT: 
        - ecg_threshold: Threshold to be imposed on the ECG signal. 
                         If ECG > ecg_threshold --> R-wave
    """
    
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(16, GPIO.OUT) 
    GPIO.setup(18, GPIO.OUT) 
 
    #PARAMETERS
    global fs_r, fs_e, fs_d, ecg_threshold
    fs_r = 50 #frequenza di campionamento per il respiro
    fs_e = 500 #frequenza di campionamento per l'ecg
    fs_d = 15000 #frequenza di campionamento per il doppler
    
    ECG_monitoring = [None]*10*fs_e
    

    global ADC
    ADC = ADS1256new.ADS1256()

    #ECG MONITORING
    print("10 s ECG monitoring")
    ADC_configuration("E")

    for i in range(0,len(ECG_monitoring)):
        ECG_monitoring[i]=ADC_reading()
 
    config.digital_write(config.CS_PIN, GPIO.HIGH)  
    config.spi_writebyte([ADS1256new.CMD['CMD_SDATAC']]) 

    ecg_threshold = np.mean(ECG_monitoring)+0.15*(np.amax(ECG_monitoring) - np.amin(ECG_monitoring))

    peaks = find_peaks(ECG_monitoring, threshold=ecg_threshold)

    # If the threshold detects more than 15 peaks in 10 seconds on a relaxed patient, it is probably also intercepting T-waves. Threshold too low. 
    while len(peaks)>15: 
        ecg_threshold = ecg_threshold + 0.02*(np.amax(ECG_monitoring) - np.amin(ECG_monitoring))
        peaks = find_peaks(ECG_monitoring, threshold=ecg_threshold)

    return ecg_threshold , ECG_monitoring

def measure_loop(delay, ecg_threshold):
    """Function to be called in a cycle for repeated measurements after the initialisation phase. 
    - It acquires the respiratory signal and detects the expiration phase 
    - It acquires the ecg and detects the R wave
    - It sends the pressure pulse
    - It acquires the Doppler signal 
    - It processes the Doppler signal 

    Input: 
    - Delay : Optional delay between R-wave detection and pressure pulse delivery 
    - ecg_threshold : Threshold for R-wave detection, calculated above
 
    Output: 
    - Latency : Latency between pressure pulse and footprint 
    - ECG : Acquired ECG singal 
    - Breath : Acquired respiratory singal 
    - Doppler : Acquired Echo-doppler signal
    """
    #Parametes: 
    breath=[]
    ECG=[]
    refresh_time = 1 * fs_r 
    doppler_samples=fs_d*1 #1 s
    doppler=[None]*doppler_samples
    go_trigger=0
    
    while go_trigger==0:

        #EXPIRATORY PHASE DETECTION
        flag_exp=0 
        ADC_configuration("R")
        num_samples = 5
         
        print("Searching for expiratory phase")
        
        for i in range(0,fs_r*5): #5s 
            breath.append(ADC_reading())

        breath_threshold=np.mean(breath)

        while flag_exp == 0: 
            breath.append(ADC_reading()) 

            if (len(breath) % refresh_time == 0): #threshold update
                breath5s = breath[-5*fs_r:] #consider the last 5 seconds 
                breath_threshold=np.mean(breath5s)
            
            pre = breath[len(breath)-num_samples*2:len(breath)-num_samples]
            post = breath[len(breath)-num_samples:len(breath)]            

            if np.amin(pre)>=breath_threshold and np.amax(post)<=breath_threshold:
                flag_exp = 1
                    
        config.digital_write(config.CS_PIN, GPIO.HIGH)
        config.spi_writebyte([ADS1256new.CMD['CMD_SDATAC']])  

        #R-WAVE DETECTION
        print("Searching for R-wave")
        flag_ondaR = 0 
        ADC_configuration("E")
        
        while flag_ondaR == 0 and len(ECG)<=1*fs_e:
            ECG.append(ADC_reading())
            
            if ECG[-1] >= ecg_threshold:
                flag_ondaR = 1
                go_trigger=1 
                print("R-wave detected")
        
        if go_trigger==0:
            print("R-wave detection Failed")
        
        config.digital_write(config.CS_PIN, GPIO.HIGH) 
        config.spi_writebyte([ADS1256new.CMD['CMD_SDATAC']])  

    time.sleep(delay) #optional delay

    ADC_configuration("D")

    #INFLATION TRIGGER
    process1 = Process(target = trigger)  
    process1.start()

    #DOPPLER SIGNAL ACQUISTION
    for i in range(0,len(doppler)):
        doppler[i]=ADC_reading()
   
    print("Doppler signal has been acquired")       
    
    #Calculation of latency between start of acquisition and peak footprint
    latency, envelope = vPWV_TD_percentage(doppler, fs_d)
    print("Computed latency: ", latency, "\n\n\n") 
    
    process1.join() #waits for the process to be completed before going on

    return latency, breath, ECG, doppler

