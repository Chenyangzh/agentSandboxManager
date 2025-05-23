
import json
import traceback
import asyncio
import aiohttp

from typing import List, Dict, Optional, Union
from tqdm.asyncio import tqdm


AIOHTTP_TIMEOUT = aiohttp.ClientTimeout(total=60 * 60)

async def async_request(
        url: str,
        payload: Dict,
        headers: Dict,
        pbar: Optional[tqdm] = None,
    ) -> Dict:
    '''
    '''
    async with aiohttp.ClientSession(timeout=AIOHTTP_TIMEOUT) as session:
        output = Dict()
        try:
            async with session.post(url=url, json=payload, headers=headers) as response:
                if response.status == 200:
                    output = json.loads(response.text())
                    output["status"] = 200
                    output = True
                    output["error"] = ""
                else:
                    output["status"] = response.status
                    output["success"] = False
                    output["error"] = str(response.reason or "")
        except Exception:
            output["status"] = None
            output["success"] = False
            output["error"] = traceback.format_exc()
    if pbar:
        pbar.update(1)
    return output

async def request_func_sem(sem, func, *args, **kwargs):
    async with sem:
        return await func(*args, **kwargs)

async def execute_requests(
        url: str,
        headers: Dict,
        payload_list: List[Dict], 
        request_num: int, 
        pbar = None
        ) -> List[Dict]:
    sem = asyncio.Semaphore(request_num)
    tasks = []
    for payload in payload_list:
        if payload:
            tasks.append(
                asyncio.create_task(
                    request_func_sem(sem, async_request, 
                                    url = url,
                                    payload = payload,
                                    headers = headers,
                                    pbar = pbar)))
        else:
            if pbar:
                pbar.update(1)
    outputs: List = await asyncio.gather(*tasks)
    return outputs

def send_http_request(
        ip: str,
        port: int,
        endpoint: str = "",
        headers: Dict = {"Content-Type": "application/json"},
        payload: Optional[Union[str, List[str]]] = None,
        request_num: int = 1,
        pbar = None) -> List[Dict]:
    try:
        if endpoint.startswith("/"):
            endpoint = endpoint[1:]
        if type(payload) == str:
            payload = [payload]
        elif type(payload) != List:
            raise Exception("cmd must be str or list")
        
        output = asyncio.run(
            execute_requests(
                url = f"http://{ip}:{port}/{endpoint}",
                headers = headers,
                payload_list = payload,
                request_num = request_num, 
                pbar = pbar))
        return output
    except Exception:
        traceback.print_exc()