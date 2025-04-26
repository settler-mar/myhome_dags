from datetime import datetime, timedelta, timezone
from typing import Optional, List, Union
from fastapi import Depends, HTTPException, FastAPI, status, Request, Response, Cookie
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette.datastructures import MutableHeaders
from typing import Annotated
import jwt
from jwt import PyJWTError, InvalidTokenError

from pydantic import BaseModel
from utils.configs import config
from utils.logs import log_print


class Token(BaseModel):
  access_token: str
  token_type: str


class TokenData(BaseModel):
  username: str | None = None


class User(BaseModel):
  id: int | None = -1
  username: str
  email: str | None = None
  full_name: str | None = None
  disabled: bool | None = None
  role: str | None = None


class UserInDB(User):
  password: str
  role: str


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
  return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
  return pwd_context.hash(password)


def get_user(username: str):
  from db_models.users import User
  from utils.db_utils import db_session
  with db_session() as db:
    user = db.query(User).filter(User.username == username).first()
  if user:
    return UserInDB(**user.__dict__)


def set_last_login(user_id: int):
  from db_models.users import User
  from utils.db_utils import db_session
  with db_session() as db:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
      user.set_last_login()
      db.commit()
  return user


def authenticate_user(username: str, password: str):
  user = get_user(username)
  if not user:
    return False
  if not verify_password(password, user.password):
    return False
  return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
  to_encode = data.copy()
  if expires_delta:
    expire = datetime.now(timezone.utc) + expires_delta
  else:
    expire = datetime.now(timezone.utc) + timedelta(minutes=15)
  to_encode.update({"exp": expire})
  encoded_jwt = jwt.encode(to_encode, config['auth']['secret_key'], algorithm=config['auth']['algorithm'])
  return encoded_jwt


def get_user_by_ip(ip: str):
  for subnet, role in config['auth'].get('role_by_ip').items():
    if ip.startswith(subnet):
      return User(username="guest", role=role)
  return None


async def get_current_user(request: Request, token: Annotated[str, Depends(oauth2_scheme)] = None):
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )
  try:
    if hasattr(request.state, 'current_user'):
      return request.state.current_user
    if token:
      payload = jwt.decode(token, config['auth']['secret_key'], algorithms=[config['auth']['algorithm']])
      username: str = payload.get("sub")
      if username is None:
        raise credentials_exception
    else:
      ip = request.client.host
      user = get_user_by_ip(ip)
      if user:
        return user
      raise credentials_exception
    token_data = TokenData(username=username)
  except InvalidTokenError:
    raise credentials_exception
  user = get_user(username=token_data.username)
  if user is None:
    raise credentials_exception
  return user


async def get_current_active_user(request: Request, current_user: Annotated[User, Depends(get_current_user)] = None):
  if current_user is None:
    ip = request.client.host
    current_user = get_user_by_ip(ip)
    if current_user is None:
      raise HTTPException(status_code=401, detail="Could not determine role by IP.")

  if current_user.disabled:
    raise HTTPException(status_code=400, detail="Inactive user")
  return current_user


CurrentUser = Annotated[User, Depends(get_current_active_user)]


def create_auth_route(app: FastAPI):
  @app.middleware("/api/*")
  async def add_role_by_ip(request: Request, call_next):
    if not 'authorization' in request.headers:
      if hasattr(request, 'cookies') and 'token' in request.cookies:
        new_header = MutableHeaders(request._headers)
        new_header['authorization'] = f'Bearer {request.cookies["token"]}'
        request._headers = new_header
        request.scope.update(headers=request.headers.raw)
      else:
        ip = request.client.host
        user = get_user_by_ip(ip)
        if user:
          new_header = MutableHeaders(request._headers)
          new_header['authorization'] = 'Bearer ' + create_access_token(data={"sub": user.username})
          request._headers = new_header
          request.scope.update(headers=request.headers.raw)

        request.state.current_user = user
    response = await call_next(request)
    return response

  @app.post("/token", tags=["auth"], response_model=Token)
  @app.post("/api/token", tags=["auth"], response_model=Token)
  async def login_for_access_token(
      form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
      response: Response) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
      raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
      )
    access_token_expires = timedelta(minutes=config['auth']['expire_minutes'])
    access_token = create_access_token(
      data={"sub": user.username}, expires_delta=access_token_expires
    )
    set_last_login(user.id)
    response.set_cookie(key='token', value=access_token, httponly=True)
    return Token(access_token=access_token, token_type="bearer")

  @app.get("/api/me/", tags=["auth"], dependencies=[Depends(RoleChecker())])
  async def read_users_me(current_user: CurrentUser):
    return current_user

  @app.get("/api/structure/", tags=["structure"], dependencies=[Depends(RoleChecker('admin'))])
  async def grt_structure_list():
    url_list = [{
      "path": route.path,
      "name": route.name
    } for route in app.routes if '/structure/' in route.path and not route.path.endswith('/structure/')]
    return url_list


def set_func_name(name):
  def decorator(func):
    func.__name__ = name
    return func

  return decorator


class RoleChecker:
  def __init__(self, allowed_roles: Union[List, str, bool] = True, is_test: bool = False):
    self.is_test = is_test
    if isinstance(allowed_roles, str):
      allowed_roles = [allowed_roles]
    if isinstance(allowed_roles, List):
      if 'user' in allowed_roles:
        allowed_roles.append('admin')
      if 'admin' in allowed_roles:
        allowed_roles.append('root')
    self.allowed_roles = allowed_roles

  def __call__(self, current_user: CurrentUser):
    if self.allowed_roles is True:
      return True
    if self.allowed_roles is False or current_user is None:
      if self.is_test:
        return False
      raise HTTPException(status_code=403, detail="You have not a permission to perform action.")

    if current_user.role in self.allowed_roles:
      return True
    if self.is_test:
      return False
    raise HTTPException(status_code=403, detail="You have not a permission to perform action.")
