# This represents the GUI of the program "vPWV.py" to evaluate vPWV.
# The user starts the GUI, enters the value of delta x and possibly of the delay and starts the main program and the graph. 
#"vPWV.py" takes the delay as input, and returns the latency value which is calculated from the doppler signal and written to a text file. 
#To insert a new delay, the program must be paused using the appropriate buttons and restart it later. 

############################################## GUI_Rpi ############################################

from turtle import delay
from typing_extensions import IntVar
from numpy import arange
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import tkinter as tk
from tkinter import ttk
import numpy as np
import time 

import vWPV


class Plot2D(tk.Frame):
    def __init__(self,root,**kwargs):
        
        tk.Frame.__init__(self,root,**kwargs)

        self.traces=dict()

        self.f=Figure(figsize=(5,5), dpi=100)
        self.a=self.f.add_subplot(111)

        self.canvas=FigureCanvasTkAgg(self.f, master=root)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=1)
        
    # Setting of x and y axes taken as input by "plot.trace()"
    def trace(self,x,y):
        if len(x)<=1:
            self.a.set_xlim(x[0]-5,x[0]+5)
        else:         
            self.a.set_xlim(x[0]-5,x[-1]+5)   
        
        self.a.set_ylim(-0.1,10)
        self.line1, = self.a.plot(x,y, "ro-")
        self.a.set_xlabel('Time (s)')
        self.a.set_ylabel('vPWV (m/s)')
        self.canvas.draw()
    
        
def up():
    """ The up() function cycles by calling itself in order to update the graph.
    It checks if the pause button has been pressed and then calls the processing script 
    that outputs a latency value from the doppler signal. This value is used to calculate 
    the speed, which will be plotted.
    """
    
    if flag_pause == False:
        
        if not len(v): #If v vector is empty (first cycle), initialization phase must be done 
            global breath_threshold, ecg_threshold, count
            text1.set("Initialization: ECG and breath monitoring (30 s).")
            root.update_idletasks()
            ecg_threshold, ECG = vWPV.initialization()
            count=0

            #Saving acquired signals 
            file_ecg = open("ecg"+title1+".txt", "w")
            file_ecg.write((str(ECG)+"\n"))
            file_ecg.close()
        
        text1.set("Pulse delivery and doppler acquisition.")
        root.update_idletasks()
        latency, breath, ECG, doppler = vWPV.measure_loop(delay, ecg_threshold)          
            
        text1.set("vWPV vlue computation.")
        root.update_idletasks()
        time.sleep(0.5)
        
        # Aggiornamento del vettore v sul grafico
        # Attenzione agli indici: come in "arange", quando si usano i due punti (:), il primo valore
        # è incluso, mentre l'ultimo è escluso (ricordiamo che i vettori sono composti da 6 valori)
            
        v.append(deltax/(latency*100)) 
        x.append(time.time())
        count += 1
        
        #I represent 6 values at a time
        if len(v)>6:
            v.pop(0)
            x.pop(0)                
 
        string1 = "vWPV (m/s)"
        for i in range(0,len(v)):
            string1 = (string1 + "\n" +str(round(v[i],3)))
            
        text_vel.set(string1)       #Writes the updated speed values into text_vel variable which is printed as a column 

        plot.trace(x,v)  

        #Saving acquired signals
        file_doppler = open("doppler_"+title1+".txt","a") 
        file_doppler.write((str(doppler)+"\n"))
        file_doppler.close()
        
        file_latency = open("latenze_"+title1+".txt", "a")
        file_latency.write((str(latency)+"\n"))
        file_latency.close()

        file_vPWV = open("vPWV"+title1+".txt", "a")
        file_vPWV.write((str(v[-1])+"\n"))
        file_vPWV.close()

        file_breath = open("respiratory_"+title1+".txt", "a")
        file_breath.write((str(breath)+"\n"))
        file_breath.close()

        file_ecg = open("ecg"+title1+".txt", "a")
        file_ecg.write((str(ECG)+"\n"))
        file_ecg.close()

        root.after(1,up)           
        

def f_grafico():
    """ Function called by START CHART button which calls up(), 
    disables the button and reassigns values to the variables used to create the graph """

    global plot, flag_pause
    
    flag_pause = False
    
    buttons[0].config(state="disabled")   #Start Chart
    buttons[1].config(state="normal") #Pause
    buttons[2].config(state="disabled") #Resume 
  
    up()
    
    
def f_invia(event):   
    """ Udates the delay"""
    
    if stringa.get().isdigit() == True:  
        global delay
        delay=stringa.get()
        delay = int(delay)

        tk.messagebox.showinfo("Dealy", "Delay Updated: "+str(delay)+" ms")
    else:
        tk.messagebox.showerror("Error", "Insert a numeric value.")
        

def click2():
    f_invia(event=None)


def f_pause():
    global flag_pause
    flag_pause = True
    print("Pause")
    text1.set("Paused. Press restar to resume measurament")
    root.update_idletasks()
    buttons[1].config(state="disabled") #pause
    buttons[2].config(state="normal") #resume 
    
def f_resume():
    global flag_pause
    flag_pause = False
    print("Resumed")
    buttons[1].config(state="normal") #pause
    buttons[2].config(state="disabled") #resume  
    up()
         
    
def f_start(event):
    """
    Generation of the GUI window 2 (main window in which the results will be displayed).
    It contains the button that starts data collection.
    """
    
   # Definizione di alcune variabili, definite globali perchè vengono richiamate anche da altre funzioni     
    global deltax, frame21, frame24, frame25, text1, text_vel, lbltext, v, x, plot, delay, title1
    
    v=[]  
    x=[]
    delay = 0
    
    
    if entrydeltax.get().isdigit() == True:     
        deltax=int(entrydeltax.get())    

        if len(entry_title.get()) >= 1:
            title1=entry_title.get()
            title1=title1+time.ctime()
        else:
            title1=""

       # Update of GUI aspect
        frame11.destroy()
        frame12.destroy()
        frame13.destroy()
        frame14.destroy()
        
        # Entry widget for delay update
        frame21=tk.Frame(root) 
        frame21.pack(side="top")

        lbldeltax = tk.Label(frame21, text="∆x: " + str(deltax) + " cm", font=("", 18))
        lbldeltax.pack(side = "left", padx=30)

        lbldelay=tk.Label(frame21, text="  Delay: ", font=("", 24,"bold"))
        lbldelay.pack(side="left")

        entry_delay=tk.Entry(frame21,textvariable = stringa,justify="right",font=("",24))
        entry_delay.pack(side="left")
        entry_delay.focus_set()
        entry_delay.bind("<Return>", f_invia)   

        lbludm=tk.Label(frame21, text="ms", font=("", 24,"bold"))
        lbludm.pack(side="left")

        btninvia=tk.Button(frame21, text="Invia", command=click2, font=("", 24))     
        btninvia.pack(side="left", padx=30)

        #"Start Chart" button
        frame22=tk.Frame(root) 
        frame22.pack(side="top")

        btngrafico = tk.Button(frame22, text="Start Chart", command=f_grafico, font=("", 24,"bold"), height=3, width=15)  # Fa partire il grafico
        btngrafico.pack(pady=30)

        buttons.append(btngrafico)

        #"Pauese" and "Resume" buttons
        frame23=tk.Frame(root) 
        frame23.pack(side="top")
        
        btnpause=tk.Button(frame23, text="Pause", command=f_pause, font=("",24))
        btnpause.pack(pady = 10, side="left", padx=30)
        buttons.append(btnpause)

        btnresume=tk.Button(frame23, text="Resume", command=f_resume, font=("",24))
        btnresume.pack(pady = 10, side="left", padx=30)
        buttons.append(btnresume)

        # String variable to be updated during the various stages of acquisition
        frame24 = tk.Frame(root) 
        frame24.pack(side="top")

        text1=tk.StringVar()    
        lbltext=tk.Label(frame24,textvariable=text1,font=("",16)) # Tabella delle velocità (che andrà                                                        # mano a mano a riempirsi)
        lbltext.pack(padx=10)
        
        text1.set("Press 'Start Chart' to start the measurement..")
        
        # Table for displaying vPWV values 
        frame25=tk.Frame(root) 
        frame25.pack(side="right")
        
        text_vel=tk.StringVar() 
        lblvel=tk.Label(frame25,textvariable=text_vel,font=("",24)) 
        lblvel.pack(padx=50)

        # Graph
        plot = Plot2D(root)
        
        # Buttons state
        buttons[0].config(state="normal") #start chart
        buttons[1].config(state="disabled") #pause
        buttons[2].config(state="disabled") #resume
            
    else:    
       tk.messagebox.showerror("Error", "Enter a numerical value")
           
    root.mainloop() 
    
    return deltax

######################################## FINE FUNZIONE START ######################################


def click():
    """ Function called after DeltaX has been entered by the user.
The function clik() in turn calls f_start(), both when the button is pressed and when the physical enter key is pressed.
    """
    f_start(event=None)
    

############################################ MAIN ######################################################

if __name__=="__main__":
    """ Function in which the initial graphic window is created with its widgets 
        and delta x (cuff-probe length) is asked.
    """
    
    global flag_pause
    flag_pause =False   
    buttons=[]      
 
    root=tk.Tk()
    root.title("vPWV measurament")
    w, h=root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry("%dx%d" % (w,h))
    root.focus_force()

    # FRAME 11: Delta X entering 
    frame11=tk.Frame(root)
    frame11.pack(side="top")

    lblentering=tk.Label(frame11, text="Enter ∆x: ", font=("", 18,"bold"))
    lblentering.pack(side="left", pady=20)

    entrydeltax=tk.Entry(frame11,justify="right",font=("",18))
    entrydeltax.pack(side="left", pady=20)
    entrydeltax.focus_set()

    lbludm=tk.Label(frame11, text="cm", font=("", 18,"bold"))
    lbludm.pack(side="left", pady=20)

    entrydeltax.bind("<Return>", f_start) 

    #FRAME 12: Start button
    frame12=tk.Frame(root)
    frame12.pack(side="top")
    
    btnstart=tk.Button(frame12, text="START", command=click, font=("", 22,"bold"),
                       height=3, width=15)     
    btnstart.pack(side="top", pady=50)
    
    #FRAME 13: Text 
    frame13=tk.Frame(root)
    frame13.pack(side="top")
    explenation = tk.Label(frame13, text="Insert the distance between the points of generation and detection of the pressure pulse. ",
                           font=("", 14))
    explenation.pack(side="top", pady=30)

    #FRAME 14: File name
    frame14=tk.Frame(root)
    frame14.pack(side="top")
    lbltitolo=tk.Label(frame14, text="File name:", font=("",14))
    lbltitolo.pack(side="left",pady=20)
    entry_title=tk.Entry(frame14,justify="right",font=("",14))
    entry_title.pack(side="left", pady=20)
    entry_title.focus_set()


    stringa=tk.StringVar(root)
    

    root.mainloop()   
######################################### FINE MAIN ###################################################

