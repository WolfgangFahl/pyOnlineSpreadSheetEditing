'''
Created on 18.04.2022

@author: wf
'''
import streamlit as st
from sl.googlesheet import GoogleSheet

url = st.text_input('google sheet url:')
if url:
    gs=GoogleSheet(url)
    gs.open()
    st.table(gs.df)
 
        