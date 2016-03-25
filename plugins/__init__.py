'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''


import numpy 
import random
from pymavlink import mavutil
from  math import *
import argparse


class ReturnMessage(mavutil.mavlink.MAVLink_message):
    def __init__(self,  *kwargs):
        mavutil.mavlink.MAVLink_message.__init__(self,  *kwargs)
    
class Plugin:
    def filter(self,  message):
        return false
             
    def run(self,  message): 
        None
            
import debugger
import google_earth_server
import gps_tool
import robotvis

class plugin_manager():
    
    def __init__(self,  plugin_callback,  data_range=[-1000,  0]):
        self.data_range=data_range
        parser =  argparse.ArgumentParser("[plugin_options]")

        parser.add_argument("--p_debug_elf", dest="p_debug_elf",  help="ELF file for debug information", default="")
        (opts, args) = parser.parse_known_args()
        
        self.active_plugins=[]#[distance_kalman_filter()]
        self.active_plugins=[google_earth_server.Google_Earth_Server(data_range = self.data_range),  \
                                        gps_tool.gps_tool(),  \
                                        gps_tool.Named_Value_Scaler() \
                                        #robotvis.robotvis()\
                                        ]
        if opts.p_debug_elf!="":
            self.active_plugins.append(debugger.Debugger(elf_filename= opts.p_debug_elf))
        
        self.plugin_callback=plugin_callback
        
    def run_plugins(self,  message):
        for p in self.active_plugins:
            if p.filter(message):
                # run plugin and send return message back to callback function of the requester
                self.plugin_callback(p.run(message))
            
            
class particle:
    def __init__(self,  dimensions):
        self.weight=0.0
        self.vector=numpy.zeros(dimensions)
        
        
def threshold(x,  t):
    if x>t:
        return 1
    else:
        return 0
    
def lpf_blur(data,  alpha):
    output=[0 for x in data]
    lpf=data[0]
    max_in=max(data)
    for i in range(0,  len(data)):
        lpf=alpha*lpf + (1.0-alpha) *data[i]
        output[i]=lpf

    lpf=data[-1]
    for i in reversed(range(0,  len(data))):
        lpf=alpha*lpf + (1.0-alpha) *data[i]
        output[i]=(output[i]+lpf)/2.0

    max_out=max(output)
    if max_out>0.0:
        output=[x*max_in/max_out for x in output]
    return output
    

def argmax(data):
    am=0
    for i in range(0,  len(data)):
        if data[i]>data[am]:
            am=i
    return am

sqrt_2_pi=sqrt(2*pi)

def gauss(mean,  sigma,  x):
    return 1/(sigma*sqrt_2_pi) * exp(-0.5*((x-mean)/sigma)**2)

class amplitude_particle_filter(Plugin):
    def __init__(self):
        self.number_of_particles=100
        self.max_distance=5.0
        self.max_vel=5.0
        self.particles=[particle(2) for x in range(0, self.number_of_particles)]        
        self.population=[particle(2) for x in range(0, 2*self.number_of_particles)]        
        self.out_msg= mavutil.mavlink.MAVLink_message(1000,  "Distance Particles")
        self.out_msg.key="%s:%s"%(self.out_msg.get_srcSystem(),  self.out_msg.__class__.__name__)
        self.out_msg._fieldnames=["vel",  "dist",  "weight",  "motion_detection",  "avg_vel",  "avg_dist",  "max_amp"]
        self.last_time=None
        self.fft_index_to_speed = 1/30.0
        self.min_amplitude=50
        self.amplitude_per_meter=20**4

    def resample(self):
        # normalise weights:
        total_weight=0.0
        for p in self.particles:
            total_weight+=p.weight
        pop_index=0
        if total_weight>0.001:
            for p in self.particles:
                    #print p.weight*self.number_of_particles/total_weight
                    for i in range(0,  int(p.weight*(len(self.population)/total_weight))):
                        if pop_index<len(self.population):
                            self.population[pop_index].weight=p.weight
                            self.population[pop_index].vector=[p.vector[0]+random.gauss(0.0,  0.1),  p.vector[1]+random.gauss(0.0,  0.1)]       
                            pop_index+=1
        if pop_index==0:
            for i in range(pop_index,  len(self.population)):
                self.population[i].vector=[2.0*(random.random()-0.5)*self.max_vel,  (random.random())*self.max_distance]
                self.population[i].weight=0.0
                pop_index=i
        #randomly draw from population
        print pop_index
        for i in range(0, self.number_of_particles):
            np=self.population[random.randint(0, pop_index-1)]
            self.particles[i].vector=[np.vector[0],  np.vector[1]]
            self.particles[i].weight=np.weight
        #print [(p.vector[0],  p.vector[1]) for p in particles]


    def filter(self,  message):
        # just an example for a filter
        return message.__class__.__name__.startswith("MAVLink_raw_data_stream") and message.stream_id==0

    def run(self,  message):
        input=message.values
        input[0]=0.0
        timestamp=message.time_boot_ms/1000.0
        if self.last_time==None: 
            self.last_time=timestamp
            return None
        dt=(timestamp-self.last_time)
        self.last_time=timestamp
        
        # make motion field by thresholding
        motion_det=[sqrt(fabs(x))*threshold(-x,  self.min_amplitude) for x in reversed(input[1:])]+[sqrt(fabs(x))*threshold(x,  self.min_amplitude) for x in input]
        if (max(motion_det)==0.0):
            motion_det[len(input)]=1.0;
        motion_det=lpf_blur(motion_det,  0.95)
        vel=(argmax(motion_det)-len(input))*self.fft_index_to_speed
        print vel
        amp_input=lpf_blur([fabs(x) for x in input],  0.9)
        for p in self.particles:
            # motion update:
            # random noise on velocity estimate
            #p.vector[0]+=random.gauss(0.0,  0.5*dt)
            # shift distance estimate by velocity estimate
            p.vector[0]=(p.vector[0]+vel)/2.0
            p.vector[1]+=p.vector[0] * dt
        
            # weighting
            p_fft_index=int(p.vector[0]/self.fft_index_to_speed)
            vel_weight=0.0
            act_amp=0.0
            if ( abs(p_fft_index)<len(input)-1):
                vel_weight=1.0+(10.0*motion_det[p_fft_index+len(input)])**2
                act_amp=amp_input[abs(p_fft_index)]
                est_dist=10.0/sqrt(sqrt(act_amp))-1.0
                exp_amp=1.0/(0.000001+(self.amplitude_per_meter * p.vector[1])**4)
                amp_weight=1.0+0.2/(1.0+(est_dist-p.vector[1])**2)
                p.weight= (vel_weight *amp_weight)
            else:
                p.weight=0
                
            if abs(p.vector[0])>self.max_vel or p.vector[1]<-0.5 or p.vector[1]>self.max_distance:
                p.weight=0

        avg_vel=0.0
        avg_dist=0.0
        tweight=0.0
        for p in self.particles:
            tweight+=p.weight
            avg_vel+=p.vector[0]*p.weight
            avg_dist+=p.vector[1]*p.weight
        avg_vel/=tweight
        avg_dist/=tweight

        
        self.out_msg.weight=[p.weight for p in self.particles]

        self.resample()

        
        # write to output
        #self.out_msg._header=message._header
        
        self.out_msg.vel=[p.vector[0] for p in self.particles]
        self.out_msg.dist=[p.vector[1] for p in self.particles]
        
        self.out_msg.avg_vel=avg_vel
        self.out_msg.avg_dist=avg_dist
        self.out_msg.max_amp=act_amp
        
        self.out_msg.motion_detection=motion_det

        return self.out_msg
        
        
        
class distance_particle_filter(Plugin):
    def __init__(self):
        self.number_of_particles=100
        self.max_distance=5.0
        self.max_vel=5.0
        self.particles=[particle(2) for x in range(0, self.number_of_particles)]        
        self.population=[particle(2) for x in range(0, 2*self.number_of_particles)]        
        self.out_msg= mavutil.mavlink.MAVLink_message(1000,  "Distance Particles")
        self.out_msg.key="%s:%s"%(self.out_msg.get_srcSystem(),  self.out_msg.__class__.__name__)
        self.out_msg._fieldnames=["vel",  "dist",  "weight",  "motion_detection",  "avg_vel",  "avg_dist",  "max_amp"]
        self.last_time=None
        self.fft_index_to_speed = 1/30.0
        self.phase_to_dist=1/1000.0
        self.min_amplitude=100
        self.amplitude_per_meter=20**4
        self.inputFFT=[]
        self.inputPhase=[]
        self.avg_dist=0
        self.avg_vel=0

    def resample(self):
        # normalise weights:
        total_weight=0.0
        for p in self.particles:
            total_weight+=p.weight
        pop_index=0
        if total_weight>0.001:
            for p in self.particles:
                    #print p.weight*self.number_of_particles/total_weight
                    for i in range(0,  int(p.weight*(len(self.population)/total_weight))):
                        if pop_index<len(self.population):
                            self.population[pop_index].weight=p.weight
                            self.population[pop_index].vector=[p.vector[0]+random.gauss(0.0,  0.15),  p.vector[1]+random.gauss(0.0,  0.1)]       
                            pop_index+=1
        if pop_index==0:
            for i in range(pop_index,  len(self.population)):
                self.population[i].vector=[2.0*(random.random()-0.5)*self.max_vel,  (random.random())*self.max_distance]
                self.population[i].weight=0.0
                pop_index=i
        #randomly draw from population
        print pop_index
        for i in range(0, self.number_of_particles):
            np=self.population[random.randint(0, pop_index-1)]
            self.particles[i].vector=[np.vector[0],  np.vector[1]]
            self.particles[i].weight=np.weight
        #print [(p.vector[0],  p.vector[1]) for p in particles]


    def filter(self,  message):
        # just an example for a filter
        if  message.__class__.__name__.startswith("MAVLink_raw_data_stream") :
            if (message.stream_id==0):
                self.inputFFT=message.values
            if (message.stream_id==1):
                self.inputPhase=message.values
                return True
        
        return False

    def run(self,  message):
        input=self.inputFFT
        input[0]=0.0
        timestamp=message.time_boot_ms/1000.0
        if self.last_time==None: 
            self.last_time=timestamp
            return None
        dt=(timestamp-self.last_time)
        self.last_time=timestamp
        
        # make motion field by thresholding
        motion_det=[(fabs(x))*threshold(-x,  self.min_amplitude) for x in reversed(input[1:])]+[(fabs(x))*threshold(x,  self.min_amplitude) for x in input]
        if (max(motion_det)==0.0):
            motion_det[len(input)]=1.0;
        motion_det=lpf_blur(motion_det,  0.95)
        vel=(argmax(motion_det)-len(input))*self.fft_index_to_speed
        
        for p in self.particles:
            # motion update:
            # random noise on velocity estimate
            #p.vector[0]+=random.gauss(0.0,  0.5*dt)
            # shift distance estimate by velocity estimate
            p.vector[0]=0.7*p.vector[0]+0.3*vel#(p.vector[0]+vel)/2.0
            p.vector[1]+=p.vector[0] * dt
        
            # weighting
            p_fft_index=int(p.vector[0]/self.fft_index_to_speed)
            vel_weight=0.0
            act_amp=0.0
            if ( abs(p_fft_index)<len(input)-1):
                vel_weight=1.0+(10.0*motion_det[p_fft_index+len(input)])**2
                
                if abs(p_fft_index)>1 and self.inputPhase[abs(p_fft_index)]>0:
                    est_dist=(self.inputPhase[abs(p_fft_index)]) * self.phase_to_dist
                    dst_weight=1.0+(1.0/(est_dist-p.vector[1])**2+0.1)
                    if p.vector[1]<0:
                        dst_weight*=0.8
                else:
                    dst_weight=20.0;
                p.weight= (vel_weight *dst_weight)
            else:
                p.weight=0
                
            if abs(p.vector[0])>self.max_vel or p.vector[1]<-0.5 or p.vector[1]>self.max_distance:
                p.weight=0

        avg_vel=0.0
        avg_dist=0.0
        tweight=0.0
        for p in self.particles:
            tweight+=p.weight
            avg_vel+=p.vector[0]*p.weight
            avg_dist+=p.vector[1]*p.weight
        avg_vel/=tweight
        avg_dist/=tweight

        
        self.out_msg.weight=[p.weight for p in self.particles]

        self.resample()

        self.avg_dist=self.avg_dist*0.6+avg_dist*0.4
        # write to output
        #self.out_msg._header=message._header
        
        self.out_msg.vel=[p.vector[0] for p in self.particles]
        self.out_msg.dist=[p.vector[1] for p in self.particles]
        
        self.out_msg.avg_vel=avg_vel
        self.out_msg.avg_dist=self.avg_dist
        self.out_msg.max_amp=act_amp
        
        self.out_msg.motion_detection=motion_det
        return self.out_msg


# Implements a linear Kalman filter.
class KalmanFilterLinear:
  def __init__(self,_A, _B, _H, _x, _P, _Q, _R):
    self.A = _A                      # State transition matrix.
    self.B = _B                      # Control matrix.
    self.H = _H                      # Observation matrix.
    self.current_state_estimate = _x # Initial state estimate.
    self.current_prob_estimate = _P  # Initial covariance estimate.
    self.Q = _Q                      # Estimated error in process.
    self.R = _R                      # Estimated error in measurements.
  def GetCurrentState(self):
    return self.current_state_estimate
  def Step(self,control_vector,measurement_vector):
    #---------------------------Prediction step-----------------------------
    predicted_state_estimate = self.A * self.current_state_estimate + self.B * control_vector
    predicted_prob_estimate = (self.A * self.current_prob_estimate) * numpy.transpose(self.A) + self.Q
    #--------------------------Observation step-----------------------------
    innovation = measurement_vector - self.H*predicted_state_estimate
    innovation_covariance = self.H*predicted_prob_estimate*numpy.transpose(self.H) + self.R
    #-----------------------------Update step-------------------------------
    kalman_gain = predicted_prob_estimate * numpy.transpose(self.H) * numpy.linalg.inv(innovation_covariance)
    self.current_state_estimate = predicted_state_estimate + kalman_gain * innovation
    # We need the size of the matrix so we can make an identity matrix.
    size = self.current_prob_estimate.shape[0]
    # eye(n) = nxn identity matrix.
    self.current_prob_estimate = (numpy.eye(size)-kalman_gain*self.H)*predicted_prob_estimate

class distance_kalman_filter(Plugin):
    def __init__(self):
        self.number_of_particles=100
        self.max_distance=5.0
        self.max_vel=5.0
        self.particles=[particle(2) for x in range(0, self.number_of_particles)]        
        self.population=[particle(2) for x in range(0, 2*self.number_of_particles)]        
        self.out_msg= mavutil.mavlink.MAVLink_message(1000,  "Kalman filter")
        self.out_msg.key="%s:%s"%(self.out_msg.get_srcSystem(),  self.out_msg.__class__.__name__)
        self.out_msg._fieldnames=["vel",  "dist",   "motion_detection",  "pdf",  "avg_vel",  "avg_dist",  "max_amp"]
        self.last_time=None
        self.fft_index_to_speed = 1/30.0
        self.phase_to_dist=1/1000.0
        self.min_amplitude=100
        self.amplitude_per_meter=20**4
        self.inputFFT=[]
        self.inputPhase=[]

        dt=1/30.0
        # motion model:
        #  1    0
        #  dt  1
        motion_model=numpy.matrix([[1.0, 0.0],  [dt,  1.0]])
        control_model=numpy.eye(2)
        
        observation=numpy.eye(2)
        initial_probability=numpy.eye(2)
        initial_state = numpy.matrix([[0.0],[0.0]])

        process_covariance = numpy.matrix([[0.1,  0.0], [0.0,  0.01]])
        measurement_covariance=numpy.matrix([[0.3,  0],  [0.0,  1.0]])
        
        self.kf=KalmanFilterLinear(motion_model, control_model, observation, initial_state, initial_probability, process_covariance, measurement_covariance)


    def filter(self,  message):
        # just an example for a filter
        if  message.__class__.__name__.startswith("MAVLink_raw_data_stream") :
            if (message.stream_id==0):
                self.inputFFT=message.values
            if (message.stream_id==1):
                self.inputPhase=message.values
                return True
        
        return False

    def run(self,  message):
        input=self.inputFFT
        input[0]=1.0
#        input[1]=0.0
        timestamp=message.time_boot_ms/1000.0
        if self.last_time==None: 
            self.last_time=timestamp
            return None
        dt=(timestamp-self.last_time)
        self.last_time=timestamp
        
        # make motion field by thresholding
        motion_det=[(fabs(x))*threshold(-x,  self.min_amplitude) for x in reversed(input[1:])]+[1.0]+[(fabs(x))*threshold(x,  self.min_amplitude) for x in input[1:]]
        if (max(motion_det)==0.0):
            motion_det[len(input)]=1.0;
        else: 
            motion_det[len(input)]=0.0;
        #motion_det=lpf_blur(motion_det,  0.95)
        peak_index=(argmax(motion_det)-len(input))
        peak_index=sum( value*frequency for value,frequency in zip(range(0, len(motion_det)),  motion_det) )/sum( motion_det )
        
        peak_amp=motion_det[int(peak_index)]

        sigma=sqrt(sum((x-peak_index)**2*count for x,  count in zip(range(0, len(motion_det)),  motion_det))/(sum( motion_det )-0.999))+0.5

        sense_filter=[gauss(peak_index-len(input),  sigma,  float(x)) for x in range(-len(motion_det)/2,  len(motion_det)/2)]
        motion_det=map(lambda x, y: x*y, motion_det,  sense_filter)
    
        dist=[x/1000.0 for x in reversed(self.inputPhase[1:])]+[0.0]+[x/1000.0 for x in self.inputPhase[1:]]
        
        dist=map(lambda x, y: x*y, dist,  sense_filter)
        
        m_vel=(peak_index-len(input)+1)*self.fft_index_to_speed
        m_dist=sum(dist)
        control_vector=numpy.matrix([[0.0], [0.0]])
        # set distance measurement uncertainty
        self.kf.R[0, 0] = sqrt(300.0/peak_amp)
        if fabs(m_vel)>0.1:
            self.kf.R[1, 1]=(1000/peak_amp)
        else:
            self.kf.R[1, 1]=1000.0
        
        self.kf.Step(control_vector,numpy.matrix([[m_vel],[m_dist]]))
        
        avg_vel=self.kf.GetCurrentState()[0, 0]
        avg_dist=self.kf.GetCurrentState()[1, 0]
        tweight=0.0
        
        # write to output
        #self.out_msg._header=message._header
        
        self.out_msg.vel=m_vel
        self.out_msg.dist=dist
        
        self.out_msg.avg_vel=avg_vel
        self.out_msg.avg_dist=avg_dist
        self.out_msg.max_amp=peak_amp
        
        self.out_msg.motion_detection=motion_det
        self.out_msg.pdf=sense_filter

        return self.out_msg

