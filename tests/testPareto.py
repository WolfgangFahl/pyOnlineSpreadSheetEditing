'''
Created on 2022-03-21

@author: wf
'''
from tests.basetest import BaseTest
from onlinespreadsheet.pareto import Pareto

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
    
