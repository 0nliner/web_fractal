import traceback
from fastapi import Request

from web_fractal.dtos import Context
from web_fractal.utils import serialize_fastapi_request


async def context_middleware(request: Request, call_next):
    client_ip = request.client.host
    request.state.context = Context(session_id=client_ip)
    response = await call_next(request)
    return response


async def my_exception_handler(request: Request, exc: Exception, logger_service):
    """
    использовать вместе с @app.exception_handler(Exception)
    """
    serialized_request = await serialize_fastapi_request(request)
    await logger_service.log([{
        f"is_error": True,
        **serialized_request,
        "err_class": exc.__class__.__name__,
        "traceback": traceback.format_exc(),        
    }])
