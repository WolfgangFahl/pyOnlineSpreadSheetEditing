from fb4.app import AppWrap
from fb4.sse_bp import SSE_BluePrint
from fb4.widgets import Copyright, Link,Menu, MenuItem
from wtforms import StringField, SelectField, SubmitField, TextAreaField, FieldList, FormField, widgets
#from wtforms.validators import InputRequired
from flask import abort,redirect,render_template, flash,request, url_for, send_file, Response
from flask_wtf import FlaskForm
from wikibot.wikiuser import WikiUser
from fb4.sqldb import db
from fb4.login_bp import login_user
from flask_login import current_user, login_required
import json
import socket
import os
import sys


from onlinespreadsheet.loginBlueprint import LoginBluePrint
from onlinespreadsheet.profile import ProfileBlueprint
from onlinespreadsheet.spreadsheet import SpreadSheetType
from onlinespreadsheet.editconfig import EditConfig, EditConfigManager
from onlinespreadsheet.propertySelector import PropertySelectorForm
from onlinespreadsheet.pareto import Pareto
from lodstorage.trulytabular import TrulyTabular, WikidataItem
from lodstorage.sparql import SPARQL
from lodstorage.query import EndpointManager, QuerySyntaxHighlight

import traceback
from werkzeug.exceptions import HTTPException

class WebServer(AppWrap):
    """
    Open Source Online Spreasheet Editing Service
    """

    def __init__(self, host=None, port=8559, editConfigPath:str=None,withUsers=True,verbose=True, debug=False):
        '''
        constructor

        Args:
            host(str): flask host
            port(int): the port to use for http connections
            editConfigPath(str): the path to load the edit and query configurations from
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
        self.sseBluePrint = SSE_BluePrint(self.app,'sse',appWrap=self)
        
        #  server specific initializations
        link=Link("http://www.bitplan.com/Wolfgang_Fahl",title="Wolfgang Fahl")
        self.copyRight=Copyright(period="2021-2022",link=link)
        
        self.wikiUsers=WikiUser.getWikiUsers()

        # add BluePrints
        self.loginBluePrint=LoginBluePrint(self.app,'login',welcome="home", appWrap=self)
        self.profileBluePrint=ProfileBlueprint(self.app, "profile", template_folder="profile", appWrap=self)
        self.withUsers = withUsers
        self.editConfigPath = editConfigPath
        self.editConfigurationManager = EditConfigManager(self.editConfigPath)
        self.editConfigurationManager.load()
        # get endpoints
        self.endpoints=EndpointManager.getEndpoints()
        self.autoLoginUser=None

        @self.app.route('/')
        def home():
            return self.homePage()
        
        @self.app.route('/editconfigs')
        @login_required
        def editConfigs():
            return self.showEditConfigs()
        
        @self.app.route('/download/<editConfigName>')
        def download(editConfigName:str):
            return self.download4EditConfigName(editConfigName)

        @self.app.route('/wikiedit',methods=['GET', 'POST'])
        @login_required
        def wikiEditNone():
            return self.wikiEdit(editConfigName=None)
      
        @self.app.route('/wikiedit/<editConfigName>',methods=['GET', 'POST'])
        @login_required
        def wikiEdit(editConfigName:str):
            return self.wikiEdit(editConfigName)
        
        @self.app.route('/tt/<itemId>',methods=['GET', 'POST'])
        def wikiTrulyTabular(itemId:str):
            return self.wikiTrulyTabular(itemId)
        
        @self.app.route('/trulytabular',methods=['GET', 'POST'])
        def wikiTrulyTabularWithForm():
            return self.wikiTrulyTabularWithForm()
        
        @self.app.route('/testPropertySelector')
        def testPropertySelector():
            return self.testPropertySelector()
        
        #
        # setup global handlers
        #
        @self.app.before_first_request
        def before_first_request_func():
            loginMenu=self.getMenu("Login")
            # self.loginBluePrint.setLoginArgs(menu=loginMenu)
            # auto login
            if self.autoLoginUser is not None:
                login_user(self.autoLoginUser, remember=True)
        
        @self.app.errorhandler(Exception)
        def handle_exception(e):
            # pass through HTTP errors
            if isinstance(e, HTTPException):
                return e
            traceMessage = traceback.format_exc()
            # to the server log
            print(traceMessage)
            if self.debug:
                errorMessage=f"{traceMessage}"
            else:    
                errorMessage=f"A server error occurred - see log for trace"
            
            return self.handleError(errorMessage)

    def run(self,args):
        '''
        Override web server start
        '''
        if self.withUsers:
            self.initUsers(user=args.user)
        super().run(args)

    def handleError(self,errorMessage,level="error"):   
        '''
        handle the error with the given error Message
        '''     
        flash(errorMessage,level)
        # now you're handling non-HTTP exceptions only
        html=self.render_template("ose/generic500.html", title="Error", activeItem="Home", error=errorMessage)
        return html
     
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
            editForm.handleQueryDelete()
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
                flash(f"{editConfig.name} downloaded","info")
                return self.download4EditConfig(editConfig)
        else:
            pass
        html=self.render_template(template, title=title, activeItem=activeItem,editForm=editForm)
        return html

    def download4EditConfig(self,editConfig):
        '''
        start a download for the given edit configuration

        Args:
            editConfig(EditConfig): the edit configuration

        Returns:
            the download via send_file

        '''
        tq=editConfig.toTableQuery()
        tq.fetchQueryResults()
        # TODO: Add option to apply enhancers and show progress
        # show download result
        spreadsheet=tq.tableEditing.toSpreadSheet(SpreadSheetType.EXCEL, name=editConfig.name)
        return self.downloadSpreadSheet(spreadsheet)

    def download4EditConfigName(self,editConfigName:str):
        '''
        start a download for the given edit configuration name

        Args:
            editConfigName(str): the edit configuration

        '''
        if editConfigName in self.editConfigurationManager.editConfigs:
            editConfig=self.editConfigurationManager.editConfigs[editConfigName]
            return self.download4EditConfig(editConfig)
        else:
            return abort(400,f"invalid edit configuration {editConfigName}")

    def downloadSpreadSheet(self,spreadsheet):
        '''
        download the given spreadsheet

        Args:
            spreadsheet(SpreadhSheet): the spreadsheet to download
        '''
        # https://stackoverflow.com/a/53666642/1497139
        sDownload=send_file(path_or_file=spreadsheet.toBytesIO(), as_attachment=True,download_name=spreadsheet.filename,mimetype=spreadsheet.MIME_TYPE)
        return sDownload
           
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
        menu.addItem(MenuItem("/trulytabular","Truly Tabular"))
        menu.addItem(MenuItem('https://wiki.bitplan.com/index.php/pyOnlineSpreadSheetEditing',"Docs",mdiIcon="description",newTab=True))
        menu.addItem(MenuItem('https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing','github',newTab=True))
        if current_user.is_anonymous:
            menu.addItem(MenuItem('/login','login',mdiIcon="login"))
        else:
            menu.addItem(MenuItem('/users', 'users', mdiIcon="people"))  # ToDo: add required role
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
        
    def initUsers(self,user=None,withDBCreate=True):
        '''
        initialize my users
        '''
        if withDBCreate:
            self.db.drop_all()
            self.db.create_all()
        wusers=WikiUser.getWikiUsers()
        userCount=len(wusers)
        if user is not None:
            userCount=1
        self.log(f"Initializing {userCount} users ...")
        for userid,wuser in enumerate(wusers.values()):
            username=self.getUserNameForWikiUser(wuser)
            doAdd=True
            if user is not None:
                doAdd=user==wuser.wikiId
                #print(f"'{user}'=='{wuser.wikiId}'? {doAdd}")
            if doAdd:
                try:
                    loginUser=self.loginBluePrint.addUser(username,wuser.getPassword(),username=userid)
                except Exception as e:
                    if "User already exists" in str(e):
                        print(f"User: {username} already exists")
                        loginUser=self.loginBluePrint.userManager.getUser(username)
                    else:
                        raise e
                if user is not None:
                    self.autoLoginUser=loginUser
    
    def testPropertySelector(self):
        jsonText="""[{
  "prop": "http://www.wikidata.org/entity/P31",
  "propLabel": "instance of",
  "count": 7539
}, {
  "prop": "http://www.wikidata.org/entity/P276",
  "propLabel": "location",
  "count": 7245
}, {
  "prop": "http://www.wikidata.org/entity/P179",
  "propLabel": "part of the series",
  "count": 7197
}, {
  "prop": "http://www.wikidata.org/entity/P17",
  "propLabel": "country",
  "count": 7143
}, {
  "prop": "http://www.wikidata.org/entity/P580",
  "propLabel": "start time",
  "count": 6942
}, {
  "prop": "http://www.wikidata.org/entity/P582",
  "propLabel": "end time",
  "count": 6938
}, {
  "prop": "http://www.wikidata.org/entity/P1813",
  "propLabel": "short name",
  "count": 6752
}, {
  "prop": "http://www.wikidata.org/entity/P1476",
  "propLabel": "title",
  "count": 6735
}, {
  "prop": "http://www.wikidata.org/entity/P973",
  "propLabel": "described at URL",
  "count": 6513
}, {
  "prop": "http://www.wikidata.org/entity/P227",
  "propLabel": "GND ID",
  "count": 3084
}, {
  "prop": "http://www.wikidata.org/entity/P214",
  "propLabel": "VIAF ID",
  "count": 2131
}, {
  "prop": "http://www.wikidata.org/entity/P921",
  "propLabel": "main subject",
  "count": 1899
}, {
  "prop": "http://www.wikidata.org/entity/P664",
  "propLabel": "organizer",
  "count": 1835
}, {
  "prop": "http://www.wikidata.org/entity/P856",
  "propLabel": "official website",
  "count": 606
}, {
  "prop": "http://www.wikidata.org/entity/P244",
  "propLabel": "Library of Congress authority ID",
  "count": 506
}, {
  "prop": "http://www.wikidata.org/entity/P585",
  "propLabel": "point in time",
  "count": 439
}, {
  "prop": "http://www.wikidata.org/entity/P823",
  "propLabel": "speaker",
  "count": 282
}, {
  "prop": "http://www.wikidata.org/entity/P710",
  "propLabel": "participant",
  "count": 123
}, {
  "prop": "http://www.wikidata.org/entity/P131",
  "propLabel": "located in the administrative territorial entity",
  "count": 119
}, {
  "prop": "http://www.wikidata.org/entity/P5124",
  "propLabel": "WikiCFP event ID",
  "count": 98
}, {
  "prop": "http://www.wikidata.org/entity/P2936",
  "propLabel": "language used",
  "count": 89
}, {
  "prop": "http://www.wikidata.org/entity/P793",
  "propLabel": "significant event",
  "count": 82
}, {
  "prop": "http://www.wikidata.org/entity/P361",
  "propLabel": "part of",
  "count": 67
}]"""
        propertyList=json.loads(jsonText)
        paretoLevels=[]
        topLevel=9
        for level in range(1,topLevel+1):
            pareto=Pareto(level)
            paretoLevels.append(pareto)
        psForm=PropertySelectorForm()
        psForm.setPropertyList(propertyList,total=7539,paretoLevels=paretoLevels)
        title='Truly Tabular Wikidata Item Query'
        template="ose/ps.html"
        activeItem="Truly Tabular"
        html=self.render_template(template, title=title, activeItem=activeItem,psForm=psForm)
        return html
        
                    
    def setInputDisabled(self,inputField,disabled:bool=True):
        '''
        disable the given input
        
        Args:
            inputField(Input): the WTForms input to disable
            disabled(bool): if true set the disabled attribute of the input 
        '''
        if inputField.render_kw is None:
            inputField.render_kw={}
        if disabled:
            inputField.render_kw["disabled"]= "disabled"
        else:
            inputField.render_kw.pop("disabled")
            
    def setRenderKw(self,inputField,key,value):
        '''
        set a render keyword dict entry for the given input field with the given key and value
        
        Args:
            inputField(Input): the field to modify
            key(str): the key to use
            value(str): the value to set
        '''
        if inputField.render_kw is None:
            inputField.render_kw={}
        inputField.render_kw[key]=value
        
    def enableButtonsOnInput(self,buttons:list,inputField):
        '''
        enable the given list of buttons on input in the given inputField
        
        Args:
            inputField(Input): the inputField to set the input trigger
            buttons(list): the list of buttons to enable
        '''
        script=""
        for button in buttons:
            script+=f"document.getElementById('{button.id}').disabled = false;"
        self.setRenderKw(inputField,"oninput",script)
            
    
    def wikiTrulyTabular(self,itemId:str):
        '''
        handle the truly tabular processing for the given itemId
        '''
        return self.wikiTrulyTabularWithForm(itemId)
    
    def getResponseFormat(self):
        responseFormat=request.args.get('format')
        if responseFormat is None:
            responseFormat="html"
            # handle content negotiation
            acceptJson=request.accept_mimetypes['application/json'] 
            if acceptJson==1: responseFormat="json"
        return responseFormat

    def wikiTrulyTabularWithForm(self,itemId:str=None):
        '''
        handle the truly tabular form
        '''
        responseFormat=self.getResponseFormat()
        ttForm=TrulyTabularForm()
        ttForm.setEndpointChoices(self.endpoints)
        ttForm.setLanguageChoices()
        for button in [ttForm.instancesButton,ttForm.propertiesButton,ttForm.idButton,ttForm.labelButton,ttForm.clearButton]:
            self.setInputDisabled(button)
        self.enableButtonsOnInput([ttForm.idButton,ttForm.clearButton],ttForm.itemLabel)
        self.enableButtonsOnInput([ttForm.labelButton,ttForm.clearButton,ttForm.instancesButton], ttForm.itemId)
        self.enableButtonsOnInput([ttForm.propertiesButton], ttForm.itemCount)
        psForm=PropertySelectorForm()
        paretoLevels=psForm.setParetoChoices()
        queryHigh=None
        qlod=None
        lodKeys=None
        tryItLink=None
        autoFill=itemId is not None
        if psForm.validate_on_submit():
            if psForm.tabularButton.data:
                flash("tabular analysis not implemented yet!")
        if ttForm.validate_on_submit() or autoFill:
            lang=ttForm.languageSelect.data
            self.setInputDisabled(ttForm.clearButton,False)
            if ttForm.clearButton.data:
                return redirect(url_for('wikiTrulyTabularWithForm'))
            endpoint=self.endpoints[ttForm.endpointName.data]
            # get id and description by label
            if ttForm.idButton.data:
                itemLabel=ttForm.itemLabel.data
                sparql=SPARQL(endpoint.endpoint,method=endpoint.method)
                items=WikidataItem.getItemsByLabel(sparql, itemLabel,lang=lang)
                if len(items)<1:
                    flash(f"no items found for {itemLabel}")
                else:
                    itemId=items[0].qid
                    ttForm.itemId.data=itemId
            elif itemId is None:
                # direct input of id from form
                itemId=ttForm.itemId.data
            else:
                # autofill the item id
                ttForm.itemId.data=itemId
            # if we have a wikidata item ID
            # we can start
            self.setInputDisabled(ttForm.instancesButton,itemId is None)
            if itemId is not None:
                tt=TrulyTabular(itemId,endpoint=endpoint.endpoint,method=endpoint.method,lang=lang)
                ttForm.itemLabel.data=tt.item.qlabel
                ttForm.itemDescription.data=tt.item.description
                if ttForm.instancesButton.data or autoFill:
                    count=tt.count()
                    ttForm.itemCount.data=count
                if ttForm.propertiesButton.data or autoFill:
                    query=tt.mostFrequentPropertiesQuery()    
                    qs=QuerySyntaxHighlight(query)
                    queryHigh=qs.highlight()
                    # TODO: configure via endpoint configuration
                    tryItUrl="https://query.wikidata.org/"
                    tryItUrlEncoded=query.getTryItUrl(tryItUrl)
                    tryItLink=Link(url=tryItUrlEncoded,title="try it!",tooltip="try out with wikidata query service")
                    qlod=tt.sparql.queryAsListOfDicts(query.query)
                    psForm.setPropertyList(qlod,int(ttForm.itemCount.data),paretoLevels)
            self.setInputDisabled(ttForm.propertiesButton,disabled=ttForm.itemCount.data is None)   
                 
        if responseFormat=="html":
            title='Truly Tabular Wikidata Item Query'
            template="ose/ttform.html"
            activeItem="Truly Tabular"
            html=self.render_template(template, title=title, activeItem=activeItem,ttForm=ttForm,psForm=psForm,queryHigh=queryHigh,tryItLink=tryItLink)
            return html
        elif responseFormat=="json":
            response = Response(status=200,mimetype='application/json')
            jsonText=json.dumps(qlod)
            response.set_data(jsonText)
            return response
                    
class TrulyTabularForm(FlaskForm):
    """
    Form to create a truly tabular analysis for a wikidata item
    """
    endpointName=SelectField('endpointName',default="wikidata")
    languageSelect=SelectField("language",default="en")
    itemId=StringField("id")
    itemLabel=StringField("label")
    itemDescription=StringField("description")
    itemCount=StringField("count")
    idButton=SubmitField("id")
    labelButton=SubmitField("label")
    instancesButton=SubmitField("count")
    propertiesButton=SubmitField("properties")
    clearButton=SubmitField("clear")
    
    def setLanguageChoices(self):
        self.languageSelect.choices=["en","es","de","fr","it"]

    def setEndpointChoices(self,endpoints):
        '''
        set my choices based on the given endpoints dict
        
        Args:
            endpoints(dict): a dictionary of endpoints
        
        '''
        self.endpointName.choices=list(endpoints.keys())
       

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

    def handleQueryDelete(self):
        """
        Delete the selected query.
        """
        delQueryIndex=None
        for i, entry in enumerate(self.queries.entries):
            if entry.data['remove']:
                if len(self.queries.entries) <= self.queries.min_entries:
                    qmin=self.queries.min_entries
                    msg=f"Can not delete Query at least {qmin} {'Query is' if qmin == 1 else 'Queries are'} required"
                    flash(msg, category="info")
                    return
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
        for _i in range(len(self.queries)):
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
    parser.add_argument('--user',help="run server with pre-logged in User access rights for the given user")
    args = parser.parse_args(_argv)
    web.optionalDebug(args)
    web.run(args)

if __name__ == '__main__':
    sys.exit(main())