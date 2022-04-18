'''
Created on 2022-04-18

@author: wf
'''
from pathlib import Path
import json
import os
from wikidataintegrator import wdi_core, wdi_login
import pprint

class Wikidata:
    '''
    wikidata access
    
    see http://learningwikibase.com/data-import/
    '''
    
    def __init__(self,baseurl,debug:bool=False):
        self.baseurl=baseurl
        self.debug=debug
        self.apiurl=f"{self.baseurl}/w/api.php"
        pass
    
    def getCredentials(self):
        '''
        get my credentials
        '''
        user=None
        pwd=None
        home = str(Path.home())
        configFilePath=f"{home}/.config/wikibase-cli/config.json"
        if os.path.isfile(configFilePath):
            with open(configFilePath, mode="r") as f:
                wikibaseConfigJson = json.load(f)
                credentials=wikibaseConfigJson["credentials"]
                credentialRow=credentials[self.baseurl]
                user=credentialRow["username"]
                pwd=credentialRow["password"]
                pass
        return user,pwd
            
    def login(self):
        user,pwd=self.getCredentials()
        if user is not None:
            self.login = wdi_login.WDLogin(user=user, pwd=pwd, mediawiki_api_url=self.apiurl)
            
    def addItem(self,ist,label,description,lang:str="en",write:bool=True):
        '''
        Args:
            ist(list): item statements
            label(str): the english label
            description(str): the english description
            lang(str): the label language
            write(bool): if True do actually write
        '''
        wbPage=wdi_core.WDItemEngine(data=ist,mediawiki_api_url=self.apiurl)
        wbPage.set_label(label, lang=lang)
        wbPage.set_description(description, lang=lang)
        if self.debug:
            pprint.pprint(wbPage.get_wd_json_representation())
        if write:
            wbPage.write(self.login) # edit_summary=
            
                