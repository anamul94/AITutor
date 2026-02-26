import asyncio
import httpx

async def main():
    async with httpx.AsyncClient() as client:
        # Login
        try:
            res = await client.post("http://127.0.0.1:8000/auth/login", data={
                "username": "test456@example.com",
                "password": "password"
            })
            token = res.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            
            # Get lesson 72
            res = await client.get("http://127.0.0.1:8000/api/courses/lessons/72", headers=headers)
            print("Lesson Get:", res.status_code)
            print("Response:", res.text)
        except Exception as e:
            print("Error connecting to backend:", e)

asyncio.run(main())
