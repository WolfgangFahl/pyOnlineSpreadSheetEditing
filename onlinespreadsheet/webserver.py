

from fb4.app import AppWrap
from fb4.sse_bp import SSE_BluePrint
from fb4.widgets import Link,Menu, MenuItem
from wtforms import  StringField,SelectField,  SubmitField, TextAreaField
from flask import render_template, flash, redirect,url_for
from flask_wtf import FlaskForm
from wikibot.wikiuser import WikiUser
from fb4.sqldb import db
from fb4.login_bp import LoginBluePrint
from flask_login import current_user, login_required
import socket
import copy
import os
import sys
from onlinespreadsheet.spreadsheet import SpreadSheetType
from onlinespreadsheet.editconfig import EditConfig, EditConfigManager


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
        self.editConfigurationManager=EditConfigManager()
        self.editConfigurationManager.load()

        @self.app.route('/')
        def home():
            return self.homePage()
        
        @self.app.route('/editconfigs')
        def editConfigs():
            return self.showEditConfigs()
        
     
        @self.app.route('/wikiedit',methods=['GET', 'POST'])
        def wikiEditNone():
            return self.wikiEdit(editConfigName=None)
      
        @self.app.route('/wikiedit/<editConfigName>',methods=['GET', 'POST'])
        @login_required
        def wikiEdit(editConfigName:str):
            return self.wikiEdit(editConfigName)
        
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
    
    def showEditConfigs(self):
        '''
        show my edit configurations
        '''
        template="ose/editconfigs.html"
        title="View/Load Edit configurations for Online Spreadsheet Editing"
        dictList=[]
        for editConfig in self.editConfigurationManager.editConfigs.values():
            link=Link(self.basedUrl(url_for("wikiEdit",editConfigName=editConfig.name)),title=editConfig.name)
            dictList.append({"name":link})
        lodKeys=["name"]    
        html=render_template(template, dictList=dictList,lodKeys=lodKeys,tableHeaders=lodKeys,title=title, menu=self.getMenuList())
        return html
    
    def wikiEdit(self,editConfigName:str=None):
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
        if editConfigName is not None:
            if editConfigName in self.editConfigurationManager.editConfigs:
                editConfig=self.editConfigurationManager.editConfigs[editConfigName]
                editForm.fromEditConfig(editConfig)
            else:
                flash(f"unknown edit configuration {editConfigName}","warn")
        # submitted
        if editForm.validate_on_submit():
            # check which button was pressed
            if editForm.save.data:
                editConfig=editForm.toEditConfig()
                self.editConfigurationManager.add(editConfig)
                self.editConfigurationManager.save()
                flash(f"{editConfig.name} saved","info")
            elif editForm.load.data:
                return redirect(self.basedUrl(url_for('editConfigs')))
                pass
            else:
                editConfig=editForm.toEditConfig()
                tq=editConfig.toTableQuery()
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
    save=SubmitField('save')
    load=SubmitField('load')
    name=StringField('name')
    sourceWiki=SelectField('source Wiki')
    targetWiki=SelectField('target Wiki')   
    query1 = TextAreaField('query 1', render_kw={"rows": 3, "cols": 80})
    queryN = TextAreaField('query N', render_kw={"rows": 3, "cols": 80})
    format=SelectField('format',choices=SpreadSheetType.asSelectFieldChoices())
    
    def toEditConfig(self):
        '''
        convert my data to an edit configuration
        
        view to model conversion
        '''
        editConfig=EditConfig(self.name.data)
        editConfig.sourceWikiId=self.sourceWiki.data
        editConfig.targetWikiId=self.targetWiki.data
        editConfig.query1=self.query1.data
        editConfig.queryN=self.queryN.data
        editConfig.format=self.format.data
        return editConfig
    
    def fromEditConfig(self,editConfig):
        '''
        update the view from the model
        '''
        self.name.data=editConfig.name
        self.sourceWiki.data=editConfig.sourceWikiId
        self.targetWiki.data=editConfig.targetWikiId
        self.query1.data=editConfig.query1
        self.queryN.data=editConfig.queryN
        self.format.data=editConfig.format
        

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