from fb4.app import AppWrap
from fb4.sse_bp import SSE_BluePrint
from fb4.widgets import  Menu, MenuItem
from wtforms import  SelectField,  SubmitField
from flask import render_template, flash
from flask_wtf import FlaskForm
from wikibot.wikiuser import WikiUser
import socket
import os
import sys

class WebServer(AppWrap):
    """
    Openline Spreasheet Editing Service
    """

    def __init__(self, host=None, port=8559, verbose=True, debug=False):
        '''
        constructor

        Args:
            host(str): flask host
            port(int): the port to use for http connections
            debug(bool): True if debugging should be switched on
            verbose(bool): True if verbose logging should be switched on
        '''
        self.debug = debug
        self.verbose = verbose
        scriptdir = os.path.dirname(os.path.abspath(__file__))
        template_folder=scriptdir + '/../templates'
        if host is None:
            host=socket.gethostname()
        super().__init__(host=host, port=port, debug=debug, template_folder=template_folder)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.app_context().push()
        self.authenticate=False
        self.sseBluePrint = SSE_BluePrint(self.app, 'sse', baseUrl=self.baseUrl)
        self.wikiUsers=WikiUser.getWikiUsers()


        @self.app.route('/')
        def home():
            return self.homePage()
        
        @self.app.route('/wikiedit',methods=['GET', 'POST'])
        def wikiEdit():
            return self.wikiEdit()
        
    def homePage(self): 
        '''
        render the homepage
        '''
        template="ose/home.html"
        title="Online Spreadsheet Editing"
        
        html=render_template(template, title=title, menu=self.getMenuList())
        return html
    
    def wikiEdit(self):
        '''
        upload
        '''
        title='wikiEdit'
        template="ose/wikiedit.html"
        editForm=WikiEditForm()
        wikiChoices=[]
        for wikiUser in sorted(self.wikiUsers):
            wikiChoices.append((wikiUser,wikiUser)) 
        editForm.sourceWiki.choices=wikiChoices    
        editForm.targetWiki.choices=wikiChoices
        if editForm.validate_on_submit():
            flash("uploading ...","info")
        else:
            pass
        html=render_template(template, title=title, menu=self.getMenuList(),editForm=editForm)
        return html
           
    def getMenuList(self):
        '''
        set up the menu for this application
        '''
        menu=Menu()
        menu.addItem(MenuItem("/","Home"))
        menu.addItem(MenuItem("/wikiedit","Wiki Edit"))
        menu.addItem(MenuItem('https://wiki.bitplan.com/index.php/pyOnlineSpreadSheetEditing',"Docs")),
        menu.addItem(MenuItem('https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing','github'))
        return menu

class WikiEditForm(FlaskForm):
    '''
    upload form
    '''
    submit=SubmitField('upload')     
    sourceWiki=SelectField('source Wiki')
    targetWiki=SelectField('target Wiki')   

DEBUG = False

def main(_argv=None):
    '''main program.'''
    # construct the web application
    web=WebServer()
    
    parser = web.getParser(description="Spreadsheet editing services for Semantic MediaWikis")
    parser.add_argument('--verbose', default=True, action="store_true", help="should relevant server actions be logged [default: %(default)s]")
    args = parser.parse_args()
    web.optionalDebug(args)
    web.run(args)

if __name__ == '__main__':
    sys.exit(main())