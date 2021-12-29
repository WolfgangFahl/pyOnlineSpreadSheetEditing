from  onlinespreadsheet.tablequery import TableQuery

from fb4.app import AppWrap
from fb4.sse_bp import SSE_BluePrint
from fb4.widgets import  Menu, MenuItem
from wtforms import  SelectField,  SubmitField, TextAreaField
from flask import render_template, flash
from flask_wtf import FlaskForm
from wikibot.wikiuser import WikiUser
from fb4.sqldb import db
from fb4.login_bp import LoginBluePrint
from flask_login import current_user, login_required
import socket
import os
import sys
from onlinespreadsheet.spreadsheet import SpreadSheetType


class WebServer(AppWrap):
    """
    Open Source Online Spreasheet Editing Service
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
        db.init_app(self.app)
        self.db=db
        self.authenticate=False
        self.sseBluePrint = SSE_BluePrint(self.app, 'sse', baseUrl=self.baseUrl)
        self.wikiUsers=WikiUser.getWikiUsers()
    
        self.loginBluePrint=LoginBluePrint(self.app,'login',welcome="home")
        self.initUsers()

        @self.app.route('/')
        def home():
            return self.homePage()
        
     
        @self.app.route('/wikiedit',methods=['GET', 'POST'])
        @login_required
        def wikiEdit():
            return self.wikiEdit()
        
        #
        # setup global handlers
        #
        @self.app.before_first_request
        def before_first_request_func():
            loginMenuList=self.getMenuList("Login")
            self.loginBluePrint.setLoginArgs(menu=loginMenuList)
        
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
        wikiEdit
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
            tq=editForm.toTableQuery()
            flash("retrieving data ...","info")
            tq.fetchQueryResults()
        else:
            pass
        html=render_template(template, title=title, menu=self.getMenuList(),editForm=editForm)
        return html
           
    def getMenuList(self,activeItem:str=None):
        '''
        get the list of menu items for the admin menu
        Args:
            activeItem(str): the active  menu item
        Return:
            list: the list of menu items
        '''
        menu=Menu()
        #self.basedUrl(url_for(
        menu.addItem(MenuItem("/","Home"))
        menu.addItem(MenuItem("/wikiedit","Wiki Edit"))
        menu.addItem(MenuItem('https://wiki.bitplan.com/index.php/pyOnlineSpreadSheetEditing',"Docs")),
        menu.addItem(MenuItem('https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing','github'))
        if current_user.is_anonymous:
            menu.addItem(MenuItem('/login','login'))
        else:
            menu.addItem(MenuItem('/logout','logout'))
        if activeItem is not None:
            for menuItem in menu.items:
                if isinstance(menuItem,MenuItem):
                    if menuItem.title==activeItem:
                        menuItem.active=True
                    menuItem.url=self.basedUrl(menuItem.url)
        return menu
    
    def log(self,msg):
        '''
        log the given message
        '''
        if self.verbose:
            print(msg)
    
    def getUserNameForWikiUser(self,wuser:WikiUser)->str:
        '''
        get the username for the given wiki user
        
        Args:
            wuser(WikiUser): the user to get the username for
        
        Returns:
            str: a fully qualifying username e.g. testuser@testwiki
        '''
        username=f"{wuser.user}@{wuser.wikiId}"
        return username
        
    def initUsers(self,withDBCreate=True):
        '''
        initialize my users
        '''  
        if withDBCreate:
            self.db.drop_all()
            self.db.create_all()
        wusers=WikiUser.getWikiUsers()
        self.log(f"Initializing {len(wusers)} users ...")
        for userid,wuser in enumerate(wusers.values()):
            username=self.getUserNameForWikiUser(wuser)
            self.loginBluePrint.addUser(self.db,username,wuser.getPassword(),userid=userid)

class WikiEditForm(FlaskForm):
    '''
    upload form
    '''
    submit=SubmitField('download')     
    sourceWiki=SelectField('source Wiki')
    targetWiki=SelectField('target Wiki')   
    query1 = TextAreaField('query1', render_kw={"rows": 3, "cols": 80})
    queryn = TextAreaField('queryn', render_kw={"rows": 3, "cols": 80})
    format=SelectField('format',choices=SpreadSheetType.asSelectFieldChoices())
    
    def toTableQuery(self)->TableQuery:
        '''
        convert me to a TableQuery
        '''
        sourceWikiId=self.sourceWiki.data
        tq = TableQuery()
        tq.addAskQuery(sourceWikiId, "query1", self.query1.data, "query 1")
        tq.addAskQuery(sourceWikiId, "queryN", self.queryn.data, "query N")
        return tq

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