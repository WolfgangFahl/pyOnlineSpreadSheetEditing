'''
Created on 2022-03-21

@author: wf
'''
from tests.basetest import BaseTest
from onlinespreadsheet.pareto import Pareto
from tabulate import tabulate

class TestPareto(BaseTest):
    '''
    test handling pareto levels
    '''

    def setUp(self):
        BaseTest.setUp(self)
        pass
    
    
    def testPareto(self):
        '''
        test the pareto levels
        '''
        debug=self.debug
        debug=True
        for level in range(1,10):
            pareto=Pareto(level)
            if debug:
                print(pareto.asText(long=True))
        ratioTests=[(0.5,1),(0.05,2)]
        for ratio,level in ratioTests:
            self.assertTrue(Pareto(level).ratioInLevel(ratio))   
            
    def testParetoTabular(self):
        '''
        test getting a table with the pareto definition
        '''
        paretoLod=[]
        for level in range(1,10):
            d=Pareto(level).asDict()
            print(d)
            paretoLod.append(d)
        for tablefmt in ["mediawiki","latex"]:
            markup=tabulate(paretoLod,headers="keys",tablefmt=tablefmt)
            print(markup)
                 
                
    
