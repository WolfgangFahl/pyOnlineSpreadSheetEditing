

from fb4.app import AppWrap
from fb4.sse_bp import SSE_BluePrint
from fb4.widgets import Copyright, Link,Menu, MenuItem
from wtforms import StringField, SelectField, SubmitField, TextAreaField, FieldList, FormField
from flask import render_template, flash, url_for, send_file
from flask_wtf import FlaskForm
from wikibot.wikiuser import WikiUser
from fb4.sqldb import db
from fb4.login_bp import LoginBluePrint
from flask_login import current_user, login_required
import socket
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
        
        #  server specific initializations
        link=Link("http://www.bitplan.com/Wolfgang_Fahl",title="Wolfgang Fahl")
        self.copyRight=Copyright(period="2021-2022",link=link)
        
        self.wikiUsers=WikiUser.getWikiUsers()
    
        self.loginBluePrint=LoginBluePrint(self.app,'login',welcome="home")
        self.initUsers()
        self.editConfigurationManager=EditConfigManager()
        self.editConfigurationManager.load()

        @self.app.route('/')
        def home():
            return self.homePage()
        
        @self.app.route('/editconfigs')
        @login_required
        def editConfigs():
            return self.showEditConfigs()
        
     
        @self.app.route('/wikiedit',methods=['GET', 'POST'])
        @login_required
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
            loginMenu=self.getMenu("Login")
            self.loginBluePrint.setLoginArgs(menu=loginMenu)
     
    def render_template(self,templateName:str,title:str,activeItem:str,**kwArgs):
        '''
        render the given template with the default arguments
        
        Args:
            templateName(str): the name of the template to render
            title(str): the title to display for html
            activeItem(str): the name of the menu item to display as active
        '''
        html=render_template(templateName,title=title,menu=self.getMenu(activeItem),copyright=self.copyRight,**kwArgs)
        return html
        
    def homePage(self): 
        '''
        render the homepage
        '''
        template="ose/home.html"
        title="Online Spreadsheet Editing"
        activeItem="Home"
        html=self.render_template(template, title=title,activeItem=activeItem)
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
        activeItem=""   
        html=self.render_template(template, dictList=dictList,lodKeys=lodKeys,tableHeaders=lodKeys,title=title, activeItem=activeItem)
        return html
    
    def wikiEdit(self,editConfigName:str=None):
        '''
        wikiEdit
        '''
        title='Multipage Wiki Editing'
        template="ose/wikiedit.html"
        activeItem="Wiki Edit"
        editForm=WikiEditForm()
        wikiChoices=[]
        for wikiUser in sorted(self.wikiUsers):
            wikiChoices.append((wikiUser,wikiUser)) 
        editForm.sourceWiki.choices=wikiChoices    
        editForm.targetWiki.choices=wikiChoices
        if editConfigName is not None and (not editForm.validate_on_submit() or editForm.addQueryButton.data):
            if editConfigName in self.editConfigurationManager.editConfigs:
                editConfig=self.editConfigurationManager.editConfigs[editConfigName]
                editForm.fromEditConfig(editConfig)
            else:
                flash(f"unknown edit configuration {editConfigName}","warn")
        # submitted
        if editForm.validate_on_submit():
            editForm.deleteQuery()
            # check which button was pressed
            if editForm.save.data:
                editConfig=editForm.toEditConfig()
                self.editConfigurationManager.add(editConfig)
                self.editConfigurationManager.save()
                flash(f"{editConfig.name} saved","info")
            elif editForm.addQueryButton.data:
                editForm.addQuery()
            elif editForm.download.data:
                editConfig=editForm.toEditConfig()
                tq=editConfig.toTableQuery()
                flash("retrieving data ...","info")
                tq.fetchQueryResults()
                # TODO: Add option to apply enhancers and show progreess
                # show download result
                spreadsheet=tq.tableEditing.toSpreadSheet(SpreadSheetType.EXCEL, name=editConfig.name)
                return send_file(path_or_file=spreadsheet.toBytesIO(), mimetype=spreadsheet.MIME_TYPE)
            else:
                pass
        else:
            pass
        html=self.render_template(template, title=title, activeItem=activeItem,editForm=editForm)
        return html
           
    def getMenu(self,activeItem:str=None):
        '''
        get the list of menu items for the admin menu
        Args:
            activeItem(str): the active  menu item
        Return:
            list: the list of menu items
        '''
        menu=Menu()
        #self.basedUrl(url_for(
        menu.addItem(MenuItem("/","Home",mdiIcon="home"))
        menu.addItem(MenuItem("/wikiedit","Wiki Edit",mdiIcon="settings_suggest"))
        menu.addItem(MenuItem("/editconfigs","Edit configurations",mdiIcon="settings"))
        menu.addItem(MenuItem('https://wiki.bitplan.com/index.php/pyOnlineSpreadSheetEditing',"Docs",mdiIcon="description",newTab=True)),
        menu.addItem(MenuItem('https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing','github',mdiIcon="reviews",newTab=True))
        if current_user.is_anonymous:
            menu.addItem(MenuItem('/login','login',mdiIcon="login"))
        else:
            menu.addItem(MenuItem('/logout','logout',mdiIcon="logout"))
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

class QueryForm(FlaskForm):
    """
    query form for entering one named query
    """
    remove=SubmitField("remove")
    name=StringField("name", render_kw={"rows": 3, "cols": 80})
    query=TextAreaField('query', render_kw={"rows": 3, "cols": 80})

class WikiEditForm(FlaskForm):
    '''
    upload form
    '''
    download=SubmitField('download')
    save=SubmitField('save')
    name=StringField('name')
    sourceWiki=SelectField('source Wiki')
    targetWiki=SelectField('target Wiki')
    addQueryButton = SubmitField("addQuery")
    # In FieldLists the serial name for its items is generated with the short_name,seperator and index of FieldList
    # (short_name=name and can not be set manually)
    # thus we set the name of the field to singular and the label to plural
    queries = FieldList(FormField(QueryForm), min_entries=1, label="Queries", name="Query")
    format=SelectField('format',choices=SpreadSheetType.asSelectFieldChoices())

    def addQuery(self, name:str=None, query:str=None) -> int:
        """
        add a new query field

        Args:
            name(str): name of the query
            query(str): the query

        Returns:
            Number of query in the form (index)
        """
        n=len(self.queries.entries)
        if name is None:
            name=f"query{n}"
        data={
            "name": name,
            "query": query
        }
        self.queries.append_entry(data)
        return n

    def deleteQuery(self):
        """
        Delete the selected query.
        """
        delQueryIndex=None
        if len(self.queries.entries)<=self.queries.min_entries:
            flash(f"Can not delete Query at least {self.queries.min_entries} {'Query is' if self.queries.min_entries == 1 else 'Queries are'} required", category="info")
            return
        for i, entry in enumerate(self.queries.entries):
            if entry.data['remove']:
                delQueryIndex=i
                break
        if delQueryIndex is not None:
            self.queries.entries.pop(delQueryIndex)

    def toEditConfig(self):
        '''
        convert my data to an edit configuration
        
        view to model conversion
        '''
        editConfig=EditConfig(self.name.data)
        editConfig.sourceWikiId=self.sourceWiki.data
        editConfig.targetWikiId=self.targetWiki.data
        for queryRecord in self.queries.entries:
            editConfig.addQuery(queryRecord.data.get("name"), queryRecord.data.get("query"))
        editConfig.format=self.format.data
        return editConfig
    
    def fromEditConfig(self,editConfig:EditConfig):
        '''
        update the view from the model

        Args:
            editConfig(EditConfig): edit config to load the form from
        '''
        self.name.data=editConfig.name
        self.sourceWiki.data=editConfig.sourceWikiId
        self.targetWiki.data=editConfig.targetWikiId
        # reset queries in form
        for i in range(len(self.queries)):
            self.queries.pop_entry()
        # load queries from config
        for name, query in editConfig.queries.items():
            self.addQuery(name=name, query=query)
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