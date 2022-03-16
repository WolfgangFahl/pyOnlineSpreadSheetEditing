from enum import Enum
from functools import wraps
from typing import List, Optional
from fb4.login_bp import LoginForm
from fb4.widgets import LodTable, Link
from flask import flash, url_for, Blueprint
from flask_login import LoginManager, logout_user, current_user, login_user, login_required, UserMixin
from flask_wtf import FlaskForm
from lodstorage.entity import EntityManager
from lodstorage.jsonable import JSONAble
from lodstorage.storageconfig import StorageConfig, StoreMode
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import redirect
from wtforms import EmailField, validators, StringField, PasswordField, SubmitField, SelectMultipleField, widgets
from wtforms.validators import InputRequired


class LoginBluePrint(object):
    '''
    a blueprint for logins
    '''

    def __init__(self, app, name: str, welcome: str = "index", template_folder: str = None, appWrap=None):
        '''
        construct me

        Args:
            name(str): my name
            welcome(str): the welcome page
            template_folder(str): the template folder
        '''
        self.name = name
        self.welcome = welcome
        if template_folder is not None:
            self.template_folder = template_folder
        else:
            self.template_folder = 'templates'
        self.blueprint = Blueprint(name, __name__, template_folder=self.template_folder)
        self.app = app
        self.appWrap=appWrap
        loginManager = LoginManager(app)
        self.loginManager = loginManager
        self.userManager=UserManager()
        self.hint = None
        app.register_blueprint(self.blueprint)

        @app.route('/login', methods=['GET', 'POST'])
        def login():
            return self.login()

        @app.route('/logout')
        @login_required
        def logout():
            return self.logOut()

        @app.route('/users')
        @login_required
        @self.roleRequired(role=Roles.ADMIN)
        def getAllUsers():
            return self.getAllUsers()

        @app.route('/users/new', methods=['GET', 'POST'])
        @login_required
        @self.roleRequired(role=Roles.ADMIN)
        def createUser():
            return self.createUser()

        @app.route('/users/<userId>', methods=['GET', 'POST'])
        @login_required
        @self.roleRequired(role=Roles.ADMIN)
        def editUser(userId:str):
            return self.editUser(userId)

        @loginManager.user_loader
        def load_user(userid):
            luser = self.userManager.getUser(userid)
            return luser

    def login(self):
        '''
        show the login form

        '''
        form = LoginForm()
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if form.validate_on_submit():
            user = self.userManager.getUser(form.username.data)
            if user is None or not user.checkPassword(form.password.data):
                flash('Invalid username or password')
                if self.hint is not None:
                    flash(self.hint)
                return redirect(url_for('login'))
            login_user(user, remember=form.rememberMe.data)
            return redirect(url_for(self.welcome))
        return self.appWrap.render_template('login.html',"login", "login", form=form)

    def logOut(self):
        '''
        logout the current user
        '''
        logout_user()
        return redirect(url_for(self.welcome))

    def getLoggedInUser(self):
        '''
        get the currently logged in user details
        '''
        # https://stackoverflow.com/a/19274791/1497139
        return current_user._get_current_object()

    def getAllUsers(self):
        '''
        get all users
        '''
        userRecords=self.userManager.getAll()
        # Todo: make users clickable
        for record in userRecords:
            record["edit"]=Link(url=f"/users/{record.get('id')}", title="edit")
        usersTable = LodTable(lod=userRecords, name="Users")
        return self.appWrap.render_template('users.html', "users", "users", users=usersTable)

    def createUser(self):
        form = CreateUserForm()
        if form.validate_on_submit():
            user = form.getUser()
            self.userManager.addUser(user)
            return redirect(url_for("users"))
        # ToDo: Propose Invitation email in response
        return self.appWrap.render_template('userForm.html', "createUser", "createUser", formTitle="Create new User", form=form)

    def editUser(self, userId):
        user=self.userManager.getUser(userId)
        form = EditUserForm()
        if form.validate_on_submit():
            user=form.getUser()
            self.userManager.updateUser(user)
            flash(f"Successfully updated the user {user.id}")
        else:
            form = EditUserForm(**user.getFormData())
        return self.appWrap.render_template('userForm.html', "editUser", "editUser", formTitle="Edit User", form=form)

    def roleRequired(self, role):
        """
        check if the current user has the required role
        """

        def decorator(func):
            @wraps(func)
            def decorated_view(*args, **kwargs):
                roles=current_user.roles
                if roles is None or role not in current_user.roles:
                    return self.loginManager.unauthorized()
                return func(*args, **kwargs)
            return decorated_view
        return decorator

    def addUser(self, id:str,password:str,username:str):
        """
        add User to db
        """
        user = User.getFromArgs(id=id, password=password, username=username)
        self.userManager.addUser(user)
        return user


class Roles(str, Enum):
    """
    roles which assign a user different access rights
    """
    ADMIN="admin"
    USER="user"

    @classmethod
    def choices(cls):
        return [(choice, choice.name) for choice in cls]

    @classmethod
    def coerce(cls, name):
        if isinstance(name, cls):
            # already coerced to instance of this enum
            return name
        try:
            return cls[name[len(f"{Roles.__name__}."):]]
        except KeyError:
            raise ValueError(name)


class User(JSONAble, UserMixin):
    """
    user
    """

    def __init__(self):
        super(User, self).__init__()
        self.active=True

    @property
    def roles(self) -> List[str]:
        if self._roles is not None and isinstance(self._roles, str):
            return [Roles[name] for name in self._roles.split(";")]

    @roles.setter
    def roles(self, roles:List[Roles]):
        self._roles = ';'.join([r.name for r in roles])

    @staticmethod
    def getSamples() -> List[dict]:
        samples = [
            {
                "id": "mail@example.org",
                "username": "Alice",
                "password_hash": "password".__hash__(),
                "wikidataid": "Q1",
                "_roles": "admin;user", # accessed over property role, separator char: ';'
                "active":False
            }
        ]
        return samples

    def setPassword(self, password:str):
        """
        sets the password of the user

        Args:
            password(str): new password
        """
        self.password_hash = generate_password_hash(password)

    def checkPassword(self, password:str):
        """
        check the password of the user

        Args:
            password(str): password to check
        """
        return check_password_hash(self.password_hash, password)

    def getWikidataRecords(self) -> dict:
        """
        Query user data from wikidata
        """
        pass

    def getFormData(self):
        """
        returns the user data as dict as required by FlaskForm
        e.g. password_hash is obmitted and roles are returned as List
        """
        records=self.__dict__
        if "password_hash" in records:
            del records["password_hash"]
        records["roles"]=self.roles
        return records

    def __repr__(self):
        return '<User {}>'.format(self.username)

    @staticmethod
    def getFromArgs(**kwargs):
        """
        Creates user from given arguments
        """
        u = User()
        if "password" in kwargs:
            if kwargs.get("password"):
                u.setPassword(kwargs["password"])
            del kwargs["password"]
        u.fromDict(kwargs)
        return u



class UserManager(EntityManager):
    """
    Manages the users
    """

    def __init__(self, storageConfig:StorageConfig=None):
        if storageConfig is None:
            storageConfig=UserManager.getDefaultStorageConfig()
        super().__init__(name="users",
                         clazz=User,
                         primaryKey="id",
                         tableName=User.__name__,
                         entityName="user",
                         entityPluralName="users",
                         config=storageConfig)
        if not self.isCached():
            self.config.getCachePath()
            self.initSQLDB(self.getSQLDB(self.getCacheFile()), withDrop=False, withCreate=True)

    def getUser(self, id:str) -> Optional[User]:
        """
        Retrieves the user records
        """
        db = self.getSQLDB(self.getCacheFile())
        res = db.query(f"SELECT * FROM {self.tableName} WHERE id == ?", params=(id, ))
        user = User()
        if isinstance(res, list) and res:
            user.fromDict(res[0])
        else:
            return None
        return user

    def updateUser(self, user:User):
        """
        update the given user

        Args:
            user(User): new user data
        """
        db = self.getSQLDB(self.getCacheFile())
        qparams = [(f"{k}=?", v) for k,v in user.__dict__.items()]
        vars = ', '.join([p[0] for p in qparams])
        params = [p[1] for p in qparams]
        db.c.execute(f"UPDATE {self.tableName} SET {vars} WHERE id == ?", (*params, user.id))
        db.c.commit()

    def addUser(self, user:User) -> bool:
        """
        Add the given user to the database

        Args:
            user(User): user to add

        Raises:

        """
        if self.getUser(user.id) is not None:
            raise Exception("User already exists")
        try:
            self.storeLoD([user.__dict__], cacheFile=self.getCacheFile(), append=True)
            return True
        except Exception as e:
            raise e

    def getAll(self) -> List[dict]:
        """
        Returns all users (without password hash)
        """
        db = self.getSQLDB(self.getCacheFile())
        users = db.query(f'SELECT id, username, wikidataid  FROM {self.tableName}')
        return users

    @staticmethod
    def getDefaultStorageConfig() -> StorageConfig:
        """
        Returns the default storageConfig

        Returns
            StorageConfig
        """
        config = StorageConfig(mode=StoreMode.SQL, cacheDirName="ose")
        return config


class ListWidget(widgets.ListWidget):

    def __call__(self, *args, **kwargs):
        del kwargs["class"]
        return super().__call__(*args, **kwargs)


class UserForm(FlaskForm):
    """
    User form to create and edit a user
    """
    id=EmailField('Email address', [validators.DataRequired()])
    username=StringField("Name", [InputRequired("Please enter a username")])
    wikidataid=StringField("Wikidata Id", [validators.Regexp('Q[1-9]\d*', message="Must be a valid  Wikidata Q identifier (Q43649390) ")])
    roles = SelectMultipleField("Role",
                                choices=Roles.choices(),
                                widget=ListWidget(prefix_label=False),
                                option_widget=widgets.CheckboxInput(),
                                coerce=Roles.coerce,
                                render_kw={"class_":""})   #ToDo: Change to ListField and checkboxes
    password=PasswordField("Password")


    def getUser(self)->User:
        """
        Returns the data of the form as user object
        """
        u = User.getFromArgs(id=self.id.data,
                             username=self.username.data,
                             wikidataid=self.wikidataid.data,
                             roles=self.roles.data,
                             password=self.password.data)
        return u


class CreateUserForm(UserForm):
    """
    User form to create and edit a user
    """
    password=PasswordField("Password", [InputRequired("Please enter a username")])
    create=SubmitField("Create")


class EditUserForm(UserForm):
    """
    User form to create and edit a user
    """
    save=SubmitField("Save")

