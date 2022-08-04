'''
Created on 2022-03-21

@author: wf
'''
import math

class Pareto(object):
    '''
    Pareto level holder
    '''

    def __init__(self, level:int=1):
        '''
        Constructor
        
        Args:
            level(int): the pareto level
            
        '''
        self.level=level
        self.good=80.0
        self.bad=20.0
        for _i in range(level-1):
            self.good=self.good+self.bad*0.8
            self.bad=100.0-self.good
        self.decimals=1-round(math.log10(self.bad))
        self.oneOutOf=round(100/self.bad)
        pass
    
    def ratioInLevel(self,ratio)->bool:
        '''
        check whether the given ratio is in this level
        '''
        inLevel=ratio>=1/self.oneOutOf
        return inLevel
    
    def asPercent(self):
        percent=100.0/self.oneOutOf
        return percent
            
    def __str__(self):
        text=self.asText(long=False)
        return text       
    
    def asText(self,long:bool=False):
        text=f"{self.good:.{self.decimals}f}:{self.bad:.{self.decimals}f}"
        if long:
            text=f"level {self.level}={text} (1 out of {self.oneOutOf})"
        return text
    
    def asDict(self)->dict:
        '''
        return me as a dict
        
        Returns:
            dict: my values as a dict
        '''
        d={}
        d["level"]=self.level
        d["ratio"]=self.asText()
        d["1 out of"]=self.oneOutOf
        return d
        
        