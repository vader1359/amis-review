#!/usr/bin/env python3
"""Create/update the four fixed PSI accounts. Requires server-only Supabase env."""
from __future__ import annotations
import asyncio, os
import httpx
from dotenv import load_dotenv

load_dotenv()
URL=os.environ["SUPABASE_URL"].rstrip("/"); KEY=os.environ["SUPABASE_SERVICE_ROLE_KEY"]
USERS={"purchase":("Purchase","purchase"),"sale":("Sale","sale"),"accounting":("Accounting","accounting"),"tech":("Tech","tech")}

async def main():
  headers={"apikey":KEY,"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}
  async with httpx.AsyncClient(timeout=30) as client:
    for login,(display,team) in USERS.items():
      email=f"{login}@psi.nanohome.local"; user_id=None
      listing=await client.get(f"{URL}/auth/v1/admin/users",headers=headers,params={"page":1,"per_page":1000})
      listing.raise_for_status()
      for u in listing.json().get("users",[]):
        if u.get("email")==email: user_id=u["id"]
      body={"email":email,"password":"nanohome","email_confirm":True,"user_metadata":{"login_id":login}}
      if user_id:
        r=await client.put(f"{URL}/auth/v1/admin/users/{user_id}",headers=headers,json=body)
      else:
        r=await client.post(f"{URL}/auth/v1/admin/users",headers=headers,json=body)
      r.raise_for_status(); user_id=r.json()["id"]
      profile={"user_id":user_id,"login_id":login,"team":team,"display_name":display}
      r=await client.post(f"{URL}/rest/v1/psi_profiles?on_conflict=user_id",headers={**headers,"Prefer":"resolution=merge-duplicates"},json=profile); r.raise_for_status()
      print(f"ready {login} ({email})")

if __name__ == "__main__": asyncio.run(main())
