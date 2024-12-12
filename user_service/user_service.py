import os
import asyncio
import logging
from concurrent import futures
import grpc
from termcolor import colored
import motor.motor_asyncio
from passlib.context import CryptContext
import jwt
from user_pb2 import (
    CreateUserRequest,
    UserResponse,
    GetUserRequest,
    AuthRequest,
    AuthResponse
)
import user_pb2_grpc

logging.basicConfig(level=os.getenv('LOG_LEVEL', 'INFO'))
logger = logging.getLogger(os.getenv('SERVICE_NAME', 'USER_SERVICE'))

MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'userdb')

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key-keep-it-safe')

client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client[MONGODB_DB]
users_collection = db.users

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService(user_pb2_grpc.UserServiceServicer):
    async def CreateUser(self, request, context):
        try:
            logger.info(colored(f"Creating user with username: {request.username}", "cyan"))
            
            existing_user = await users_collection.find_one({"username": request.username})
            if existing_user:
                logger.error(colored(f"User {request.username} already exists", "red"))
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details('User already exists')
                return UserResponse()

            hashed_password = pwd_context.hash(request.password)
            
            user_doc = {
                "username": request.username,
                "email": request.email,
                "hashed_password": hashed_password
            }
            
            result = await users_collection.insert_one(user_doc)
            user_id = str(result.inserted_id)
            
            logger.info(colored(f"User created successfully with ID: {user_id}", "green"))
            
            return UserResponse(
                user_id=user_id,
                username=request.username,
                email=request.email
            )
        except Exception as e:
            logger.error(colored(f"Error creating user: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return UserResponse()

    async def GetUser(self, request, context):
        try:
            logger.info(colored(f"Getting user with ID: {request.user_id}", "cyan"))
            
            from bson import ObjectId
            user = await users_collection.find_one({"_id": ObjectId(request.user_id)})
            
            if user:
                logger.info(colored(f"User found: {user['username']}", "green"))
                return UserResponse(
                    user_id=str(user['_id']),
                    username=user['username'],
                    email=user['email']
                )
            else:
                logger.warning(colored(f"User not found with ID: {request.user_id}", "yellow"))
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details('User not found')
                return UserResponse()
        except Exception as e:
            logger.error(colored(f"Error getting user: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return UserResponse()

    async def AuthenticateUser(self, request, context):
        try:
            logger.info(colored(f"Authenticating user: {request.username}", "cyan"))
            
            user = await users_collection.find_one({"username": request.username})
            
            if not user or not pwd_context.verify(request.password, user['hashed_password']):
                logger.error(colored("Invalid credentials", "red"))
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details('Invalid credentials')
                return AuthResponse(success=False, token="", error="Invalid credentials")

            token = jwt.encode(
                {
                    'user_id': str(user['_id']),
                    'username': user['username']
                },
                JWT_SECRET_KEY,
                algorithm='HS256'
            )
            
            logger.info(colored(f"User authenticated successfully: {request.username}", "green"))
            return AuthResponse(success=True, token=token, error="")
            
        except Exception as e:
            logger.error(colored(f"Error authenticating user: {str(e)}", "red"))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal error occurred')
            return AuthResponse(success=False, token="", error=str(e))

async def serve():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    user_pb2_grpc.add_UserServiceServicer_to_server(UserService(), server)
    listen_addr = '[::]:50051'
    server.add_insecure_port(listen_addr)
    logger.info(colored(f"Starting server on {listen_addr}", "green"))
    await server.start()
    await server.wait_for_termination()

if __name__ == '__main__':
    logger.info(colored("User service starting...", "green"))
    asyncio.run(serve())
