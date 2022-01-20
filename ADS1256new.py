import config
import RPi.GPIO as GPIO

ScanMode=0
# Gains
ADS1256_GAIN_E = {'ADS1256_GAIN_1' : 0, # GAIN   1
                  'ADS1256_GAIN_2' : 1, # GAIN   2
                  'ADS1256_GAIN_4' : 2, # GAIN   4
                  'ADS1256_GAIN_8' : 3, # GAIN   8
                  'ADS1256_GAIN_16' : 4,# GAIN  16
                  'ADS1256_GAIN_32' : 5,# GAIN  32
                  'ADS1256_GAIN_64' : 6,# GAIN  64
                 }

# Acuqision frequency rate 
ADS1256_DRATE_E = {'ADS1256_30000SPS' : 0xF0, #1111 0000 
                   'ADS1256_15000SPS' : 0xE0, #1110 0000
                   'ADS1256_7500SPS' : 0xD0,  #1101 0000
                   'ADS1256_3750SPS' : 0xC0,  #1100 0000
                   'ADS1256_2000SPS' : 0xB0,  #1011 0000
                   'ADS1256_1000SPS' : 0xA1,  #1010 0001 
                   'ADS1256_500SPS' : 0x92,   #1001 0010
                   'ADS1256_100SPS' : 0x82,   #1000 0010
                   'ADS1256_60SPS' : 0x72,    #0111 0010
                   'ADS1256_50SPS' : 0x63,    #0110 0011
                   'ADS1256_30SPS' : 0x53,    #0101 0011
                   'ADS1256_25SPS' : 0x43,    #0100 0011
                   'ADS1256_15SPS' : 0x33,    #0011 0011
                   'ADS1256_10SPS' : 0x23,    #0010 0011 NB nella libreria on line era 0x20, cambito a 23 per rispettare il datasheet
                   'ADS1256_5SPS' : 0x13,     #0001 0011
                   'ADS1256_2d5SPS' : 0x03    #0000 0011
                  }

# REGISTER DEFINITION
# Registers manage converter activity.
# They contain all the information about multiplexing management, data rate, calibration, etc.
# Each register is associated with a set of 8 bits, which contain the read values. 
REG_E = {'REG_STATUS' : 0,  # x1H
         'REG_MUX' : 1,     # 01H
         'REG_ADCON' : 2,   # 20H
         'REG_DRATE' : 3,   # F0H
         'REG_IO' : 4,      # E0H
         'REG_OFC0' : 5,    # xxH
         'REG_OFC1' : 6,    # xxH
         'REG_OFC2' : 7,    # xxH
         'REG_FSC0' : 8,    # xxH
         'REG_FSC1' : 9,    # xxH
         'REG_FSC2' : 10,   # xxH
        }

# COMMAND DEFINITION
# Commands control all converter operations.
# The CS pin must remain LOW while sending commands. 
CMD = {'CMD_WAKEUP' : 0x00,     # Completes SYNC and Exits Standby Mode 0000  0000 (00h)
       'CMD_RDATA' : 0x01,      # Read Data 0000  0001 (01h)
       'CMD_RDATAC' : 0x03,     # Read Data Continuously 0000   0011 (03h)
       'CMD_SDATAC' : 0x0F,     # Stop Read Data Continuously 0000   1111 (0Fh)
       'CMD_RREG' : 0x10,       # Read from REG rrr 0001 rrrr (1xh)
       'CMD_WREG' : 0x50,       # Write to REG rrr 0101 rrrr (5xh)
       'CMD_SELFCAL' : 0xF0,    # Offset and Gain Self-Calibration 1111    0000 (F0h)
       'CMD_SELFOCAL' : 0xF1,   # Offset Self-Calibration 1111    0001 (F1h)
       'CMD_SELFGCAL' : 0xF2,   # Gain Self-Calibration 1111    0010 (F2h)
       'CMD_SYSOCAL' : 0xF3,    # System Offset Calibration 1111   0011 (F3h)
       'CMD_SYSGCAL' : 0xF4,    # System Gain Calibration 1111    0100 (F4h)
       'CMD_SYNC' : 0xFC,       # Synchronize the A/D Conversion 1111   1100 (FCh)
       'CMD_STANDBY' : 0xFD,    # Begin Standby Mode 1111   1101 (FDh)
       'CMD_RESET' : 0xFE,      # Reset to Power-Up Values 1111   1110 (FEh)
      }


class ADS1256:
    def __init__(self):
        """ This function configures the three management pins: reset (RST), chip select (CS), data ready (DRDY)

        RST (read and write): resets the ADC if set to LOW
        CS (read and write): must be set to LOW every time a communication with the ADC takes place (setting registers, reading data, sending commands, etc...).
            Then it must be reset to HIGH.
        DRDY (read only): when ADC is ready to read the input value, DRDY goes LOW"""

        self.rst_pin = config.RST_PIN
        self.cs_pin = config.CS_PIN
        self.drdy_pin = config.DRDY_PIN

    # Hardware reset
    def ADS1256_reset(self):
        """This function resets the ACD using the RST pin"""
        config.digital_write(self.rst_pin, GPIO.HIGH) 
        config.delay_ms(200) 
        config.digital_write(self.rst_pin, GPIO.LOW) 
        config.delay_ms(200)
        config.digital_write(self.rst_pin, GPIO.HIGH)
        
    def ADS1256_WriteCmd(self, reg):
        """This function allows the use of commands"""
        config.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        config.spi_writebyte([reg])
        config.digital_write(self.cs_pin, GPIO.HIGH)#cs 1
    
    def ADS1256_WriteReg(self, reg, data):
        """This funtion writes value contained in "data" in register "reg" """
        
        config.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        config.spi_writebyte([CMD['CMD_WREG'] | reg, 0x00, data])
        config.digital_write(self.cs_pin, GPIO.HIGH)#cs 1

    def ADS1256_Read_data(self, reg):
        """ This function Takes in input the number of the desired register and reads the corresponding value of length 1 byte """
       
        config.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        config.spi_writebyte([CMD['CMD_RREG'] | reg, 0x00])
        data = config.spi_readbytes(1)
        config.digital_write(self.cs_pin, GPIO.HIGH)#cs 1

        return data

    def ADS1256_WaitDRDY(self):
        """It waits for the DRDY pin to go LOW, which indicates that the ADC is ready and the input value can be read.
        When the input value has been read, the DRDY pin goes HIGH, while the input value is updated."""
        for i in range(0,400000,1):
            if(config.digital_read(self.drdy_pin) == 0):
                break
        if(i >= 400000):
            print ("Time Out ...\r\n")


    def ADS1256_init(self,gain,drate,ch):
        """ This function resets the ADC and checks its status. 
            It sets the desired gain and sampling rate and it selects the input channel.
            
            Input: 
            - gain: Gain, to be passed as ADS1256_GAIN_E list address. 
            - drate: Sampling frequency, to be passed as address of list ADS1256_DRATE_E. 
            - ch: Input channel (between 0 and 7)      

            Output: 
            - 0: Configuration successful 
            -1: Error occurred during configuration      
            
            Example: ADS.ADS1256_init(ADS1256new.ADS1256_GAIN_E['ADS1256_GAIN_1'], ADS1256new.ADS1256_DRATE_E['ADS1256_50SPS'])"""
        
        if(config.module_init() != 0):
            return -1
        
        self.ADS1256_reset()

        #Checking ADC's ID
        id = self.ADS1256_ReadChipID()
        if id == 3 :
            print("ID Read success  ")
        else:
            print("ID Read failed   ")
            return -1
        
        #Setting of gain, frequency and input channel 
        self.ADS1256_WaitDRDY()
        buf = [0,0,0,0]
        buf[0] = 0x04 
        buf[1] = (ch<<4)|0x08
        buf[2] = 0x01<<5 | gain
        buf[3] = drate
               
        config.digital_write(self.cs_pin, GPIO.LOW)#cs  0
        config.spi_writebyte([CMD['CMD_WREG'] | 0x00, 0x03])
        #Starting from register with address 0x00, it writes 4 registers (3+1)
        config.spi_writebyte(buf)
        
        # Which registers am I writing via the buf array?
        # 0x00 Reg Status: 0000 0100 --> enable self calibration
        # 0x01 Reg Multiplexer: ch 1000 --> select the desired channel as positive input and AINCOM as negative input
        # 0x02 Reg A/D control register: 0010 0gain --> set clock to f(CLKIN), disable sensor detector and set the gain
        # 0x03 Reg drate: drate --> set the sampling frequency

        config.digital_write(self.cs_pin, GPIO.HIGH)#cs 1
        config.delay_ms(1)

        return 0

    
    def ADS1256_ReadChipID(self):
        """Using the status register, this function reads the byte corresponding to the ID.
        Useful function when using several chips at the same time. """

        self.ADS1256_WaitDRDY()
        id = self.ADS1256_Read_data(REG_E['REG_STATUS'])
        id = id[0] >> 4
        # print 'ID',id
        return id

#### END OF FILE ####