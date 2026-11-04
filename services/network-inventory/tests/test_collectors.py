import asyncio
import httpx
import pytest
from inventory.collectors import pages

def test_pagination_cannot_treat_missing_page_as_complete():
 count=0
 def handler(request):
  nonlocal count
  count+=1
  return httpx.Response(200,json={'totalCount':2,'data':[{'id':'a'}] if count==1 else []})
 async def run():
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
   with pytest.raises(ValueError,match='incomplete'):await pages(c,'https://example.invalid/list',{})
 asyncio.run(run())
def test_complete_pagination():
 def handler(request):
  offset=int(request.url.params['offset']);return httpx.Response(200,json={'totalCount':2,'data':[{'id':str(offset)}]})
 async def run():
  async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:return await pages(c,'https://example.invalid/list',{})
 assert len(asyncio.run(run()))==2
