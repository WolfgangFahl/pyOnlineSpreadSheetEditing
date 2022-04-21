'''
Created on 18.04.2022

@author: wf
'''
import streamlit as st
from spreadsheet.googlesheet import GoogleSheet
from st_aggrid import AgGrid

def showTable(url,sheetName):
    gs=GoogleSheet(url)
    sheetNames=[sheetName]
    gs.open(sheetNames)
    AgGrid(gs.dfs[sheetName],editable=True)
    #st.table(gs.df)
 
url = st.text_input('google sheet url:')
    
sheetName=st.text_input('sheetname:')   
if url and sheetName:
    showTable(url,sheetName)
    
 
        