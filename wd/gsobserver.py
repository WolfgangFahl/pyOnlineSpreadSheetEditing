'''
Created on 18.04.2022

@author: wf
'''
import streamlit as st
from sl.googlesheet import GoogleSheet
from st_aggrid import AgGrid

def showTable(url):
    gs=GoogleSheet(url)
    gs.open()
    AgGrid(gs.df,editable=True)
    #st.table(gs.df)
    
url = st.text_input('google sheet url:')
if url:
    showTable(url)
    
 
        